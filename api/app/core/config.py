"""Configuração da API — lê variáveis de ambiente (ver .env.example)."""
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", "supabase_url", "cors_origins", mode="before")
    @classmethod
    def _sem_espacos_nem_quebras_de_linha(cls, v: str) -> str:
        # Paineis como o do Render por vezes guardam um "\n" à frente/atrás do
        # valor colado (ex: colado a partir de um ficheiro .env) — isso
        # invalida URLs a meio (http.client rejeita hosts com "\n").
        return v.strip() if isinstance(v, str) else v

    # Postgres do Supabase — connection string com privilégios de escrita
    # (usada só pela API para a ingestão em massa; nunca exposta ao Next.js).
    # Painel Supabase: Project Settings → Database → Connection string (URI).
    database_url: str = ""

    # Painel Supabase: Project Settings → API → API Keys (Publishable key,
    # "Project URL"). Usado para validar os tokens de sessão que o Next.js
    # envia no header Authorization: Bearer <jwt> — a API nunca gera os seus
    # próprios tokens, só confirma os que o Supabase Auth já emitiu, via o
    # endpoint público JWKS (Supabase "JWT Signing Keys", assimétrico —
    # não há segredo partilhado nenhum para configurar aqui).
    supabase_url: str = ""

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    # Origem(ns) autorizadas a chamar esta API (o domínio do Next.js).
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
