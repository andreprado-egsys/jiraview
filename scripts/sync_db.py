#!/usr/bin/env python3
"""
egSYS JiraView — Script de Sincronização e Pareamento de Bancos de Dados (SQLite / Data)
Sincroniza auth.db e filtros.json entre o ambiente local e o servidor de produção (monitoramento-egsys).

Uso:
  python3 scripts/sync_db.py --status   # Verifica se os bancos local e produção estão pareados
  python3 scripts/sync_db.py --pull     # Baixa banco de produção para o ambiente local
  python3 scripts/sync_db.py --push     # Envia banco local para o servidor de produção
"""
import sys
import os
import argparse
import subprocess
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

REMOTE_HOST = os.getenv("JIRAVIEW_REMOTE_HOST", "monitoramento-egsys")
REMOTE_PATH = os.getenv("JIRAVIEW_REMOTE_DIR", "/var/egsys-docker/container/jiraview/data")
LOCAL_PATH = Path(__file__).resolve().parent.parent / "data"


def get_local_users() -> list[dict]:
    db_file = LOCAL_PATH / "auth.db"
    if not db_file.exists():
        return []
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        rows = cur.execute("SELECT id, username, nome, role, estado, is_active, must_change_password FROM users ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"[!] Erro ao ler banco local: {e}")
        return []
    finally:
        conn.close()


def get_remote_users() -> list[dict]:
    cmd = [
        "ssh", REMOTE_HOST,
        "python3 -c \"import sqlite3; conn = sqlite3.connect('" + REMOTE_PATH + "/auth.db'); "
        "conn.row_factory = sqlite3.Row; cur = conn.cursor(); "
        "import json; print(json.dumps([dict(r) for r in cur.execute('SELECT id, username, nome, role, estado, is_active, must_change_password FROM users ORDER BY id')]))\""
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        return json.loads(res.stdout.strip())
    except Exception as e:
        print(f"[!] Erro ao ler banco remoto: {e}")
        return []


def check_status():
    print("=" * 70)
    print("🔍 VERIFICAÇÃO DE PAREAMENTO DE BANCOS (LOCAL vs PRODUÇÃO)")
    print(f"   Ambiente Remoto: {REMOTE_HOST}:{REMOTE_PATH}/auth.db")
    print(f"   Ambiente Local:  {LOCAL_PATH}/auth.db")
    print("=" * 70)

    local_u = get_local_users()
    remote_u = get_remote_users()

    print(f"📊 Usuários no Local:     {len(local_u)}")
    print(f"📊 Usuários na Produção:  {len(remote_u)}")

    local_dict = {u["username"]: u for u in local_u}
    remote_dict = {u["username"]: u for u in remote_u}

    all_keys = sorted(set(local_dict.keys()) | set(remote_dict.keys()))
    divergencias = []

    print("-" * 70)
    print(f"{'Username':<20} | {'Status Local':<18} | {'Status Prod':<18} | {'Paridade':<10}")
    print("-" * 70)

    for k in all_keys:
        loc = local_dict.get(k)
        rem = remote_dict.get(k)
        if loc and rem:
            diff = [f"{field}: {loc[field]} != {rem[field]}" for field in ("role", "estado", "is_active", "must_change_password") if loc[field] != rem[field]]
            if diff:
                divergencias.append(f"{k} com divergências de dados: {', '.join(diff)}")
                print(f"{k:<20} | Presente (ID {loc['id']})   | Presente (ID {rem['id']})   | ⚠️ DIFERENTE")
            else:
                print(f"{k:<20} | Presente (ID {loc['id']})   | Presente (ID {rem['id']})   | ✅ OK")
        elif loc and not rem:
            divergencias.append(f"{k} existe apenas localmente")
            print(f"{k:<20} | Presente (ID {loc['id']})   | ❌ Ausente         | ⚠️ PENDENTE PROD")
        else:
            divergencias.append(f"{k} existe apenas na produção")
            print(f"{k:<20} | ❌ Ausente         | Presente (ID {rem['id']})   | ⚠️ PENDENTE LOCAL")

    print("-" * 70)
    if not divergencias and len(local_u) == len(remote_u) and len(local_u) > 0:
        print("🎉 100% PAREADO: Os bancos local e produção estão rigorosamente idênticos!")
        return True
    else:
        print(f"⚠️ {len(divergencias)} DIVERGÊNCIAS DETECTADAS:")
        for d in divergencias:
            print(f"   - {d}")
        print("\nPara sincronizar use:")
        print("   python3 scripts/sync_db.py --pull  (Produção ➔ Local)")
        print("   python3 scripts/sync_db.py --push  (Local ➔ Produção)")
        return False


def pull_db():
    print(f"📥 Baixando banco de dados de produção ({REMOTE_HOST}) para o ambiente local...")
    LOCAL_PATH.mkdir(parents=True, exist_ok=True)
    local_db = LOCAL_PATH / "auth.db"

    # Backup local preventivo
    if local_db.exists():
        bkp = LOCAL_PATH / f"auth.db.local.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(local_db, bkp)
        print(f"   [+] Backup local gerado: {bkp.name}")

    # Transferência
    cmd = ["scp", "-p", f"{REMOTE_HOST}:{REMOTE_PATH}/auth.db", str(local_db)]
    subprocess.run(cmd, check=True)

    # Copia filtros.json se existir
    subprocess.run(["scp", "-p", f"{REMOTE_HOST}:{REMOTE_PATH}/filtros.json", str(LOCAL_PATH / "filtros.json")], stderr=subprocess.DEVNULL)

    print("✅ Download concluído com sucesso!")
    check_status()


def push_db():
    local_db = LOCAL_PATH / "auth.db"
    if not local_db.exists():
        print("❌ Arquivo auth.db local não existe. Impossível enviar.")
        sys.exit(1)

    print(f"📤 Enviando banco de dados local para produção ({REMOTE_HOST})...")

    # Backup remoto preventivo
    bkp_cmd = [
        "ssh", REMOTE_HOST,
        f"cp {REMOTE_PATH}/auth.db {REMOTE_PATH}/auth.db.prod.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')} 2>/dev/null || true"
    ]
    subprocess.run(bkp_cmd, check=True)
    print("   [+] Backup remoto preventivo realizado.")

    # Transferência
    cmd = ["scp", "-p", str(local_db), f"{REMOTE_HOST}:{REMOTE_PATH}/auth.db"]
    subprocess.run(cmd, check=True)

    local_filtros = LOCAL_PATH / "filtros.json"
    if local_filtros.exists():
        subprocess.run(["scp", "-p", str(local_filtros), f"{REMOTE_HOST}:{REMOTE_PATH}/filtros.json"], check=False)

    print("✅ Upload para produção concluído com sucesso!")
    check_status()


def main():
    parser = argparse.ArgumentParser(description="egSYS JiraView — Pareamento e Sincronização de Bancos SQLite")
    parser.add_argument("--status", action="store_true", help="Verifica paridade entre bancos local e produção")
    parser.add_argument("--pull", action="store_true", help="Baixa o banco de dados da produção para o local")
    parser.add_argument("--push", action="store_true", help="Envia o banco de dados local para a produção")

    args = parser.parse_args()

    if args.pull:
        pull_db()
    elif args.push:
        push_db()
    elif args.status:
        check_status()
    else:
        check_status()


if __name__ == "__main__":
    main()
