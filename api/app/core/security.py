"""Validação de sessão — confirma o JWT emitido pelo Supabase Auth.

A API nunca faz login nem emite tokens (isso é o Supabase Auth, Fase 3 do
plano). Aqui só se verifica a assinatura/validade de um token já emitido e
extrai o `sub` (user id) para usar nas queries seguintes.

Este projeto usa o sistema novo de "JWT Signing Keys" do Supabase — chaves
assimétricas (ES256), publicadas no endpoint JWKS do projeto. Ao contrário do
sistema antigo (um único segredo partilhado, HS256), aqui não há segredo
nenhum para configurar: a verificação usa só a chave pública, obtida
automaticamente a partir de SUPABASE_URL. O PyJWKClient trata da cache.
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

_bearer = HTTPBearer(auto_error=False)
_jwks_client: jwt.PyJWKClient | None = None


class UtilizadorAtual:
    def __init__(self, user_id: str, email: str | None):
        self.user_id = user_id
        self.email = email


def _obter_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        settings = get_settings()
        if not settings.supabase_url:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "SUPABASE_URL não configurado no servidor.",
            )
        _jwks_client = jwt.PyJWKClient(settings.supabase_jwks_url, cache_keys=True)
    return _jwks_client


def obter_utilizador_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UtilizadorAtual:
    if credenciais is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão em falta.")

    try:
        chave_assinatura = _obter_jwks_client().get_signing_key_from_jwt(credenciais.credentials)
        payload = jwt.decode(
            credenciais.credentials,
            chave_assinatura.key,
            algorithms=["ES256"],
            audience="authenticated",
        )
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida ou expirada.")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token sem utilizador associado.")

    return UtilizadorAtual(user_id=user_id, email=payload.get("email"))
