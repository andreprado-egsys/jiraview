# egSYS JiraView — Autenticação Unitária & Roteamento de Painéis
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..core.db import authenticate_user, get_user_by_username, change_user_password
from ..core.security import create_access_token, get_current_user, TokenPayload

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    nome: str
    role: str
    estado: str
    painel_url: str
    must_change_password: bool = False


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    redirect_url: str
    user: UserInfo


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """Autentica usuário local e retorna token com URL de redirecionamento para seu painel."""
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas ou usuário inativo",
            headers={"WWW-Authenticate": "Bearer"},
        )

    must_change = bool(user.get("must_change_password", 0))

    token = create_access_token(
        sub=user["username"],
        role=user["role"],
        state=user["estado"],
        nome=user["nome"],
        painel_url=user["painel_url"],
        must_change_password=must_change,
    )

    return LoginResponse(
        token=token,
        token_type="bearer",
        redirect_url=user["painel_url"],
        user=UserInfo(
            username=user["username"],
            nome=user["nome"],
            role=user["role"],
            estado=user["estado"],
            painel_url=user["painel_url"],
            must_change_password=must_change,
        )
    )


class ChangePasswordRequest(BaseModel):
    new_password: str
    current_password: Optional[str] = None


@router.post("/change-password")
async def change_password_endpoint(
    req: ChangePasswordRequest,
    current_user: TokenPayload = Depends(get_current_user),
):
    """Atualiza a senha do próprio usuário autenticado (1º acesso ou redefinição)."""
    if len(req.new_password.strip()) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha deve possuir no mínimo 6 caracteres.",
        )

    updated_user = change_user_password(current_user.sub, req.new_password.strip())
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    # Gera novo token com must_change_password = False
    new_token = create_access_token(
        sub=updated_user["username"],
        role=updated_user["role"],
        state=updated_user["estado"],
        nome=updated_user["nome"],
        painel_url=updated_user["painel_url"],
        must_change_password=False,
    )

    return {
        "status": "ok",
        "message": "Senha alterada com sucesso!",
        "token": new_token,
        "user": {
            "username": updated_user["username"],
            "nome": updated_user["nome"],
            "role": updated_user["role"],
            "estado": updated_user["estado"],
            "painel_url": updated_user["painel_url"],
            "must_change_password": False,
        }
    }


@router.get("/me", response_model=Dict[str, Any])
async def me(user: TokenPayload = Depends(get_current_user)):
    """Retorna dados do usuário atualmente autenticado via Bearer token."""
    db_user = get_user_by_username(user.sub)
    if db_user:
        return {
            "username": db_user["username"],
            "nome": db_user["nome"],
            "role": db_user["role"],
            "estado": db_user["estado"],
            "painel_url": db_user["painel_url"],
            "must_change_password": bool(db_user.get("must_change_password", 0)),
        }
    return {
        "username": user.sub,
        "nome": user.nome or user.sub,
        "role": user.role,
        "estado": user.state,
        "painel_url": user.painel_url or "/painel_sc",
        "must_change_password": user.must_change_password,
    }

from ..core.db import (
    list_users as db_list_users,
    create_user as db_create_user,
    update_user as db_update_user,
    delete_user as db_delete_user,
    get_user_by_id as db_get_user_by_id,
)


def require_admin_or_coordinator(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
    """Verifica se o usuário tem privilégio de gestão de acessos."""
    if user.role in ("admin", "coordenador") or user.sub in ("coordenador", "admin") or user.state == "todos":
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Acesso restrito à Coordenação de Suporte ou Administrador Geral. Usuário conectado: '{user.sub}' (perfil: '{user.role}', estado: '{user.state}'). Faça login com 'coordenador'.",
    )


class CreateUserRequest(BaseModel):
    username: str
    password: str
    nome: str
    role: str = "manager"
    estado: str = "sc"
    painel_url: str = "/painel_sc"
    is_active: int = 1
    must_change_password: Optional[int] = 1


class UpdateUserRequest(BaseModel):
    nome: Optional[str] = None
    role: Optional[str] = None
    estado: Optional[str] = None
    painel_url: Optional[str] = None
    is_active: Optional[int] = None
    must_change_password: Optional[int] = None
    password: Optional[str] = None


@router.get("/users")
async def list_users_endpoint(_: TokenPayload = Depends(require_admin_or_coordinator)):
    """Lista todos os usuários cadastrados no banco SQLite."""
    return {"users": db_list_users()}


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    req: CreateUserRequest,
    _: TokenPayload = Depends(require_admin_or_coordinator),
):
    """Cadastra um novo usuário no sistema."""
    try:
        new_user = db_create_user(
            username=req.username,
            password=req.password,
            nome=req.nome,
            role=req.role,
            estado=req.estado,
            painel_url=req.painel_url,
            is_active=req.is_active,
            must_change_password=1 if req.must_change_password is None or req.must_change_password else 0,
        )
        return {"status": "ok", "user": new_user}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro interno: {e}")


@router.put("/users/{user_id}")
async def update_user_endpoint(
    user_id: int,
    req: UpdateUserRequest,
    _: TokenPayload = Depends(require_admin_or_coordinator),
):
    """Atualiza dados cadastrais ou redefine senha de um usuário."""
    existing = db_get_user_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    updated = db_update_user(
        user_id=user_id,
        nome=req.nome,
        role=req.role,
        estado=req.estado,
        painel_url=req.painel_url,
        is_active=req.is_active,
        must_change_password=req.must_change_password,
        password=req.password,
    )
    return {"status": "ok", "user": updated}


@router.delete("/users/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    current_user: TokenPayload = Depends(require_admin_or_coordinator),
):
    """Exclui usuário do banco."""
    target = db_get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    # Impede que o usuário logado exclua a si mesmo
    if target["username"].lower() == current_user.sub.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Você não pode excluir sua própria conta")

    success = db_delete_user(user_id)
    return {"status": "ok", "deleted": success}
