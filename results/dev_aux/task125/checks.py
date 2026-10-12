import sys,json,hashlib
from pathlib import Path
root=Path.cwd();out=root/'results/dev_aux/task125';out.mkdir(exist_ok=True)
rows=[]
for task,name,tag in [('task108','test_controller.py','controller'),('task110','test_adapter.py','adapter')]:
 p=root/'results/dev_aux'/task/name;raw=p.read_bytes();before=hashlib.sha256(raw).hexdigest()
 sys.path.insert(0,str(p.parent));code=raw.decode().replace('Path(__file__).with_name("test_result.json")',repr(str(out/(tag+'_checks.json')))+' and Path('+repr(str(out/(tag+'_checks.json')))+')')
 g={'__file__':str(p),'__name__':'__main__'};exec(compile(code,str(p),'exec'),g)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==before
 rows.append(dict(source=str(p.relative_to(root)),source_sha256=before,check_count=g['output']['check_count'],output_file=tag+'_checks.json',change='Only output path redirected; all checks unchanged'))
(out/'checks.json').write_text(json.dumps(dict(complete=True,rows=rows,check_count=sum(r['check_count'] for r in rows),mature_games=0,scope='Existing meaningful dependency checks; not new scientific evidence'),indent=2),encoding='utf-8')