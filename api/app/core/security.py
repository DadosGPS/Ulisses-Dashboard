"""Validação de sessão — confirma o JWT emitido pelo Supabase Auth.

A API nunca faz login nem emite tokens (isso é o Supabase Auth, Fase 3 do
plano). Aqui só se verifica a assinatura/validade de um token já emitido e
extrai o `sub` (user id) para usar nas queries seguintes.
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

_bearer = HTTPBearer(auto_error=False)


class UtilizadorAtual:
    def __init__(self, user_id: str, email: str | None):
        self.user_id = user_id
        self.email = email


def obter_utilizador_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UtilizadorAtual:
    if credenciais is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão em falta.")

    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "SUPABASE_JWT_SECRET não configurado no servidor.",
        )

    try:
        payload = jwt.decode(
            credenciais.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada.")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token sem utilizador associado.")

    return UtilizadorAtual(user_id=user_id, email=payload.get("email"))
