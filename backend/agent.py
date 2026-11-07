"""Alert triage logic. Uses retrieved memories as evidence, never as automatic truth."""
import json
import os
from dotenv import load_dotenv
from . import memory

load_dotenv()

def _rule_based(alert, memories):
    severity = str(alert.get("severity", "medium")).lower()
    details = str(alert.get("details", "")).lower()
    ip = str(alert.get("source_ip", ""))
    suspicious = any(word in details for word in ["impossible travel", "multiple failed", "malware", "ransomware",
                                                    "privilege escalation", "new country", "exfiltration"])
    remembered = " ".join(m.get("text", "") for m in memories).lower()
    same_ip_seen = bool(ip and ip in remembered)
    if suspicious or severity == "critical":
        verdict = "Escalate"
        confidence = 82
        explanation = "The alert contains high-risk indicators or critical severity. Escalate for human investigation."
    elif severity == "high":
        verdict = "Needs review"
        confidence = 72
        explanation = "High severity warrants analyst review even if similar historical activity exists."
    elif same_ip_seen and severity in ("low", "medium"):
        verdict = "Likely benign"
        confidence = 68
        explanation = "A prior memory mentions this source IP. Confirm the host, user, timing and activity still match before closing."
    else:
        verdict = "Needs review"
        confidence = 60
        explanation = "There is not enough reliable history to safely classify this alert. Review the evidence."
    return {"verdict": verdict, "confidence": confidence, "explanation": explanation,
            "key_factors": ["Rule: " + str(alert.get("rule_name", "Unknown")),
                            "Severity: " + severity,
                            "Historical matches: " + str(len(memories))]}

def triage(alert):
    memories = memory.recall(alert)
    fallback = _rule_based(alert, memories)
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return {**fallback, "model": "Rule-based fallback (add GROQ_API_KEY for Groq)",
                "memories": memories, "memory_mode": memory.mode()}
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        prompt = {
            "alert": alert,
            "prior_analyst_memories": memories,
            "instructions": [
                "Act as a cautious SOC alert triage assistant.",
                "Return JSON only with verdict, confidence, explanation, key_factors.",
                "verdict must be Likely benign, Needs review, or Escalate.",
                "confidence is a heuristic confidence score from 0 to 100, not a calibrated probability.",
                "Do not treat memory as proof. A new source IP, host, user, country, or changed behavior weakens similarity.",
                "Critical severity, malware, ransomware, exfiltration, privilege escalation, or multiple failed logins should be escalated or urgently reviewed.",
                "Never claim an alert is safe solely because a similar alert was benign."
            ]
        }
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {"role": "system", "content": "You are a careful security operations alert triage assistant. Output valid JSON only."},
                {"role": "user", "content": json.dumps(prompt)}
            ],
            temperature=0.2,
            max_completion_tokens=700,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        verdict = data.get("verdict")
        if verdict not in ["Likely benign", "Needs review", "Escalate"]:
            raise ValueError("Unexpected verdict")
        confidence = max(0, min(100, int(data.get("confidence", fallback["confidence"]))))
        return {"verdict": verdict, "confidence": confidence,
                "explanation": str(data.get("explanation", fallback["explanation"])),
                "key_factors": data.get("key_factors", fallback["key_factors"]),
                "model": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
                "memories": memories, "memory_mode": memory.mode()}
    except Exception as exc:
        return {**fallback, "model": f"Rule-based fallback (Groq error: {exc})",
                "memories": memories, "memory_mode": memory.mode()}
