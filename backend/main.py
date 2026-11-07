from pathlib import Path
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .agent import triage
from . import memory
from .metrics import calculate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HISTORY_FILE = DATA / "history.json"
LIVE_FILE = DATA / "live_alerts.json"

app = FastAPI(title="SentinelMind SOC Alert Triage", version="1.0.0",
              description="Memory-augmented SOC alert triage demo")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def write_live(alerts):
    LIVE_FILE.write_text(json.dumps(alerts, indent=2), encoding="utf-8")

alerts = read_json(LIVE_FILE) if LIVE_FILE.exists() else []
# Analyze the shipped demo alerts at startup so the feed is immediately interactive.
for _alert in alerts:
    if not _alert.get("analysis"):
        _alert["analysis"] = triage(_alert)

class AlertIn(BaseModel):
    rule_name: str
    severity: str = "medium"
    source_ip: str = "unknown"
    host: str = "unknown"
    user: str = "unknown"
    timestamp: str = "just now"
    details: str = ""

class VerdictIn(BaseModel):
    alert_id: str
    verdict: str
    reason: str = Field(default="Reviewed by analyst", max_length=1000)

@app.get("/api/health")
def health():
    return {"status": "ok", "memory_mode": memory.mode()}

@app.get("/api/alerts")
def get_alerts():
    return alerts

@app.post("/api/alerts")
def create_alert(payload: AlertIn):
    item = payload.model_dump()
    item["id"] = f"AL-{len(alerts)+1:03d}"
    item["status"] = "Pending"
    item["analyst_verdict"] = None
    item["analysis"] = triage(item)
    alerts.insert(0, item)
    write_live(alerts)
    return item

@app.post("/api/verdict")
def submit_verdict(payload: VerdictIn):
    if payload.verdict not in ["Likely benign", "Needs review", "Escalate"]:
        raise HTTPException(status_code=400, detail="Invalid verdict")
    item = next((a for a in alerts if a["id"] == payload.alert_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Alert not found")
    item["analyst_verdict"] = payload.verdict
    item["analyst_reason"] = payload.reason
    item["status"] = "Reviewed"
    result = memory.retain(item, payload.verdict, payload.reason)
    write_live(alerts)
    return {"success": True, "memory": result, "alert": item}

@app.get("/api/metrics")
def get_metrics():
    return calculate(alerts)

@app.get("/api/patterns")
def get_patterns():
    return memory.reflect()

@app.post("/api/demo/reset")
def reset_demo():
    global alerts
    alerts = read_json(LIVE_FILE)
    # Reset to the shipped live-alert demo set; does not erase Hindsight or local memory.
    write_live(alerts)
    return {"success": True, "count": len(alerts)}

app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
