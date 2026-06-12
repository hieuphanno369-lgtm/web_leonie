"""KPI tracker CRUD — stores in data/kpi.json."""
import json
import uuid
from pathlib import Path
from datetime import datetime

KPI_FILE = Path("data/kpi.json")
PERIODS = ["weekly", "monthly", "quarterly"]


def load_kpis() -> list[dict]:
    if not KPI_FILE.exists():
        return []
    try:
        return json.loads(KPI_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(kpis: list[dict]) -> None:
    KPI_FILE.parent.mkdir(parents=True, exist_ok=True)
    KPI_FILE.write_text(
        json.dumps(kpis, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def add_kpi(name: str, unit: str, target: float, period: str = "monthly") -> dict:
    kpis = load_kpis()
    kpi = {
        "id":         str(uuid.uuid4())[:8],
        "name":       name,
        "unit":       unit,
        "target":     float(target),
        "period":     period,
        "actuals":    [],
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    kpis.append(kpi)
    _save(kpis)
    return kpi


def add_actual(kpi_id: str, value: float, note: str = "") -> None:
    """Add an actual data point to a KPI."""
    kpis = load_kpis()
    for k in kpis:
        if k["id"] == kpi_id:
            k["actuals"].append({
                "date":  datetime.now().strftime("%Y-%m-%d"),
                "value": float(value),
                "note":  note,
            })
    _save(kpis)


def delete_kpi(kpi_id: str) -> None:
    _save([k for k in load_kpis() if k["id"] != kpi_id])


def get_latest(kpi: dict) -> float | None:
    actuals = kpi.get("actuals", [])
    return actuals[-1]["value"] if actuals else None


def get_achievement_pct(kpi: dict) -> float | None:
    latest = get_latest(kpi)
    if latest is None or kpi["target"] == 0:
        return None
    return round(latest / kpi["target"] * 100, 1)
