"""Import the bundled historical analyst decisions into the configured memory bank."""
import json
from pathlib import Path
from . import memory

ROOT = Path(__file__).resolve().parents[1]
history = json.loads((ROOT / "data" / "history.json").read_text(encoding="utf-8"))
for item in history:
    result = memory.retain(item, item["analyst_verdict"], item["analyst_reason"])
    print(item["id"], result["mode"], result["message"])
print(f"Processed {len(history)} historical examples. Memory mode: {memory.mode()}")
