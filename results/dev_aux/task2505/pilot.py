"""Fresh bounded-approximation pilot; original full-q cap is closed forever."""
from pathlib import Path
import json,hashlib
import results.dev_aux.task2502.pilot as pilot
from results.dev_aux.task2504.search import TrainingSearch
if __name__=='__main__':
 out=Path('results/dev_aux/task2505');p=json.loads((out/'plan.json').read_text())
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 pilot.OUT=out;pilot.TrainingSearch=TrainingSearch;pilot.run()
