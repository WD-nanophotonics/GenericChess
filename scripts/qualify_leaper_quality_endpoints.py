"""Source/data-only quality endpoint audit; no game engine or archived code execution."""
from __future__ import annotations
import argparse, collections, gzip, hashlib, itertools, json, subprocess
from pathlib import Path
from tools.local_agent.common import write_json

H6_SHA = '5584387c8de5b23a3b1524cce9c29bd694bee2d8'
H6_ROOT = 'docs/research/data/leaper_h6_initial_truth_20261023/'
H6_HASHES = {'inputs.json.gz':'75ce22f0ce2b4bc522a8f1e0149d5e68a138eefc45468068779e84146720956b', 'truth.json.gz':'56e720c681c4417693758a777c6625485c6fd330f283242c74442c9440a1911c'}

def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'))
def digest(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def load(p):
 p=Path(p);raw=p.read_bytes();return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)
def action(a):
 # Preserve full semantic identity; normalize only the two stored wire formats.
 if 'from_square' not in a:return a
 return dict(kind='semantic_board',actor_type_id=a['actor_type_id'],pattern_id=a['pattern_id'],geometry_id=a['geometry_id'],promotion_target_id=a.get('promotion_target_id'),**{'from':[a['from_square']['file'],a['from_square']['rank']],'to':[a['to_square']['file'],a['to_square']['rank']]})
def geometry(rule):
 """Restricted leap-template geometry/roster descriptor, NOT rules equivalence.

 Canonical under square D4 symmetry, type renaming and simultaneous owner swap.
 Excludes initial layouts, clocks and rule policies; those stay separate contracts.
 Equal descriptors are not a proof of complete-rule equivalence. Different
 descriptors distinguish templates only under these declared transformations.
 """
 n=rule['board_size'];counts=collections.Counter((p['current_type_id'],p['owner']) for row in rule['initial_position'] for p in row if p)
 variants=[]
 for swap in (False,True):
  for flip in (False,True):
   for turns in range(4):
    types=[]
    for t in rule['piece_types']:
     offsets=[]
     for atom in t['movement_atoms']:
      assert atom['kind']=='leap','descriptor limited to leap templates'
      x,y=atom['offset']
      if abs(x)>=n or abs(y)>=n:continue # no finite-board incidence
      if flip:x=-x
      for _ in range(turns):x,y=-y,x
      offsets.append((x,y))
     owners=(counts[t['type_id'],int(swap)],counts[t['type_id'],1-int(swap)])
     types.append((bool(t.get('is_anchor')),owners,sorted(set(offsets))))
    variants.append(canon((n,sorted(types))))
 return hashlib.sha256(min(variants).encode()).hexdigest()

def dense_bounds(rows):
 """Finite signed utility possibilities; missing/ongoing is never DRAW."""
 assert len(rows)%2==0
 indices=[r['game_id'] for r in rows];assert sorted(indices)==list(range(len(rows)))
 unknown=[r['game_id'] for r in rows if r['status']!='TERMINAL']
 assert len(unknown)<=12, 'bounded metadata enumeration only'
 possibilities=[]
 for completion in itertools.product((-1,0,1),repeat=len(unknown)):
  values=dict(zip(unknown,completion))
  for r in rows:
   if r['status']=='TERMINAL':
    t=r['Core_terminal'];assert t['status']!='ongoing'
    w=t['winner'];assert w in (None,0,1)
    values[r['game_id']]=0 if w is None else 1 if w==r['long_seat'] else -1
  per_family=[values[2*f]+values[2*f+1] for f in range(len(rows)//2)]
  possibilities.append((sum(values.values())/len(rows),sum(x>0 for x in per_family)))
 return dict(signed_mean_bounds=[min(x[0] for x in possibilities),max(x[0] for x in possibilities)],positive_family_bounds=[min(x[1] for x in possibilities),max(x[1] for x in possibilities)],completions=len(possibilities),unknown=unknown)

def source_h6():
 values={};provenance=[]
 for name,expected in H6_HASHES.items():
  raw=subprocess.check_output(['git','show',H6_SHA+':'+H6_ROOT+name]);assert hashlib.sha256(raw).hexdigest()==expected
  values[name]=json.loads(gzip.decompress(raw));provenance.append(dict(commit=H6_SHA,path=H6_ROOT+name,sha256=expected))
 return values['inputs.json.gz'],values['truth.json.gz'],provenance

def audit(output):
 inputs,truth,provenance=source_h6();families={f['family']:f for f in inputs['families']};by=collections.defaultdict(list)
 for r in inputs['rows']:by[r['family']].append(r)
 h6=[];truth_by_id={r['id']:r for r in truth['roots']};seen=set()
 for t in truth['roots']:
  r=by[t['family_index']][t['root_index']];assert r['fingerprint']==t['fingerprint'] and r['full_record']==t['record']
  # Exact template full rules are bound through both source input and truth packet.
  assert truth['rules'][t['fingerprint']]==families[r['family']]['rule']
  assert r['full_state']['position']['side_to_move']==0 and r['full_state']['ply_count']==0
  assert len(r['actions'])==len(t['action_bounds'])
  assert {canon(action(x['action'])) for x in r['actions']}=={canon(x['action']) for x in t['action_bounds']}
  values=[x['wdl_bounds'] for x in t['action_bounds']];assert all(lo==hi and lo in (-1,0,1) for lo,hi in values)
  lo,hi=t['wdl_bounds'];assert lo==hi==max(x[0] for x in values)
  distinct=len({x[0] for x in values})>1;assert distinct==t['wdl_fork']
  immediate=any(x['terminal']['winner']==0 for x in r['actions'])
  literal_immediate=bool(r['feature_oneply_scoring_child']);assert immediate==literal_immediate
  h6.append(dict(id=t['id'],family=r['family'],fingerprint=t['fingerprint'],setup_key=r['setup_key'],geometry=geometry(families[r['family']]['rule']),root_wdl=lo,values=sorted({x[0] for x in values}),fork=distinct,oneply_win=immediate,split=r['split'],record_sha256=r['record_sha256'],nonterminal_action_values=sorted({x['wdl_bounds'][0] for x in t['action_bounds'] if next(z for z in r['actions'] if action(z['action'])==x['action'])['terminal']['status']=='ongoing'})))
  assert t['id'] not in seen;seen.add(t['id'])
 counts=[]
 for f in inputs['families']:
  rs=[r for r in h6 if r['family']==f['family']]
  counts.append(dict(family=f['family'],masks=f['masks'],split=f['split'],roots=len(rs),geometry=rs[0]['geometry'] if rs else None,root_wdl=dict(collections.Counter(str(r['root_wdl']) for r in rs)),forks=sum(r['fork'] for r in rs),nonimmediate_forks=sum(r['fork'] and not r['oneply_win'] for r in rs),nonterminal_action_forks=sum(len(r['nonterminal_action_values'])>1 for r in rs)))
 old=Path('docs/research/data/leaper_h6_syntax_20261026');sources={};queries=[]
 for name in ['syntax-abort-queries.jsonl.gz','syntax-query-queries.jsonl.gz']:
  raw=(old/name).read_bytes();sources[str(old/name)]=hashlib.sha256(raw).hexdigest()
  for line in gzip.decompress(raw).splitlines():
   q=json.loads(line)
   if 'slot' in q:
    q.update(id=q['slot']['id'],arm=q['slot']['arm'],family=truth_by_id[q['slot']['id']]['family_index'])
    assert q['root_state_sha256']==q['id']
    expected=truth_by_id[q['id']]['record'];actual=q['before_record']
    assert actual['ruleset_fingerprint']==expected['ruleset_fingerprint'] and actual['actions']==expected['actions']
    assert actual.get('initial_setup_key')==expected.get('initial_setup_key') and actual['resigned_by']==expected['resigned_by']
   queries.append(dict(packet=name,**q))
 selected=[]
 for q in queries:
  t=truth_by_id[q['id']];choice=action(q['decision']['action']);bounds=[a['wdl_bounds'] for a in t['action_bounds'] if a['action']==choice];assert len(bounds)==1
  selected.append(dict(id=q['id'],family=q['family'],condition=q.get('condition','D6performance'),phase=q.get('phase','performance'),arm=q['arm'],best=t['wdl_bounds'][0],chosen=bounds[0][0],regret=t['wdl_bounds'][0]-bounds[0][0],depth=q['decision']['completed_depth'],packet=q['packet']))
 cohorts=[]
 for condition,phase in sorted({(x['condition'],x['phase']) for x in selected}):
  ss=[x for x in selected if x['condition']==condition and x['phase']==phase];cohorts.append(dict(condition=condition,phase=phase,returns=len(ss),unique_roots=len({x['id'] for x in ss}),families=len({x['family'] for x in ss}),inferior_unique_roots=len({x['id'] for x in ss if x['regret']>0}),inferior=sum(x['regret']>0 for x in ss),inferior_families=sorted({x['family'] for x in ss if x['regret']>0}),limits='Exposed abort/performance test conditions; not equal-wall quality trial or independently sampled returns.'))
 arenas=[]
 for label,name in [('resource','docs/research/data/leaper_root_order_quality_20261026/population-games/games.json.gz'),('pvs','docs/research/data/leaper_pvs_quality_pilot_20261026/pilot/games.json.gz')]:
  raw=Path(name).read_bytes();sources[name]=hashlib.sha256(raw).hexdigest();games=json.loads(gzip.decompress(raw));assert len(games)==24
  cases=collections.defaultdict(list)
  for g in games:cases[g['case_id']].append(g)
  for case,gs in sorted(cases.items()):
   assert len(gs)==2 and gs[0]['initial_record']==gs[1]['initial_record'] and gs[0]['fingerprint']==gs[1]['fingerprint']
   assert {g['long_seat'] if label=='resource' else g['on_seat'] for g in gs}=={0,1}
   outcomes=[]
   for g in gs:
    terminal=g['Core_terminal'];seat=g['long_seat'] if label=='resource' else g['on_seat'];winner=terminal['winner']
    outcomes.append(dict(game=g['game_id'],status=g['status'],terminal=terminal,seat=seat,net=0 if winner is None else 1 if winner==seat else -1,timing_eligible=g['timing_eligible'],queries=len(g['queries'])))
   arenas.append(dict(study=label,case=case,family=int(case.split('-f')[1].split('-')[0]),fingerprint=gs[0]['fingerprint'],record_sha256=digest(gs[0]['initial_record']),outcomes=outcomes))
 result=dict(scope='NEW joined endpoint stratification; source only; zeroCore/Player/solver/game/build. Not a replay or independent truth proof.',h6_sources=provenance,other_sources=sources,h6_roots=len(h6),families=counts,geometry_templates=len({r['geometry'] for r in h6}),all_derived_roots=h6,saved_search_cohorts=cohorts,saved_choices=selected,arenas=arenas,decision='NO_GO current records as already-qualified >=3-family near-strength equal-outer-time endpoint. H6 nonimmediate root-action forks can be development diagnostics only; current-play discrimination and fresh independent families remain unmeasured.')
 output.parent.mkdir(parents=True,exist_ok=True);assert not output.exists();write_json(output,result)
 print(json.dumps({k:result[k] for k in ['h6_roots','geometry_templates','families','saved_search_cohorts','decision']}))
if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();audit(a.output)
