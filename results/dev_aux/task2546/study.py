"""Sole serial experiment process: original TRAIN then prospectively fixed EVAL."""
from pathlib import Path
import json,subprocess,sys,hashlib,datetime
D=Path('results/dev_aux/task2546');E=Path('results/dev_aux/task2547')
def run():
 assert not(D/'orchestration-started.json').exists();(D/'orchestration-started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())))
 subprocess.run([sys.executable,'-m','results.dev_aux.task2546.run'],check=True)
 t=json.loads((D/'result.json').read_text());p=json.loads((E/'plan.json').read_text());p['pins']={str(f).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest()for f in[D/'result.json',D/'plan.json',D/'pins.json',E/'evaluate.py']};(E/'plan.json').write_text(json.dumps(p,indent=2));(E/'pre-fitness-binding.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),train_status=t['status'],arms=len(t['arms']),plan_sha=hashlib.sha256((E/'plan.json').read_bytes()).hexdigest(),models_sha=hashlib.sha256((D/'result.json').read_bytes()).hexdigest(),selection='ALL prospective endpoints/no result filtering')))
 subprocess.run([sys.executable,'-m','results.dev_aux.task2547.evaluate'],check=True)
 (D/'orchestration-ended.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='ORIGINAL_TRAIN_AND_EVAL_CLOSED')))
if __name__=='__main__':run()
