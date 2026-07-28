# LoadMonitorSystem API — FastAPI
#
# Inclui já as dependências de sistema do WeasyPrint (pango/harfbuzz), mesmo
# antes da exportação de PDF ser construída (Fase 9 do plano), para provar a
# história de deploy cedo em vez de a descobrir só quando for preciso.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# `utils/` vive na raiz do repositório (irmã de `api/`) e é partilhado com a
# app Streamlit — copiado tal e qual, sem duplicar código.
COPY utils/ ./utils/
COPY api/ ./api/

WORKDIR /app/api
EXPOSE 8000
# Forma shell (não exec) de propósito — deixa expandir $PORT, que o Railway
# injeta dinamicamente; localmente/noutros hosts sem essa variável cai nos 8000.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
