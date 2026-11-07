from collections import Counter

def calculate(alerts):
    reviewed = [a for a in alerts if a.get("analyst_verdict")]
    verdicts = Counter(a["analyst_verdict"] for a in reviewed)
    return {
        "total_alerts": len(alerts),
        "reviewed_alerts": len(reviewed),
        "pending_alerts": len(alerts) - len(reviewed),
        "verdict_counts": dict(verdicts),
        "review_rate": round((len(reviewed) / len(alerts) * 100), 1) if alerts else 0
    }
