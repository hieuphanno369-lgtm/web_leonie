# Leonie Codebase Cleanup — Design Spec

**Date:** 2026-05-29  
**Author:** Claude (via superpowers:brainstorming)  
**Goal:** Xóa dead pages, fix 53 backend test failures, kiểm tra TypeScript errors.

---

## Context

Sau khi merge Cohort Comparison feature, codebase có:
- 5 frontend pages không có backend API (Learn tab + EtlArchitecture) — chỉ dùng localStorage
- 53 failing backend tests do 2 nguyên nhân độc lập
- Cần TypeScript clean-pass sau khi xóa pages

Approach: **Surgical** — verify trước khi xóa, fix từng lỗi có root cause rõ ràng.

---

## Section 1: Frontend Page Deletion

### Pages xóa

| File | Lines | Lý do |
|------|-------|-------|
| `frontend/src/pages/learn/Roadmap.tsx` | ~280 | localStorage only, không có API |
| `frontend/src/pages/learn/DailyQuiz.tsx` | 642 | localStorage only, không có API |
| `frontend/src/pages/learn/PracticeRepos.tsx` | 472 | localStorage only, không có API |
| `frontend/src/pages/learn/Resources.tsx` | ~500 | localStorage only, không có API |
| `frontend/src/pages/data/EtlArchitecture.tsx` | 190 | Static diagram, không có API |

### Files cần update sau khi xóa

**`frontend/src/App.tsx`** — Xóa 5 lazy imports và 5 Route entries:
- Xóa: `const Roadmap = lazy(...)`, `const DailyQuiz = lazy(...)`, `const PracticeRepos = lazy(...)`, `const Resources = lazy(...)`, `const EtlArchitecture = lazy(...)`
- Xóa: `<Route path="learn/roadmap" .../>`, `<Route path="learn/quiz" .../>`, `<Route path="learn/repos" .../>`, `<Route path="learn/resources" .../>`, `<Route path="data/etl" .../>`

**`frontend/src/components/layout/Sidebar.tsx`** — Xóa:
- Toàn bộ LEARN category (4 items: Roadmap, Daily Quiz, Practice Repos, Resources)
- ETL/Architecture item trong DATA category
- Unused icon imports: `Map`, `BookOpen`, `FolderGit2`, `Link2`, `GitBranch` (verify từng cái trước)

**`frontend/src/types.ts`** — Xóa `'learn'` khỏi `NavCategoryId` union type (nếu không còn Learn category trong nav).

---

## Section 2: Backend Bug Fixes

### Bug 1 — SPA Catch-All (production impact)

**File:** `backend/main.py` line 74

**Root cause:** `async def serve_spa(_: str)` — tham số `_: str` được FastAPI interpret là required query parameter, không phải path parameter. Mọi request đến unknown path nhận 422 "Field required".

**Fix:**
```python
# BEFORE (broken):
@app.get("/{full_path:path}")
async def serve_spa(_: str):

# AFTER (fixed):
@app.get("/{full_path:path}")
async def serve_spa(_full_path: str = ""):
```

### Bug 2 — Test URL Prefix Sai (53 failing tests)

**Root cause:** Tất cả test files gọi URL thiếu `/api` prefix. Router được mount tại `prefix="/api"` trong `main.py`, nhưng tests gọi trực tiếp như `/tasks`, `/eda`, `/wip`, v.v.

**Files cần fix** (thêm `/api` prefix vào TẤT CẢ URL calls):

| Test file | Ví dụ sai | Sau khi fix |
|-----------|-----------|-------------|
| `test_tasks.py` | `/tasks` | `/api/tasks` |
| `test_eda.py` | `/eda` | `/api/eda` |
| `test_wip.py` | `/wip` | `/api/wip` |
| `test_kpi.py` | `/kpi` | `/api/kpi` |
| `test_notes.py` | `/notes` | `/api/notes` |
| `test_discord.py` | `/discord-settings` | `/api/discord-settings` |
| `test_performance.py` | `/performance` | `/api/performance` |
| `test_ml.py` | `/ml/...` | `/api/ml/...` |
| `test_ml_quality.py` | `/ml/quality/...` | `/api/ml/quality/...` |

> `test_health.py` và `test_database.py` không có URL prefix issue — kiểm tra để xác nhận.

**Strategy:** Dùng sed-style replace `/` → `/api/` cho mọi `client.get(`, `client.post(`, `client.patch(`, `client.delete(` call trong mỗi file. Verify sau khi replace bằng cách chạy test suite.

---

## Section 3: TypeScript Dead Code Cleanup

**Sau khi xóa pages và update Sidebar, chạy:**
```
cd frontend && npx tsc --noEmit
```

**Kiểm tra:**
1. Không còn import nào reference các file đã xóa
2. `NavCategoryId` type consistent với nav entries thực tế
3. `cohortUtils.ts` — `cellText()` vẫn được dùng trong `MlCohortView.tsx` → giữ nguyên

**Xử lý TypeScript errors** (nếu có) sau khi xóa pages.

---

## Out of Scope

- Refactoring logic bên trong các pages được giữ lại
- Performance optimization (memoization, bundle splitting)
- Thêm tính năng mới
- "Leonie AI" button placeholder trong Sidebar (intentional UI element)

---

## Success Criteria

- [ ] 5 page files đã xóa, không còn trong codebase
- [ ] App.tsx và Sidebar.tsx clean, không còn reference đến pages đã xóa
- [ ] `npx tsc --noEmit` không có errors
- [ ] `pytest backend/tests/ -v` pass ≥ 100/111 tests (target: tất cả)
- [ ] Backend app khởi động bình thường
- [ ] Frontend build thành công (`npm run build`)
