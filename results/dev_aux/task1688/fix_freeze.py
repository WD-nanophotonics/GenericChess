from pathlib import Path
import ast,json
R=Path.cwd();O=R/'results/dev_aux/task1688'
s=(O/'freeze.py').read_text(encoding='utf-8-sig').replace("task1690'","task1692'").replace('q[16]','q[64]');(O/'freeze_fixed.py').write_text(s,encoding='utf8');ast.parse(s)
s=(O/'transfer.py').read_text(encoding='utf-8-sig').replace("task1691'","task1693'").replace('task1690/plan.json','task1692/plan.json');(O/'transfer_fixed.py').write_text(s,encoding='utf8');ast.parse(s)
for n,cause in [(1690,'Frozenrootgenerator retained q[16]sidefilter whilevalidstate usesq[64]; priceblindfirstroot samplingfailed beforequeries.'),(1691,'Dependenttransfer entry attempted missing1690plan afterfreeze failure; noengine/query/data. Shellpipeline dependency now aborts onnonzero.')]:
 (R/f'results/dev_aux/task{n}/failure.json').write_text(json.dumps({'status':'PREQUERY_FAILURE_PRESERVED','cause':cause,'actual_go':0,'correction':'task1688/freeze_fixed.py andtransfer_fixed.py,new1692/1693'},indent=2))
