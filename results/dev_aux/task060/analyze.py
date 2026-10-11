"""Frozen record audit. Does not import or execute an engine."""
import subprocess,json,zipfile,io,hashlib,collections,ast
from pathlib import Path
PIN='bebe3d98ebb0832207e112ca0755fa9837cef3e7'
OUT=Path(__file__).resolve().parent
def git(path): return subprocess.check_output(['git','show',PIN+':'+path])
def digest(b):return hashlib.sha256(b).hexdigest()
index=json.loads(git('docs/research/data/q4_iteration_20261011.json'))
raw=git(index['archive']['path']); z=zipfile.ZipFile(io.BytesIO(raw))
assert digest(raw)==index['archive']['sha256']
assert len(raw)==index['archive']['bytes']
assert len(z.namelist())==len(index['members'])==56
assert set(z.namelist())=={m['path'] for m in index['members']}
for m in index['members']:
 b=z.read(m['path']); assert len(b)==m['bytes'] and digest(b)==m['sha256'],m['path']
assert sum(len(z.read(n)) for n in z.namelist())==index['archive']['uncompressed_bytes']
summary={'pin':PIN,'base_sha':index['base_sha'],'archive_sha256':digest(raw),'verified_members':56,'scopes':{},'pairs':[],'phase_rows':[]}
for scope,n in [('policy',48),('core',40),('generated',16)]:
 report=json.loads(z.read('.local_agent/q4-completion-'+scope+'-20261011/result.json'));rows=report['rows']
 assert report['complete'] and len(rows)==n
 pairs=collections.defaultdict(dict); phases=collections.Counter(); changes=collections.Counter(); totals=collections.Counter()
 for r in rows:
  s,d=r['stats'],r['decision']; native=r.get('native_requested',scope=='policy')
  assert r['root_restored'] and s['runtime_depth_balanced'] and s['runtime_pushes']==s['runtime_pops']
  assert s['native_legality_enabled']==int(native)
  assert (s['native_legality_calls']>0)==native
  assert s['native_legality_fallbacks']==s['native_legality_operational_failures']==0
  assert d['action'] is not None and d['choice_kind']=='ACTION'
  assert d['result_ordinary_qdepth'] in (0,4) and d['result_check_hard_qdepth']==8
  assert d['nodes']+d['qnodes']<=1000000
  for k in set(s)&set(d):assert s[k]==d[k],(scope,r['root'],k)
  key=(r['root'],native,r['seconds'],r['order']);assert r['arm'] not in pairs[key];pairs[key][r['arm']]=r
  ev=r['events']
  if r['arm']=='baseline':assert ev==[]
  else:
   assert [e['phase'] for e in ev] in (['reserve','begin','complete'],['reserve','begin','aborted'])
   reserve,begin,end=ev;phases[end['phase']]+=1
   assert len({e['budget_identity'] for e in ev})==len({e['deadline'] for e in ev})==1
   assert all(e['runtime_depth']==0 and e['runtime_balanced'] and e['runtime_restored'] for e in ev)
   assert all(e['q']==4 for e in ev)
   assert reserve['use_tt'] and not begin['use_tt'] and not end['use_tt']
   assert reserve['nodes']==begin['nodes'] and reserve['qnodes']==begin['qnodes']
   assert reserve['at']<=begin['at']<=end['at']
   assert reserve['nodes']<=end['nodes']<=s['nodes'] and reserve['qnodes']<=end['qnodes']<=s['qnodes']
   assert begin['tt_hits']==end['tt_hits']
   visits=end['nodes']+end['qnodes']-begin['nodes']-begin['qnodes']
   if end['phase']=='aborted':
    assert d['completed_depth']==1 and d['result_source']=='main_iteration' and d['result_ordinary_qdepth']==0
    assert (d['action'],d['score'],d['principal_variation'])==(reserve['action'],reserve['score'],reserve['pv'])
    assert (end['action'],end['score'],end['pv'])==(reserve['action'],reserve['score'],reserve['pv'])
   elif d['completed_depth']==1:
    assert d['result_source']=='refresh_iteration' and d['result_ordinary_qdepth']==4
    assert (d['action'],d['score'],d['principal_variation'])==(end['action'],end['score'],end['pv'])
   else:assert d['result_source']=='main_iteration' and d['result_ordinary_qdepth']==4
   summary['phase_rows'].append(dict(scope=scope,root=r['root'],native=native,seconds=r['seconds'],order=r['order'],phase=end['phase'],refresh_visits=visits,refresh_seconds=end['at']-begin['at'],cross_clock_difference_unqualified=end['deadline']-end['at'],returned_source=d['result_source']))
  for k in ['nodes','qnodes','runtime_pushes','legal_generation_calls','evaluation_calls','native_legality_calls']:totals[k]+=s[k]
  totals['wall']+=r['wall']
 expected={(root,native,seconds,order) for root in (['generated13','generated15'] if scope=='generated' else ['chess-ep','shogi-middle','shogi-drop']) for native in ([False,True] if scope=='generated' else [scope=='policy']) for seconds in ([4] if scope=='generated' else ([1,4] if scope=='core' and root=='chess-ep' else [1,4,16,64])) for order in (0,1)}
 assert set(pairs)==expected
 for key,arms in pairs.items():
  assert set(arms)=={'baseline','fullq4_refresh'}
  b,p=[arms[a]['decision'] for a in ['baseline','fullq4_refresh']]
  flags=dict(depth_delta=p['completed_depth']-b['completed_depth'],action_changed=p['action']!=b['action'],score_changed=p['score']!=b['score'],pv_changed=p['principal_variation']!=b['principal_variation'],q_upgrade=b['result_ordinary_qdepth']==0 and p['result_ordinary_qdepth']==4)
  changes['pairs']+=1
  for k,v in flags.items():changes[k]+=v
  assert flags['depth_delta']==0
  summary['pairs'].append(dict(scope=scope,root=key[0],native=key[1],seconds=key[2],order=key[3],baseline_depth=b['completed_depth'],baseline_q=b['result_ordinary_qdepth'],policy_q=p['result_ordinary_qdepth'],baseline_score=b['score'],policy_score=p['score'],**flags))
 summary['scopes'][scope]=dict(rows=n,phase_counts=dict(phases),pair_changes=dict(changes),totals=dict(totals))
(OUT/'audit.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary['scopes'],indent=2))

base=index['base_sha']
def basegit(path):return subprocess.check_output(['git','show',base+':'+path])
search=basegit('generic_chess/ai/alphabeta/search.py').decode();tree=ast.parse(search)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_root_search')
source='\n'.join(search.splitlines()[node.lineno-1:node.end_lineno])+'\n'
rr=basegit('scripts/reserve_refresh_diagnostic.py').decode();constants={}
for n in ast.parse(rr).body:
 if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('ANCHOR','REFRESH'):constants[n.targets[0].id]=ast.literal_eval(n.value)
assert source.count(constants['ANCHOR'])==1
changed=source.replace(constants['ANCHOR'],constants['ANCHOR']+constants['REFRESH']).replace('ctx.qdepth_limit = min(1, original_q)','ctx.qdepth_limit = original_q')
binding=dict(source_pin=PIN,search_base=base,search_file_sha256=digest(search.encode()),root_function_sha256=digest(source.encode()),generated_function_sha256=digest(changed.encode()),rr_sha256=digest(rr.encode()),producers={})
for scope in ('policy','core','generated'):
 raw=z.read('.local_agent/q4_completion_'+scope+'.py');decl=json.loads(z.read('.local_agent/q4-completion-'+scope+'-20261011/declaration.json'))
 assert digest(raw)==decl['source_sha256'] and digest(changed.encode())==decl['generated_function_sha256']
 assert decl['q']==4 and decl['hardq']==8 and decl['max_nodes']==1000000 and decl['max_depth']==12
 binding['producers'][scope]=dict(raw_sha256=digest(raw),declaration=decl)
(OUT/'source_binding.json').write_text(json.dumps(binding,indent=2)+'\n',encoding='utf-8')
