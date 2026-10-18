from pathlib import Path
import json,hashlib
def run():
 src=Path("results/dev_aux/task2577/result.json");d=Path("results/dev_aux/task2579");s=json.loads(src.read_text());s["arms"]=[a for a in s["arms"]if a["method"].endswith("|q2")];s["source_binding_sha"]=hashlib.sha256(src.read_bytes()).hexdigest();s["scope"]="ALLq2deploymodels frommainbinding; no price/seedselection. Fixedq2foes separatelyregistered."
 (d/"result.json").write_text(json.dumps(s,indent=2));print(json.dumps(dict(bound_models=len(s["arms"]))))
if __name__=="__main__":run()
