# Combine file — Redesign (generic, value-aware multi-file merge)

- **Date:** 2026-06-08
- **Status:** Design approved (pending spec review) → next: writing-plans
- **Replaces:** the current "Gộp file" tab (`MlMergeView` + `MlMergeChips` +
  `MlMergeSummary`, backend `analytics/merge.py` + `routers/ml.py /merge/*`).
- **Scope marker:** sections tagged **[MVP]** ship now; **[V2]** is round-two.

---

## 1. Context & problem

The current merge feature already has a clean/dedup/complete pipeline, but it is
**hidden and phone-centric**, so users can't reach the outcome quality of the
reference Python notebook.

| | Notebook (gold) | Current web run |
|---|---|---|
| total thu thập | 3483 | 3483 |
| hợp lệ định dạng | 3293 | 3483 |
| null/sai | 190 | 0 |
| trùng đã loại | 551 (thô) | 0 |
| distinct | 2932 | 690 |
| distinct đủ thông tin | 612 | — |

Root causes:

1. **Flat chip-wall** (`MlMergeChips`): every field in one `flex-wrap`; no
   "common vs per-file" distinction; cleaning power buried in tiny per-chip
   `📞`/`🔑` toggles users never find.
2. **Phone-only cleaning**: `clean_phone` is the only normalizer; "valid format"
   only means phone. No generic typing.
3. **Name-only matching**: `normalize_field` matches columns by name. Columns
   that hold the *same kind of data under different names* are never detected.

### Design driver (user, verbatim)

> "phone chỉ là Ví dụ. bạn cần phải đọc các file đó và có hướng đề xuất rằng tôi
> thấy value khá giống nhau nhưng tên field lại khác kiểu vậy"

→ The tool must **read actual cell values**, infer each column's semantic type,
and **proactively suggest unifying differently-named columns that hold similar
values**. This is the core, not a footnote.

---

## 2. Goals / non-goals

**Goals [MVP]**

- Rename tab **"Gộp file" → "Combine file"**, move to **just before Auto-EDA**.
- Replace the chip-wall with a **2-group field view** (common / per-file) + file
  provenance.
- **Value-aware field engine**: profile each column, guess one of **6 semantic
  types**, and suggest unification groups (by name + inferred type).
- A **confirmation UI** for semantic types ("is this 'phone' field really a
  phone?") with value samples + override dropdown.
- **Generic cleaning** dispatcher (replaces phone-only path).
- **Coalesce dedup** on a single key; **user-chosen required fields** define
  "đủ thông tin".
- **Detailed outcome** mirroring the notebook (8 metrics) + **both** duplicate
  definitions (361 clean / 551 raw) + per-field fill-rate + per-file
  contribution.
- **4-step wizard** with a dry-run **preview** before creating the dataset.
- Exports: clean **CSV/XLSX** + **"Tải bản bị loại"** (rejected rows audit).

**Non-goals [V2]** — explicitly deferred:

- Cross-file **value-set overlap (Jaccard)** similarity for generic types.
- **Composite** dedup keys; **keep-latest-by-timestamp** strategy.
- Extra semantic types (ID, age-range, gender), saved mapping templates,
  per-field custom transform editor.

---

## 3. Decisions (from 10 dropdown Qs)

1. Tab "Combine file", position **before Auto-EDA**.
2. Fields in **2 groups** — chung (mọi file) / riêng — with `x/N file` badge +
   hover file names.
3. Unify differently-named columns: **manual merge UI + suggestions**.
4. **6 semantic types**: Phone-VN · Email · Date · Number · Category · Text —
   tool guesses, user confirms.
5. Phone validity: **lenient ≥9 digits → prefix '0'** (one example of a
   per-type rule, not special).
6. Dedup: **coalesce** (keep most-complete row, fill blanks from duplicates).
7. "Complete": **user-selected required fields**, all non-null.
8. Duplicate count: **show both** 361 (clean = valid−distinct) and 551
   (raw = total−distinct).
9. Workflow: **4-step wizard + preview**.
10. Phasing: **MVP first**, V2 later.

Accepted defaults: fill-rate table + per-file contribution **on**; rejected-rows
export **yes**; dedup key v1 **single column**.

---

## 4. Architecture

### 4.1 Backend — `analytics/merge.py`

Keep existing helpers (`normalize_field`, `clean_phone`, `common_fields`); add:

```python
SemanticType = Literal["phone", "email", "date", "number", "category", "text"]

@dataclass
class ColumnProfile:
    file: str                 # source filename
    name: str                 # raw column name
    norm: str                 # normalize_field(name)
    inferred_type: SemanticType
    confidence: float         # 0..1, fraction of sampled values matching type
    samples: list[str]        # up to 5 distinct non-null example values
    non_null: int
    distinct: int
    fill_rate: float          # non_null / rows_in_file

def profile_columns(frames, filenames, *, sample=500) -> list[ColumnProfile]: ...

@dataclass
class FieldGroupSuggestion:
    canonical: str            # proposed unified name (first-seen display)
    members: list[str]        # raw column names being unified (across files)
    inferred_type: SemanticType
    confidence: float
    reason: Literal["name", "type", "name+type"]

def suggest_groups(profiles) -> list[FieldGroupSuggestion]: ...

def normalize_value(v, t: SemanticType) -> str | None: ...     # dispatcher
def is_valid(v, t: SemanticType) -> bool: ...                  # post-normalize validity
```

Generalize `align_and_merge` to v2. New args are additive; **the return becomes
a 3-tuple** `(clean, rejected, summary)` and `semantic_types` / `drop_invalid_key`
**supersede** the old `phone_cols` / `drop_null_key` (which are removed). The only
in-repo caller is `/merge/run`, updated in lock-step; existing
`backend/tests/test_merge.py` cases are updated to the new return.

```python
def align_and_merge(
    frames, selected, alias_map=None, *,
    field_groups: dict[str, list[str]] | None = None,   # canonical -> [raw names]
    semantic_types: dict[str, SemanticType] | None = None,  # replaces phone_cols
    dedup_key: str | None = None,
    required_fields: list[str] | None = None,           # for "complete"
    coalesce: bool = True,                               # vs keep="first"
    drop_invalid_key: bool = True,                       # replaces drop_null_key
    trim: bool = True,
) -> tuple[pl.DataFrame, pl.DataFrame, MergeSummary]:    # (clean, rejected, summary)
```

`MergeSummary` gains the richer fields (see §7).

### 4.2 Backend — endpoints (`routers/ml.py`)

- **`POST /merge/stage`** → extend `MergeStageOut` with `profiles:
  list[ColumnProfile]` and `suggestions: list[FieldGroupSuggestion]`. Existing
  `common_fields`/`all_fields` stay (frontend grouping still uses them).
- **`POST /merge/run`** → extend `MergeRunIn.options` with `field_groups`,
  `semantic_types`, `required_fields`, `coalesce`; add top-level **`dry_run:
  bool`**. When `dry_run=true`: compute `(clean, rejected, summary)`, return
  summary + a **preview** (`clean.head(30)` as records) + counts, but **do not**
  register a dataset. When `false`: register as today + also persist the
  rejected frame for download.
- **`GET /merge/{session_id}/rejected.csv`** (new) → streams the last run's
  rejected rows (written next to the parquet during a non-dry run).

### 4.3 Frontend

Split `MlMergeView` into a wizard container + step components:

```
components/ml/merge/
  MergeWizard.tsx         # step state machine (1..4), session, api orchestration
  MergeStepUpload.tsx     # B1 — dropzone + staged-file list
  MergeFieldGroups.tsx    # B2 — common / per-file groups + provenance
  MergeUnifySuggestions.tsx  # B2 — suggestion cards (accept/edit/split)
  MergeTypePicker.tsx     # B2 — per-canonical-field type confirm + samples
  MergeCleanStep.tsx      # B3 — key, required fields, per-type toggles
  MergePreview.tsx        # B4 — preview table + dry-run metrics
  MergeOutcome.tsx        # B4 — 8 metrics + fill-rate + per-file + exports
```

`types.ts`, `api/ml.ts` updated to match new contracts. `MlResultTabs.tsx`:
rename + reorder the tab. Old `MlMergeChips`/`MlMergeSummary` are absorbed/removed.

### 4.4 Data flow

```
B1 upload ──POST /merge/stage──▶ {files, common, all, profiles, suggestions}
                                         │
B2 user confirms field_groups + semantic_types (seeded by suggestions/profiles)
B3 user picks dedup_key + required_fields + per-type cleaning
                                         │
B4 ──POST /merge/run {dry_run:true}──▶ {summary, preview}      (recompute on change)
   ──POST /merge/run {dry_run:false}─▶ {summary, dataset}  → onDatasetCreated → Auto-EDA
```

---

## 5. Value-aware field engine [MVP core]

### 5.1 Column profiling

For each (file, column): sample up to 500 non-null values; compute
`inferred_type`, `confidence`, `samples`, `non_null`, `distinct`, `fill_rate`.

### 5.2 Semantic-type inference

Score each value against each type; pick the **highest-priority type clearing
its threshold** (≥0.70 of sampled values), in this disambiguation order:

| Priority | Type | Match test (per value) | Notes |
|---|---|---|---|
| 1 | **email** | matches `^[^@\s]+@[^@\s]+\.[^@\s]+$` | unambiguous |
| 2 | **phone** | `len(digits) in 9..15` and not email | beats number for digit strings |
| 3 | **date** | parses via a small format set (ISO, `d/m/Y`, `d-m-Y`, `Y/m/d`) | |
| 4 | **number** | parses as float after stripping `., ` separators | excludes phone (rule 2) |
| 5 | **category** | `distinct ≤ max(20, 0.05·n)` and mean length ≤ 30 | low-cardinality |
| 6 | **text** | fallback | |

`confidence` = fraction matching the chosen type. A column where no type clears
0.70 → **text** (confidence = its text fraction = 1.0, since everything is text).

### 5.3 Group suggestion [MVP]

Cluster columns across files into canonical groups:

- Two columns are suggested into the same group when **inferred types match**
  AND any of: equal normalized names · token-overlap ≥ 0.5 · one normalized name
  is a substring of the other.
- **Plus** (the "value giống nhau, tên khác" case): columns sharing a **strong
  type** (phone/email/date) are suggested together even when names are
  unrelated, tagged `reason="type"` and surfaced as *"gộp theo loại giá trị"*.
- `confidence` = blend(name_similarity, type_agreement). Suggestions are
  **proposals**; nothing is auto-applied — the user confirms in B2.

**[V2]** add value-set Jaccard overlap across files to catch same-data-different-
name for *generic* types (category/number/text).

### 5.4 Confirmation UX

- Each **suggestion card**: canonical name (editable) · member columns w/ file
  badges · inferred type · confidence · 3–5 value samples · **Đồng ý / Sửa /
  Tách**.
- Each **canonical field** in the type picker: inferred type + value samples +
  a **dropdown** to override (the 6 types). This is the "à field 'phone' này có
  thật là SĐT không" checkpoint.

---

## 6. Semantic types & cleaning [MVP]

`normalize_value(v, t)` / `is_valid(v, t)`:

| Type | Normalize | Valid when |
|---|---|---|
| phone | digits → if ≥9: `'0'+last9` else None | result non-null |
| email | trim + lowercase | matches email regex |
| date | parse (format set) → ISO `YYYY-MM-DD` | parsed |
| number | strip `., ` separators → float → canonical str | parsed |
| category | trim + collapse whitespace | non-empty |
| text | trim | non-empty |

Cleaning is **driven by the confirmed `semantic_types`**, applied per merged
canonical column. `clean_phone` becomes the `phone` branch (behavior unchanged,
so the notebook phone numbers still reproduce).

---

## 7. Merge, dedup & metrics [MVP]

### 7.1 Alignment

Build each frame's rename map from `field_groups` (canonical → raw members) with
`alias_map`/`normalize_field` as fallback; select canonical `selected`; cast
Utf8; `concat(how="diagonal_relaxed")` — as today.

### 7.2 Cleaning

Trim + empty→null (as today), then `normalize_value` per column using
`semantic_types`.

### 7.3 Coalesce dedup

With a chosen `dedup_key` K (cleaned + validity-filtered):

1. `df_valid` = rows where K is non-null **and** `is_valid(K, type[K])`.
2. Rejected = the complement (null/invalid key) → goes to the rejected export.
3. Group `df_valid` by normalized K. For each group, **coalesce**: output one
   row; for every other field take the **first non-null** value across the
   group's rows (most-complete wins). `keep="first"` is the `coalesce=false`
   fallback.

### 7.4 Metrics (generic over K and required-fields R)

```
total_raw        = Σ file row counts
valid_format     = rows where is_valid(K)              # 3293
null_or_wrong    = total_raw − valid_format            # 190
distinct         = n_unique(valid K)                   # 2932
dup_removed_clean= valid_format − distinct             # 361  (Q8: shown)
dup_removed_raw  = total_raw   − distinct              # 551  (Q8: shown)
complete         = distinct groups where all R non-null after coalesce   # 612
incomplete       = distinct − complete                 # 2320
```

`MergeSummary` carries all of the above plus:

- `per_field_fill_rate: dict[str, float]` (non-null / distinct, post-coalesce).
- `per_file_contribution: dict[str, int]` (valid rows contributed per file).
- `rejected: int` (= null_or_wrong).

The clean dataset = the `distinct` coalesced rows. `complete` is a **metric**,
not a filter (incomplete rows stay in the dataset).

---

## 8. Wizard UX [MVP]

- **B1 Upload** — `MlMergeDropzone` (reused) → staged-file list (name · rows ·
  cols · remove). "Tiếp tục" stages via `/merge/stage`.
- **B2 Map & unify** — two columns:
  - left: **Field chung (mọi file)** / **Field riêng** lists with `x/N` badges
    + hover file names;
  - right: **suggestion cards** (§5.4) + per-canonical **type picker**. User
    selects which canonical fields to include.
- **B3 Clean & dedup** — pick **dedup key** (single, from included fields);
  per-type cleaning toggles (auto-on by type, e.g. normalize phone/date, trim);
  pick **required fields** (for "đủ thông tin"); option *bỏ dòng khóa rỗng/sai*.
- **B4 Preview & create** — `dry_run` preview (~30 rows) + the §7.4 metric cards
  (both 361/551) + fill-rate table + per-file bars + **CSV / XLSX / Tải bản bị
  loại** + **"Tạo dataset"** → `handleDatasetCreated` (lands on Auto-EDA, as
  today). Re-running B2/B3 re-triggers the dry-run.

---

## 9. API contract (delta)

```ts
// stage (extends MergeStageResult)
profiles: ColumnProfile[]
suggestions: FieldGroupSuggestion[]

// run input (extends MergeOptions; old phone_cols/drop_null_key removed)
field_groups: Record<string, string[]>
semantic_types: Record<string, SemanticType>
required_fields: string[]
coalesce: boolean
drop_invalid_key: boolean   // default true
// + MergeRunIn.dry_run: boolean

// run output
// dry_run=true  -> { summary, preview: Record<string,string>[] }   (no dataset)
// dry_run=false -> { summary, dataset, rejected_url }
```

`MergeSummaryOut` extends with `valid_format, null_or_wrong, dup_removed_clean,
dup_removed_raw, complete, incomplete, per_field_fill_rate, per_file_contribution,
rejected`. (Old names kept as aliases where cheap to avoid churn.)

---

## 10. Tab rename / reposition

`MlResultTabs.tsx` `TABS`: change the `merge` entry label `'Gộp file' →
'Combine file'` and move it from first to **just before `eda`**:
`… cohort · merge · eda`. The no-dataset special-case (merge can run without a
dataset) stays. Default landing tab unchanged.

---

## 11. Testing [MVP]

Backend `pytest` (pure-polars, no FastAPI), in `backend/tests/test_merge.py`:

- `normalize_value`/`is_valid` per type (phone lenient rule, email, date
  formats, number separators).
- `profile_columns` types a synthetic mixed frame correctly (phone col under 3
  different names all → phone).
- `suggest_groups` clusters the 3 phone-named columns into one canonical group.
- `align_and_merge` **reproduces the notebook numbers** from a synthetic fixture
  engineered to yield exactly `3483 / 3293 / 190 / 551 / 361 / 2932 / 612 /
  2320` (validates the metric math end-to-end).
- Coalesce fills blanks from duplicate rows (most-complete wins).

Frontend: `npm run build` green (tsc + vite).

---

## 12. Delivery

Per project constraints: implement in the worktree, commit, **FF-merge to local
`master`** so it reaches the MAIN working tree (where the dev server runs).
**Do NOT push** (`master` history contains live secrets). `.env` stays
untracked.

---

## 13. Open items

- **Sample data**: the 23 source `.xlsx` (Colab `/content/File_Nghiem_Thu`) are
  not in the repo. The engine runs at upload-time, so this doesn't block coding,
  but 2–3 representative files would let us validate the type-inference and
  suggestion heuristics against real data before finalizing thresholds.
