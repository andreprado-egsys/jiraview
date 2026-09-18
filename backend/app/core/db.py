# egSYS JiraView — Banco de Dados Ultraleve (SQLite Nativo)
# Gerenciamento de credenciais locais, estados atendidos e roteamento de painéis.
import os
import sqlite3
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, List

# Diretório padrão para o arquivo SQLite (suporta volume de produção /app/data ou ./data)
_DATA_DIR_ENV = os.getenv("JIRAVIEW_DATA")
if _DATA_DIR_ENV:
    _DATA_DIR = Path(_DATA_DIR_ENV)
elif Path("/app/data").exists():
    _DATA_DIR = Path("/app/data")
elif (Path(__file__).resolve().parents[3] / "data").exists():
    _DATA_DIR = Path(__file__).resolve().parents[3] / "data"
else:
    _DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_DB_PATH = Path(os.getenv("AUTH_DB_PATH", _DATA_DIR / "auth.db"))


def _get_connection() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Gera hash PBKDF2-HMAC-SHA256 padrão NIST (100.000 iterações)."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verifica se a senha em texto plano confere com o hash armazenado."""
    try:
        salt, key_hex = hashed.split('$', 1)
        computed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return secrets.compare_digest(key_hex, computed)
    except Exception:
        return False


def init_db():
    """Inicializa tabelas do SQLite e popula usuários iniciais caso não existam."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'manager',
                estado TEXT NOT NULL DEFAULT 'sc',
                espacos TEXT DEFAULT '',
                painel_url TEXT NOT NULL DEFAULT '/painel_sc',
                is_active INTEGER NOT NULL DEFAULT 1,
                must_change_password INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

        # Inspeciona colunas existentes para migração idempotente
        cur = conn.execute("PRAGMA table_info(users);")
        colunas = [r["name"] for r in cur.fetchall()]

        if "must_change_password" not in colunas:
            conn.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 1;")
            conn.commit()

        if "espacos" not in colunas:
            conn.execute("ALTER TABLE users ADD COLUMN espacos TEXT DEFAULT '';")
            conn.commit()

        if "modulos_ativos" not in colunas:
            conn.execute("ALTER TABLE users ADD COLUMN modulos_ativos TEXT DEFAULT '';")
            conn.commit()
            conn.execute("UPDATE users SET modulos_ativos = 'visao_gerencial,analise_dev,relatorio_email,certificados_alert' WHERE role = 'admin' OR username IN ('coordenador', 'admin');")
            conn.commit()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS certificates_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                host TEXT NOT NULL,
                state TEXT NOT NULL,
                status TEXT NOT NULL,
                dias_restantes INTEGER NOT NULL,
                valid_from TEXT,
                valid_until TEXT,
                issuer TEXT,
                padrao TEXT DEFAULT 'Let''s Encrypt',
                tipo_renovacao TEXT DEFAULT 'Automática Traefik (TLS-ALPN-01)',
                precisa_token TEXT DEFAULT 'Não (Automático)',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(domain, host) ON CONFLICT REPLACE
            );
        """)
        conn.commit()

        # Inspeciona colunas de certificates_status para migração idempotente
        cur_cert = conn.execute("PRAGMA table_info(certificates_status);")
        col_cert = [r["name"] for r in cur_cert.fetchall()]
        if "valid_from" not in col_cert:
            conn.execute("ALTER TABLE certificates_status ADD COLUMN valid_from TEXT;")
        if "padrao" not in col_cert:
            conn.execute("ALTER TABLE certificates_status ADD COLUMN padrao TEXT DEFAULT 'Let''s Encrypt';")
        if "tipo_renovacao" not in col_cert:
            conn.execute("ALTER TABLE certificates_status ADD COLUMN tipo_renovacao TEXT DEFAULT 'Automática Traefik (TLS-ALPN-01)';")
        if "precisa_token" not in col_cert:
            conn.execute("ALTER TABLE certificates_status ADD COLUMN precisa_token TEXT DEFAULT 'Não (Automático)';")
        conn.commit()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,
                destinatarios TEXT NOT NULL,
                total_tarefas INTEGER DEFAULT 0,
                status_envio TEXT NOT NULL,
                mensagem TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                relatorio_executivo INTEGER DEFAULT 1,
                alertas_certificados INTEGER DEFAULT 1,
                ativo INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS noc_layouts (
                tipo TEXT PRIMARY KEY,
                num_cols TEXT DEFAULT '3',
                columns_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

        # Seed inicial de destinatários se tabela estiver vazia
        cur_rec = conn.execute("SELECT COUNT(*) as total FROM email_recipients;")
        if cur_rec.fetchone()["total"] == 0:
            conn.execute("""
                INSERT INTO email_recipients (nome, email, relatorio_executivo, alertas_certificados, ativo)
                VALUES 
                ('André Prado', 'andre.prado@egsys.com.br', 1, 1, 1),
                ('Coordenação de Suporte egSYS', 'coordenacao@egsys.com.br', 1, 1, 1);
            """)
            conn.commit()

        # Verifica se já há usuários cadastrados
        cur = conn.execute("SELECT COUNT(*) as total FROM users;")
        row = cur.fetchone()
        if row and row["total"] == 0:
            _seed_initial_users(conn)
            conn.commit()
        else:
            # Garante que o usuário de demonstração Mazzola (com múltiplos espaços) exista
            cur_m = conn.execute("SELECT id FROM users WHERE username = 'mazzola';")
            if not cur_m.fetchone():
                conn.execute("""
                    INSERT INTO users (username, password_hash, nome, role, estado, espacos, painel_url, is_active, must_change_password)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    "mazzola",
                    hash_password("egsys@mazzola2026"),
                    "João Mário Mazzola",
                    "manager",
                    "sc",
                    "HDPMSC,SSC",
                    "/painel_sc",
                    1,
                    0
                ))
                conn.commit()

            # Garante que o usuário monitor (Kiosk TV da sala do suporte) exista
            cur_mon = conn.execute("SELECT id FROM users WHERE username = 'monitor';")
            if not cur_mon.fetchone():
                conn.execute("""
                    INSERT INTO users (username, password_hash, nome, role, estado, espacos, modulos_ativos, painel_url, is_active, must_change_password)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    "monitor",
                    hash_password("egsys@monitor2026"),
                    "Monitor NOC Suporte (TV/Kiosk)",
                    "monitor",
                    "todos",
                    "",
                    "analise_dev,triagem_n1n2,certificados_alert",
                    "/coordenador",
                    1,
                    0
                ))
                conn.commit()
    finally:
        conn.close()


def _seed_initial_users(conn: sqlite3.Connection):
    """Popula os usuários padrão para direcionamento dos painéis."""
    initial_users = [
        (
            "coordenador",
            hash_password("egsys!@#$0000"),
            "Coordenação de Suporte egSYS",
            "admin",
            "todos",
            "/coordenador",
            1,
            0  # Coordenador já inicia sem pendência de troca
        ),
        (
            "admin",
            hash_password("admin@egsys2026"),
            "Administrador Geral egSYS",
            "admin",
            "todos",
            "/coordenador",
            1,
            0
        ),
        (
            "gestor.sc",
            hash_password("egsys@sc2026"),
            "Gestão PMSC (Santa Catarina)",
            "manager",
            "sc",
            "/painel_sc",
            1,
            1  # Gestor estadual exige troca no primeiro acesso
        ),
        (
            "gestor.to",
            hash_password("egsys@to2026"),
            "Gestão PMTO (Tocantins)",
            "manager",
            "to",
            "/painel_to",
            1,
            1
        ),
        (
            "gestor.am",
            hash_password("egsys@am2026"),
            "Gestão PMAM (Amazonas)",
            "manager",
            "am",
            "/painel_am",
            1,
            1
        ),
        (
            "gestor.ro",
            hash_password("egsys@ro2026"),
            "Gestão SESDEC (Rondônia)",
            "manager",
            "ro",
            "/painel_ro",
            1,
            1
        ),
        (
            "gestor.pr",
            hash_password("egsys@pr2026"),
            "Gestão PMPR (Paraná)",
            "manager",
            "pr",
            "/painel_pr",
            1,
            1
        ),
        (
            "gestor.mt",
            hash_password("egsys@mt2026"),
            "Gestão PMMT (Mato Grosso)",
            "manager",
            "mt",
            "/painel_mt",
            1,
            1
        ),
        (
            "gestor.gm",
            hash_password("egsys@gm2026"),
            "Gestão Guardas Municipais",
            "manager",
            "gm",
            "/painel_gm",
            1,
            1
        ),
        (
            "monitor",
            hash_password("egsys@monitor2026"),
            "Monitor NOC Suporte (TV/Kiosk)",
            "monitor",
            "todos",
            "/coordenador",
            1,
            0
        ),
    ]

    conn.executemany("""
        INSERT INTO users (username, password_hash, nome, role, estado, painel_url, is_active, must_change_password)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """, initial_users)


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Obtém registro do usuário por username."""
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE;", (username.strip(),))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Autentica usuário e retorna seus dados caso ativo e credenciais válidas."""
    user = get_user_by_username(username)
    if not user:
        return None
    if not user.get("is_active"):
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def list_users() -> List[Dict[str, Any]]:
    """Lista usuários cadastrados (sem password_hash)."""
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT id, username, nome, role, estado, espacos, modulos_ativos, painel_url, is_active, must_change_password, created_at FROM users ORDER BY id;")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Obtém registro do usuário por ID."""
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT id, username, nome, role, estado, espacos, modulos_ativos, painel_url, is_active, must_change_password, created_at FROM users WHERE id = ?;", (user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        conn.close()


def create_user(
    username: str,
    password: str,
    nome: str,
    role: str = "manager",
    estado: str = "sc",
    espacos: str = "",
    modulos_ativos: str = "",
    painel_url: str = "/painel_sc",
    is_active: int = 1,
    must_change_password: int = 1,
) -> Dict[str, Any]:
    """Cria um novo usuário com senha criptografada e pendência de troca."""
    username = username.strip().lower()
    if get_user_by_username(username):
        raise ValueError(f"Usuário '{username}' já existe no sistema.")

    pwd_hash = hash_password(password)
    conn = _get_connection()
    try:
        with conn:
            cur = conn.execute("""
                INSERT INTO users (username, password_hash, nome, role, estado, espacos, modulos_ativos, painel_url, is_active, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (username, pwd_hash, nome.strip(), role.strip(), estado.strip().lower(), espacos.strip().upper(), modulos_ativos.strip(), painel_url.strip(), is_active, 1 if must_change_password else 0))
            new_id = cur.lastrowid
        return get_user_by_id(new_id)
    finally:
        conn.close()


def update_user(
    user_id: int,
    nome: Optional[str] = None,
    role: Optional[str] = None,
    estado: Optional[str] = None,
    espacos: Optional[str] = None,
    modulos_ativos: Optional[str] = None,
    painel_url: Optional[str] = None,
    is_active: Optional[int] = None,
    must_change_password: Optional[int] = None,
    password: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Atualiza dados cadastrais ou redefine senha do usuário."""
    user = get_user_by_id(user_id)
    if not user:
        return None

    fields = []
    values = []

    if nome is not None:
        fields.append("nome = ?")
        values.append(nome.strip())
    if role is not None:
        fields.append("role = ?")
        values.append(role.strip())
    if estado is not None:
        fields.append("estado = ?")
        values.append(estado.strip().lower())
    if espacos is not None:
        fields.append("espacos = ?")
        values.append(espacos.strip().upper())
    if modulos_ativos is not None:
        fields.append("modulos_ativos = ?")
        values.append(modulos_ativos.strip())
    if painel_url is not None:
        fields.append("painel_url = ?")
        values.append(painel_url.strip())
    if is_active is not None:
        fields.append("is_active = ?")
        values.append(1 if is_active else 0)
    if must_change_password is not None:
        fields.append("must_change_password = ?")
        values.append(1 if must_change_password else 0)
    if password is not None and password.strip():
        fields.append("password_hash = ?")
        values.append(hash_password(password.strip()))

    if not fields:
        return user

    values.append(user_id)
    query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?;"

    conn = _get_connection()
    try:
        with conn:
            conn.execute(query, tuple(values))
        return get_user_by_id(user_id)
    finally:
        conn.close()


def upsert_certificate(
    domain: str,
    host: str,
    state: str,
    status: str,
    dias_restantes: int,
    valid_from: Optional[str] = None,
    valid_until: Optional[str] = None,
    issuer: Optional[str] = None,
    padrao: Optional[str] = None,
    tipo_renovacao: Optional[str] = None,
    precisa_token: Optional[str] = None,
) -> None:
    """Insere ou atualiza status de certificado SSL no SQLite."""
    conn = _get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO certificates_status (
                    domain, host, state, status, dias_restantes, valid_from, valid_until,
                    issuer, padrao, tipo_renovacao, precisa_token, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(domain, host) DO UPDATE SET
                    state = excluded.state,
                    status = excluded.status,
                    dias_restantes = excluded.dias_restantes,
                    valid_from = COALESCE(excluded.valid_from, certificates_status.valid_from),
                    valid_until = excluded.valid_until,
                    issuer = COALESCE(excluded.issuer, certificates_status.issuer),
                    padrao = COALESCE(excluded.padrao, certificates_status.padrao),
                    tipo_renovacao = COALESCE(excluded.tipo_renovacao, certificates_status.tipo_renovacao),
                    precisa_token = COALESCE(excluded.precisa_token, certificates_status.precisa_token),
                    updated_at = CURRENT_TIMESTAMP;
            """, (
                domain.strip(),
                host.strip(),
                state.strip().upper(),
                status.strip().upper(),
                int(dias_restantes),
                valid_from,
                valid_until,
                issuer,
                padrao or "Let's Encrypt (DV X.509 RSA/ECC)",
                tipo_renovacao or "Automática Traefik (TLS-ALPN-01)",
                precisa_token or "Não (Automático Traefik)",
            ))
    finally:
        conn.close()


def sync_traefik_acme_certificates(acme_paths: Optional[List[str]] = None) -> int:
    """Lê acme.json do Traefik e sincroniza os certificados Let's Encrypt na base."""
    import base64
    import json
    from datetime import datetime, timezone
    from pathlib import Path

    try:
        from cryptography import x509
    except ImportError:
        x509 = None

    if not acme_paths:
        acme_paths = [
            "/app/data/acme.json",
            "/var/egsys-docker/container/traefik/acme.json",
            "/etc/traefik/acme.json",
        ]

    target_file = None
    for p in acme_paths:
        if Path(p).is_file():
            target_file = p
            break

    if not target_file:
        return 0

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[CertSync] Erro ao ler {target_file}: {e}")
        return 0

    total_sincronizados = 0
    agora = datetime.now(timezone.utc)

    for resolver_name, res in data.items():
        certs = res.get("Certificates", []) if isinstance(res, dict) else []
        for c in certs:
            domain_meta = c.get("domain", {})
            main = domain_meta.get("main")
            if not main:
                continue

            valid_from_str = None
            valid_until_str = None
            dias_restantes = 90
            issuer_desc = "Let's Encrypt"

            cert_b64 = c.get("certificate", "")
            if cert_b64 and x509:
                try:
                    cert_bytes = base64.b64decode(cert_b64)
                    cert_obj = x509.load_pem_x509_certificate(cert_bytes)
                    nb = getattr(cert_obj, "not_valid_before_utc", None) or cert_obj.not_valid_before.replace(tzinfo=timezone.utc)
                    na = getattr(cert_obj, "not_valid_after_utc", None) or cert_obj.not_valid_after.replace(tzinfo=timezone.utc)

                    valid_from_str = nb.strftime("%d/%m/%Y")
                    valid_until_str = na.strftime("%d/%m/%Y")
                    dias_restantes = (na - agora).days

                    iss_comps = cert_obj.issuer.rdns
                    iss_names = [attr.value for rdn in iss_comps for attr in rdn if hasattr(attr, "value")]
                    if iss_names:
                        issuer_desc = f"Let's Encrypt ({iss_names[0]})"
                except Exception as ex:
                    print(f"[CertSync] Erro decodificando cert {main}: {ex}")

            # Identificação de padrões e exigência de tokens
            padrao = "Let's Encrypt (DV X.509 RSA/ECC)"
            if "duckdns.org" in main:
                precisa_token = "Sim (Token DuckDNS)"
                tipo_renovacao = "ACME DNS-01 / DuckDNS Token"
                estado = "INFRA"
            elif ".com.br" in main:
                precisa_token = "Sim (Token Registro.br / DNS)"
                tipo_renovacao = "ACME HTTP-01 / DNS-01 (Registro.br)"
                estado = "CORP"
            elif ".gov.br" in main:
                precisa_token = "Não (Institucional Gov)"
                tipo_renovacao = "Manual / CIASC DITI"
                estado = "GOV"
            else:
                precisa_token = "Não (Automático Traefik)"
                tipo_renovacao = "ACME TLS-ALPN-01 (Traefik 443)"
                estado = "INFRA"

            if dias_restantes <= 0:
                status_calc = "VENCIDO"
            elif dias_restantes <= 15:
                status_calc = "CRITICO"
            elif dias_restantes <= 30:
                status_calc = "ALERTA"
            else:
                status_calc = "OK"

            upsert_certificate(
                domain=main,
                host="monitoramento-egsys (Traefik)",
                state=estado,
                status=status_calc,
                dias_restantes=dias_restantes,
                valid_from=valid_from_str,
                valid_until=valid_until_str,
                issuer=issuer_desc,
                padrao=padrao,
                tipo_renovacao=tipo_renovacao,
                precisa_token=precisa_token,
            )
            total_sincronizados += 1

    return total_sincronizados


def list_certificates() -> List[Dict[str, Any]]:
    """Retorna listagem de certificados SSL monitorados."""
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT * FROM certificates_status ORDER BY dias_restantes ASC, state ASC;")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def log_report_history(tipo: str, destinatarios: str, total_tarefas: int, status_envio: str, mensagem: str = "") -> None:
    """Registra histórico de disparo de relatórios corporativos."""
    conn = _get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO reports_history (tipo, destinatarios, total_tarefas, status_envio, mensagem)
                VALUES (?, ?, ?, ?, ?);
            """, (tipo, destinatarios, int(total_tarefas), status_envio, mensagem))
    finally:
        conn.close()


def list_reports_history(limit: int = 20) -> List[Dict[str, Any]]:
    """Retorna histórico dos últimos disparos de relatórios."""
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT * FROM reports_history ORDER BY id DESC LIMIT ?;", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def change_user_password(username_or_id: Any, new_password: str) -> Optional[Dict[str, Any]]:
    """Atualiza a senha do usuário e remove a pendência de primeiro acesso (must_change_password = 0)."""
    if isinstance(username_or_id, int) or (isinstance(username_or_id, str) and username_or_id.isdigit()):
        user = get_user_by_id(int(username_or_id))
    else:
        user = get_user_by_username(str(username_or_id))

    if not user:
        return None

    pwd_hash = hash_password(new_password)
    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?;",
                (pwd_hash, user["id"]),
            )
        return get_user_by_id(user["id"])
    finally:
        conn.close()


def delete_user(user_id: int) -> bool:
    """Remove usuário do banco SQLite."""
    conn = _get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM users WHERE id = ?;", (user_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


def list_email_recipients(tipo: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna lista de destinatários de e-mail cadastrados."""
    conn = _get_connection()
    try:
        if tipo == "relatorio_executivo":
            cur = conn.execute("SELECT * FROM email_recipients WHERE ativo = 1 AND relatorio_executivo = 1 ORDER BY nome ASC;")
        elif tipo == "alertas_certificados":
            cur = conn.execute("SELECT * FROM email_recipients WHERE ativo = 1 AND alertas_certificados = 1 ORDER BY nome ASC;")
        else:
            cur = conn.execute("SELECT * FROM email_recipients ORDER BY ativo DESC, nome ASC;")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def upsert_email_recipient(
    nome: str,
    email: str,
    relatorio_executivo: bool = True,
    alertas_certificados: bool = True,
    ativo: bool = True,
) -> int:
    """Insere ou atualiza destinatário de e-mail."""
    conn = _get_connection()
    try:
        with conn:
            cur = conn.execute("""
                INSERT INTO email_recipients (nome, email, relatorio_executivo, alertas_certificados, ativo)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    nome = excluded.nome,
                    relatorio_executivo = excluded.relatorio_executivo,
                    alertas_certificados = excluded.alertas_certificados,
                    ativo = excluded.ativo;
            """, (
                nome.strip(),
                email.strip().lower(),
                1 if relatorio_executivo else 0,
                1 if alertas_certificados else 0,
                1 if ativo else 0,
            ))
            return cur.lastrowid
    finally:
        conn.close()


def update_email_recipient(
    recipient_id: int,
    nome: Optional[str] = None,
    email: Optional[str] = None,
    relatorio_executivo: Optional[bool] = None,
    alertas_certificados: Optional[bool] = None,
    ativo: Optional[bool] = None,
) -> bool:
    """Atualiza seletivamente as opções de um destinatário de e-mail."""
    conn = _get_connection()
    try:
        with conn:
            cur = conn.execute("SELECT * FROM email_recipients WHERE id = ?;", (recipient_id,))
            rec = cur.fetchone()
            if not rec:
                return False

            n_nome = nome.strip() if nome is not None else rec["nome"]
            n_email = email.strip().lower() if email is not None else rec["email"]
            n_rel = (1 if relatorio_executivo else 0) if relatorio_executivo is not None else rec["relatorio_executivo"]
            n_cert = (1 if alertas_certificados else 0) if alertas_certificados is not None else rec["alertas_certificados"]
            n_ativo = (1 if ativo else 0) if ativo is not None else rec["ativo"]

            conn.execute("""
                UPDATE email_recipients 
                SET nome = ?, email = ?, relatorio_executivo = ?, alertas_certificados = ?, ativo = ?
                WHERE id = ?;
            """, (n_nome, n_email, n_rel, n_cert, n_ativo, recipient_id))
            return True
    finally:
        conn.close()


def delete_email_recipient(recipient_id: int) -> bool:
    """Remove destinatário de e-mail."""
    conn = _get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM email_recipients WHERE id = ?;", (recipient_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


def get_noc_layout(tipo: str) -> Optional[Dict[str, Any]]:
    """Recupera o layout personalizado de colunas e cards de um módulo NOC."""
    import json
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT num_cols, columns_json FROM noc_layouts WHERE tipo = ?;", (tipo,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "numCols": row["num_cols"],
            "columns": json.loads(row["columns_json"])
        }
    except Exception as e:
        print(f"Erro ao ler layout {tipo}: {e}")
        return None
    finally:
        conn.close()


def save_noc_layout(tipo: str, num_cols: str, columns: list) -> bool:
    """Persiste o layout personalizado de colunas e cards de um módulo NOC no SQLite."""
    import json
    conn = _get_connection()
    try:
        with conn:
            conn.execute("""
                INSERT INTO noc_layouts (tipo, num_cols, columns_json, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(tipo) DO UPDATE SET
                    num_cols = excluded.num_cols,
                    columns_json = excluded.columns_json,
                    updated_at = CURRENT_TIMESTAMP;
            """, (tipo, str(num_cols), json.dumps(columns)))
            return True
    except Exception as e:
        print(f"Erro ao salvar layout {tipo}: {e}")
        return False
    finally:
        conn.close()


# Inicializa o banco no import do módulo
init_db()

