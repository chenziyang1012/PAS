# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PAS (Product Analysis System) — a full-stack web app for managing product selection and review workflows. Roles: **admin**, **selector** (选品员), **reviewer** (审核员).

Product status state machine: `draft → pending_review → approved / rejected`. Approved products can be marked done (`special_tag=done`) or flagged as infringe (`special_tag=infringe`). Rejected with type `other` keeps the product in the main list without a special tag.

## Dev Commands

**Backend** (from `backend/`, venv activated):
```bash
uvicorn main:app --reload --port 8000
```

**Frontend** (from `frontend/`):
```bash
npm run dev      # Vite dev server on :5173
npm run build    # vue-tsc + vite build → dist/
```

Convenience scripts at repo root: `start_backend.bat`, `start_frontend.bat`.

No test runner is configured.

## Architecture

### Backend — FastAPI + MySQL

- Entry point: `backend/main.py` — registers routers, runs `_migrate()` on startup for additive schema changes, serves `uploads/` as static files.
- ORM: SQLAlchemy 2.0 (sync), PyMySQL driver.
- Auth: JWT (`python-jose`), bcrypt passwords. Token passed as `Authorization: Bearer` header.
- Config: `backend/app/config.py` (Pydantic Settings — DB URL, JWT secret, upload dir, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `PROXY_URL`).
- Schema evolution: `_migrate()` in `main.py` handles new columns inline. **Every new model column must also be added to `_migrate()`** — Alembic is present but not the primary migration path.

**Routers** (`backend/app/routers/`):
- `auth.py` — login, `/me`, logout
- `users.py` — user CRUD (admin only). `/selectors` endpoint is accessible to reviewer+admin for populating filter dropdowns without exposing full user management.
- `products.py` — product CRUD, submit-review, bulk ops (delete/complete/submit), scrape, bookmarklet import, done/infringe lists, proxy settings, 1688 cookie settings
- `reviews.py` — pending list (ordered by `submit_time desc`), approve, reject (with `reject_type`: `done`/`infringe`/`other`)
- `upload.py` — image upload to `uploads/`
- `todo.py` — approved products queue for image generation. Manages materials (`ProductMaterial`), generated images (`GeneratedImage`), prompt templates (`PromptTemplate`), and OpenAI settings. Image generation runs in a **daemon background thread** (`_do_generate`) — the POST endpoint returns immediately after creating pending records.

### Frontend — Vue 3 + Vite + TypeScript + Element Plus

- Single Pinia store: `frontend/src/stores/auth.ts` (`useAuthStore`) — holds `user` + `token`, persists token to `localStorage`, 401 interceptor clears token.
- Single Axios instance in `frontend/src/api/index.ts` — base URL `/`, Bearer token injected via interceptor, proxied to `:8000` in dev via `vite.config.ts`.
- `@` alias maps to `frontend/src/`.

**Key views** (`frontend/src/views/`):
- `products/ProductList.vue` — main product list with filters, pagination, bulk ops, Excel export
- `products/TodoList.vue` — approved products queue: material management (drag-drop, upload, 1688 scrape), GPT image generation with polling, prompt template management
- `products/DoneList.vue` / `InfringeList.vue` — completed/infringe lists (delete restricted to reviewer+admin)
- `products/ProductForm.vue` — create/edit product (rejected products cannot resubmit for review)
- `reviews/ReviewList.vue` — pending review list with selector filter (reviewer+admin), batch approve/reject
- `reviews/ReviewDetail.vue` — approve or reject with type selection
- `BookmarkletImport.vue` — popup page opened by the bookmarklet (must be a top-level route with `meta: { public: true }`, outside the layout shell)

**Shared component**: `frontend/src/components/PreviewImage.vue` — thumbnail that opens a fullscreen Teleport-based lightbox overlay (position:fixed, scroll-wheel zoom, click-outside-to-close). Use this everywhere instead of `el-image :preview-src-list` — el-image's built-in preview does not support click-outside-to-close and scroll zoom is constrained to the dialog box.

### Polling pattern in list views

All list views that auto-refresh use **two separate functions**:
- `load()` — user-triggered (filter change, pagination, post-action). Shows loading spinner, always replaces list data.
- `silentRefresh()` — called by `setInterval` every 15s. Skips when dialogs are open; only replaces list data when content actually changed (JSON diff); no loading spinner. This prevents flash and loss of table selection state.

Never change `setInterval` to call `load()` — it will cause flash and deselect issues.

### Image generation flow

`TodoList.vue` → `POST /api/todo/{id}/generate` → backend creates two `GeneratedImage` records (`pending`) and spawns a daemon thread → frontend polls `GET /api/todo/{id}/generated` every 3s until all records are `done` or `failed`.

Key constraints:
- OpenAI `images.edit` requires a **square RGBA PNG** input. Downloaded 1688 materials are JPEG — `_do_generate` converts them via Pillow before the API call.
- `openai>=1.52` is required for `httpx>=0.28` compatibility (`proxies` kwarg was removed from httpx 0.28; older openai versions pass it internally).
- For authenticated proxies with `curl_cffi` + `impersonate`, credentials embedded in the proxy URL are NOT forwarded during the CONNECT tunnel. Use `_split_proxy_auth()` in `scraper.py` to separate credentials and pass them via `proxy_auth`.

## Git Workflow

**每次改动：本地 commit，不自动推送。** 只有用户明确说"推送"或"push"时才执行 `git push`。

## Deployment

Server: Alibaba Cloud at `/opt/PAS`. Update command:
```bash
cd /opt/PAS && git pull && cd frontend && npm run build && systemctl restart prs-backend
```

## Debugging

遇到无法本地复现的问题时，主动向用户索要所需信息（如截图、接口返回数据、日志等），不要猜测。
