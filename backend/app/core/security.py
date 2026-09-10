# egSYS JiraView — Segurança: RBAC + serviços JSM read-only
from typing import Annotated, Literal, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import get_settings

Role = Literal["viewer", "manager", "admin", "coordenador"]

ROLE_LEVEL = {"viewer": 1, "manager": 2, "admin": 3, "coordenador": 3}


class TokenPayload(BaseModel):
    sub: str
    role: str = "viewer"
    state: str = "sc"
    nome: Optional[str] = None
    painel_url: Optional[str] = None
    must_change_password: bool = False
    exp: int = 0


class JSMService:
    """Client read-only da API Jira (padrão Orion: zero credencial no client)."""

    def __init__(self):
        self._s = get_settings()

    def _basic(self) -> dict:
        import base64

        raw = f"{self._s.jira_user}:{self._s.jira_token}".encode()
        return {"Authorization": "Basic " + base64.b64encode(raw).decode()}

    async def health(self) -> bool:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(
                    f"{self._s.jira_url}/rest/api/3/myself",
                    headers=self._basic(),
                )
                return r.status_code == 200
        except Exception:
            return False

    async def search(self, jql: str, max_results: int = 25,
                     fields: str = "summary,status,resolution,assignee,created,updated,priority,reporter,duedate,issuetype",
                     start_at: int = 0,
                     ) -> list[dict]:
        import httpx

        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(
                f"{self._s.jira_url}/rest/api/3/search/jql",
                params={"jql": jql,
                        "maxResults": min(max_results, 100),
                        "startAt": start_at,
                        "fields": fields},
                headers=self._basic(),
            )
            r.raise_for_status()
            return r.json().get("issues", [])


def create_access_token(
    sub: str,
    role: str = "viewer",
    state: str = "sc",
    nome: Optional[str] = None,
    painel_url: Optional[str] = None,
    must_change_password: bool = False,
) -> str:
    from datetime import datetime, timedelta, timezone

    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.access_token_expire_minutes)
    payload = {
        "sub": sub,
        "role": role,
        "state": state,
        "nome": nome or sub,
        "painel_url": painel_url or "/painel_sc",
        "must_change_password": bool(must_change_password),
        "exp": exp,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, s.secret_key, algorithm="HS256")


_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    cred: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> TokenPayload:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticação necessária")
    s = get_settings()
    try:
        payload = jwt.decode(cred.credentials, s.secret_key, algorithms=["HS256"])
        return TokenPayload(**payload)
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido/expirado")


def require_role(min_role: Role):
    def check(user: Annotated[TokenPayload, Depends(get_current_user)]):
        if ROLE_LEVEL[user.role] < ROLE_LEVEL[min_role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente")
        return user

    return check


def jsm() -> JSMService:
    return JSMService()
