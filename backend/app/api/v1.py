# egSYS JiraView — API: issues, dashboard (métricas), meta e filtros salvos do gestor
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.security import TokenPayload, get_current_user, jsm, require_role
from ..core.estados import estado_por_sigla, projeto_em_estado
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
    """Mapeia status do Jira para a régua canônica de 8 etapas e posse da bola."""
    st = (status_nome or "").lower()
    cat = (status_cat or "").lower()

    # 8. Concluído (Entregue)
    if cat == "done" or any(x in st for x in ("concluído", "concluido", "resolvido", "fechado", "done", "cancelado")):
        return {"num": 8, "nome": "Concluído", "posse": "egsys", "label_posse": "Finalizado"}

    # 7. Validação / Homologação Cliente
    if any(x in st for x in ("homologa", "aguardando cliente", "validação cliente", "validacao cliente", "pendente cliente", "espera cliente", "aguardando informações", "aguardando resposta", "aguardando")):
        return {"num": 7, "nome": "Homologação Cliente", "posse": "cliente", "label_posse": "Ação com o Cliente"}

    # 6. Validação Interna (Suporte N1 / Atendimento)
    if any(x in st for x in ("validação n1", "validacao n1", "validação interna", "validacao interna", "resolução suporte", "resolucao suporte", "desenvolvimento concluído", "desenvolvimento concluido")):
        return {"num": 6, "nome": "Validação Interna (Suporte N1)", "posse": "egsys", "label_posse": "Ação com egSYS"}

    # 5. Testes de Qualidade (QA)
    if any(x in st for x in ("qa", "testes", "teste", "validação qa", "validacao qa", "revisão", "revisao", "code review", "homologação técnica")):
        return {"num": 5, "nome": "Testes de Qualidade (QA)", "posse": "egsys", "label_posse": "Ação com egSYS"}

    # 4. Em Desenvolvimento
    if any(x in st for x in ("executando", "em desenvolvimento", "desenvolvimento em andamento", "em andamento")):
        return {"num": 4, "nome": "Em Desenvolvimento", "posse": "egsys", "label_posse": "Ação com egSYS"}

    # 3. Análise de Desenvolvimento
    if any(x in st for x in ("análise de desenvolvimento", "analise de desenvolvimento", "análise", "analise", "desenvolvimento")):
        return {"num": 3, "nome": "Análise de Dev", "posse": "egsys", "label_posse": "Ação com egSYS"}

    # 2. Triagem (N2)
    if any(x in st for x in ("n2", "validação n2", "validacao n2", "triagem n2", "triagem (n2)", "suporte n2", "suporte avançado", "suporte avancado")):
        return {"num": 2, "nome": "Triagem (N2)", "posse": "egsys", "label_posse": "Ação com egSYS"}

    # 1. Triagem (N1)
    if any(x in st for x in ("n1", "triagem n1", "triagem", "aberto", "novo", "backlog")):
        return {"num": 1, "nome": "Triagem (N1)", "posse": "egsys", "label_posse": "Ação com egSYS"}

    if cat == "indeterminate":
        return {"num": 2, "nome": "Triagem (N2)", "posse": "egsys", "label_posse": "Ação com egSYS"}

    return {"num": 1, "nome": "Triagem (N1)", "posse": "egsys", "label_posse": "Ação com egSYS"}


def _jql_janela(periodo: Optional[str] = None) -> str:
    """Periodo -> clausula de janela de criacao em JQL (dias; M deprecado no Cloud)."""
    if not periodo or periodo in ("tudo", "todos", "all"):
        return ""
    if periodo == "ano":
        import datetime
        cur_year = datetime.date.today().year
        return f' AND created >= "{cur_year}-01-01"'
    if periodo == "30d":
        return " AND created >= -30d"
    if periodo == "60d":
        return " AND created >= -60d"
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
    
    # Tratamento semântico do Funil de Atendimento (alinhado rigorosamente a _detectar_fase)
    if funil_stage in ("novas", "em_atendimento", "aguardando_validacao"):
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


def _resolver_projetos_e_permissoes(
    estado: Optional[str],
    projetos_req: Optional[str],
    user: TokenPayload,
) -> tuple[list[str], list[dict], str]:
    """
    Resolve a lista de projetos Jira a serem consultados e valida permissões RBAC.
    Retorna (lista_projetos, lista_reporters, nome_exibicao).
    Suporta coordenador/admin (acesso aos 73 espaços) e clientes com múltiplos espaços (ex.: HDPMSC + SSC).
    """
    from ..core.estados import clientes_do_estado

    is_coord = user.role in ("admin", "coordenador") or user.state in ("todos", "all") or user.sub in ("coordenador", "admin")

    # 1. Coordenador / Administrador Geral: Acesso irrestrito a qualquer espaço ou combinação de espaços
    if is_coord:
        if projetos_req:
            projs = [p.strip().upper() for p in projetos_req.split(",") if p.strip()]
            return projs, [], f"Personalizado ({', '.join(projs)})"
        if estado and estado not in ("todos", "all"):
            cfg = estado_por_sigla(estado)
            if cfg:
                only_rep = cfg.get("only_reporter")
                reps = [{"accountId": only_rep}] if only_rep else []
                return cfg.get("projects", [estado.upper()]), reps, cfg.get("display_name", estado.upper())
            return [estado.upper()], [], estado.upper()
        return ["HDPMSC"], [], "Geral"

    # 2. Cliente / Gestor Estadual (viewer ou manager):
    user_espacos_raw = getattr(user, "espacos", "") or ""
    cfg_estado = estado_por_sigla(user.state)

    projetos_autorizados = set()
    if user_espacos_raw:
        for p in user_espacos_raw.split(","):
            if p.strip():
                projetos_autorizados.add(p.strip().upper())
    if cfg_estado and cfg_estado.get("projects"):
        for p in cfg_estado["projects"]:
            projetos_autorizados.add(p.upper())
    if not projetos_autorizados:
        projetos_autorizados.add("HDPMSC")

    if projetos_req:
        projs_pedidos = [p.strip().upper() for p in projetos_req.split(",") if p.strip()]
        for p in projs_pedidos:
            if p not in projetos_autorizados:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    f"Espaço '{p}' não autorizado para o usuário '{user.sub}'."
                )
        projs_finais = projs_pedidos
    elif estado and estado != user.state:
        cfg_solicitado = estado_por_sigla(estado)
        projs_do_estado = [p.upper() for p in (cfg_solicitado.get("projects", []) if cfg_solicitado else [])]
        if not any(p in projetos_autorizados for p in projs_do_estado):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Fora do escopo do usuário")
        projs_finais = [p for p in projs_do_estado if p in projetos_autorizados]
    else:
        projs_finais = sorted(list(projetos_autorizados))

    only_rep = cfg_estado.get("only_reporter") if cfg_estado else None
    reporters = [{"accountId": only_rep}] if only_rep else []
    display = cfg_estado.get("display_name", ", ".join(projs_finais)) if cfg_estado else ", ".join(projs_finais)
    return projs_finais, reporters, display


@router.get("/issues")
async def list_issues(
    estado: Optional[str] = None,
    projetos: Optional[str] = None,
    espacos: Optional[str] = None,
    status_filter: Optional[str] = None,
    tipo: Optional[str] = None,
    origem: Optional[str] = None,
    posse_filter: Optional[str] = None,
    funil_stage: Optional[str] = None,
    jql: Optional[str] = None,
    abertas: bool = True,
    periodo: Optional[str] = None,
    max_results: int = 250,
    user: TokenPayload = Depends(get_current_user),
):
    projs_req = projetos or espacos
    projs, reporters, _ = _resolver_projetos_e_permissoes(estado, projs_req, user)
    # A janela temporal de período aplica-se a toda a consulta (ativas e concluídas)
    janela_jql = _jql_janela(periodo)
    q = _build_jql(projs, status_filter, tipo, jql, abertas,
                   reporters=reporters, janela=janela_jql,
                   funil_stage=funil_stage)
    issues = await JSM.search_full(q, cap=max_results)
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
        is_done = st_cat == "done" or fase_info["num"] == 8 or bool((f.get("resolution") or {}).get("name"))

        # Filtro estrito do Funil de Atendimento (100% idêntico a /dashboard)
        if funil_stage == "novas":
            if is_done or fase_info["num"] not in (1, 2):
                continue
        elif funil_stage == "em_atendimento":
            if is_done or fase_info["num"] not in (3, 4, 5, 6):
                continue
        elif funil_stage == "aguardando_validacao":
            if is_done or (fase_info["num"] != 7 and fase_info["posse"] != "cliente"):
                continue
        elif funil_stage == "concluidas":
            if not is_done:
                continue

        if posse_filter and fase_info["posse"] != posse_filter:
            continue

        chave = it.get("key") or ""
        prefixo_espaco = chave.split("-")[0] if "-" in chave else "JIRA"

        out.append({
            "tipo": (f.get("issuetype") or {}).get("name"),
            "origem": origem_da_issue,
            "referencia": chave,
            "espaco": prefixo_espaco,
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
async def dashboard(
    estado: Optional[str] = None,
    projetos: Optional[str] = None,
    espacos: Optional[str] = None,
    periodo: Optional[str] = None,
    user: TokenPayload = Depends(get_current_user)
):
    """Métricas agregadas (funil de 4 estágios + cards estilo Jira Dashboard) com suporte a múltiplos espaços."""
    projs_req = projetos or espacos
    projs, reporters, display_name = _resolver_projetos_e_permissoes(estado, projs_req, user)
    projetos_str = ", ".join(projs)

    _rp = ", ".join('"'+c["accountId"]+'"' for c in reporters if c.get("accountId"))
    _filtro_rp = f" AND reporter in ({_rp})" if _rp else ""

    # Aplica janela temporal de forma unificada e transparente
    janela = _jql_janela(periodo)

    # 1. Backlog Ativo da janela selecionada
    abertas_jql = f"project in ({projetos_str}){_filtro_rp} AND resolution is EMPTY{janela} ORDER BY updated DESC"
    todas_abertas = await JSM.search_full(abertas_jql, cap=1000)

    # 2. Concluídas da janela selecionada
    conc_jql = f"project in ({projetos_str}){_filtro_rp} AND (resolution is not EMPTY OR statusCategory in ('Done')){janela} ORDER BY updated DESC"
    todas_concluidas = await JSM.search_full(conc_jql, cap=1000)

    todas = todas_abertas + todas_concluidas
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

        # Classificação do Funil de 4 Estágios (Régua Canônica de 8 Etapas)
        fase_info = _detectar_fase(st, key)
        fase_num = fase_info["num"]
        if key == "done" or fase_num == 8 or (f.get("resolution") or {}).get("name"):
            funil["concluidas"] += 1
        elif fase_num == 7 or fase_info["posse"] == "cliente":
            funil["aguardando_validacao"] += 1
        elif fase_num in (3, 4, 5, 6):
            funil["em_atendimento"] += 1
        elif fase_num in (1, 2):
            funil["novas"] += 1
        else:
            funil["novas"] += 1

        upd = (f.get("updated") or "")[:10]
        try:
            if datetime.fromisoformat(upd) >= limite and key == "done":
                concluidas_7d += 1
        except Exception:
            pass
    return {
        "estado": display_name,
        "projetos": projs,
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
async def meta(
    estado: Optional[str] = None,
    projetos: Optional[str] = None,
    espacos: Optional[str] = None,
    user: TokenPayload = Depends(get_current_user)
):
    """Status e tipos disponíveis para os filtros do painel com contagem completa."""
    import json
    import httpx

    projs_req = projetos or espacos
    projs, reporters, _ = _resolver_projetos_e_permissoes(estado, projs_req, user)
    projetos_str = ", ".join(projs)
    statuses = []
    tipos = []
    hdr = JSM._basic()
    async with httpx.AsyncClient() as c:
        # tipos
        for p in projs:
            try:
                r = await c.get("https://egsys.atlassian.net/rest/api/3/issue/createmeta",
                                params={"projectKeys": p}, headers=hdr, timeout=4.0)
                if r.status_code == 200:
                    data = r.json()
                    for proj in data.get("projects", []):
                        for it in proj.get("issuetypes", []):
                            tipos.append(it.get("name"))
            except Exception:
                pass
        # statuses do projeto principal (workflow completo)
        if projs:
            try:
                r = await c.get(f"https://egsys.atlassian.net/rest/api/3/project/{projs[0]}/statuses", headers=hdr, timeout=4.0)
                if r.status_code == 200:
                    for it in r.json():
                        for st in it.get("statuses", []):
                            statuses.append(st.get("name"))
            except Exception:
                pass
    statuses = sorted(set(statuses))
    
    # contagem real por status (issues do estado sem cap de 100)
    contagem = {}
    try:
        issues_all = await JSM.search(f"project in ({projetos_str}) ORDER BY created DESC", 1000)
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

    # Resolução dinâmica e resiliente do estado (suporta sigla 'sc', projeto 'HDPMSC' ou prefixo da chave)
    cfg = estado_por_sigla(estado) if estado else None
    if not cfg and estado:
        siglas = projeto_em_estado(estado)
        if siglas:
            cfg = estado_por_sigla(siglas[0])
            estado = siglas[0]

    if not cfg and "-" in key:
        proj = key.split("-")[0]
        siglas = projeto_em_estado(proj)
        if siglas:
            cfg = estado_por_sigla(siglas[0])
            estado = siglas[0]

    is_global_coord = user.role in ("admin", "coordenador") or getattr(user, "state", "") in ("todos", "all")
    if not cfg:
        if is_global_coord:
            cfg = {"display_name": "Coordenação Geral", "projects": []}
        else:
            raise HTTPException(404, "Estado não configurado")

    if not is_global_coord and user.role == "viewer" and user.state != estado:
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

    # Montar Stepper de 8 Etapas
    etapas_nomes = [
        (1, "Triagem (N1)"),
        (2, "Triagem (N2)"),
        (3, "Análise de Desenvolvimento"),
        (4, "Em Desenvolvimento"),
        (5, "Testes de Qualidade (QA)"),
        (6, "Validação Interna (Suporte N1)"),
        (7, "Validação / Homologação Cliente"),
        (8, "Concluído (Entregue)"),
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
async def charts(
    estado: Optional[str] = None,
    projetos: Optional[str] = None,
    espacos: Optional[str] = None,
    periodo: Optional[str] = None,
    user: TokenPayload = Depends(get_current_user)
):
    """Agregados para os gráficos (barras, donut, prioridade, solicitante, tempo) com suporte a múltiplos espaços."""
    from collections import Counter, defaultdict

    projs_req = projetos or espacos
    projs, reporters, _ = _resolver_projetos_e_permissoes(estado, projs_req, user)
    projetos_str = ", ".join(projs)
    _rp = ", ".join('"'+c["accountId"]+'"' for c in reporters if c.get("accountId"))
    _filtro_rp = f" AND reporter in ({_rp})" if _rp else ""
    issues = await JSM.search(
        f"project in ({projetos_str}){_filtro_rp}{_jql_janela(periodo)} ORDER BY created DESC",
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


