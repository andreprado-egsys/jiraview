# egSYS JiraView — Extensões Modulares Perfiladas (Feature Modules)
# Módulos internos absorvidos do jira-dashboard e node-red:
# 1. Visão Gerencial Multi-Estado & NOC
# 2. Esteira de Análise de Desenvolvimento
# 3. Relatórios Matinais & E-mails Corporativos
# 4. Webhook & Monitor de Certificados SSL
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from ..core.config import get_settings
from ..core.db import (
    delete_email_recipient,
    get_noc_layout,
    get_user_by_username,
    list_certificates,
    list_email_recipients,
    list_reports_history,
    log_report_history,
    save_noc_layout,
    sync_traefik_acme_certificates,
    update_email_recipient,
    upsert_certificate,
    upsert_email_recipient,
)
from ..core.security import TokenPayload, get_current_user, jsm, require_module
from ..core.sheets import sync_google_sheets_and_db

router = APIRouter(prefix="/api/v1/modules", tags=["modules"])

MODULES_CATALOG = [
    {
        "id": "visao_gerencial",
        "nome": "Visão Gerencial Multi-Estado & NOC",
        "icone": "📊",
        "descricao": "Consolidação de chamados, gargalos e triagem em lote multi-estado",
        "badge": "Operações",
    },
    {
        "id": "analise_dev",
        "nome": "Esteira de Análise de Desenvolvimento",
        "icone": "📐",
        "descricao": "Monitoramento de itens na fase de análise técnica antes do sprint",
        "badge": "Engenharia",
    },
    {
        "id": "relatorio_email",
        "nome": "Relatórios Matinais & E-mails",
        "icone": "📧",
        "descricao": "Disparo diário (07h50) e sob demanda de relatórios executivos via SMTP institucional",
        "badge": "Governança",
    },
    {
        "id": "certificados_alert",
        "nome": "Monitor & Webhook de Certificados SSL",
        "icone": "🛡️",
        "descricao": "Monitoramento e alertas preventivos de expiração de certificados SSL dos servidores",
        "badge": "Infraestrutura",
    },
    {
        "id": "triagem_n1n2",
        "nome": "Esteira de Triagem N1 & N2",
        "icone": "📟",
        "descricao": "Triagem técnica de suporte N1 e N2 por estado com contadores e SLAs",
        "badge": "Operações",
    },
]

PROJETOS_ESTADOS_MAP = {
    "HDPMAM": {"estado": "Amazonas", "sigla": "AM", "cor": "#065F46"},
    "HDPMTO": {"estado": "Tocantins", "sigla": "TO", "cor": "#166534"},
    "HDSISEGGM": {"estado": "Guardas Municipais", "sigla": "GM", "cor": "#6D28D9"},
    "HDPMPR": {"estado": "Paraná", "sigla": "PR", "cor": "#1D4ED8"},
    "HDPMSC": {"estado": "Santa Catarina", "sigla": "SC", "cor": "#7C3AED"},
    "HDCMBPR": {"estado": "CBM Paraná", "sigla": "CBM-PR", "cor": "#B91C1C"},
    "HDPMMT": {"estado": "Mato Grosso", "sigla": "MT", "cor": "#92400E"},
    "HDSESDEC": {"estado": "Rondônia", "sigla": "RO", "cor": "#0369A1"},
    "SSC": {"estado": "Suporte SC", "sigla": "SSC", "cor": "#4C1D95"},
}


@router.get("/catalog")
async def get_catalog(user: TokenPayload = Depends(get_current_user)):
    """Retorna o catálogo completo de módulos e quais estão ativos para o usuário conectado."""
    is_admin = user.role in ("admin", "coordenador") or user.sub in ("admin", "coordenador")
    db_u = get_user_by_username(user.sub)
    modulos_str = (db_u.get("modulos_ativos") if db_u else None) or getattr(user, "modulos_ativos", "") or ""
    ativos_set = set([m.strip().lower() for m in modulos_str.split(",") if m.strip()])

    catalog = []
    for mod in MODULES_CATALOG:
        m_id = mod["id"]
        habilitado = is_admin or (m_id in ativos_set)
        catalog.append({**mod, "habilitado": habilitado})

    return {
        "user": user.sub,
        "role": user.role,
        "is_admin": is_admin,
        "modules": catalog,
    }


# ============================================================================
# MÓDULO 1: VISÃO GERENCIAL MULTI-ESTADO & NOC
# ============================================================================
@router.get("/noc/overview")
async def get_noc_overview(user: TokenPayload = Depends(require_module("visao_gerencial"))):
    """Retorna visão consolidada multi-estado de chamados pendentes (absorve aba 1 do Node-RED)."""
    lista_projetos = ", ".join(PROJETOS_ESTADOS_MAP.keys())
    jql = (
        f"project in ({lista_projetos}) AND status not in ("
        f"'Concluído', 'Done', 'Cancelado', 'Cancelled', 'Closed', 'Resolved', "
        f"'Itens concluídos', 'Concluído(a)') ORDER BY created ASC"
    )

    issues = await jsm().search(jql, max_results=100)

    por_estado: Dict[str, Dict[str, Any]] = {}
    for p_key, meta in PROJETOS_ESTADOS_MAP.items():
        por_estado[p_key] = {
            "sigla": meta["sigla"],
            "estado": meta["estado"],
            "cor": meta["cor"],
            "total": 0,
            "criticas": 0,
            "paradas_3d": 0,
            "issues": [],
        }

    agora = datetime.now(timezone.utc)
    for issue in issues:
        fields = issue.get("fields") or {}
        proj = (fields.get("project") or {}).get("key") or issue.get("key", "").split("-")[0]
        if proj not in por_estado:
            continue

        prio = ((fields.get("priority") or {}).get("name") or "").lower()
        is_critica = prio in ("highest", "high", "alta", "altíssima", "crítica", "urgente")

        updated_str = fields.get("updated") or fields.get("created")
        dias_parado = 0
        if updated_str:
            try:
                dt = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
                dias_parado = (agora - dt).days
            except Exception:
                pass

        por_estado[proj]["total"] += 1
        if is_critica:
            por_estado[proj]["criticas"] += 1
        if dias_parado >= 3:
            por_estado[proj]["paradas_3d"] += 1

        if len(por_estado[proj]["issues"]) < 10:
            por_estado[proj]["issues"].append({
                "key": issue.get("key"),
                "summary": fields.get("summary"),
                "status": (fields.get("status") or {}).get("name"),
                "priority": (fields.get("priority") or {}).get("name"),
                "dias_parado": dias_parado,
            })

    total_geral = sum(v["total"] for v in por_estado.values())
    total_criticas = sum(v["criticas"] for v in por_estado.values())

    return {
        "total_geral": total_geral,
        "total_criticas": total_criticas,
        "estados": list(por_estado.values()),
    }


# ============================================================================
# MÓDULO 2: ESTEIRA DE ANÁLISE DE DESENVOLVIMENTO
# ============================================================================
ORDEM_ESTADOS_ANALISE = [
    "HDPMAM",
    "HDPMTO",
    "HDSISEGGM",
    "HDPMPR",
    "HDPMSC",
    "HDCMBPR",
    "HDPMMT",
    "HDSESDEC",
    "SSC",
]


def _extrair_texto_desc(desc: Any) -> str:
    if not desc:
        return ""
    if isinstance(desc, str):
        return desc[:250]
    try:
        content = desc.get("content", [])
        if content and isinstance(content, list):
            sub = content[0].get("content", [])
            if sub and isinstance(sub, list):
                txt = sub[0].get("text", "")
                return txt[:250]
    except Exception:
        pass
    return ""


@router.get("/analise-dev/issues")
async def get_analise_dev_issues():
    """Retorna itens em 'Análise de Desenvolvimento' modulados por estado (absorve aba 3 do Node-RED)."""
    lista_projetos = ", ".join(PROJETOS_ESTADOS_MAP.keys())
    jql = (
        f"project in ({lista_projetos}) AND status = 'Análise de Desenvolvimento' "
        f"AND created >= -100d ORDER BY created DESC"
    )

    issues = await jsm().search(jql, max_results=100)
    agora = datetime.now(timezone.utc)
    processados = []
    seen = set()

    for item in issues:
        k = item.get("key")
        if not k or k in seen:
            continue
        seen.add(k)

        fields = item.get("fields") or {}
        proj = (fields.get("project") or {}).get("key") or k.split("-")[0]
        meta = PROJETOS_ESTADOS_MAP.get(proj, {"estado": proj, "sigla": proj, "cor": "#64748B"})

        created_str = fields.get("created")
        dias_aberta = 0
        data_exibicao = "---"
        raw_date = 0

        if created_str:
            try:
                dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                dias_aberta = (agora - dt).days
                data_exibicao = dt.strftime("%d/%m/%Y %H:%M")
                raw_date = int(dt.timestamp())
            except Exception:
                data_exibicao = str(created_str)[:16]

        if dias_aberta >= 7:
            urg_class = "badge-red"
            urg_label = f"{dias_aberta}d ⚠️"
        elif dias_aberta >= 5:
            urg_class = "badge-yellow"
            urg_label = f"{dias_aberta}d"
        else:
            urg_class = "badge-green"
            urg_label = f"{dias_aberta}d"

        assignee = (fields.get("assignee") or {}).get("displayName") or "Não Atribuído"

        processados.append({
            "key": k,
            "projKey": proj,
            "summary": fields.get("summary") or "Sem Título",
            "description": _extrair_texto_desc(fields.get("description")),
            "created": data_exibicao,
            "rawDate": raw_date,
            "diasAberta": dias_aberta,
            "urgClass": urg_class,
            "urgLabel": urg_label,
            "assignee": assignee,
            "link": f"https://egsys.atlassian.net/browse/{k}",
            "estado": meta["estado"],
            "sigla": meta["sigla"],
            "cor": meta["cor"],
            "priority": (fields.get("priority") or {}).get("name") or "Média",
        })

    # Agrupa por estado na ordem canônica da egSYS
    grupos = []
    conhecidos = set()

    for proj_key in ORDEM_ESTADOS_ANALISE:
        meta = PROJETOS_ESTADOS_MAP.get(proj_key, {"estado": proj_key, "sigla": proj_key, "cor": "#64748B"})
        tasks = [t for t in processados if t["projKey"] == proj_key]
        tasks.sort(key=lambda x: x["rawDate"], reverse=True)
        conhecidos.add(proj_key)

        if tasks:
            grupos.append({
                "projKey": proj_key,
                "nome": meta["estado"],
                "sigla": meta["sigla"],
                "cor": meta["cor"],
                "total": len(tasks),
                "hasAlert": any(t["diasAberta"] >= 7 for t in tasks),
                "tasks": tasks,
            })

    # Inclui qualquer outro projeto com tasks fora da lista fixa
    outros_proj = sorted(list(set(t["projKey"] for t in processados if t["projKey"] not in conhecidos)))
    for proj_key in outros_proj:
        meta = PROJETOS_ESTADOS_MAP.get(proj_key, {"estado": proj_key, "sigla": proj_key, "cor": "#64748B"})
        tasks = [t for t in processados if t["projKey"] == proj_key]
        tasks.sort(key=lambda x: x["rawDate"], reverse=True)
        if tasks:
            grupos.append({
                "projKey": proj_key,
                "nome": meta["estado"],
                "sigla": meta["sigla"],
                "cor": meta["cor"],
                "total": len(tasks),
                "hasAlert": any(t["diasAberta"] >= 7 for t in tasks),
                "tasks": tasks,
            })

    total_tasks = len(processados)
    has_alert = any(t["diasAberta"] >= 7 for t in processados)
    has_critico_10d = any(t["diasAberta"] >= 10 for t in processados)

    return {
        "total": total_tasks,
        "grupos": grupos,
        "hasAlert": has_alert,
        "hasCritico10d": has_critico_10d,
        "issues": processados,
    }


# ============================================================================
# MÓDULO 5: ESTEIRA DE TRIAGEM N1 & N2 (SUPORTE OPERACIONAL MULTI-ESTADO)
# ============================================================================
STATUSES_TRIAGEM_N1N2 = [
    "Validação N1",
    "Validação N2",
    "Resolução Suporte",
    "1. Triagem (N1)",
    "2. Triagem (N2)",
    "Triagem (N1)",
    "Triagem (N2)",
    "Triagem N1",
    "Triagem N2",
    "Aguardando Suporte",
    "Aguardando N1",
    "Aguardando N2",
    "Em Triagem",
]


@router.get("/triagem-n1n2/issues")
async def get_triagem_n1n2_issues():
    """Retorna itens em triagem técnica N1/N2 e suporte modulados por estado."""
    lista_projetos = ", ".join(PROJETOS_ESTADOS_MAP.keys())
    st_jql = ", ".join([f"'{s}'" for s in STATUSES_TRIAGEM_N1N2])
    jql = (
        f"project in ({lista_projetos}) AND status in ({st_jql}) "
        f"ORDER BY created ASC"
    )

    issues = await jsm().search(jql, max_results=100)
    agora = datetime.now(timezone.utc)
    processados = []
    seen = set()

    for item in issues:
        k = item.get("key")
        if not k or k in seen:
            continue
        seen.add(k)

        fields = item.get("fields") or {}
        proj = (fields.get("project") or {}).get("key") or k.split("-")[0]
        meta = PROJETOS_ESTADOS_MAP.get(proj, {"estado": proj, "sigla": proj, "cor": "#64748B"})

        created_str = fields.get("created")
        dias_aberta = 0
        data_exibicao = "---"
        raw_date = 0

        if created_str:
            try:
                dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                dias_aberta = (agora - dt).days
                data_exibicao = dt.strftime("%d/%m/%Y %H:%M")
                raw_date = int(dt.timestamp())
            except Exception:
                data_exibicao = str(created_str)[:16]

        if dias_aberta >= 7:
            urg_class = "badge-red"
            urg_label = f"{dias_aberta}d ⚠️"
        elif dias_aberta >= 3:
            urg_class = "badge-yellow"
            urg_label = f"{dias_aberta}d"
        else:
            urg_class = "badge-green"
            urg_label = f"{dias_aberta}d"

        assignee = (fields.get("assignee") or {}).get("displayName") or "Não Atribuído"
        st_name = (fields.get("status") or {}).get("name") or "Em Triagem"

        processados.append({
            "key": k,
            "projKey": proj,
            "summary": fields.get("summary") or "Sem Título",
            "description": _extrair_texto_desc(fields.get("description")),
            "created": data_exibicao,
            "rawDate": raw_date,
            "diasAberta": dias_aberta,
            "urgClass": urg_class,
            "urgLabel": urg_label,
            "assignee": assignee,
            "status": st_name,
            "link": f"https://egsys.atlassian.net/browse/{k}",
            "estado": meta["estado"],
            "sigla": meta["sigla"],
            "cor": meta["cor"],
            "priority": (fields.get("priority") or {}).get("name") or "Média",
        })

    grupos = []
    conhecidos = set()

    for proj_key in ORDEM_ESTADOS_ANALISE:
        meta = PROJETOS_ESTADOS_MAP.get(proj_key, {"estado": proj_key, "sigla": proj_key, "cor": "#64748B"})
        tasks = [t for t in processados if t["projKey"] == proj_key]
        tasks.sort(key=lambda x: x["rawDate"])  # Mais antigas primeiro no atendimento suporte
        conhecidos.add(proj_key)

        if tasks:
            grupos.append({
                "projKey": proj_key,
                "nome": meta["estado"],
                "sigla": meta["sigla"],
                "cor": meta["cor"],
                "total": len(tasks),
                "hasAlert": any(t["diasAberta"] >= 7 for t in tasks),
                "tasks": tasks,
            })

    outros_proj = sorted(list(set(t["projKey"] for t in processados if t["projKey"] not in conhecidos)))
    for proj_key in outros_proj:
        meta = PROJETOS_ESTADOS_MAP.get(proj_key, {"estado": proj_key, "sigla": proj_key, "cor": "#64748B"})
        tasks = [t for t in processados if t["projKey"] == proj_key]
        tasks.sort(key=lambda x: x["rawDate"])
        if tasks:
            grupos.append({
                "projKey": proj_key,
                "nome": meta["estado"],
                "sigla": meta["sigla"],
                "cor": meta["cor"],
                "total": len(tasks),
                "hasAlert": any(t["diasAberta"] >= 7 for t in tasks),
                "tasks": tasks,
            })

    total_tasks = len(processados)
    has_alert = any(t["diasAberta"] >= 7 for t in processados)
    has_critico_10d = any(t["diasAberta"] >= 10 for t in processados)

    return {
        "total": total_tasks,
        "grupos": grupos,
        "hasAlert": has_alert,
        "hasCritico10d": has_critico_10d,
        "issues": processados,
    }


# ============================================================================
# MÓDULO 3: RELATÓRIOS MATINAIS & E-MAILS
# ============================================================================
class SendReportRequest(BaseModel):
    destinatarios: Optional[str] = None


@router.post("/reports/trigger-analise-dev")
async def trigger_analise_dev_report(
    req: Optional[SendReportRequest] = None,
    user: Optional[TokenPayload] = Depends(require_module("relatorio_email")),
):
    """Compila e dispara relatório matinal executivo de tarefas em Análise de Desenvolvimento (absorve aba 2)."""
    destinatarios = (req.destinatarios if req and req.destinatarios else "").strip()
    if not destinatarios:
        destinatarios = os.getenv(
            "REPORTS_EMAIL_RECIPIENTS",
            "joao.sopran@egsys.com.br, alexandre.publio@egsys.com.br, coordenacao@egsys.com.br",
        )

    # Busca tarefas
    jql = "project in (HDPMAM, HDPMTO, HDSESDEC, HDPMPR, HDPMSC, HDCMBPR, HDPMMT, HDSISEGGM) AND status = 'Análise de Desenvolvimento' AND created >= -100d ORDER BY created DESC"
    issues = await jsm().search(jql, max_results=100)

    agora = datetime.now(timezone.utc)
    linhas_html = []
    for it in issues:
        f = it.get("fields") or {}
        proj = (f.get("project") or {}).get("key") or it.get("key", "").split("-")[0]
        meta = PROJETOS_ESTADOS_MAP.get(proj, {"sigla": proj, "cor": "#64748B"})
        dias = 0
        if f.get("created"):
            try:
                dt = datetime.fromisoformat(f["created"].replace("Z", "+00:00"))
                dias = (agora - dt).days
            except Exception:
                pass
        linhas_html.append(f"""
            <tr style="border-bottom: 1px solid #E2E8F0;">
                <td style="padding: 10px; font-weight: bold;"><span style="background: {meta['cor']}; color: #fff; padding: 2px 6px; border-radius: 4px; font-size: 11px;">{meta['sigla']}</span> <a href="https://egsys.atlassian.net/browse/{it.get('key')}" style="color: #2563EB; text-decoration: none;">{it.get('key')}</a></td>
                <td style="padding: 10px; color: #1E293B;">{f.get('summary', '')}</td>
                <td style="padding: 10px; color: #64748B; font-size: 12px;">{(f.get('assignee') or {}).get('displayName') or 'Não atribuído'}</td>
                <td style="padding: 10px; text-align: center; font-weight: bold; color: {'#DC2626' if dias >= 15 else '#D97706' if dias >= 7 else '#16A34A'};">{dias}d</td>
            </tr>
        """)

    tabela_conteudo = "".join(linhas_html) if linhas_html else "<tr><td colspan='4' style='padding: 20px; text-align: center; color: #64748B;'>Nenhuma tarefa em Análise de Desenvolvimento no período.</td></tr>"

    html_corpo = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #F8FAFC; margin: 0; padding: 20px;">
        <div style="max-width: 800px; margin: 0 auto; background: #FFFFFF; border-radius: 8px; border: 1px solid #E2E8F0; overflow: hidden;">
            <div style="background: #0F172A; padding: 20px; color: #FFFFFF;">
                <h2 style="margin: 0; font-size: 18px; font-weight: 600;">📊 egSYS JiraView — Relatório Matinal</h2>
                <p style="margin: 4px 0 0; font-size: 13px; color: #94A3B8;">Tarefas em Análise de Desenvolvimento • Gerado em {agora.strftime('%d/%m/%Y às %H:%M UTC')}</p>
            </div>
            <div style="padding: 20px;">
                <p style="color: #334155; font-size: 14px; margin-top: 0;">Total de tarefas aguardando análise técnica: <strong>{len(issues)}</strong></p>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                    <thead>
                        <tr style="background: #F1F5F9; color: #475569; text-transform: uppercase; font-size: 11px;">
                            <th style="padding: 10px;">Chave / Estado</th>
                            <th style="padding: 10px;">Resumo</th>
                            <th style="padding: 10px;">Responsável</th>
                            <th style="padding: 10px; text-align: center;">Idade</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tabela_conteudo}
                    </tbody>
                </table>
            </div>
            <div style="background: #F8FAFC; padding: 12px 20px; font-size: 12px; color: #64748B; border-top: 1px solid #E2E8F0; text-align: center;">
                egSYS Inteligência & Sustentação • Painel Corporativo JiraView
            </div>
        </div>
    </body>
    </html>
    """

    # Resolve lista de destinatários cadastrados caso não seja fornecida
    if not destinatarios or not destinatarios.strip():
        recadastrados = list_email_recipients(tipo="relatorio_executivo")
        destinatarios = ", ".join(r["email"] for r in recadastrados if r.get("email"))

    if not destinatarios:
        destinatarios = "andre.prado@egsys.com.br"

    lista_dest = [d.strip() for d in destinatarios.split(",") if d.strip()]
    assunto = f"📊 [egSYS NOC] Análise de Desenvolvimento — {len(issues)} tasks ({agora.strftime('%d/%m')})"
    
    ok, msg_detalhe = enviar_email_corporativo(lista_dest, assunto, html_corpo)
    status_envio = "enviado" if ok else "falha"

    log_report_history("analise_dev", destinatarios, len(issues), status_envio, msg_detalhe)

    return {
        "status": status_envio,
        "total_tarefas": len(issues),
        "destinatarios": destinatarios,
        "detalhe": msg_detalhe,
    }


def enviar_email_corporativo(destinatarios: List[str], assunto: str, html_corpo: str) -> Tuple[bool, str]:
    """Dispara e-mail via SMTP corporativo (padronizado com o projeto Orion)."""
    s = get_settings()
    host = s.smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(s.smtp_port or os.getenv("SMTP_PORT", "587"))
    user = s.smtp_user or os.getenv("SMTP_USER", "orion@egsys.com.br")
    pwd = s.smtp_password or os.getenv("SMTP_PASSWORD", "xrnrxpuvmdncxwgk")
    from_email = s.smtp_from_email or os.getenv("SMTP_FROM_EMAIL", "orion@egsys.com.br")

    if not destinatarios:
        return False, "Nenhum destinatário informado."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = f"egSYS Observabilidade & Segurança <{from_email}>"
        msg["To"] = ", ".join(destinatarios)
        msg.attach(MIMEText(html_corpo, "html"))

        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, pwd)
            server.sendmail(from_email, destinatarios, msg.as_string())
        return True, f"Enviado com sucesso via {host} para {len(destinatarios)} destinatário(s)."
    except Exception as ex:
        return False, f"Falha no envio SMTP ({host}:{port}): {ex}"


class RecipientPayload(BaseModel):
    nome: str
    email: str
    relatorio_executivo: bool = True
    alertas_certificados: bool = True
    ativo: bool = True


class RecipientUpdatePayload(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    relatorio_executivo: Optional[bool] = None
    alertas_certificados: Optional[bool] = None
    ativo: Optional[bool] = None


@router.get("/recipients")
async def get_recipients(tipo: Optional[str] = None, user: TokenPayload = Depends(require_module("relatorio_email"))):
    """Lista destinatários de e-mail cadastrados para notificações."""
    return {"recipients": list_email_recipients(tipo)}


@router.post("/recipients")
async def create_or_update_recipient(payload: RecipientPayload, user: TokenPayload = Depends(require_module("relatorio_email"))):
    """Cadastra ou atualiza um destinatário de e-mail."""
    rid = upsert_email_recipient(
        nome=payload.nome,
        email=payload.email,
        relatorio_executivo=payload.relatorio_executivo,
        alertas_certificados=payload.alertas_certificados,
        ativo=payload.ativo,
    )
    return {"status": "ok", "id": rid}


@router.put("/recipients/{recipient_id}")
async def edit_recipient(recipient_id: int, payload: RecipientUpdatePayload, user: TokenPayload = Depends(require_module("relatorio_email"))):
    """Atualiza seletivamente as opções de um destinatário de e-mail."""
    ok = update_email_recipient(
        recipient_id=recipient_id,
        nome=payload.nome,
        email=payload.email,
        relatorio_executivo=payload.relatorio_executivo,
        alertas_certificados=payload.alertas_certificados,
        ativo=payload.ativo,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Destinatário não encontrado")
    return {"status": "ok"}


@router.delete("/recipients/{recipient_id}")
async def remove_recipient(recipient_id: int, user: TokenPayload = Depends(require_module("relatorio_email"))):
    """Remove destinatário de e-mail."""
    ok = delete_email_recipient(recipient_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Destinatário não encontrado")
    return {"status": "ok"}


@router.post("/recipients/test-email")
async def send_test_email(payload: Dict[str, str], user: TokenPayload = Depends(require_module("relatorio_email"))):
    """Envia um e-mail de teste de conectividade para o endereço especificado."""
    dest = payload.get("email")
    if not dest:
        raise HTTPException(status_code=400, detail="E-mail de destino é obrigatório")

    agora_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;">
        <div style="background: #0f172a; padding: 16px 20px; border-radius: 6px; color: #ffffff; margin-bottom: 20px;">
            <h2 style="margin: 0; font-size: 18px;">🛡️ egSYS Observabilidade & Segurança</h2>
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Teste de Conectividade SMTP Corporativo</div>
        </div>
        <p style="font-size: 14px; color: #334155;">Olá!</p>
        <p style="font-size: 14px; color: #334155;">Este é um teste de confirmação de entrega do canal corporativo de notificações do <strong>egSYS JiraViewer</strong> (padronizado com a infraestrutura Orion).</p>
        <div style="background: #f0fdf4; border: 1px solid #86efac; border-radius: 6px; padding: 12px; font-size: 13px; color: #166534; margin: 20px 0;">
            ✅ <strong>Canal de e-mail validado com sucesso!</strong><br>
            Você está habilitado para receber Relatórios Executivos e Alertas Preventivos de Certificados.
        </div>
        <div style="font-size: 11px; color: #64748B; border-top: 1px solid #E2E8F0; padding-top: 12px; text-align: center;">
            Disparado em {agora_str} • Painel Corporativo egSYS
        </div>
    </div>
    """
    ok, msg = enviar_email_corporativo([dest.strip()], "✅ [egSYS] Teste de Notificações Corporativas", html)
    return {"status": "ok" if ok else "error", "mensagem": msg}


@router.post("/certificates/send-alert")
async def send_certificates_alert_endpoint(user: Optional[TokenPayload] = Depends(require_module("certificados_alert"))):
    """Coleta certificados críticos/vencidos e dispara alerta por e-mail para a lista cadastrada."""
    recipients = list_email_recipients(tipo="alertas_certificados")
    emails = [r["email"].strip() for r in recipients if r.get("email")]
    if not emails:
        return {"status": "error", "mensagem": "Nenhum destinatário ativo cadastrado com a opção 'Alertas de Certificados'."}

    certs = list_certificates()
    criticos_vencidos = [
        c for c in certs 
        if int(c.get("dias_restantes", 999)) <= 15 or c.get("status") in ("VENCIDO", "CRITICO")
    ]
    alertas = [
        c for c in certs 
        if 15 < int(c.get("dias_restantes", 999)) <= 30
    ]

    if not criticos_vencidos and not alertas:
        return {
            "status": "ok",
            "mensagem": "Nenhum certificado em risco no momento. Todos com prazo regular (> 30 dias).",
            "enviado": False
        }

    linhas_html = ""
    for c in criticos_vencidos + alertas:
        dias = int(c.get("dias_restantes", 0))
        cor_fundo = "#fee2e2" if dias <= 15 else "#fef3c7"
        cor_texto = "#dc2626" if dias <= 15 else "#d97706"
        status_label = "VENCIDO" if dias <= 0 else (f"CRÍTICO ({dias}d)" if dias <= 15 else f"ALERTA ({dias}d)")
        
        linhas_html += f"""
        <tr style="border-bottom: 1px solid #E2E8F0;">
            <td style="padding: 10px 12px; font-weight: 700; color: #1e293b;">
                <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 6px;">{c.get('state', 'N/A')}</span>
                {c.get('domain', c.get('host', ''))}
            </td>
            <td style="padding: 10px 12px; font-size: 12px; color: #475569;">{c.get('valid_until', 'N/A')}</td>
            <td style="padding: 10px 12px; text-align: center;">
                <span style="background: {cor_fundo}; color: {cor_texto}; font-weight: 800; padding: 4px 8px; border-radius: 4px; font-size: 11px;">
                    {status_label}
                </span>
            </td>
            <td style="padding: 10px 12px; font-size: 12px; color: #475569;">{c.get('precisa_token', 'Não')}</td>
        </tr>
        """

    agora_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin: 0; padding: 20px; background: #F8FAFC; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="max-width: 750px; margin: 0 auto; background: #ffffff; border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
            <div style="background: #0f172a; padding: 20px 24px; color: #ffffff; border-bottom: 4px solid #ef4444;">
                <div style="font-size: 11px; font-weight: 700; color: #f87171; text-transform: uppercase; letter-spacing: 0.5px;">ALERTA PREVENTIVO DE INFRAESTRUTURA</div>
                <h1 style="margin: 4px 0 0; font-size: 20px; font-weight: 800;">🚨 Certificados SSL Expirados ou em Vencimento Crítico</h1>
                <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">egSYS Observabilidade • Auditoria em {agora_str}</div>
            </div>
            
            <div style="padding: 20px 24px;">
                <p style="font-size: 14px; color: #334155; margin-top: 0;">
                    Atenção equipe de infraestrutura e suporte: foram detectados <strong>{len(criticos_vencidos)} certificados críticos/vencidos</strong> e <strong>{len(alertas)} em janela de alerta</strong> nos servidores e serviços do ecossistema corporativo.
                </p>

                <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; margin: 20px 0;">
                    <thead>
                        <tr style="background: #F1F5F9; color: #475569; text-transform: uppercase; font-size: 11px;">
                            <th style="padding: 10px 12px;">Domínio / Estado</th>
                            <th style="padding: 10px 12px;">Vence Em</th>
                            <th style="padding: 10px 12px; text-align: center;">Status / Prazo</th>
                            <th style="padding: 10px 12px;">Exigência de Token</th>
                        </tr>
                    </thead>
                    <tbody>
                        {linhas_html}
                    </tbody>
                </table>

                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px 18px; margin-top: 20px;">
                    <div style="font-weight: 700; font-size: 13px; color: #1e293b; margin-bottom: 4px;">🔗 Ação Recomendada:</div>
                    <div style="font-size: 12px; color: #64748B; line-height: 1.5;">
                        Acesse o painel do Coordenador para verificar o status em tempo real, efetuar as renovações manuais com token do Registro.br ou disparar nova sincronização com o Google Sheets:
                        <br><br>
                        <a href="https://suporte-monitor.egsys.siseg.tech/coordenador" style="display: inline-block; background: #0f172a; color: #ffffff; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 700; font-size: 12px;">Acessar Painel do Coordenador ↗️</a>
                    </div>
                </div>
            </div>

            <div style="background: #F8FAFC; padding: 14px 24px; font-size: 12px; color: #64748B; border-top: 1px solid #E2E8F0; text-align: center;">
                egSYS Inteligência & Sustentação • Notificação Automática de Segurança
            </div>
        </div>
    </body>
    </html>
    """
    assunto = f"🚨 [egSYS Alerta SSL] {len(criticos_vencidos)} certificados críticos/vencidos ({agora_str})"
    ok, msg = enviar_email_corporativo(emails, assunto, html)
    log_report_history("alerta_ssl", ", ".join(emails), len(criticos_vencidos) + len(alertas), "enviado" if ok else "falha", msg)
    return {
        "status": "ok" if ok else "error",
        "total_criticos": len(criticos_vencidos),
        "total_alerta": len(alertas),
        "destinatarios": emails,
        "mensagem": msg,
        "enviado": ok
    }


@router.get("/reports/history")
async def get_reports_history(user: TokenPayload = Depends(require_module("relatorio_email"))):
    """Retorna histórico dos últimos relatórios disparados."""
    return {"history": list_reports_history(20)}


# ============================================================================
# MÓDULO 4: WEBHOOK & MONITOR DE CERTIFICADOS SSL
# ============================================================================
class CertificatePayload(BaseModel):
    domain: str
    host: str
    state: str
    status: str
    dias_restantes: int
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    issuer: Optional[str] = None
    padrao: Optional[str] = None
    tipo_renovacao: Optional[str] = None
    precisa_token: Optional[str] = None


@router.post("/certificates/probe")
async def receive_certificate_probe(payload: CertificatePayload):
    """Recebe atualização unitária de certificado SSL de sonda externa."""
    upsert_certificate(
        domain=payload.domain,
        host=payload.host,
        state=payload.state,
        status=payload.status,
        dias_restantes=payload.dias_restantes,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        issuer=payload.issuer,
        padrao=payload.padrao,
        tipo_renovacao=payload.tipo_renovacao,
        precisa_token=payload.precisa_token,
    )
    return {"status": "ok", "domain": payload.domain}


@router.post("/certificates/webhook-legacy")
async def receive_legacy_certificates_webhook(payload: Dict[str, Any]):
    """Recebe webhook no formato legado do Node-RED ('states -> hosts -> certs')."""
    estados = payload.get("states") or {}
    total_gravados = 0
    criticos = 0

    for sigla, info in estados.items():
        hosts = info.get("hosts") or []
        for h in hosts:
            domain = h.get("domain") or h.get("url") or h.get("host")
            if not domain:
                continue
            dias = int(h.get("daysLeft", h.get("dias_restantes", 999)))
            st = h.get("status") or ("VENCIDO" if dias <= 0 else "CRITICO" if dias <= 15 else "OK")
            upsert_certificate(
                domain=domain,
                host=h.get("host") or domain,
                state=sigla,
                status=st,
                dias_restantes=dias,
                valid_from=h.get("validFrom") or h.get("valid_from"),
                valid_until=h.get("validUntil") or h.get("valid_until"),
                issuer=h.get("issuer"),
                padrao=h.get("padrao") or "Let's Encrypt (DV X.509 RSA/ECC)",
                tipo_renovacao=h.get("tipo_renovacao") or "ACME HTTP-01 / DNS-01",
                precisa_token=h.get("precisa_token") or ("Sim (Token Registro.br / DNS)" if ".com.br" in domain else "Não (Automático)"),
            )
            total_gravados += 1
            if dias <= 15 or st in ("VENCIDO", "CRITICO"):
                criticos += 1

    return {
        "status": "ok",
        "total_processados": total_gravados,
        "criticos": criticos,
    }


@router.post("/certificates/sync-traefik")
async def sync_certificates_traefik_endpoint(user: TokenPayload = Depends(require_module("certificados_alert"))):
    """Sincroniza imediatamente todos os certificados gerenciados pelo Traefik (acme.json)."""
    total = sync_traefik_acme_certificates()
    return {"status": "ok", "total_sincronizados": total}


@router.post("/certificates/sync-sheets")
async def sync_certificates_sheets_endpoint(user: TokenPayload = Depends(require_module("certificados_alert"))):
    """Executa varredura SSL completa em todos os domínios corporativos e sincroniza com a Planilha Google Oficial."""
    res = sync_google_sheets_and_db(update_sheet=True)
    return res


@router.get("/certificates")
async def get_certificates():
    """Lista todos os certificados SSL monitorados com contadores analíticos e status detalhados."""
    # Sincroniza dinamicamente se acme.json estiver disponível
    try:
        sync_traefik_acme_certificates()
    except Exception:
        pass

    certs = list_certificates()
    vencidos = sum(1 for c in certs if c.get("status") == "VENCIDO" or int(c.get("dias_restantes", 999)) <= 0)
    criticos = sum(1 for c in certs if 0 < int(c.get("dias_restantes", 999)) <= 15)
    alertas = sum(1 for c in certs if 15 < int(c.get("dias_restantes", 999)) <= 30)
    normais = sum(1 for c in certs if int(c.get("dias_restantes", 999)) > 30)

    # Identifica itens em situação de risco para card de alerta imediato
    itens_alerta = [
        {
            "domain": c["domain"],
            "host": c.get("host", ""),
            "state": (c.get("state") or "INFRA").upper(),
            "dias": int(c.get("dias_restantes", 0)),
            "status": "VENCIDO" if int(c.get("dias_restantes", 0)) <= 0 else "CRÍTICO",
            "vence_em": c.get("valid_until") or "N/A",
            "precisa_token": c.get("precisa_token") or "Não",
        }
        for c in certs
        if int(c.get("dias_restantes", 999)) <= 15 or c.get("status") == "VENCIDO"
    ]

    return {
        "resumo": {
            "total": len(certs),
            "vencidos": vencidos,
            "criticos": criticos,
            "alerta": alertas,
            "ok": normais,
            "has_alert": len(itens_alerta) > 0,
            "itens_alerta": itens_alerta,
        },
        "certificados": certs,
    }


class NocLayoutPayload(BaseModel):
    numCols: str = "3"
    columns: List[List[str]] = []


@router.get("/noc/layout/{tipo}")
async def get_noc_layout_endpoint(tipo: str):
    """Retorna o layout customizado de colunas e cards de um módulo NOC."""
    layout = get_noc_layout(tipo)
    return {"status": "ok", "layout": layout}


@router.post("/noc/layout/{tipo}")
async def save_noc_layout_endpoint(tipo: str, payload: NocLayoutPayload):
    """Persiste o layout customizado de colunas e cards de um módulo NOC."""
    ok = save_noc_layout(tipo, payload.numCols, payload.columns)
    return {"status": "ok" if ok else "error"}

