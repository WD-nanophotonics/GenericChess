"""Independent stdlib replay of pinned physical-outcome timer and reference."""
import ast,collections,hashlib,json,zipfile,random,math
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).parent
source=ROOT/'.local_agent/availability-core-20261011/physical_outcome.py'
text=source.read_text();tree=ast.parse(text)
stage_ast=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='stage')
clock=SimpleNamespace(now=0.0)
clock.perf_counter=lambda:clock.now
p=SimpleNamespace(stack=[])
ns={'time':clock,'p':p,'outside':collections.Counter(),'calls':[]}
exec(compile(ast.Module(body=[stage_ast],type_ignores=[]),str(source),'exec'),ns)
checks=[]
def execute_node(node):
    def body():
        for piece in node['pieces']:
            if isinstance(piece,dict):wrapped[piece['id']]()
            else:clock.now+=piece
    return ns['stage'](node['id'],body)
def make_tree(rng,depth,counter):
    name='n'+str(next(counter));pieces=[rng.randrange(1,7)]
    if depth:
        for _ in range(rng.randrange(1,4)):
            pieces += [make_tree(rng,depth-1,counter),rng.randrange(1,7)]
    return {'id':name,'pieces':pieces}
def walk(node):
    yield node
    for x in node['pieces']:
        if isinstance(x,dict):yield from walk(x)
def oracle(node):
    own=sum(x for x in node['pieces'] if not isinstance(x,dict))
    return own+sum(oracle(x)[0] for x in node['pieces'] if isinstance(x,dict)),own
for seed in range(32):
    rng=random.Random(seed);node=make_tree(rng,seed%4,iter(range(10000)))
    bucket=collections.Counter();p.stack=[bucket];clock.now=0.;ns['calls']=[]
    wrapped={n['id']:execute_node(n) for n in walk(node)}
    wrapped[node['id']]()
    for n in walk(node):
        inclusive,exclusive=oracle(n)
        assert bucket[n['id']+'_calls']==1
        assert bucket[n['id']+'_inclusive_seconds']==inclusive
        assert bucket[n['id']+'_exclusive_seconds']==exclusive
    assert not ns['calls']
    assert sum(v for k,v in bucket.items() if k.endswith('_exclusive_seconds'))==clock.now
    checks.append({'seed':seed,'stage_count':len(wrapped),'total':clock.now})
# Exception nesting must preserve both frame balance and elapsed bookkeeping.
p.stack=[collections.Counter()];clock.now=0.;ns['calls']=[]
def failing_leaf():
    clock.now+=3;raise RuntimeError('injected leaf failure')
leaf=ns['stage']('leaf',failing_leaf)
def parent_body():
    clock.now+=2;leaf()
parent=ns['stage']('parent',parent_body)
try:parent()
except RuntimeError:pass
assert not ns['calls']
assert p.stack[-1]['parent_inclusive_seconds']==5
assert p.stack[-1]['parent_exclusive_seconds']==2
# Calls after formal push closes cannot be attributed to a child bucket.
p.stack=[];ns['outside']=collections.Counter();clock.now=0.
ns['stage']('classifier_check',lambda:setattr(clock,'now',clock.now+7))()
assert ns['outside']['classifier_check_inclusive_seconds']==7
index=json.loads((ROOT/'docs/research/data/physical_outcome_20261011.json').read_text())
with zipfile.ZipFile(ROOT/index['archive']['path']) as z:
    raw=z.read('.local_agent/availability-core-20261011/physical-outcome.json');reference=json.loads(raw)
def non_time(v):
    if isinstance(v,dict):return {k:non_time(x) for k,x in v.items() if 'seconds' not in k and not k.startswith('time_')}
    if isinstance(v,list):return [non_time(x) for x in v]
    return v
summaries=[]
for order in range(2):
    rows=[r for r in reference['rows'] if r['order']==order]
    assert len(rows)==2 and {r['measured'] for r in rows}=={True,False}
    assert non_time(rows[0]['decision'])==non_time(rows[1]['decision'])
    row=next(r for r in rows if r['measured']);totals=collections.Counter()
    for v in row['stages']:
        if v['outcome']=='excluded':totals[v['metric']]+=v['value']
    assert totals['children']==35187
    for name in ('terminal','availability','component_diff','snapshot','context','runtime_frontier'):
        assert totals[name+'_calls']==totals['children']
    # From actual source graph: terminal -> availability -> trial -> transition/attack.
    residuals={
        'terminal_to_availability':totals['terminal_inclusive_seconds']-totals['terminal_exclusive_seconds']-totals['availability_inclusive_seconds'],
        'availability_to_trial':totals['availability_inclusive_seconds']-totals['availability_exclusive_seconds']-totals['trial_inclusive_seconds'],
    }
    assert all(abs(x)<1e-8 for x in residuals.values())
    assert row['decision']['completed_depth']==2 and row['decision']['termination_reason']=='completed_depth'
    assert row['decision']['native_legality_calls']==3179 and row['decision']['native_legality_fallbacks']==0
    summaries.append({'order':order,'excluded':dict(totals),'nesting_residuals':residuals,'decision':non_time(row['decision'])})
assert {k:v for k,v in summaries[0]['excluded'].items() if k.endswith('_calls') or k=='children'}=={k:v for k,v in summaries[1]['excluded'].items() if k.endswith('_calls') or k=='children'}
report={'kind':'source-extracted synthetic timer replay + archived-reference consistency, not a fresh search replication',
 'producer_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'reference_sha256':hashlib.sha256(raw).hexdigest(),
 'tree_replays':checks,'exception_balance':True,'post_push_classifier_cost_outside':True,'reference':summaries,
 'pitfall':'Adding terminal inclusive to availability inclusive double-counts availability; exclusive sums cover only selected seams. Classification/pop/untimed push work and instrumentation overhead are excluded; this is not predicted removable wall time.',
 'limitations':['No fresh D2 engine execution','No independently measured wall-clock timing','Native enabled requested in source; archived decision records actual native calls and zero fallback','Session identity assertion is source-level; restoration was not independently executed']}
(OUT/'audit_result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'trees':len(checks),'stages':sum(c['stage_count'] for c in checks),'orders':len(summaries),'excluded_each':35187,'nesting_residuals':[s['nesting_residuals'] for s in summaries]},indent=2))
