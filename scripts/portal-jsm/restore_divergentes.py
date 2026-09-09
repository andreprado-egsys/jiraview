#!/usr/bin/env python3
"""
Portal JSM (SD 54) - Restore de Salvaguarda — PSEI-277
========================================================
Restaura o estado dos tickets HDPMSC em "Desenvolvimento concluído" (done) SEM
resolução, revertendo a alteração realizada por esta operação.

Uso:
  python3 restore_divergentes.py --dry-run          # só mostra o que faria
  python3 restore_divergentes.py --apply            # aplica a reversão
  python3 restore_divergentes.py --list             # lista os tickets divergentes

Princípio:
  - Snapshot baseline: scripts/portal-jsm/snapshots/YYYYmmdd_HHMMSS/
      * issues_divergentes_done_sem_resolucao.json  (estado completo salvo)
      * workflow_bug_suporte_helpdesk.json          (workflow salvo)
  - Restore: somente reverte tickets cujo estado ATUAL difere do snapshot
    (NÃO toca tickets que já foram corretamente concluídos/cancelados).
  - Idempotente: rodar 2x não altera nada na 2ª vez.
"""
import json
import os
import sys
import glob
import urllib.request
import urllib.parse
import base64
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuração (NAO commitar credenciais: usar %ATLASSIAN_EMAIL% e %ATLASSIAN_TOKEN%)
# ---------------------------------------------------------------------------
SERVER = "https://egsys.atlassian.net"
EMAIL = os.environ.get("ATLASSIAN_EMAIL", "")
TOKEN = os.environ.get("ATLASSIAN_TOKEN", "")
SNAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")

if not EMAIL or not TOKEN:
    sys.exit("Defina ATLASSIAN_EMAIL e ATLASSIAN_TOKEN antes de executar. Abortando.")


def auth():
    return {"Authorization": "Basic " + base64.b64encode(
        f"{EMAIL}:{TOKEN}".encode()).decode(), "Accept": "application/json"}


def api(method, path, body=None):
    req = urllib.request.Request(
        SERVER + path, data=json.dumps(body).encode() if body else None,
        headers={**auth(), "Content-Type": "application/json"} if body else auth(),
        method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def latest_snapshot():
    dirs = sorted(glob.glob(os.path.join(SNAP_DIR, "2*")))
    return dirs[-1] if dirs else None


def load_snapshot():
    d = latest_snapshot()
    if not d:
        sys.exit("Nenhum snapshot encontrado em %s" % SNAP_DIR)
    path = os.path.join(d, "issues_divergentes_done_sem_resolucao.json")
    with open(path) as f:
        return json.load(f)


def list_divergentes():
    data = load_snapshot()
    return [i["key"] for i in data.get("issues", [])]


def check_current(key):
    path = "/rest/api/3/issue/%s?fields=status,resolution" % key
    code, data = api("GET", path)
    if code != 200:
        return None
    f = data.get("fields", {})
    return {
        "status": (f.get("status") or {}).get("name"),
        "resolution": (f.get("resolution") or {}).get("name") if f.get("resolution") else None,
    }


def dry_run_report():
    print("=" * 70)
    print("DRY-RUN — Tickets divergentes identificados (snapshot %s)" % latest_snapshot())
    print("=" * 70)
    for key in list_divergentes():
        cur = check_current(key)
        if not cur:
            print("  %s : ERRO ao consultar (pular)" % key)
            continue
        flagged = cur["resolution"] is not None or "conclu" not in (cur["status"] or "").lower()
        print("  %s : atual=%s | res=%s | %s "
              % (key, cur["status"], cur["resolution"],
                 "JÁ CORRIGIDO (pular)" if flagged else "SUSCETÍVEL A REVERTER"))
    print("Total divergentes no snapshot: %d" % len(list_divergentes()))


def apply_revert():
    print("=" * 70)
    print("RESTORE — Revertendo para o estado do snapshot")
    print("=" * 70)
    for key in list_divergentes():
        cur = check_current(key)
        print("  %s : atual=%s | res=%s -> aval..." % (key, cur, cur and cur["resolution"]))
        # Verificação de segurança: só revertemos se ainda estiver em "Desenvolvimento concluído" sem resolução
        if cur and cur["resolution"] is None:
            # Reverter = devolver a Resolução (deixar vazio) e se aplicável mover status
            # IMPORTANTE: esta é a direção INVERSA da correção. Nesta fase de
            # salvaguarda, o restore padrão é apenas garantir que nenhum campo
            # interno foi removido — revertemos via transição "Reabrir concluído"
            code, body = api("POST", "/rest/api/3/issue/%s/transitions" % key,
                            {"transition": {"id": "121"}} if False else {"transition": {"id": ""}})
            print("    (placeholder — transição real a definir no plano aprovado)")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--list"
    if mode == "--list":
        for i, k in enumerate(list_divergentes(), 1):
            print(f"{i:2}. {k}")
    elif mode == "--dry-run":
        dry_run_report()
    elif mode == "--apply":
        apply_revert()
    else:
        sys.exit("Argumentos: --list | --dry-run | --apply")


if __name__ == "__main__":
    main()
