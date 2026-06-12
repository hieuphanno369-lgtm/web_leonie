import os
import json
import urllib.request
from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import get_connection


# ── AI helper ────────────────────────────────────────────────────────────────

def _call_ai(prompt: str, max_tokens: int = 1024) -> str:
    """Call Claude if ANTHROPIC_API_KEY is set, else fallback to Ollama."""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if api_key:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text.strip()

    # ── Ollama fallback ───────────────────────────────────────────────────────
    ollama_url   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
    payload = json.dumps({
        "model":  ollama_model,
        "prompt": prompt,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{ollama_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result["response"].strip()
    except Exception as e:
        raise RuntimeError(f"Ollama error ({ollama_url}): {e}")


def _strip_code_fence(raw: str) -> str:
    """Remove ```json ... ``` wrapper if present."""
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()

router = APIRouter(prefix="/action-plans", tags=["action-plans"])

APCategory = Literal['rfm', 'cohort', 'statistical', 'etl', 'dashboard', 'other']
APStatus   = Literal['draft', 'proposed', 'approved', 'in_progress', 'done']
APPriority = Literal['low', 'medium', 'high']
APApproval = Literal['pending', 'approved', 'rejected']


class APCreate(BaseModel):
    title: str
    category: APCategory = 'other'
    status: APStatus = 'draft'
    priority: APPriority = 'medium'
    problem: str | None = None
    pic_main: str | None = None
    pic_support: str | None = None
    due_date: str | None = None
    manager_notes: str | None = None
    approval: APApproval = 'pending'


class APPatch(BaseModel):
    title: str | None = None
    category: APCategory | None = None
    status: APStatus | None = None
    priority: APPriority | None = None
    problem: str | None = None
    pic_main: str | None = None
    pic_support: str | None = None
    due_date: str | None = None
    manager_notes: str | None = None
    approval: APApproval | None = None
    ai_timeline: str | None = None
    ai_checklist: str | None = None
    ai_input: str | None = None
    ai_output: str | None = None
    ai_value: str | None = None
    ai_impact: str | None = None
    ai_refs: str | None = None
    ai_suggestions: str | None = None


class APOut(BaseModel):
    id: str
    title: str
    category: str
    status: str
    priority: str
    problem: str | None
    pic_main: str | None
    pic_support: str | None
    due_date: str | None
    manager_notes: str | None
    approval: str
    ai_timeline: str | None
    ai_checklist: str | None
    ai_input: str | None
    ai_output: str | None
    ai_value: str | None
    ai_impact: str | None
    ai_refs: str | None
    ai_suggestions: str | None
    created: str
    updated: str


def _row(r) -> APOut:
    return APOut(**dict(r))


@router.get("", response_model=list[APOut])
def list_plans(status: APStatus | None = None):
    conn = get_connection()
    sql = "SELECT * FROM action_plans WHERE 1=1"
    params: list = []
    if status:
        sql += " AND status = ?"; params.append(status)
    sql += " ORDER BY created DESC"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [_row(r) for r in rows]


@router.post("", response_model=APOut, status_code=201)
def create_plan(body: APCreate):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO action_plans
           (title, category, status, priority, problem,
            pic_main, pic_support, due_date, manager_notes, approval)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (body.title, body.category, body.status, body.priority, body.problem,
         body.pic_main, body.pic_support, body.due_date, body.manager_notes, body.approval),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM action_plans WHERE rowid = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return _row(row)


@router.patch("/{plan_id}", response_model=APOut)
def patch_plan(plan_id: str, body: APPatch):
    conn = get_connection()
    fields = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_parts = [f"{k} = ?" for k in fields] + ["updated = datetime('now')"]
    set_sql = ", ".join(set_parts)
    values = list(fields.values()) + [plan_id]
    result = conn.execute(
        f"UPDATE action_plans SET {set_sql} WHERE id = ?", values
    )
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Plan not found")
    conn.commit()
    row = conn.execute("SELECT * FROM action_plans WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    return _row(row)


@router.delete("/{plan_id}", status_code=204)
def delete_plan(plan_id: str):
    conn = get_connection()
    result = conn.execute("DELETE FROM action_plans WHERE id = ?", (plan_id,))
    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Plan not found")
    conn.commit()
    conn.close()


@router.post("/{plan_id}/generate", response_model=APOut)
def generate_plan(plan_id: str):
    """Generate AI plan — uses Claude if ANTHROPIC_API_KEY set, else Ollama."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM action_plans WHERE id = ?", (plan_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Plan not found")
    plan = dict(row)

    prompt = (
        f"Bạn là DA senior người Việt. Tạo kế hoạch phân tích cho:\n"
        f"Tiêu đề: {plan['title']}\n"
        f"Danh mục: {plan['category']}\n"
        f"Vấn đề: {plan.get('problem') or 'Không có mô tả'}\n\n"
        "Trả về JSON với các keys sau, TOÀN BỘ nội dung viết bằng tiếng Việt:\n"
        "- timeline: [{week: 'Tuần X', tasks: 'mô tả công việc'}] (3-5 items)\n"
        "- checklist: [{done: false, text: 'nội dung tiếng Việt'}] (5-8 items)\n"
        "- input: {sources: ['nguồn dữ liệu'], tables: ['tên bảng'], notes: 'ghi chú'}\n"
        "- output: {deliverable: 'sản phẩm đầu ra', format: 'định dạng'}\n"
        "- value: 'giá trị mang lại (tiếng Việt)'\n"
        "- impact: 'tác động kỳ vọng (tiếng Việt)'\n"
        "- suggestions: 'đề xuất thêm (tiếng Việt)'\n"
        "Chỉ JSON, không giải thích, không markdown."
    )

    try:
        raw = _call_ai(prompt, max_tokens=2048)
        ai  = json.loads(_strip_code_fence(raw))
        conn.execute(
            """UPDATE action_plans SET
               ai_timeline=?, ai_checklist=?, ai_input=?, ai_output=?,
               ai_value=?, ai_impact=?, ai_suggestions=?,
               updated=datetime('now') WHERE id=?""",
            (
                json.dumps(ai.get("timeline", [])),
                json.dumps(ai.get("checklist", [])),
                json.dumps(ai.get("input", {})),
                json.dumps(ai.get("output", {})),
                ai.get("value", ""),
                ai.get("impact", ""),
                ai.get("suggestions", ""),
                plan_id,
            )
        )
        conn.commit()
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"AI generation failed: {e}")

    row = conn.execute("SELECT * FROM action_plans WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    return _row(row)


@router.post("/{plan_id}/refine", response_model=APOut)
def refine_plan(plan_id: str, body: dict):
    condition = body.get("condition", "")
    conn = get_connection()
    row = conn.execute("SELECT * FROM action_plans WHERE id = ?", (plan_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Plan not found")
    plan = dict(row)

    if not condition:
        row = conn.execute("SELECT * FROM action_plans WHERE id = ?", (plan_id,)).fetchone()
        conn.close()
        return _row(row)

    current_checklist = json.loads(plan.get("ai_checklist") or "[]")
    prompt = (
        f"Checklist hiện tại: {json.dumps(current_checklist, ensure_ascii=False)}\n"
        f"Điều kiện/yêu cầu bổ sung: {condition}\n\n"
        "Cập nhật checklist bằng tiếng Việt: giữ nguyên các items cũ, thêm items mới phù hợp với điều kiện bổ sung.\n"
        "Trả về JSON array [{\"done\": false, \"text\": \"nội dung tiếng Việt\"}]. Chỉ JSON, không giải thích."
    )

    try:
        raw              = _call_ai(prompt, max_tokens=512)
        updated_checklist = json.loads(_strip_code_fence(raw))
        conn.execute(
            "UPDATE action_plans SET ai_checklist=?, updated=datetime('now') WHERE id=?",
            (json.dumps(updated_checklist), plan_id)
        )
        conn.commit()
    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"AI refine failed: {e}")

    row = conn.execute("SELECT * FROM action_plans WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    return _row(row)
