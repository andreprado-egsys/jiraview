# egSYS JiraView — Scheduler em Background para Verificação de Certificados e Relatórios
import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("jiraview.scheduler")

_scheduler_task = None


async def start_background_scheduler():
    """Inicia o loop assíncrono em background para verificações e disparos matinais."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_scheduler_loop())
        logger.info("Background Scheduler iniciado com sucesso (Certificados & Notificações).")


async def _scheduler_loop():
    """
    Loop periódico:
    1. A cada 6 horas: Varredura SSL em todos os domínios corporativos e sincronização com Google Sheets.
    2. A cada 1 hora: Verificação reforçada se houver certificados críticos (<= 15 dias).
    3. Diariamente às 07h50 (UTC-3): Disparo do Relatório Executivo da Esteira de Desenvolvimento.
    4. Diariamente às 08h00 (UTC-3): Disparo de Alertas Preventivos de Certificados SSL (se houver itens em risco).
    """
    # Espera 10 segundos após o startup para não competir com a subida do servidor
    await asyncio.sleep(10)

    ultimo_sync_certificados = 0
    ultimo_disparo_matinal = ""
    ultimo_disparo_alertas_ssl = ""

    # Fuso horário corporativo Brasil (UTC-3)
    tz_br = timezone(timedelta(hours=-3))

    while True:
        try:
            agora_utc = datetime.now(timezone.utc)
            agora_br = agora_utc.astimezone(tz_br)
            hora_minuto = agora_br.strftime("%H:%M")
            dia_str = agora_br.strftime("%Y-%m-%d")

            agora_ts = int(agora_utc.timestamp())

            # ------------------------------------------------------------------
            # 1. VARREDURA DE CERTIFICADOS & GOOGLE SHEETS
            # ------------------------------------------------------------------
            # Roda na inicialização e a cada 6 horas (21600 segundos)
            intervalo_sync = 21600

            # Importação defensiva local
            from .db import list_certificates
            certs = list_certificates()
            tem_criticos = any(int(c.get("dias_restantes", 999)) <= 15 or c.get("status") in ("VENCIDO", "CRITICO") for c in certs)

            # Se houver críticos, reduz o intervalo de auditoria para 1 hora (3600 segundos)
            if tem_criticos:
                intervalo_sync = 3600

            if agora_ts - ultimo_sync_certificados >= intervalo_sync:
                logger.info("Iniciando varredura agendada de certificados SSL e Google Sheets...")
                try:
                    from .sheets import sync_google_sheets_and_db
                    # Executa o probe concorrente em thread separada para não bloquear o loop asyncio
                    await asyncio.to_thread(sync_google_sheets_and_db, update_sheet=True)
                    ultimo_sync_certificados = agora_ts
                    logger.info("Varredura agendada de certificados concluída com sucesso.")
                except Exception as e:
                    logger.error(f"Erro na varredura agendada de certificados: {e}")

            # ------------------------------------------------------------------
            # 2. DISPARO DO RELATÓRIO MATINAL (07h50 UTC-3)
            # ------------------------------------------------------------------
            if hora_minuto == "07:50" and ultimo_disparo_matinal != dia_str:
                logger.info("Disparando Relatório Executivo Matinal automático (07h50)...")
                try:
                    from ..api.modules import trigger_analise_dev_report, SendReportRequest
                    await trigger_analise_dev_report(SendReportRequest())
                    ultimo_disparo_matinal = dia_str
                except Exception as ex_mail:
                    logger.error(f"Erro no disparo matinal automático: {ex_mail}")

            # ------------------------------------------------------------------
            # 3. DISPARO DO ALERTA DE CERTIFICADOS (08h00 UTC-3)
            # ------------------------------------------------------------------
            if hora_minuto == "08:00" and ultimo_disparo_alertas_ssl != dia_str:
                logger.info("Verificando necessidade de disparo matinal de alertas SSL (08h00)...")
                try:
                    from ..api.modules import send_certificates_alert_endpoint
                    # Dispara alerta de certificados se houver itens críticos
                    await send_certificates_alert_endpoint(user=None)
                    ultimo_disparo_alertas_ssl = dia_str
                except Exception as ex_ssl:
                    logger.error(f"Erro no disparo de alerta SSL: {ex_ssl}")

        except Exception as loop_ex:
            logger.error(f"Exceção no loop do scheduler: {loop_ex}")

        # Dorme por 30 segundos antes do próximo ciclo de checagem
        await asyncio.sleep(30)
