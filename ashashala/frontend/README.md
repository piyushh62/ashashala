# AshaShala Frontend

React 18 + Vite + TypeScript + Tailwind. State via Zustand (auth + voice),
server state via TanStack Query, charts via Recharts, routing via React Router.

## Run locally

```bash
cd frontend
cp .env.example .env        # leave VITE_API_URL blank to use the Vite dev proxy
npm install
npm run dev                 # http://localhost:5173
```

The Vite dev server proxies `/api/*` to the backend at `http://localhost:8000`
(override with `VITE_API_URL`). Start the backend first:

```bash
cd ../backend && uvicorn app.main:app --reload
```

> If `npm run dev` reports **"vite is not recognized"**, dependencies aren't
> installed yet — run `npm install` first.

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Vite dev server with HMR + API proxy |
| `npm run build` | Type-check (`tsc -b`) then production build to `dist/` |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run preview` | Serve the production build |

## Structure

```
src/
├── api/          client.ts (JWT + auto-refresh + SSE), endpoints.ts, queryClient.ts
├── stores/       auth.ts (Zustand), voice.ts (localStorage-persisted)
├── types/        api.ts (mirrors the FastAPI schemas)
├── components/
│   ├── ui/       Card, Button, Table, Toast, Skeleton, EmptyState…
│   ├── layout/   AppLayout, Sidebar, RoleGuard
│   ├── dashboard/ MasteryRadar, TimetableGrid
│   ├── citations/ ClickableCitation (PDF page / YouTube timestamp / URL)
│   ├── voice/    VoiceInputButton (Web Speech), TTSPlayer (SpeechSynthesis)
│   └── quiz/      QuizGame (timer, XP, level-up)
└── routes/       Login + admin/ school/ teacher/ student/ parent/
```

## Auth model

Access token lives in memory (Zustand); the refresh token is persisted so a
reload re-establishes the session. `RoleGuard` redirects unauthenticated users
to `/login` and wrong-role users to their home. On 401 the client makes one
refresh attempt, then logs out.

## Voice

Push-to-talk uses the browser Web Speech API and degrades gracefully (the mic
button hides with a tooltip when unsupported). TTS uses `SpeechSynthesis` with
the user's saved rate/pitch/voice; the server endpoints `/student/voice/stt`
and `/student/voice/tts` (NVIDIA) are the fallbacks.

## Deploy (Vercel)

`vercel.json` (repo root) builds `frontend/` and rewrites all routes to
`index.html` for SPA client-side routing.
