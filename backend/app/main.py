# egSYS JiraView — FastAPI entrypoint (padrão Orion: headers defensivos + RBAC + Login Unitário)
from pathlib import Path
from fastapi import FastAPI, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .core.config import get_settings
from .core.security import TokenPayload, get_current_user, jsm
from .core.estados import estado_por_sigla
from .api.v1 import router as v1_router
from .api.auth import router as auth_router

settings = get_settings()
is_prod = settings.app_env == "prod"

app = FastAPI(
    title="egSYS JiraView",
    version="0.2.0",
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)


class DefensiveHeaders(BaseHTTPMiddleware):
    """ACH-011 (Orion): HSTS, X-Frame-Options DENY, nosniff, CSP, Referrer-Policy e Hardening."""

    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        resp.headers["X-Frame-Options"] = "SAMEORIGIN"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = "frame-ancestors 'self'"
        resp.headers["Server"] = "egSYS-Shield"
        resp.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if is_prod:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        return resp


app.add_middleware(DefensiveHeaders)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(v1_router)

# Suporte universal com e sem stripPrefix do Traefik
app.include_router(auth_router, prefix="/painel_sc")
app.include_router(v1_router, prefix="/painel_sc")


@app.get("/api/v1/health")
async def health():
    ok = await jsm().health()
    return {"status": "ok" if ok else "degraded", "jira": ok}


@app.get("/api/v1/overview")
async def overview(user: TokenPayload = Depends(get_current_user)):
    """Solicitações do estado do usuário (role viewer+)."""
    cfg = estado_por_sigla(user.state)
    projetos = ", ".join(cfg["projects"]) if cfg and cfg.get("projects") else "HDPMSC"
    states = await jsm().search(
        f"project in ({projetos}) AND resolution is EMPTY ORDER BY updated DESC",
        max_results=50,
    )
    return {"role": user.role, "state": user.state, "issues": states}


_FRONTEND = Path(__file__).parent.parent.parent / "frontend"


@app.api_route("/login", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/login/", methods=["GET", "HEAD"], include_in_schema=False)
async def login_page():
    """Tela de login unitária para autenticação e direcionamento por estado."""
    return FileResponse(_FRONTEND / "login.html")


@app.api_route("/painel_sc", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/painel_sc/", methods=["GET", "HEAD"], include_in_schema=False)
async def painel_sc_page():
    """Painel do cliente Santa Catarina (PMSC)."""
    return FileResponse(_FRONTEND / "index.html")


@app.api_route("/coordenador", methods=["GET", "HEAD"], include_in_schema=False)
@app.api_route("/coordenador/", methods=["GET", "HEAD"], include_in_schema=False)
async def coordenador_page():
    """Painel do Coordenador de Suporte."""
    coordenador_file = _FRONTEND / "coordenador.html"
    if coordenador_file.exists():
        return FileResponse(coordenador_file)
    return RedirectResponse(url="/painel_sc")


# Redirecionamento da raiz caso acesse diretamente
@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
async def root_redirect():
    """Acesso raiz direciona para a tela de login unitária."""
    return FileResponse(_FRONTEND / "login.html")


app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")
