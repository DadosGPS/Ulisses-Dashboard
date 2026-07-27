# LoadMonitorSystem — Web (Next.js)

Frontend da migração descrita em `C:\Users\Asus\.claude\plans\wild-churning-aurora.md`.
Estes ficheiros foram escritos à mão (o ambiente onde foram gerados não tinha Node.js
para correr `npm install`) — a primeira coisa a fazer é instalar e correr localmente.

## Arrancar

```bash
cd web
npm install
cp .env.local.example .env.local   # preenche NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY
npm run dev
```

Precisa também da API (FastAPI) a correr em paralelo — ver `../api/README.md` (ou o
`.env.example` em `api/`) — o dashboard chama `NEXT_PUBLIC_API_URL` (por omissão
`http://localhost:8000`).

## Estrutura

- `app/` — App Router. `login/`, `signup/` (Fase 3 — Supabase Auth), `dashboard/`
  (Fase 5 — página piloto, Server Component que chama a API FastAPI).
- `lib/supabase/` — clientes Supabase (`client.ts` para Client Components,
  `server.ts` para Server Components, `middleware.ts` para o refresh de sessão).
- `lib/theme.ts` — paleta e template de gráficos, porta direta de
  `utils/ui_safe.py` (`aplicar_tema_graficos`).
- `lib/types.ts` — tipos TypeScript que espelham o JSON devolvido pela API.
- `components/ui/` — componentes portados de `utils/ui_safe.py`:
  `KpiTile` (`team_kpi_tile`), `RankingCard` (`ranking_metric_card`).
  `AlertList` é novo (não existia em `ui_safe.py` como componente isolado).

## Por construir (fases seguintes do plano)

- `SemaphoreTable`, `LoadProfileTable`, `CleanBarChart` (Fase 6-7).
- Página `/forgot-password` (Fase 3 — falta só o formulário, o backend é
  `resetPasswordForEmail`/`updateUser` nativos do Supabase).
- Upload de ficheiros no frontend, a chamar `POST /api/ingest` (Fase 4 já tem
  o endpoint pronto no lado da API — falta a UI de upload aqui).
