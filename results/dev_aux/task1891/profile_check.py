from pathlib import Path
import json
from results.dev_aux.task1878.profile_audit import audit
r=audit('results/dev_aux/task1890')
with Path('results/dev_aux/task1891/profile_report.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
