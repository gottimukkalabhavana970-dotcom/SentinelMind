"""Memory adapter: Hindsight first, local JSON fallback for an easy offline demo."""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parents[1]
LOCAL_FILE = ROOT / "backend" / "local_memory.json"
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "sentinelmind-demo")
_client = None
_hindsight_ready = False

def _load_local():
    if LOCAL_FILE.exists():
        try:
            return json.loads(LOCAL_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def _save_local(items):
    LOCAL_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")

def _get_client():
    global _client, _hindsight_ready
    base_url = os.getenv("HINDSIGHT_BASE_URL", "").strip()
    if not base_url:
        return None
    if _client is not None:
        return _client
    try:
        from hindsight_client import Hindsight
        kwargs = {"base_url": base_url}
        api_key = os.getenv("HINDSIGHT_API_KEY", "").strip()
        if api_key:
            kwargs["api_key"] = api_key
        _client = Hindsight(**kwargs)
        try:
            _client.create_bank(bank_id=BANK_ID, name="SentinelMind SOC Alert Memory")
        except Exception:
            # Bank may already exist; the next operation will confirm connectivity.
            pass
        _hindsight_ready = True
        return _client
    except Exception as exc:
        print(f"[memory] Hindsight unavailable; using local JSON memory: {exc}")
        return None

def mode():
    return "Hindsight" if _get_client() else "Local JSON fallback"

def retain(alert: dict, verdict: str, reason: str):
    content = (
        f"SOC analyst verdict. Rule: {alert.get('rule_name')}. "
        f"Severity: {alert.get('severity')}. Source IP: {alert.get('source_ip')}. "
        f"Host: {alert.get('host')}. User: {alert.get('user')}. "
        f"Details: {alert.get('details')}. Verdict: {verdict}. "
        f"Analyst reason: {reason}. Recorded: {datetime.now(timezone.utc).isoformat()}."
    )
    client = _get_client()
    if client:
        try:
            client.retain(bank_id=BANK_ID, content=content)
            return {"stored": True, "mode": "Hindsight", "message": "Analyst verdict retained in Hindsight."}
        except Exception as exc:
            print(f"[memory] Hindsight retain failed: {exc}")
    items = _load_local()
    items.append({"content": content, "alert": alert, "verdict": verdict, "reason": reason,
                  "created_at": datetime.now(timezone.utc).isoformat()})
    _save_local(items)
    return {"stored": True, "mode": "Local JSON fallback", "message": "Verdict saved locally."}

def recall(alert: dict, limit: int = 6):
    query = (
        f"Previous SOC alerts similar to rule {alert.get('rule_name')}, "
        f"severity {alert.get('severity')}, source IP {alert.get('source_ip')}, "
        f"host {alert.get('host')}, user {alert.get('user')}, details {alert.get('details')}. "
        "Return prior analyst verdicts and reasons. Treat new IPs and changed context cautiously."
    )
    client = _get_client()
    if client:
        try:
            result = client.recall(bank_id=BANK_ID, query=query, max_tokens=2500, budget="low")
            return [{"text": item.text, "type": getattr(item, "type", "memory")} for item in result.results[:limit]]
        except Exception as exc:
            print(f"[memory] Hindsight recall failed: {exc}")
    items = _load_local()
    # Simple transparent keyword overlap fallback; not a semantic search engine.
    terms = set((str(alert.get("rule_name", "")) + " " + str(alert.get("host", "")) +
                 " " + str(alert.get("details", ""))).lower().split())
    scored = []
    for item in items:
        old = item.get("alert", {})
        old_terms = set((str(old.get("rule_name", "")) + " " + str(old.get("host", "")) +
                         " " + str(old.get("details", ""))).lower().split())
        score = len(terms & old_terms)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [{"text": x[1]["content"], "type": "local_memory"} for x in scored[:limit]]

def reflect():
    client = _get_client()
    if client:
        try:
            result = client.reflect(
                bank_id=BANK_ID,
                query=("Summarize recurring SOC alert patterns, known benign activity, suspicious changes, "
                       "and analyst lessons. Separate evidence from assumptions.")
            )
            return {"summary": result.text, "mode": "Hindsight"}
        except Exception as exc:
            print(f"[memory] Hindsight reflect failed: {exc}")
    items = _load_local()
    if not items:
        return {"summary": "No analyst verdicts have been recorded yet. Review alerts and submit verdicts to build organizational memory.",
                "mode": "Local JSON fallback"}
    counts = {}
    for item in items:
        key = item.get("alert", {}).get("rule_name", "Unknown rule")
        counts.setdefault(key, {"total": 0, "verdicts": {}})
        counts[key]["total"] += 1
        v = item.get("verdict", "Unknown")
        counts[key]["verdicts"][v] = counts[key]["verdicts"].get(v, 0) + 1
    lines = ["Patterns from saved analyst feedback (local keyword-memory mode):"]
    for rule, data in sorted(counts.items(), key=lambda x: x[1]["total"], reverse=True):
        lines.append(f"- {rule}: {data['total']} reviewed; {data['verdicts']}")
    return {"summary": "\n".join(lines), "mode": "Local JSON fallback"}
