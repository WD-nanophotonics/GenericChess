import subprocess,sys,json,hashlib
from pathlib import Path
p=Path('results/dev_aux/task2540');subprocess.run([sys.executable,'-X','utf8','-m','results.dev_aux.task2539.run'],check=True)
r=json.loads(Path('results/dev_aux/task2539/result.json').read_text());assert r['arms']
(p/'pre-fitness-binding.json').write_text(json.dumps(dict(training_result_sha=hashlib.sha256(Path('results/dev_aux/task2539/result.json').read_bytes()).hexdigest(),plan_sha=hashlib.sha256((p/'plan.json').read_bytes()).hexdigest(),scope='All available preregistered arms/rawweights, no selection; missing arms remain missing.'),indent=2))
subprocess.run([sys.executable,'-X','utf8','-m','results.dev_aux.task2540.evaluate'],check=True)
