#!/usr/bin/env python3
"""
Portal JSM (PSEI-277) — Correção Contínua de Tickets Divergentes (HDPMSC + SCPMH)
================================================================================
1) HDPMSC: tickets "Desenvolvimento concluído" (done) SEM resolução
   -> transição "Resolvido Pelo Desenvolvimento" (111) + Resolução "Concluído" (10000)
2) SCPMH (inativo): tickets done SEM resolução do cliente João Mário Mazzola
   -> apenas preenche campo Resolução via PUT (status permanece intacto)

Uso:
  python3 corrige_divergentes.py --dry-run   # lista sem alterar
  python3 corrige_divergentes.py --apply     # corrige (scan + write + snapshot por ticket)
  python3 corrige_divergentes.py --audit     # relatório final

Segurança:
  - Idempotente (rodar 2x não altera nada na 2ª)
  - Escopo estrito: projeto HDPMSC / projeto SCPMH filtrado por reporter Mazzola
  - Só age se: resolution is EMPTY AND (status correto por projeto)
  - Snapshot de cada ticket antes de alterar (./snapshots/runtime/)
"""
import json
import os
import sys
import base64
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

SERVER = "https://egsys.atlassian.net"
EMAIL = os.environ.get("ATLASSIAN_EMAIL", "")
TOKEN = os.environ.get("ATLASSIAN_TOKEN", "")
BASE = os.path.dirname(os.path.abspath(__file__))
SNAP_DIR = os.path.join(BASE, "snapshots")

# (nome, jql, via_transicao)  — via_transicao=True usa POST transitions/111
#                                 via_transicao=False usa PUT (preenche resolution apenas)
BATTERIES = [
    ("HDPMSC",
     'project = HDPMSC AND status = "Desenvolvimento concluído" AND resolution is EMPTY ORDER BY key',
     True),
    ("SCPMH-Mazzola",
     'project = SCPMH AND resolution is EMPTY AND statusCategory = done AND reporter = "João Mário Mazzola" ORDER BY key',
     False),
]
TRANSITION_ID = "111"      # HDPMSC: "Resolvido Pelo Desenvolvimento" -> Concluído
RESOLUTION_ID = "10000"    # Concluído


def auth():
    return {"Authorization": "Basic " + base64.b64encode(
        f"{EMAIL}:{TOKEN}".encode()).decode(), "Accept": "application/json"}


def api(method, path, body=None, timeout=30):
    data = json.dumps(body).encode() if body else None
    headers = {**auth(), "Content-Type": "application/json"} if data else auth()
    req = urllib.request.Request(SERVER + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        return e.code, {}


def find_divergentes(jql):
    code, data = api("GET", "/rest/api/3/search/jql?" + urllib.parse.urlencode(
        {"jql": jql, "maxResults": 100, "fields": "summary,status,resolution,assignee"}))
    if code != 200:
        sys.exit(f"Erro na busca JQL: {code} {data}")
    return [i["key"] for i in data.get("issues", [])]


def snapshot_ticket(key, payload):
    os.makedirs(os.path.join(SNAP_DIR, "runtime"), exist_ok=True)
    path = os.path.join(SNAP_DIR, "runtime", f"{key}_{datetime.now():%Y%m%d_%H%M%S}.json")
    with open(path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, cls=_JiraEncoder)
    return path


class _JiraEncoder(json.JSONEncoder):
    def default(self, o):
        return str(o)


def fix_ticket(key, via_transition, apply=False):
    code, cur = api("GET", f"/rest/api/3/issue/{key}?fields=status,resolution")
    if code != 200:
        return key, "ERRO consulta", None
    resolution = ((cur.get("fields") or {}).get("resolution") or {}).get("name")
    if resolution:
        return key, "JÁ CORRIGIDO (pular)", resolution
    if apply:
        snapshot_ticket(key, cur)
        if via_transition:
            code, _ = api("POST", f"/rest/api/3/issue/{key}/transitions",
                          {"transition": {"id": TRANSITION_ID},
                           "update": {"resolution": [{"set": {"id": RESOLUTION_ID}}]}})
        else:
            code, _ = api("PUT", f"/rest/api/3/issue/{key}",
                          {"fields": {"resolution": {"id": RESOLUTION_ID}}})
        return key, f"CORRIGIDO {code}", None
    return key, (cur.get("fields", {}).get("status") or {}).get("name") or "?", None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    if EMAIL == "" or TOKEN == "":
        sys.exit("Defina ATLASSIAN_EMAIL e ATLASSIAN_TOKEN.")
    for name, jql, via in BATTERIES:
        keys = find_divergentes(jql)
        print(f"[{name}] {len(keys)} tickets divergentes")
        if mode == "--dry-run":
            for k in keys:
                key, result, _ = fix_ticket(k, via, apply=False)
                print(f"  {key}: {result}")
        elif mode == "--apply":
            ok = fail = 0
            for k in keys:
                key, result, _ = fix_ticket(k, via, apply=True)
                if result.startswith("CORRIGIDO 204"):
                    ok += 1
                elif result.startswith("JÁ CORRIGIDO"):
                    ok += 1
                else:
                    fail += 1
                print(f"  {key}: {result}")
            print(f"  -> {ok} ok | {fail} falhas")
        elif mode == "--audit":
            for k in keys:
                code, cur = api("GET", f"/rest/api/3/issue/{k}?fields=status,resolution")
                r = ((cur.get("fields") or {}).get("resolution") or {}).get("name")
                print(f"  {k}: {((cur.get('fields') or {}).get('status') or {}).get('name')} | res={r}")
        else:
            sys.exit("Argumentos: --dry-run | --apply | --audit")


if __name__ == "__main__":
    main()
