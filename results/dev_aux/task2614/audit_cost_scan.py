"""Schema, cap, count and no-label audit for DEV_AUX2614."""
import json
from pathlib import Path
T=Path(__file__).parent
r=json.loads((T/"result.json").read_text(encoding="utf-8-sig"))
rows=[json.loads(x) for x in (T/"slots.jsonl").read_text(encoding="utf-8-sig").splitlines()]
assert r["slots_completed"]==r["slots_planned"]==32
assert len(rows)==32 and len({x["slot"] for x in rows})==32
assert r["outcomes_or_weights_emitted"] is False
for row in rows:
    assert row["nodes_total"]==row["nodes_candidate"]+row["nodes_fixed_foe"]
    assert row["nodes_total"]<=20000
    assert not ({"outcome","winner","draw","weights","fitness","score"}&set(row))
    assert row["incomplete_queries"] in (0,1)
assert r["nodes_total"]==sum(x["nodes_total"] for x in rows)
assert r["wall_seconds"]<600
print(json.dumps({"status":"PASS","slots":len(rows),"nodes":r["nodes_total"],"seconds":r["wall_seconds"],"label_keys_absent":True},indent=2))
