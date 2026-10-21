"""LoadMonitorSystem API — motor de ingestão/cálculo (FastAPI).

Evoluído do spike em webapp/main.py (Fase 2 do plano de migração). Ao
contrário do spike, esta versão não serve frontend estático — o Next.js
substitui-o por completo — e tem autenticação real via Supabase Auth
(ver app/core/security.py) em vez de endpoints abertos.
"""
import sys
from pathlib import Path

# Garante que `utils/` (na raiz do repositório, irmã desta pasta `api/`) é
# importável independentemente de como o processo é arrancado — localmente
# (`uvicorn api.main:app` a partir da raiz) já funciona sem isto, mas em
# produção (Docker) é mais seguro não depender da cwd.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.routers import academia, analise, calendario, equipa_tecnica, avancado, carga_externa, combinada, comparacoes, configuracoes, dashboard, equipa, filtros, health, ia, ingest, jogadores, lesoes, match_benchmark, mensagens, perfil, planeamento, prontidao, relatorio, rtp, sessoes, sistema, velocidade, wellness

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title="LoadMonitorSystem API", version="0.1.0")


# Apanha qualquer exceção não tratada e devolve JSON. IMPORTANTE: tem de ser
# registado ANTES do CORSMiddleware para que o CORS fique "por fora" e adicione
# os cabeçalhos também à resposta de erro. Sem isto, o Starlette devolve o 500
# pelo ServerErrorMiddleware (fora do CORS) SEM cabeçalhos CORS — e o browser
# bloqueia a resposta antes de o frontend a conseguir ler, mostrando sempre
# "Não foi possível ligar à API" em vez do erro real. (Comportamento confirmado
# com testes ao stack de middleware do Starlette.)
@app.middleware("http")
async def apanhar_erros_nao_tratados(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Ocorreu um erro interno ao processar o pedido. "
                                "Tenta novamente; se persistir, o ficheiro pode ser grande demais para o plano atual."},
        )


# Papéis só de consulta (treinador): recusa alterações antes de chegarem ao
# endpoint. Só olha para pedidos de escrita com sessão válida; tudo o resto
# segue (cada endpoint continua a verificar a pertença à equipa).
@app.middleware("http")
async def bloquear_so_consulta(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith(("/api/teams/", "/api/academia", "/api/ingest")):
        cab = request.headers.get("authorization", "")
        if cab.lower().startswith("bearer "):
            from fastapi.security import HTTPAuthorizationCredentials
            from starlette.concurrency import run_in_threadpool

            from app.core.db import get_conn
            from app.core.security import obter_utilizador_atual
            from app.services.equipa_tecnica_service import motivo_bloqueio

            def verificar():
                try:
                    u = obter_utilizador_atual(HTTPAuthorizationCredentials(scheme="Bearer", credentials=cab[7:].strip()))
                except Exception:
                    return None  # sessão inválida: o endpoint responde 401
                try:
                    with get_conn() as conn:
                        with conn.cursor() as cur:
                            return motivo_bloqueio(cur, u.user_id, request.method, request.url.path)
                except Exception:
                    return None  # ex.: migração 0017 por aplicar
            motivo = await run_in_threadpool(verificar)
            if motivo:
                return JSONResponse(status_code=403, content={"detail": motivo})
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(academia.router)
app.include_router(equipa_tecnica.router)
app.include_router(ingest.router)
app.include_router(perfil.router)
app.include_router(velocidade.router)
app.include_router(lesoes.router)
app.include_router(prontidao.router)
app.include_router(mensagens.router)
app.include_router(rtp.router)
app.include_router(dashboard.router)
app.include_router(analise.router)
app.include_router(carga_externa.router)
app.include_router(comparacoes.router)
app.include_router(combinada.router)
app.include_router(match_benchmark.router)
app.include_router(sessoes.router)
app.include_router(configuracoes.router)
app.include_router(filtros.router)
app.include_router(equipa.router)
app.include_router(jogadores.router)
app.include_router(planeamento.router)
app.include_router(calendario.router)
app.include_router(avancado.router)
app.include_router(sistema.router)
app.include_router(relatorio.router)
app.include_router(wellness.router)
app.include_router(ia.router)
