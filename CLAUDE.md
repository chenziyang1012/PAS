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
- Config: `backend/app/config.py` (Pydantic Settings — DB URL, JWT secret, upload dir).
- Schema evolution: `_migrate()` in `main.py` handles new columns inline. Alembic is present but not the primary migration path.

**Routers** (`backend/app/routers/`):
- `auth.py` — login, `/me`, logout
- `users.py` — user CRUD, status toggle, password reset, delete (admin only, guards against self-delete and users with products)
- `products.py` — product CRUD, submit-review, bulk ops (delete/complete/submit), scrape, bookmarklet import, done/infringe lists
- `reviews.py` — pending list, approve, reject (with `reject_type`: `done`/`infringe`/`other`)
- `upload.py` — image upload to `uploads/`

### Frontend — Vue 3 + Vite + TypeScript + Element Plus

- Single Pinia store: `frontend/src/stores/auth.ts` (`useAuthStore`) — holds `user` + `token`, persists token to `localStorage`, 401 interceptor clears token.
- Single Axios instance in `frontend/src/api/index.ts` — base URL `/`, Bearer token injected via interceptor, proxied to `:8000` in dev via `vite.config.ts`.
- `@` alias maps to `frontend/src/`.

**Key views** (`frontend/src/views/`):
- `products/ProductList.vue` — main product list with filters, pagination, bulk ops, Excel export
- `products/DoneList.vue` / `InfringeList.vue` — completed/infringe lists (delete restricted to reviewer+admin)
- `products/ProductForm.vue` — create/edit product (rejected products cannot resubmit for review)
- `reviews/ReviewDetail.vue` — approve or reject with type selection
- `BookmarkletImport.vue` — popup page opened by the bookmarklet (must be a top-level route with `meta: { public: true }`, outside the layout shell)

**Shared component**: `frontend/src/components/PreviewImage.vue` — thumbnail that opens a full-size `el-dialog` (replaces `el-image` to support click-outside-to-close).

## Git Workflow

**每次改动：本地 commit，不自动推送。** 只有用户明确说"推送"或"push"时才执行 `git push`。

## Deployment

Server: Alibaba Cloud at `/opt/PAS`. Update command:
```bash
cd /opt/PAS && git pull && cd frontend && npm run build && systemctl restart prs-backend
```
