# LoadMonitorSystem — Web (Next.js)

Frontend da migração descrita em `C:\Users\Asus\.claude\plans\wild-churning-aurora.md`.

Em produção: publicado no Vercel (Root Directory = `web`). A API (FastAPI) está
publicada no Render — ver `../api/README.md`.

## Arrancar localmente

```bash
cd web
npm install
cp .env.local.example .env.local   # preenche NEXT_PUBLIC_SUPABASE_URL / _ANON_KEY / _API_URL
npm run dev
```

Precisa também da API (FastAPI) a correr em paralelo (localmente ou publicada) —
ver `../api/README.md` — o dashboard chama `NEXT_PUBLIC_API_URL`.

## Estrutura

- `app/(app)/` — páginas autenticadas, com barra lateral partilhada
  (`app/(app)/layout.tsx` + `components/layout/Sidebar.tsx`): `dashboard/`,
  `equipa/`, `jogadores/`, `planeamento/`, `avancado/`, `sistema/`, `upload/`,
  `relatorio/` (exportação PDF).
- `app/login/`, `app/signup/` — Supabase Auth, fora da barra lateral.
- `lib/supabase/` — clientes Supabase (`client.ts` para Client Components,
  `server.ts` para Server Components, `middleware.ts`/`proxy.ts` para o
  refresh de sessão).
- `lib/theme.ts` — paleta, espaçamento e template de gráficos, porta direta
  de `utils/ui_safe.py` (`aplicar_tema_graficos`).
- `lib/types.ts` — tipos TypeScript que espelham o JSON devolvido pela API.
- `components/ui/` — componentes portados de `utils/ui_safe.py`: `KpiTile`,
  `RankingCard`, `LoadProfileTable`, `AcwrList`, `Resumo5W1HCard`.
- `components/charts/PlotlyChart.tsx` — wrapper client-only do Plotly.js
  (sem SSR — Plotly acede a `window`).

## Notas de deploy (Vercel)

- **Root Directory**: `web` (obrigatório — sem isto, o Vercel tenta também
  construir `api/` como funções Python e falha por excesso de tamanho).
- Variáveis de ambiente: `NEXT_PUBLIC_SUPABASE_URL`,
  `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL` (URL pública da API
  no Render).
