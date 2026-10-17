"""NEW heldout seeds for corrected episode TD; no refit or seed selection."""
from pathlib import Path
import json,hashlib
import results.dev_aux.task2493.evaluate as evaluator
if __name__=='__main__':
 out=Path('results/dev_aux/task2496');p=json.loads((out/'plan.json').read_text())
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h
 evaluator.OUT=out;evaluator.run()
