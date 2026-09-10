# egSYS JiraView — API: issues, dashboard (métricas), meta e filtros salvos do gestor
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.security import TokenPayload, get_current_user, jsm, require_role
from ..core.estados import estado_por_sigla
from ..core.filtros import FiltroRepo

router = APIRouter(prefix="/api/v1", tags=["jiraview"])

# Campos retornados na listagem (colunas da imagem: Referência, Resumo, Status,
# Solicitante, Prioridade, Data de Atualização, Data de Entrega, Tipo, Componentes, Labels)
_FIELDS = "summary,status,priority,reporter,assignee,created,updated,duedate,issuetype,resolution,components,labels"
JSM = jsm()


def _detectar_area(fields: dict) -> str:
    """Classifica a área de atendimento (SADE, Cidadão, Integração, Operações)."""
    texto = " ".join([
        fields.get("summary") or "",
        " ".join(c.get("name", "") for c in fields.get("components") or []),
        " ".join(fields.get("labels") or []),
        (fields.get("issuetype") or {}).get("name") or "",
    ]).lower()

    if "cidad" in texto or "190" in texto or "mobile" in texto:
        return "Cidadão"
    if "integra" in texto or "api" in texto or "webservice" in texto or "barramento" in texto:
        return "Integração"
    if "sade" in texto or "despacho" in texto or "cad" in texto or "atendimento" in texto:
        return "SADE"
    return "Operações"


def _detectar_fase(status_nome: str, status_cat: str) -> dict:
    """Mapeia status do Jira para a régua canônica de 7 etapas e posse da bola."""
    st = (status_nome or "").lower()
    cat = (status_cat or "").lower()

    # 7. Concluído (Entregue)
    if cat == "done" or any(x in st for x in ("concluído", "concluido", "resolvido", "fechado", "done", "cancelado", "resolução", "desenvolvimento concluído")):
        return {"num": 7, "nome": "Concluído", "posse": "egsys", "label_posse": "Finalizado"}

    # 6. Validação / Homologação Cliente
    if any(x in st for x in ("homologa", "aguardando cliente", "validação cliente", "pendente cliente", "espera cliente", "aguardando informações", "aguardando resposta", "aguardando")):
        return {"num": 6, "nome": "Homologação Cliente", "posse": "cliente", "label_posse": "Ação com o Cliente"}

    # 5. Validação Interna / QA
    if any(x in st for x in ("validação interna", "validacao interna", "qa", "testes", "revisão", "revisao", "code review")):
        return {"num": 5, "nome": "Validação Interna / QA", "posse": "egsys", "label_posse": "Ação com egSYS"}

    # 4. Em Desenvolvimento
    if any(x in st for x in ("executando", "em desenvolvimento", "desenvolvimento em andamento", "em andamento")):
        return {"num": 4, "nome": "Em Desenvolvimento", "posse": "egsys", "label_posse": "Ação com egSYS"}

    # 3. Análise de Desenvolvimento
    if any(x in st for x in ("análise de desenvolvimento", "analise de desenvolvimento", "análise", "analise", "desenvolvimento")):
        return {"num": 3, "nome": "Análise de Dev", "posse": "egsys", "label_posse": "Ação com egSYS"}

    # 2. Triagem (N2)
    if "n2" in st or "validação n2" in st or "validacao n2" in st or "triagem n2" in st:
        return {"num": 2, "nome": "Triagem (N2)", "posse": "egsys", "label_posse": "Ação com egSYS"}

    # 1. Triagem (N1)
    if any(x in st for x in ("n1", "validação n1", "validacao n1", "triagem", "aberto", "novo")):
        return {"num": 1, "nome": "Triagem (N1)", "posse": "egsys", "label_posse": "Ação com egSYS"}

    if cat == "indeterminate":
        return {"num": 2, "nome": "Triagem (N2)", "posse": "egsys", "label_posse": "Ação com egSYS"}

    return {"num": 1, "nome": "Triagem (N1)", "posse": "egsys", "label_posse": "Ação com egSYS"}


def _jql_janela(periodo: Optional[str] = None) -> str:
    """Periodo -> clausula de janela de criacao em JQL (dias; M deprecado no Cloud)."""
    if not periodo:
        return ""
    if periodo == "ano":
        import datetime
        cur_year = datetime.date.today().year
        return f' AND created >= "{cur_year}-01-01"'
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
    funil_stage: Optional[str] = None,
) -> str:
    parts = [f"project in ({', '.join(projetos)})"]
    if reporters:
        from ..core.estados import carregar_estados
        _accts = [c["accountId"] for c in reporters if c.get("accountId")]
        if _accts:
            parts.append(f"reporter in ({', '.join('\"' + a + '\"' for a in _accts)})")
    if status:
        parts.append(f'status = "{status}"')
    
    # Tratamento semântico do Funil de Atendimento
    if funil_stage == "novas":
        parts.append('(statusCategory in ("To Do") OR status in ("Novo", "Aberto", "Backlog", "Triagem"))')
        parts.append("resolution is EMPTY")
    elif funil_stage == "em_atendimento":
        parts.append('(statusCategory in ("In Progress") AND status not in ("Aguardando Informações", "Aguardando Homologação", "Homologação", "Aguardando Cliente", "Validação Cliente", "Pendente"))')
        parts.append("resolution is EMPTY")
    elif funil_stage == "aguardando_validacao":
        parts.append('status in ("Aguardando Informações", "Aguardando Homologação", "Homologação", "Aguardando Cliente", "Validação Cliente", "Pendente")')
        parts.append("resolution is EMPTY")
    elif funil_stage == "concluidas":
        parts.append('(statusCategory in ("Done") OR resolution is not EMPTY)')
    elif aberto_apenas:
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
    posse_filter: Optional[str] = None,
    funil_stage: Optional[str] = None,
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
                   reporters=clientes_do_estado(estado), janela=_jql_janela(periodo),
                   funil_stage=funil_stage)
    issues = await JSM.search(q, max_results)
    if origem in ("cliente", "interno"):
        def _eh_origem(it):
            acct = str(((it.get("fields", {}).get("reporter") or {}).get("accountId") or ""))
            return acct.startswith("qm:")
        issues = [it for it in issues if _eh_origem(it) == (origem == "cliente")]
    # normaliza campos p/ frontend (colunas do painel + observabilidade)
    out = []
    for it in issues:
        f = it.get("fields", {})
        rep = f.get("reporter") or {}
        origem_da_issue = "cliente" if str(rep.get("accountId", "")).startswith("qm:") else "interno"
        st_nome = (f.get("status") or {}).get("name") or "Novo"
        st_cat = (f.get("status") or {}).get("statusCategory", {}).get("key") or "new"
        area = _detectar_area(f)
        fase_info = _detectar_fase(st_nome, st_cat)

        if posse_filter and fase_info["posse"] != posse_filter:
            continue

        out.append({
            "tipo": (f.get("issuetype") or {}).get("name"),
            "origem": origem_da_issue,
            "referencia": it.get("key"),
            "resumo": f.get("summary"),
            "status": st_nome,
            "statusCategoria": st_cat,
            "area": area,
            "faseNum": fase_info["num"],
            "faseNome": fase_info["nome"],
            "posse": fase_info["posse"],
            "posseLabel": fase_info["label_posse"],
            "solicitante": (f.get("reporter") or {}).get("displayName"),
            "responsavel": (f.get("assignee") or {}).get("displayName") or "Não atribuído",
            "prioridade": (f.get("priority") or {}).get("name") or "Normal",
            "atualizacao": (f.get("updated") or "")[:10],
            "criacao": (f.get("created") or "")[:10],
            "entrega": (f.get("duedate") or None),
            "resolucao": (f.get("resolution") or {}).get("name"),
        })
    return {"issues": out, "total": len(out)}


@router.get("/dashboard")
async def dashboard(estado: str, periodo: Optional[str] = None, user: TokenPayload = Depends(get_current_user)):
    """Métricas agregadas (funil de 4 estágios + cards estilo Jira Dashboard)."""
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
    todas = await _todos(f"project in ({projetos}){_filtro_rp}{_jql_janela(periodo)} ORDER BY created DESC")
    por_status, cat = {}, {"new": 0, "indeterminate": 0, "done": 0}
    funil = {"novas": 0, "em_atendimento": 0, "aguardando_validacao": 0, "concluidas": 0}
    por_origem = {"cliente_new": 0, "cliente_ind": 0, "cliente_done": 0,
                  "interno_new": 0, "interno_ind": 0, "interno_done": 0}
    por_tipo = {}
    concluidas_7d = 0
    from datetime import datetime, timedelta
    limite = datetime.now() - timedelta(days=7)
    for it in todas:
        f = it.get("fields", {})
        st = (f.get("status") or {}).get("name") or "Novo"
        key = (f.get("status") or {}).get("statusCategory", {}).get("key") or "new"
        por_status[st] = por_status.get(st, 0) + 1
        tp = (f.get("issuetype") or {}).get("name") or "?"
        por_tipo[tp] = por_tipo.get(tp, 0) + 1
        rep = (f.get("reporter") or {}).get("accountId") or ""
        origem_ab = "cliente" if str(rep).startswith("qm:") else "interno"
        chave = f"{origem_ab}_{key if key in ('new', 'indeterminate', 'done') else 'new'}"
        if chave in por_origem:
            por_origem[chave] += 1
        if key in cat:
            cat[key] += 1

        # Classificação do Funil de 4 Estágios
        fase_info = _detectar_fase(st, key)
        if key == "done" or fase_info["num"] == 7:
            funil["concluidas"] += 1
        elif fase_info["num"] == 6:
            funil["aguardando_validacao"] += 1
        elif fase_info["num"] in (2, 3, 4, 5):
            funil["em_atendimento"] += 1
        else:
            funil["novas"] += 1

        upd = (f.get("updated") or "")[:10]
        try:
            if datetime.fromisoformat(upd) >= limite and key == "done":
                concluidas_7d += 1
        except Exception:
            pass
    return {
        "estado": cfg["display_name"],
        "projetos": cfg["projects"],
        "funil": funil,
        "abertas": funil["novas"],               # 1. Novas / Não Tratadas
        "em_andamento": funil["em_atendimento"], # 2. Em Atendimento
        "aguardando_validacao": funil["aguardando_validacao"], # 3. Aguardando Validação
        "concluidas": funil["concluidas"],       # 4. Concluídas
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
    """Status e tipos disponíveis para os filtros do painel com contagem completa."""
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
            r = await c.get("https://egsys.atlassian.net/rest/api/3/issue/createmeta",
                            params={"projectKeys": p}, headers=hdr)
            if r.status_code == 200:
                data = r.json()
                for proj in data.get("projects", []):
                    for it in proj.get("issuetypes", []):
                        tipos.append(it.get("name"))
        # statuses do projeto principal (workflow completo)
        r = await c.get(f"https://egsys.atlassian.net/rest/api/3/project/{cfg['projects'][0]}/statuses", headers=hdr)
        if r.status_code == 200:
            for it in r.json():
                for st in it.get("statuses", []):
                    statuses.append(st.get("name"))
    statuses = sorted(set(statuses))
    
    # contagem real por status (issues do estado sem cap de 100)
    contagem = {}
    try:
        issues_all = await JSM.search(f"project in ({projetos}) ORDER BY created DESC", 1000)
        for it in issues_all:
            st = (it.get("fields", {}).get("status") or {}).get("name")
            if st:
                contagem[st] = contagem.get(st, 0) + 1
    except Exception:
        pass
    statuses_info = [{"name": s, "tickets": contagem.get(s, 0)} for s in statuses]
    return {"statuses": statuses_info, "tipos": sorted(set(tipos))}


def _traduzir_status_engenharia(st_nome: str) -> dict:
    """Traduz o status técnico de engenharia para linguagem executiva de negócio."""
    st = (st_nome or "").lower()
    if any(x in st for x in ("concluído", "concluido", "resolvido", "fechado", "done", "desenvolvimento concluído", "resolução")):
        return {"label": "✅ Concluído (Pronto p/ release)", "cor": "var(--green)"}
    if any(x in st for x in ("qa", "testes", "validação interna", "code review", "revisão")):
        return {"label": "🧪 Validação Interna & QA", "cor": "#a371f7"}
    if any(x in st for x in ("executando", "desenvolvimento", "andamento", "dev")):
        return {"label": "⚙️ Em Codificação Ativa", "cor": "var(--blue)"}
    if any(x in st for x in ("análise", "analise", "arquitetura", "especificação")):
        return {"label": "🔍 Em Análise Técnica / Arquitetura", "cor": "var(--blue)"}
    if any(x in st for x in ("homologa", "aguardando cliente", "aguardando informações")):
        return {"label": "🟡 Aguardando Validação", "cor": "var(--yellow)"}
    return {"label": "📋 Na Fila da Engenharia", "cor": "var(--text-sub)"}


@router.get("/issues/{key}/journey")
async def issue_journey(
    key: str,
    estado: str,
    user: TokenPayload = Depends(get_current_user),
):
    """Retorna a radiografia completa da jornada do ticket para a Gaveta Lateral (Drawer)."""
    import asyncio
    import httpx
    from datetime import datetime

    cfg = estado_por_sigla(estado)
    if not cfg:
        raise HTTPException(404, "Estado não configurado")
    if user.role == "viewer" and user.state != estado:
        raise HTTPException(403, "Fora do estado do usuário")

    hdr = JSM._basic()
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"https://egsys.atlassian.net/rest/api/3/issue/{key}?expand=changelog",
            headers=hdr,
        )
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"Não foi possível carregar o chamado {key}")
        data = r.json()

        f = data.get("fields", {})
        st_nome = (f.get("status") or {}).get("name") or "Novo"
        st_cat = (f.get("status") or {}).get("statusCategory", {}).get("key") or "new"
        fase_atual = _detectar_fase(st_nome, st_cat)
        area = _detectar_area(f)

        # Extrair vínculos e derivações de engenharia (issuelinks)
        links = f.get("issuelinks", [])
        linked_keys = []
        for l in links:
            item = l.get("outwardIssue") or l.get("inwardIssue")
            if item and item.get("key"):
                rel = l.get("type", {}).get("outward" if "outwardIssue" in l else "inward", "Vinculado")
                tipo_link = l.get("type", {}).get("name", "Relacionado")
                linked_keys.append((item.get("key"), rel, tipo_link, item))

        async def fetch_link_detail(k: str, rel: str, t_link: str, shallow_item: dict):
            try:
                r_det = await c.get(
                    f"https://egsys.atlassian.net/rest/api/3/issue/{k}?fields=summary,status,assignee,subtasks,issuetype,priority",
                    headers=hdr,
                    timeout=4.0,
                )
                if r_det.status_code == 200:
                    d_det = r_det.json()
                    f_det = d_det.get("fields", {})
                    st_l_nome = (f_det.get("status") or {}).get("name") or "Novo"
                    subtasks = f_det.get("subtasks", [])
                    sub_done = sum(1 for s in subtasks if (s.get("fields", {}).get("status", {}).get("statusCategory", {}).get("key") == "done"))
                    st_trad = _traduzir_status_engenharia(st_l_nome)
                    return {
                        "chave": k,
                        "resumo": f_det.get("summary") or "Sem descrição",
                        "tipo": (f_det.get("issuetype") or {}).get("name", "Tarefa"),
                        "status_raw": st_l_nome,
                        "status_executivo": st_trad["label"],
                        "status_cor": st_trad["cor"],
                        "responsavel": (f_det.get("assignee") or {}).get("displayName") or "Equipe de Engenharia",
                        "prioridade": (f_det.get("priority") or {}).get("name") or "Normal",
                        "relacao": rel,
                        "tipo_link": t_link,
                        "total_subtasks": len(subtasks),
                        "subtasks_concluidas": sub_done,
                    }
            except Exception:
                pass
            st_shallow = (shallow_item.get("fields", {}).get("status") or {}).get("name") or "Novo"
            st_trad = _traduzir_status_engenharia(st_shallow)
            return {
                "chave": k,
                "resumo": shallow_item.get("fields", {}).get("summary") or "Demanda vinculada",
                "tipo": (shallow_item.get("fields", {}).get("issuetype") or {}).get("name", "Tarefa"),
                "status_raw": st_shallow,
                "status_executivo": st_trad["label"],
                "status_cor": st_trad["cor"],
                "responsavel": "Equipe de Engenharia",
                "prioridade": (shallow_item.get("fields", {}).get("priority") or {}).get("name") or "Normal",
                "relacao": rel,
                "tipo_link": t_link,
                "total_subtasks": 0,
                "subtasks_concluidas": 0,
            }

        derivacoes = []
        if linked_keys:
            results = await asyncio.gather(*(fetch_link_detail(k, r_type, t, it) for k, r_type, t, it in linked_keys))
            derivacoes = [d for d in results if d]

    # Extrair histórico de transições de status do changelog
    transicoes = []
    last_status_change = None
    changelog = data.get("changelog", {}).get("histories", [])
    for h in changelog:
        autor = (h.get("author") or {}).get("displayName") or "Sistema"
        quando = h.get("created")
        for item in h.get("items", []):
            if item.get("field") == "status":
                de_st = item.get("fromString")
                para_st = item.get("toString")
                transicoes.append({
                    "de": de_st,
                    "para": para_st,
                    "quando": quando[:19].replace("T", " "),
                    "autor": autor,
                })
                if last_status_change is None:
                    last_status_change = quando

    if last_status_change is None:
        last_status_change = f.get("created")

    # Calcular tempos
    agora = datetime.now()
    tempo_etapa_str = "Recentemente"
    tempo_total_str = "Hoje"
    try:
        if last_status_change:
            dt_change = datetime.fromisoformat(last_status_change[:19])
            delta_etapa = agora - dt_change
            dias = delta_etapa.days
            horas = delta_etapa.seconds // 3600
            if dias > 0:
                tempo_etapa_str = f"{dias}d {horas}h"
            elif horas > 0:
                tempo_etapa_str = f"{horas}h"
            else:
                tempo_etapa_str = f"{max(1, delta_etapa.seconds // 60)}min"
    except Exception:
        pass

    try:
        created = f.get("created")
        if created:
            dt_created = datetime.fromisoformat(created[:19])
            delta_total = agora - dt_created
            dias_tot = delta_total.days
            tempo_total_str = f"{dias_tot} dias" if dias_tot > 0 else f"{delta_total.seconds // 3600}h"
    except Exception:
        pass

    # Montar Stepper de 7 Etapas
    etapas_nomes = [
        (1, "Triagem (N1)"),
        (2, "Triagem (N2)"),
        (3, "Análise de Desenvolvimento"),
        (4, "Em Desenvolvimento"),
        (5, "Validação Interna / QA"),
        (6, "Validação / Homologação Cliente"),
        (7, "Concluído (Entregue)"),
    ]
    etapas = []
    for num, nome_etapa in etapas_nomes:
        if num < fase_atual["num"]:
            estado_etapa = "concluido"
        elif num == fase_atual["num"]:
            estado_etapa = "ativo"
        else:
            estado_etapa = "pendente"
        etapas.append({
            "num": num,
            "nome": nome_etapa,
            "estado": estado_etapa,
        })

    rep = f.get("reporter") or {}
    origem_da_issue = "cliente" if str(rep.get("accountId", "")).startswith("qm:") else "interno"

    return {
        "referencia": key,
        "resumo": f.get("summary"),
        "status": st_nome,
        "statusCategoria": st_cat,
        "area": area,
        "tipo": (f.get("issuetype") or {}).get("name"),
        "origem": origem_da_issue,
        "solicitante": rep.get("displayName") or "N/D",
        "responsavel": (f.get("assignee") or {}).get("displayName") or "Não atribuído",
        "prioridade": (f.get("priority") or {}).get("name") or "Normal",
        "criacao": (f.get("created") or "")[:10],
        "atualizacao": (f.get("updated") or "")[:10],
        "entrega": (f.get("duedate") or None),
        "resolucao": (f.get("resolution") or {}).get("name"),
        "etapa_atual": fase_atual["num"],
        "etapas": etapas,
        "derivacoes_engenharia": derivacoes,
        "posse": {
            "tipo": fase_atual["posse"], # "egsys" | "cliente"
            "label": fase_atual["label_posse"],
            "responsavel": ((f.get("assignee") or {}).get("displayName") if fase_atual["posse"] == "egsys" else (rep.get("displayName") or "Cliente / Homologador")),
            "tempo_etapa": tempo_etapa_str,
            "tempo_total": tempo_total_str,
        },
        "transicoes": transicoes,
    }


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


