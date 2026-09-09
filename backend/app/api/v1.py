# egSYS JiraView — API: issues, dashboard (métricas), meta e filtros salvos do gestor
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.security import TokenPayload, get_current_user, jsm, require_role
from ..core.estados import estado_por_sigla
from ..core.filtros import FiltroRepo

router = APIRouter(prefix="/api/v1", tags=["jiraview"])

# Campos retornados na listagem (colunas da imagem: Referência, Resumo, Status,
# Solicitante, Prioridade, Data de Atualização, Data de Entrega, Tipo)
_FIELDS = "summary,status,priority,reporter,assignee,created,updated,duedate,issuetype,resolution"
JSM = jsm()


def _jql_janela(periodo: Optional[str] = None) -> str:
    """Periodo -> clausula de janela de criacao em JQL (dias; M deprecado no Cloud)."""
    if not periodo:
        return ""
    if periodo == "ano":
        return ' AND created >= "2026-01-01"'
    if periodo == "90d":
        return " AND created >= -90d"
    if periodo == "6m":
        return " AND created >= -180d"
    if periodo == "12m":
        return " AND created >= -365d"
    return ""


def _build_jql(
    projetos: list[str],
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    jql_extra: Optional[str] = None,
    aberto_apenas: bool = False,
    reporters: Optional[list[str]] = None,
    janela: str = "",
) -> str:
    parts = [f"project in ({', '.join(projetos)})"]
    if reporters:
        from ..core.estados import carregar_estados
        _accts = [c["accountId"] for c in reporters if c.get("accountId")]
        if _accts:
            parts.append(f"reporter in ({', '.join('\"' + a + '\"' for a in _accts)})")
    if status:
        parts.append(f'status = "{status}"')
    if aberto_apenas:
        parts.append("resolution is EMPTY")
    if tipo:
        parts.append(f'issuetype = "{tipo}"')
    if jql_extra:
        parts.append(f"({jql_extra})")
    return " AND ".join(parts) + janela + " ORDER BY updated DESC"


@router.get("/issues")
async def list_issues(
    estado: str,
    status_filter: Optional[str] = None,
    tipo: Optional[str] = None,
    origem: Optional[str] = None,
    jql: Optional[str] = None,
    abertas: bool = True,
    periodo: Optional[str] = None,
    max_results: int = 50,
    user: TokenPayload = Depends(get_current_user),
):
    cfg = estado_por_sigla(estado)
    if not cfg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estado não configurado")
    if user.role == "viewer" and user.state != estado:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Fora do estado do usuário")

    from ..core.estados import clientes_do_estado
    q = _build_jql(cfg["projects"], status_filter, tipo, jql, abertas,
                   reporters=clientes_do_estado(estado), janela=_jql_janela(periodo))
    issues = await JSM.search(q, max_results)
    if origem in ("cliente", "interno"):
        def _eh_origem(it):
            acct = str(((it.get("fields", {}).get("reporter") or {}).get("accountId") or ""))
            return acct.startswith("qm:")
        issues = [it for it in issues if _eh_origem(it) == (origem == "cliente")]
    # normaliza campos p/ frontend (colunas do painel)
    out = []
    for it in issues:
        f = it.get("fields", {})
        rep = f.get("reporter") or {}
        # Origem: cliente do portal = accountId "qm:" (Atlassian customer);
        # agente interno = "712020:" / conta do site. (Regra de negócio Alexandre)
        origem_da_issue = "cliente" if str(rep.get("accountId", "")).startswith("qm:") else "interno"
        out.append({
            "tipo": (f.get("issuetype") or {}).get("name"),
            "origem": origem_da_issue,
            "referencia": it.get("key"),
            "resumo": f.get("summary"),
            "status": (f.get("status") or {}).get("name"),
            "statusCategoria": (f.get("status") or {}).get("statusCategory", {}).get("key"),
            "solicitante": (f.get("reporter") or {}).get("displayName"),
            "responsavel": (f.get("assignee") or {}).get("displayName"),
            "prioridade": (f.get("priority") or {}).get("name"),
            "atualizacao": (f.get("updated") or "")[:10],
            "criacao": (f.get("created") or "")[:10],
            "entrega": (f.get("duedate") or None),
            "resolucao": (f.get("resolution") or {}).get("name"),
        })
    return {"issues": out, "total": len(out)}


@router.get("/dashboard")
async def dashboard(estado: str, periodo: Optional[str] = None, user: TokenPayload = Depends(get_current_user)):
    """Métricas agregadas (cards estilo Jira Dashboard)."""
    cfg = estado_por_sigla(estado)
    if not cfg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estado não configurado")
    projetos = ", ".join(cfg["projects"])

    async def _todos(pag_jql: str, cap: int = 2000) -> list:
        """Busca paginada (100/página) até esgotar, com cap de segurança."""
        out, start = [], 0
        while start < cap:
            chunk = await JSM.search(pag_jql, 100, start_at=start)
            out.extend(chunk)
            if len(chunk) < 100:
                break
            start += 100
        return out

    from ..core.estados import clientes_do_estado
    _rp = ", ".join('"'+c["accountId"]+'"' for c in clientes_do_estado(estado) if c.get("accountId"))
    _filtro_rp = f" AND reporter in ({_rp})" if _rp else ""
    # Janela do painel = últimos 90 dias (padrão de report do NOC; evita
    # contabilizar o histórico legado sem fim dos 4 responsáveis).
    todas = await _todos(f"project in ({projetos}){_filtro_rp}{_jql_janela(periodo)} ORDER BY created DESC")
    por_status, cat = {}, {"new": 0, "indeterminate": 0, "done": 0}
    por_origem = {"cliente_new": 0, "cliente_ind": 0, "cliente_done": 0,
                  "interno_new": 0, "interno_ind": 0, "interno_done": 0}
    por_tipo = {}
    concluidas_7d = 0
    from datetime import datetime, timedelta
    limite = datetime.now() - timedelta(days=7)
    for it in todas:
        f = it.get("fields", {})
        st = (f.get("status") or {}).get("name")
        key = (f.get("status") or {}).get("statusCategory", {}).get("key")
        por_status[st] = por_status.get(st, 0) + 1
        tp = (f.get("issuetype") or {}).get("name") or "?"
        por_tipo[tp] = por_tipo.get(tp, 0) + 1
        rep = (f.get("reporter") or {}).get("accountId") or ""
        origem_ab = "cliente" if str(rep).startswith("qm:") else "interno"
        chave = f"{origem_ab}_{key if key in ("new", "indeterminate", "done") else 'new'}"
        if chave in por_origem:
            por_origem[chave] += 1
        if key in cat:
            cat[key] += 1
        upd = (f.get("updated") or "")[:10]
        try:
            if datetime.fromisoformat(upd) >= limite and key == "done":
                concluidas_7d += 1
        except Exception:
            pass
    return {
        "estado": cfg["display_name"],
        "projetos": cfg["projects"],
        "abertas": cat["new"],                # cliente: o que está aguardando início
        "em_andamento": cat["indeterminate"],  # cliente: em andamento
        "fechadas_7d": concluidas_7d,
        "por_status": por_status,
        "por_origem": por_origem,
        "por_tipo": por_tipo,
        "total_geral": len(todas),
        "total_com_resolucao": cat["done"],
        "periodo": periodo or "tudo",
    }


@router.get("/meta")
async def meta(estado: str, user: TokenPayload = Depends(get_current_user)):
    """Status e tipos disponíveis para os filtros do painel."""
    import json
    import httpx

    cfg = estado_por_sigla(estado)
    if not cfg:
        raise HTTPException(404, "Estado não configurado")
    projetos = ", ".join(cfg["projects"])
    statuses = []
    tipos = []
    hdr = JSM._basic()
    async with httpx.AsyncClient() as c:
        # tipos
        for p in cfg["projects"]:
            r = await c.get(f"https://egsys.atlassian.net/rest/api/3/issue/createmeta",
                            params={"projectKeys": p}, headers=hdr)
            if r.status_code == 200:
                data = r.json()
                for proj in data.get("projects", []):
                    for it in proj.get("issuetypes", []):
                        tipos.append(it.get("name"))
        # statuses do projeto principal (workflow completo)
        r = await c.get("https://egsys.atlassian.net/rest/api/3/project/"
                        f"{cfg['projects'][0]}/statuses", headers=hdr)
        if r.status_code == 200:
            for it in r.json():
                for st in it.get("statuses", []):
                    statuses.append(st.get("name"))
    statuses = sorted(set(statuses))
    # contagem real por status (issues do estado, independente de resolução)
    contagem = {}
    try:
        issues_all = await JSM.search(
            f"project in ({projetos}) ORDER BY created DESC", 100)
        for it in issues_all:
            st = (it.get("fields", {}).get("status") or {}).get("name")
            contagem[st] = contagem.get(st, 0) + 1
    except Exception:
        pass
    statuses_info = [{"name": s, "tickets": contagem.get(s, 0)} for s in statuses]
    return {"statuses": statuses_info, "tipos": sorted(set(tipos))}


@router.get("/filtros")
async def list_filtros(estado: str, user: TokenPayload = Depends(get_current_user)):
    return {"filtros": FiltroRepo().listar(user.sub, estado)}


@router.post("/filtros")
async def salvar_filtro(estado: str, filtro: dict,
                        user: TokenPayload = Depends(require_role("manager"))):
    return FiltroRepo().salvar(user.sub, estado, filtro)


@router.delete("/filtros/{fid}")
async def apagar_filtro(estado: str, fid: str,
                        user: TokenPayload = Depends(require_role("manager"))):
    return FiltroRepo().apagar(user.sub, estado, fid)

@router.get("/charts")
async def charts(estado: str, periodo: Optional[str] = None, user: TokenPayload = Depends(get_current_user)):
    """Agregados para os gráficos (barras, donut, prioridade, solicitante, tempo)."""
    from collections import Counter, defaultdict

    cfg = estado_por_sigla(estado)
    if not cfg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estado não configurado")
    projetos = ", ".join(cfg["projects"])
    from ..core.estados import clientes_do_estado
    _rp = ", ".join('"'+c["accountId"]+'"' for c in clientes_do_estado(estado) if c.get("accountId"))
    _filtro_rp = f" AND reporter in ({_rp})" if _rp else ""
    issues = await JSM.search(
        f"project in ({projetos}){_filtro_rp}{_jql_janela(periodo)} ORDER BY created DESC",
        100)
    por_status = Counter()
    por_prioridade = Counter()
    por_solicitante = Counter()
    por_tipo = Counter()
    por_dia = defaultdict(int)
    from datetime import datetime, timedelta
    hoje = datetime.now()
    for it in issues:
        f = it.get("fields", {})
        st = (f.get("status") or {}).get("name")
        por_status[st] += 1
        por_tipo[(f.get("issuetype") or {}).get("name") or "?"] += 1
        por_prioridade[(f.get("priority") or {}).get("name") or "Sem prioridade"] += 1
        por_solicitante[(f.get("reporter") or {}).get("displayName") or "N/D"] += 1
        cr = f.get("created") or ""
        try:
            dia = datetime.fromisoformat(cr[:19]).date()
            por_dia[dia] += 1
        except Exception:
            pass
    # últimos 15 dias com contagem (0 nos vazios)
    serie = []
    for i in range(14, -1, -1):
        d = (hoje - timedelta(days=i)).date()
        serie.append({"dia": d.isoformat(), "count": por_dia[d]})
    return {
        "por_status": dict(por_status.most_common(15)),
        "por_prioridade": dict(por_prioridade.most_common()),
        "por_solicitante": dict(por_solicitante.most_common(6)),
        "por_tipo": dict(por_tipo.most_common()),
        "por_dia": serie,
        "total": len(issues),
    }

