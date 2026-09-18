# egSYS JiraView — Sincronização e Auditoria de Certificados SSL com Google Sheets
import csv
import io
import json
import logging
import os
import re
import socket
import ssl
import subprocess
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jose import jwt

from .db import upsert_certificate

logger = logging.getLogger("jiraview.sheets")

DEFAULT_SHEET_ID = "1yO1L72qkR1-SXSBGrYtTe9xtm1QCSVcfKqRqzSjbtGU"

KEY_PATHS = [
    Path("/app/data/google_service_account.json"),
    Path("data/google_service_account.json"),
    Path("backend/data/google_service_account.json"),
    Path("../data/google_service_account.json"),
]


def _get_service_account_key() -> Optional[Dict[str, Any]]:
    """Localiza a chave de conta de serviço Google no sistema de arquivos."""
    for p in KEY_PATHS:
        if p.is_file():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Falha ao ler chave Google em {p}: {e}")
    return None


def get_sheets_access_token() -> Optional[str]:
    """Gera um token de acesso OAuth2 usando a chave da Service Account via JWT RS256."""
    key_data = _get_service_account_key()
    if not key_data:
        return None

    now = int(time.time())
    payload = {
        "iss": key_data["client_email"],
        "sub": key_data["client_email"],
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now,
        "exp": now + 3600,
        "scope": "https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/drive",
    }
    signed_jwt = jwt.encode(payload, key_data["private_key"], algorithm="RS256")

    token_req_data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": signed_jwt,
    }).encode("utf-8")

    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=token_req_data)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_resp = json.loads(resp.read().decode("utf-8"))
            return token_resp.get("access_token")
    except Exception as e:
        logger.error(f"Erro ao obter access token da Google Sheets API: {e}")
        return None


def clean_host(url_str: str) -> str:
    """Extrai hostname limpo removendo protocolo, portas e caminhos."""
    url_str = url_str.strip()
    if not url_str.startswith("http://") and not url_str.startswith("https://"):
        url_str = "https://" + url_str
    parsed = urllib.parse.urlparse(url_str)
    host = parsed.netloc or parsed.path.split("/")[0]
    if ":" in host:
        host = host.split(":")[0]
    return host.strip()


def probe_ssl(host: str, port: int = 443, timeout: float = 3.5) -> Dict[str, Any]:
    """Realiza handshake TLS com o host para extrair datas reais de emissão e vencimento."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                nb = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
                na = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                issuer_dict = dict(x[0] for x in cert.get("issuer", []))
                issuer = issuer_dict.get("organizationName") or issuer_dict.get("commonName") or "Let's Encrypt"
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                days = (na - now).days
                return {
                    "ok": True,
                    "valid_from": nb.strftime("%d/%m/%Y"),
                    "valid_until": na.strftime("%d/%m/%Y"),
                    "days_remaining": days,
                    "issuer": issuer,
                }
    except ssl.SSLCertVerificationError:
        # Tenta fallback via openssl para certificados expirados ou autoassinados
        try:
            cmd = f"openssl s_client -servername {host} -connect {host}:{port} </dev/null 2>/dev/null | openssl x509 -noout -dates -issuer"
            out = subprocess.check_output(cmd, shell=True, timeout=timeout).decode("utf-8")
            nb, na, issuer = "", "", ""
            d_until = None
            for line in out.splitlines():
                if line.startswith("notBefore="):
                    val = line.split("=", 1)[1]
                    d = datetime.strptime(val, "%b %d %H:%M:%S %Y %Z")
                    nb = d.strftime("%d/%m/%Y")
                elif line.startswith("notAfter="):
                    val = line.split("=", 1)[1]
                    d = datetime.strptime(val, "%b %d %H:%M:%S %Y %Z")
                    na = d.strftime("%d/%m/%Y")
                    d_until = d
                elif line.startswith("issuer="):
                    issuer = line.split("=", 1)[1]
            if na and d_until:
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                days = (d_until - now).days
                return {
                    "ok": True,
                    "valid_from": nb,
                    "valid_until": na,
                    "days_remaining": days,
                    "issuer": issuer or "Outro",
                }
        except Exception as e2:
            return {"ok": False, "error": f"{e2}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

    return {"ok": False, "error": "Handshake timeout ou não acessível"}


def sync_google_sheets_and_db(
    sheet_id: str = DEFAULT_SHEET_ID,
    update_sheet: bool = True,
    csv_fallback_path: str = "/tmp/planilha_certificados_egsys.csv"
) -> Dict[str, Any]:
    """
    Sincroniza os dados entre Google Sheets, varredura SSL e banco de dados SQLite.
    1. Lê a planilha do Google Sheets via API v4 (ou CSV como fallback).
    2. Realiza probe SSL concorrente nos domínios.
    3. Atualiza SQLite (certificates_status).
    4. Atualiza a planilha Google com as datas apuradas via batchUpdate.
    """
    token = get_sheets_access_token()
    raw_values = []
    sheet_title = "Página1"

    if token:
        try:
            # 1. Obter nome da primeira aba
            meta_req = urllib.request.Request(
                f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}?fields=sheets.properties.title",
                headers={"Authorization": f"Bearer {token}"}
            )
            with urllib.request.urlopen(meta_req, timeout=10) as m_resp:
                meta_data = json.loads(m_resp.read().decode("utf-8"))
                sheets_list = meta_data.get("sheets", [])
                if sheets_list:
                    sheet_title = sheets_list[0].get("properties", {}).get("title", "Página1")

            # 2. Ler valores de A1:J150 com URL quote seguro para nomes de aba com acentos
            range_name = f"'{sheet_title}'!A1:J150"
            quoted_range = urllib.parse.quote(range_name)
            req = urllib.request.Request(
                f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{quoted_range}",
                headers={"Authorization": f"Bearer {token}"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_values = data.get("values", [])
        except Exception as ex:
            logger.warning(f"Erro ao ler Google Sheets via API ({ex}), usando fallback CSV.")

    if not raw_values and os.path.exists(csv_fallback_path):
        with open(csv_fallback_path, "r", encoding="utf-8") as f:
            raw_values = list(csv.reader(f))

    if not raw_values:
        return {"status": "error", "message": "Nenhum dado encontrado na planilha ou fallback CSV."}

    # Processamento de linhas
    items = []
    for idx, r in enumerate(raw_values):
        if idx == 0 or not r or not any(r):
            continue
        state = r[0].strip() if len(r) > 0 else ""
        url = r[1].strip() if len(r) > 1 else ""
        if not url or url.startswith("DNS") or not state:
            continue
        host = clean_host(url)
        items.append({
            "row_number": idx + 1,  # 1-indexed para Sheets
            "state": state,
            "url": url,
            "host": host,
            "sheet_from": r[5].strip() if len(r) > 5 else "",
            "sheet_until": r[6].strip() if len(r) > 6 else "",
            "is_lets_encrypt": r[7].strip() if len(r) > 7 else "",
            "obs": r[9].strip() if len(r) > 9 else "",
        })

    def _worker(it: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        return it, probe_ssl(it["host"])

    with ThreadPoolExecutor(max_workers=15) as pool:
        results = list(pool.map(_worker, items))

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    batch_updates = []
    total_sucesso = 0
    total_vencidos = 0
    total_criticos = 0
    total_alerta = 0
    total_ok = 0

    for it, res in results:
        row_num = it["row_number"]
        obs = it["obs"]
        url = it["url"]
        host = it["host"]
        state = it["state"]

        # Determina exigência de token e tipo de renovação
        if "registro br" in obs.lower() or "registro.br" in obs.lower():
            precisa_token = "Sim (Token Registro.br DNS)"
            tipo_renovacao = "DNS-01 (Registro.br)"
        elif "duckdns" in obs.lower():
            precisa_token = "Sim (Token DuckDNS)"
            tipo_renovacao = "DNS-01 (DuckDNS)"
        elif "problema com o certificado" in obs.lower():
            precisa_token = "Atenção (Falha de Renovação)"
            tipo_renovacao = "Certbot ACME"
        elif "deprecad" in obs.lower() or "inativo" in obs.lower():
            precisa_token = "Não (Inativo / Depreciado)"
            tipo_renovacao = "Manual / Depreciado"
        else:
            precisa_token = "Não (Automático Traefik/Certbot)"
            tipo_renovacao = "Traefik TLS-ALPN-01" if "traefik" in obs.lower() else "Automática Traefik / ACME"

        if res.get("ok"):
            total_sucesso += 1
            valid_from = res["valid_from"]
            valid_until = res["valid_until"]
            dias = res["days_remaining"]
            issuer = res["issuer"]
            padrao = "Let's Encrypt (DV RSA/ECC)" if "encrypt" in issuer.lower() else f"{issuer} (X.509)"
            status = "VENCIDO" if dias <= 0 else ("CRITICO" if dias <= 15 else ("ALERTA" if dias <= 30 else "OK"))

            # Se as datas apuradas diferem da planilha, prepara update
            if valid_from != it["sheet_from"] or valid_until != it["sheet_until"]:
                batch_updates.append({
                    "range": f"'{sheet_title}'!F{row_num}:G{row_num}",
                    "values": [[valid_from, valid_until]],
                })
        else:
            valid_from = it["sheet_from"]
            valid_until = it["sheet_until"]
            dias = 999
            if valid_until:
                try:
                    dt_u = datetime.strptime(valid_until, "%d/%m/%Y")
                    dias = (dt_u - now).days
                except Exception:
                    pass
            status = "INATIVO" if ("deprecad" in obs.lower() or "inativo" in obs.lower()) else ("VENCIDO" if dias <= 0 else ("CRITICO" if dias <= 15 else ("ALERTA" if dias <= 30 else "OK")))
            issuer = "Manual / Registro.br" if "registro br" in obs.lower() else "Let's Encrypt"
            padrao = "Let's Encrypt (Standby / Intranet)" if it["is_lets_encrypt"].upper() == "TRUE" else "X.509 / Privado"

        if status == "VENCIDO" or dias <= 0:
            total_vencidos += 1
        elif dias <= 15:
            total_criticos += 1
        elif dias <= 30:
            total_alerta += 1
        else:
            total_ok += 1

        upsert_certificate(
            domain=url,
            host=host,
            state=state,
            status=status,
            dias_restantes=dias,
            valid_from=valid_from,
            valid_until=valid_until,
            issuer=issuer,
            padrao=padrao,
            tipo_renovacao=tipo_renovacao,
            precisa_token=precisa_token,
        )

    # 4. Atualizar o Google Sheets se solicitado e houver alterações
    sheet_atualizada = False
    total_linhas_atualizadas = 0
    if update_sheet and token and batch_updates:
        try:
            update_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values:batchUpdate"
            payload_data = json.dumps({
                "valueInputOption": "USER_ENTERED",
                "data": batch_updates,
            }).encode("utf-8")
            b_req = urllib.request.Request(
                update_url,
                data=payload_data,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(b_req, timeout=20) as b_resp:
                b_res = json.loads(b_resp.read().decode("utf-8"))
                total_linhas_atualizadas = b_res.get("totalUpdatedRows", len(batch_updates))
                sheet_atualizada = True
        except Exception as ex:
            logger.error(f"Erro no batchUpdate do Google Sheets: {ex}")

    return {
        "status": "ok",
        "total_dominios": len(items),
        "probes_sucesso": total_sucesso,
        "probes_indisponiveis": len(items) - total_sucesso,
        "resumo_status": {
            "vencidos": total_vencidos,
            "criticos": total_criticos,
            "alerta": total_alerta,
            "ok": total_ok,
        },
        "sheet_sync": {
            "atualizado": sheet_atualizada,
            "celulas_alteradas": len(batch_updates) * 2,
            "linhas_atualizadas": total_linhas_atualizadas,
        },
    }
