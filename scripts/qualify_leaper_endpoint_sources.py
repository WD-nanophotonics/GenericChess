"""One bounded saved-data/source qualification; stdlib, no Core or search calls."""
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

PACKET = 'docs/research/data/leaper_forward_design_20261022/observations.json.gz'
PUBLICATION = 'e8f4abf94bde7b6de1ab1a9acc3abfd24533c002'
PRODUCT = (
 'generic_chess/rules/schema.py', 'generic_chess/rules/compiler.py',
 'generic_chess/core/semantic_executor.py','generic_chess/session/serialization.py',
 'generic_chess/ai/alphabeta/player.py','generic_chess/ai/alphabeta/search.py',
 'generic_chess/ai/alphabeta/ordering.py','generic_chess/ai/alphabeta/tuning.py',
 'generic_chess/ai/evaluation/profile.py','generic_chess/ai/evaluation/evaluator.py',
 'generic_chess/core/search_runtime.py','generic_chess/ai/alphabeta/transposition.py',
 'generic_chess/ai/alphabeta/statistics.py','generic_chess/ai/decision.py',
 'generic_chess/core/identity.py','generic_chess/session/session.py')
def sha(b): return hashlib.sha256(b).hexdigest()
def digest(x):return sha(json.dumps(x,sort_keys=True,separators=(',',':')).encode())
def action(a):
 return dict(kind='semantic_board',pattern_id=a['pattern_id'],geometry_id=a['geometry_id'],
 actor_type_id=a['actor_type_id'],**{'from':[a['from_square']['file'],a['from_square']['rank']],
 'to':[a['to_square']['file'],a['to_square']['rank']]},promotion_target_id=a['promotion_target_id'])
def audit(root):
 raw=(root/PACKET).read_bytes();decoded=gzip.decompress(raw);x=json.loads(decoded)
 manifest=json.loads((root/Path(PACKET).with_name('manifest.json')).read_text())
 assert sha(raw)==manifest['compressed_sha256'] and sha(decoded)==manifest['decoded_sha256']
 for name,text in x['producer_sources'].items():assert sha(text.encode())==manifest['producer_sources'][name]
 source_by_hash={sha(text.encode()):name for name,text in x['producer_sources'].items()}
 runs={};worlds=x['runs']['pilot']['inputs']['worlds'];rows=[]
 for name in ('pilot','new_seed_repeats'):
  run=x['runs'][name];reg=run['registration'];assert sha((json.dumps(run['inputs'],indent=2)+'\n').encode())==reg['input_sha256']
  assert reg['nodes']==512 and reg['q']==0 and reg['forced_check_depth']==8 and reg['rule_max_ply']==128 and reg['repetition_limit']==4
  bound=source_by_hash[reg['source_sha256']]
  runs[name]={'producer':bound,'producer_sha256':reg['source_sha256'],'input_sha256':reg['input_sha256'],
    'slots':len(run['results']['slots']),'has_unattempted':bool(run['results']['unattempted']),
    'initial_failure_recovery':run['results'].get('repair',None),
    'limits':{'max_nodes':512,'max_depth':64,'time':None,'ordinary_q':0,'check_hard_q':8},
    'full_product_execution_version':'NOT_CAPTURED_IN_THIS_PACKET'}
  assert run['inputs']['worlds']==worlds
 games=[y for y in x['games'] if y['run'] in runs];assert len(games)==480
 terminal=Counter();query_count=0;ab_count=0;records=[];root_tactical_wins=0
 for w in worlds:
  rule=w['rule'];fp=w['fingerprint'];semantic=dict(rule);semantic.pop('metadata',None);assert digest(semantic)==fp
  assert rule['board_size']==4 and rule['max_ply']==128 and rule['repetition_limit']==4 and rule['capture_disposition']=='remove_from_game'
  assert all(a['kind']=='leap' for t in rule['piece_types'] for a in t['movement_atoms'])
  assert not rule['promotion_allowed'] and not rule['promotion_forced'] and not any(v for masks in rule['drop_allowed'].values() for mask in masks for v in mask)
  assert not any(rule.get(k) for k in ('declarations','automatic_adjudications','consecutive_action_adjudications','repeated_cycle_target_conditions','no_progress_draw','pass_enabled','semantic_actions','initial_setup_options'))
  sample=[y for y in games if y['game']['world']==w['world']];assert len(sample)==48
  counts={p:Counter() for p in ('AB_RNG','FLOOR_RNG','RNG_RNG')};seats=Counter();ab_terms=Counter();pairrecords=[]
  for item in sample:
   g=item['game'];reg=x['runs'][item['run']]['registration'];assert item['rule']==rule
   assert g['initial_record']['ruleset_fingerprint']==g['final_record']['ruleset_fingerprint']==fp
   assert not g['initial_record']['actions'] and g['initial_record']['resigned_by'] is None
   assert not g['censor'] and g['terminal']['status'] in ('checkmate','stalemate','repetition','max_ply')
   queries=g['queries'];acts=g['final_record']['actions'];assert len(queries)==len(acts)==g['final_state']['ply_count']
   assert queries[0]['state_sha256']==digest(w['initial_state'])
   assert w['initial_state']['position']['ruleset_fingerprint']==g['final_state']['position']['ruleset_fingerprint']==fp
   assert len(w['initial_state']['history'])==1 and w['initial_state']['ply_count']==0
   assert g['final_record']['resigned_by'] is None
   assert len(g['final_state']['history'])==len(acts)+1
   assert g['final_state']['terminal_status']['status']==g['terminal']['status'] and g['final_state']['terminal_status']['winner']==g['terminal']['winner']
   role=g['role'];policies=reg['pairs'][g['pair']];expected={str(role):policies[0],str(1-role):policies[1]};assert g['policy_by_actor']==expected
   seeds={str(a):reg['seed']+10000*w['world']+100*g['repeat']+10*role+a for a in (0,1)};assert g['rng_seeds']==seeds
   for index,(q,a) in enumerate(zip(queries,acts)):
    assert q['root_ply']==index and q['actor']==index%2 and q['policy']==expected[str(q['actor'])]
    assert action(q['action'])==a
    if q['policy']=='AB':
     ab_count+=1;d=q['decision'];assert d['action']==q['action']
     if d['result_source']=='root_immediate_win':
      assert d['completed_depth']==0 and d['result_ordinary_qdepth'] is None and d['result_check_hard_qdepth'] is None
     else:assert d['result_ordinary_qdepth']==0 and d['result_check_hard_qdepth']==8
     if index==len(queries)-1 and g['terminal']['winner']==q['actor']:
      root_tactical_wins+=q['decision']['termination_reason']=='root_immediate_win'
   query_count+=len(queries);terminal[g['terminal']['status']]+=1
   value=0 if g['terminal']['winner'] is None else 1 if g['terminal']['winner']==role else -1
   assert g['utility']==[value,value];label={-1:'LOSS',0:'DRAW',1:'WIN'}[value];counts[g['pair']][label]+=1
   h=digest(g['final_record']);records.append(h)
   if g['pair']=='AB_RNG':
    ab_terms[g['terminal']['status']]+=1;pairrecords.append(h)
    if value==1:seats[str(role)]+=1
  rows.append({'world':w['world'],'masks':w['masks'],'fingerprint':fp,'initial_record_sha256':digest(w['initial_record']),
   'source_wire_hash':digest(rule),'counts':{p:dict(c) for p,c in counts.items()},'AB_wins_by_seat':dict(seats),
   'AB_terminal_counts':dict(ab_terms),'distinct_AB_final_records':len(set(pairrecords)),
   'wire_qualification':'PASS source-only; not compiled/replayed','current_quality':'UNKNOWN_NO_CURRENT_CONTROLLERS_RUN'})
 bindings=[]
 for name in PRODUCT:
  old=subprocess.check_output(['git','show',PUBLICATION+':'+name],cwd=root);current=(root/name).read_bytes()
  bindings.append({'path':name,'publication_tree_sha256':sha(old),'current_sha256':sha(current),
   'same_LF':old.replace(b'\r\n',b'\n')==current.replace(b'\r\n',b'\n')})
 current=ast.parse((root/'scripts/leaper_design.py').read_text());calls={}
 for name,entry in runs.items():
  old=ast.parse(x['producer_sources'][entry['producer']]);checks={}
  for function in ('limits','floor','run'):
   a=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==function)
   b=next(n for n in current.body if isinstance(n,ast.FunctionDef) and n.name==function)
   checks[function]=ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
  calls[name]=checks
 return {'status':'COMPLETE_SOURCE_QUALIFICATION','packet_sha256':sha(raw),'decoded_sha256':sha(decoded),
  'manifest_sources_verified':len(x['producer_sources']),'runs':runs,'rows':rows,'physical_games':480,
  'distinct_final_records':len(set(records)),'source_queries':query_count,'source_AB_decisions':ab_count,
  'literal_source_terminal_counts':dict(terminal),'last_AB_win_root_scan_returns':root_tactical_wins,
  'producer_vs_current_AST':calls,'publication_tree':PUBLICATION,'product_source_bindings':bindings,
  'actual_execution_tree_pinned':False,'packet_product_source_members':[],
  'qualification':{'input_wire_record_bindings':'GO_SOURCE_ONLY_ALL10','historical_executable_equivalence':'UNKNOWN',
   'current_Q4_one_second_quality':'NO_GO_NOT_ESTABLISHED','algorithm_mechanism_experiment':'NO_GO_NO_NEW_RUN_AUTHORITY'},
  'new_Core':0,'new_Player':0,'new_solver':0,'new_game':0,'archived_code_executed':False,
  'limits':'JSON consistency, AST and source hashes only. No legal action/terminal/PV/TT or RNG replay; no source WDL proof, no current saturation inference.'}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=audit(Path(__file__).resolve().parents[1])
 from tools.local_agent.common import write_json
 write_json(a.output,result)
 print(json.dumps({k:v for k,v in result.items() if k not in ('rows','product_source_bindings','runs')}))
