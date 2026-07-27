# LoadMonitorSystem — API (FastAPI)

Motor de ingestão/cálculo da migração descrita em
`C:\Users\Asus\.claude\plans\wild-churning-aurora.md`. Reutiliza `utils/dados.py`
e `utils/calculos.py` (raiz do repo) diretamente — não há lógica duplicada.

## Arrancar localmente

```bash
cd api
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env          # preenche DATABASE_URL / SUPABASE_JWT_SECRET
uvicorn main:app --reload
```

Corre a partir da pasta `api/` — `main.py` já adiciona a raiz do repo ao
`sys.path` para conseguir importar `utils.dados`/`utils.calculos`.

Documentação interativa em `http://localhost:8000/docs` depois de arrancar.

## Endpoints

- `GET /api/health` — sem autenticação.
- `POST /api/ingest` — multipart (`team_id`, `file`), requer `Authorization: Bearer <jwt>`.
  Fase 4 do plano: parseia o Excel/CSV com `utils/dados.py` e grava em
  `gps_sessions`/`exercises`.
- `GET /api/teams/{team_id}/dashboard` — requer `Authorization: Bearer <jwt>`.
  Fase 5 do plano: KPIs, alertas ACWR/wellness e rankings Top3/Bottom3 para a
  página piloto Dashboard.

Todos os endpoints protegidos verificam que o utilizador do JWT pertence à
equipa pedida (`app/core/db.py::verificar_pertenca_equipa`) antes de ler/escrever
— a ligação à base de dados usada aqui é privilegiada (service-role) e ignora
RLS, por isso essa verificação é feita em código, não pela base de dados.

## Testado neste ambiente (sem Node, sem Postgres local)

- Sintaxe e imports de todos os ficheiros.
- `utils/dados.py`/`utils/calculos.py` importam e funcionam corretamente **sem
  o Streamlit instalado** (pré-requisito para isto correr num container FastAPI
  limpo) — ver o `try/except` à volta de `import streamlit` em ambos.
- App FastAPI completo via `TestClient`: `/api/health` responde 200; endpoints
  protegidos respondem 401 sem token, 401 com token adulterado, e passam a
  autenticação corretamente com um JWT válido (falham depois por falta de
  `DATABASE_URL`, como esperado sem uma base de dados real configurada).
- Pipeline de parsing de `POST /api/ingest` contra o `LoadMonitorSystem_Template.xlsx`
  real do repo — carregamento, mapeamento de colunas e serialização JSON/psycopg2
  confirmados (incluindo a conversão de tipos `numpy` para tipos nativos Python).

## Por testar (precisa de Supabase real)

- Escrita efetiva em `gps_sessions`/`exercises`/`players`/`uploads` (a lógica
  está feita e testada até à fronteira da ligação à BD — falta só ligar a um
  Postgres real).
- RLS ponta a ponta (ver `supabase/README.md`).
