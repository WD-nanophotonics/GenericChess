import ast,json,sys,time,hashlib,random
from pathlib import Path
from fractions import Fraction
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task437';O.mkdir(exist_ok=True);future=(R/'results/dev_aux/task436/audit.py').read_text(encoding='utf-8');node=ast.parse(future);tf=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name=='tables');exec(compile(ast.Module(body=[tf],type_ignores=[]),'future_tables_component','exec'))
text=(R/'results/dev_aux/task426/audit.py').read_text(encoding='utf-8');a=text.index('def random_audit(');b=text.index("folder=R/'results/dev_aux/task425'",a);exec(compile(text[a:b],'shared_native_random_component','exec'))
t0=time.perf_counter();games=0;go=0;pv=0;draws=0;price=0
d=json.loads((R/'results/dev_aux/task417/declaration.json').read_text(encoding='utf-8'))
for g in map(json.loads,(R/'results/dev_aux/task419/games.jsonl').open(encoding='utf-8')):
 d['nodes']=1024;n,qs,nd=random_audit(g);games+=1;go+=len(qs);pv+=n;draws+=nd
for g in map(json.loads,(R/'results/dev_aux/task428/games.jsonl').open(encoding='utf-8')):
 if g['opponent_arm']!='random':continue
 d['nodes']=8192;n,qs,nd=random_audit(g);games+=1;go+=len(qs);pv+=n;draws+=nd
for task,field in [(421,'prices'),(425,'price_acks'),(428,'price_acks'),(427,'price_acks')]:
 price+=tables(json.loads((R/f'results/dev_aux/task{task}/result.json').read_text(encoding='utf-8'))[field])
out=dict(status='PASS_COMPONENTS_REAL_EXISTING_FIXTURES',existing_games_replayed=games,existing_candidate_queries=go,existing_PV_move_checks=pv,random_draws=draws,price_table_entries=price,new_go=0,new_games=0,seconds=time.perf_counter()-t0,future_436_sha256=hashlib.sha256((R/'results/dev_aux/task436/audit.py').read_bytes()).hexdigest(),scope='Onlysharedindependentnative random-game checker at1024/8192 andfuturetables component onREALcomplete27records; future432..435 production/fullaudit/qualification NOTexecuted. No mockfuture outcomes orentryacceptance.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
