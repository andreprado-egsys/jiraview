# egSYS JiraView — FastAPI entrypoint (padrão Orion: headers defensivos + RBAC)
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .core.config import get_settings
from .core.security import TokenPayload, get_current_user, jsm
from .api.v1 import router as v1_router
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="egSYS JiraView", version="0.1.0")


class DefensiveHeaders(BaseHTTPMiddleware):
    """ACH-011 (Orion): HSTS, X-Frame-Options DENY, nosniff, CSP, Referrer-Policy."""

    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
        if get_settings().app_env == "prod":
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return resp


app.add_middleware(DefensiveHeaders)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization"],
)


@app.get("/api/v1/health")
async def health():
    ok = await jsm().health()
    return {"status": "ok" if ok else "degraded", "jira": ok}


@app.get("/api/v1/overview")
async def overview(user: TokenPayload = Depends(get_current_user)):
    """Solicitações do estado do usuário (role viewer+)."""
    states = await jsm().search(
        f'project in (HDPMSC, SCPMH) AND resolution is EMPTY ORDER BY updated DESC',
        max_results=50,
    )
    return {"role": user.role, "state": user.state, "issues": states}

app.include_router(v1_router)


@app.post("/api/v1/demo-token")
async def demo_token():
    """DEV ONLY — em produção a auth é por credencial/RFBAC com refresh."""
    from .core.security import create_access_token
    return {"token": create_access_token("andre", "manager", "sc")}


_FRONTEND = Path(__file__).parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")
