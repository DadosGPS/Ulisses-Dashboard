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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import analise, avancado, carga_externa, combinada, comparacoes, configuracoes, dashboard, equipa, filtros, health, ia, ingest, jogadores, match_benchmark, planeamento, relatorio, sessoes, sistema, wellness

settings = get_settings()

app = FastAPI(title="LoadMonitorSystem API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ingest.router)
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
app.include_router(avancado.router)
app.include_router(sistema.router)
app.include_router(relatorio.router)
app.include_router(wellness.router)
app.include_router(ia.router)
