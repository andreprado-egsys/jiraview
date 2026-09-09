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


def _build_jql(
    projetos: list[str],
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    jql_extra: Optional[str] = None,
    aberto_apenas: bool = False,
) -> str:
    parts = [f"project in ({', '.join(projetos)})"]
    if status:
        parts.append(f'status = "{status}"')
    if aberto_apenas:
        parts.append("resolution is EMPTY")
    if tipo:
        parts.append(f'issuetype = "{tipo}"')
    if jql_extra:
        parts.append(f"({jql_extra})")
    return " AND ".join(parts) + " ORDER BY updated DESC"


@router.get("/issues")
async def list_issues(
    estado: str,
    status_filter: Optional[str] = None,
    tipo: Optional[str] = None,
    jql: Optional[str] = None,
    abertas: bool = True,
    max_results: int = 50,
    user: TokenPayload = Depends(get_current_user),
):
    cfg = estado_por_sigla(estado)
    if not cfg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estado não configurado")
    if user.role == "viewer" and user.state != estado:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Fora do estado do usuário")

    q = _build_jql(cfg["projects"], status_filter, tipo, jql, abertas)
    issues = await JSM.search(q, max_results)
    # normaliza campos p/ frontend (colunas do painel)
    out = []
    for it in issues:
        f = it.get("fields", {})
        out.append({
            "tipo": (f.get("issuetype") or {}).get("name"),
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
async def dashboard(estado: str, user: TokenPayload = Depends(get_current_user)):
    """Métricas agregadas (cards estilo Jira Dashboard)."""
    cfg = estado_por_sigla(estado)
    if not cfg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estado não configurado")
    projetos = ", ".join(cfg["projects"])
    aberto = await JSM.search(f"project in ({projetos}) AND resolution is EMPTY", 100)
    por_status = {}
    for it in aberto:
        st = (it.get("fields", {}).get("status") or {}).get("name")
        por_status[st] = por_status.get(st, 0) + 1
    concluidas_7d = await JSM.search(
        f"project in ({projetos}) AND resolution is not EMPTY AND updated >= -7d", 100)
    return {
        "estado": cfg["display_name"],
        "projetos": cfg["projects"],
        "abertas": len(aberto),
        "em_andamento": len(await JSM.search(
            f"project in ({projetos}) AND resolution is EMPTY AND statusCategory = indeterminate", 100)),
        "por_status": por_status,
        "fechadas_7d": len(concluidas_7d),
    }


@router.get("/meta")
async def meta(estado: str, user: TokenPayload = Depends(get_current_user)):
    """Status e tipos disponíveis para os filtros do painel."""
    import json
    import httpx

    cfg = estado_por_sigla(estado)
    if not cfg:
        raise HTTPException(404, "Estado não configurado")
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
        # statuses do projeto principal
        r = await c.get("https://egsys.atlassian.net/rest/api/3/project/"
                        f"{cfg['projects'][0]}/statuses", headers=hdr)
        if r.status_code == 200:
            for it in r.json():
                for st in it.get("statuses", []):
                    statuses.append(st.get("name"))
    return {"statuses": sorted(set(statuses)), "tipos": sorted(set(tipos))}


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
async def charts(estado: str, user: TokenPayload = Depends(get_current_user)):
    """Agregados para os gráficos (barras, donut, prioridade, solicitante, tempo)."""
    from collections import Counter, defaultdict

    cfg = estado_por_sigla(estado)
    if not cfg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Estado não configurado")
    projetos = ", ".join(cfg["projects"])
    issues = await JSM.search(
        f"project in ({projetos}) AND resolution is EMPTY ORDER BY created DESC",
        100)
    por_status = Counter()
    por_prioridade = Counter()
    por_solicitante = Counter()
    por_dia = defaultdict(int)
    from datetime import datetime, timedelta
    hoje = datetime.now()
    for it in issues:
        f = it.get("fields", {})
        st = (f.get("status") or {}).get("name")
        por_status[st] += 1
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
        "por_dia": serie,
        "total": len(issues),
    }

