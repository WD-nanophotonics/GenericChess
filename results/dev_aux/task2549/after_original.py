from pathlib import Path
import json,hashlib,subprocess,sys,datetime
D=Path('results/dev_aux/task2549');T=Path('results/dev_aux/task2546')
def run():
 assert (T/'orchestration-ended.json').exists() and not(D/'started.json').exists()
 p=json.loads((D/'plan.json').read_text());p['pins']={str(f).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest()for f in[T/'result.json',T/'plan.json',D/'evaluate.py']};(D/'plan.json').write_text(json.dumps(p,indent=2));(D/'pre-fitness-binding.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),models_sha=hashlib.sha256((T/'result.json').read_bytes()).hexdigest(),plan_sha=hashlib.sha256((D/'plan.json').read_bytes()).hexdigest(),selection='ALL original endpoints, no adaptation to D2fitness')))
 subprocess.run([sys.executable,'-m','results.dev_aux.task2549.evaluate'],check=True)
if __name__=='__main__':run()
