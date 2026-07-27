"""Configuração da API — lê variáveis de ambiente (ver .env.example)."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres do Supabase — connection string com privilégios de escrita
    # (usada só pela API para a ingestão em massa; nunca exposta ao Next.js).
    # Painel Supabase: Project Settings → Database → Connection string (URI).
    database_url: str = ""

    # Painel Supabase: Project Settings → API → JWT Secret.
    # Usado para validar os tokens de sessão que o Next.js envia no header
    # Authorization: Bearer <jwt> — a API nunca gera os seus próprios tokens,
    # só confirma os que o Supabase Auth já emitiu.
    supabase_jwt_secret: str = ""

    # Origem(ns) autorizadas a chamar esta API (o domínio do Next.js).
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
