# egSYS JiraView — Banco de Dados Ultraleve (SQLite Nativo)
# Gerenciamento de credenciais locais, estados atendidos e roteamento de painéis.
import os
import sqlite3
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, List

# Diretório padrão para o arquivo SQLite (suporta volume de produção /app/data)
_DEFAULT_LOCAL_DIR = Path(__file__).parent.parent.parent / "data"
_DATA_DIR_ENV = os.getenv("JIRAVIEW_DATA")
if _DATA_DIR_ENV:
    _DATA_DIR = Path(_DATA_DIR_ENV)
elif Path("/app/data").exists() or Path("/app").exists():
    _DATA_DIR = Path("/app/data")
else:
    _DATA_DIR = _DEFAULT_LOCAL_DIR

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
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'manager',
                    estado TEXT NOT NULL DEFAULT 'sc',
                    painel_url TEXT NOT NULL DEFAULT '/painel_sc',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    must_change_password INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Migração automática: adiciona coluna must_change_password caso a tabela já exista
            try:
                conn.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 1;")
            except Exception:
                pass

            # Verifica se já há usuários cadastrados
            cur = conn.execute("SELECT COUNT(*) as total FROM users;")
            row = cur.fetchone()
            if row and row["total"] == 0:
                _seed_initial_users(conn)
    finally:
        conn.close()


def _seed_initial_users(conn: sqlite3.Connection):
    """Popula os usuários padrão para direcionamento dos painéis."""
    initial_users = [
        (
            "coordenador",
            hash_password("egsys@coordenador2026"),
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
        cur = conn.execute("SELECT id, username, nome, role, estado, painel_url, is_active, must_change_password, created_at FROM users ORDER BY id;")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Obtém registro do usuário por ID."""
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT id, username, nome, role, estado, painel_url, is_active, must_change_password, created_at FROM users WHERE id = ?;", (user_id,))
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
                INSERT INTO users (username, password_hash, nome, role, estado, painel_url, is_active, must_change_password)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (username, pwd_hash, nome.strip(), role.strip(), estado.strip().lower(), painel_url.strip(), is_active, 1 if must_change_password else 0))
            new_id = cur.lastrowid
        return get_user_by_id(new_id)
    finally:
        conn.close()


def update_user(
    user_id: int,
    nome: Optional[str] = None,
    role: Optional[str] = None,
    estado: Optional[str] = None,
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


# Inicializa o banco no import do módulo
init_db()

