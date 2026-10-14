from pathlib import Path
import json,importlib.util,collections,time
R=Path.cwd();O=R/'results/dev_aux/task1649';O.mkdir(exist_ok=False);start=time.monotonic()
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1626/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
G=R/'results/dev_aux/task1627';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));v=json.loads((G/'values.json').read_bytes());ix={s:i for i,s in enumerate(states)}
slots=(1,2,3,5,6,7)
def mask(s):return sum(1<<i for i,k in enumerate(slots) if s[k]!=16)
counts=collections.Counter(mask(s) for s in states);mate=collections.Counter();stale=collections.Counter();witness={}
for i,s in enumerate(states):
 if v['value'][i]==-1 and v['rank'][i]==0:
  assert not T.moves(s) and T.attacked(s,s[4*s[8]],1-s[8]);m=mask(s);mate[m]+=1;witness.setdefault(m,s)
 elif v['value'][i]==0 and not T.moves(s):stale[mask(s)]+=1
# Everyruleedge preserve/reduce exactownership stock; graph complete <=4 and separatelyALLliteralqualified.
edges=0
for line in (G/'edges.jsonl').open():
 x=json.loads(line)
 s=states[x['id']]; a=mask(s); assert [u for u,t in T.moves(s)]==[u for u,j in x['moves']]; assert all((mask(states[j])&a)==mask(states[j]) for u,j in x['moves']); edges+=len(x['moves'])
# No edge mutation or8x8 insufficient shortcut; closedstock derived by exact4board seedcoverage.
safe=[m for m in counts if not any((q&m)==q for q in mate)]
for m in safe:assert all(v['value'][i]==0 for i,s in enumerate(states) if mask(s)&m==mask(s))
z={'status':'PASS_COMPLETE_DOWNWARD_STOCK_CLOSURE_NO_CHECKMATE_PROOF','edge_closure_checks':edges,'slots':slots,'state_counts':dict(counts),'mate_counts':dict(mate),'stale_counts':dict(stale),'proved_no_mate_masks':safe,'mate_witnesses':{str(k):v for k,v in witness.items()},'proof':'Fullqualified<=4graph enumerates all rule-valid states. Stockownership canonlyloseactors via capture; noadds/transfers/promotions/drops. If no subsetstock hasanycheckmate state, no policy can everwin/lose: infinitecycles/nonterminalgame payoffDraw. Scope<=4only; do not claim full5stock coverage.','seconds':time.monotonic()-start};(O/'result.json').write_text(json.dumps(z,indent=2));print(z)

