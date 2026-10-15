from pathlib import Path
import json
from results.dev_aux.task1878.profile_audit import audit
r=audit('results/dev_aux/task1898')
with Path('results/dev_aux/task1900/filter_profiles.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r))
