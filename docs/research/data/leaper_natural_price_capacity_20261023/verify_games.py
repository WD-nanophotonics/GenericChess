"""Replay compact ABC continuation slots and metadata-selected PV examples.

Full raw query trajectories stay private. All terminal outcomes are checked;
only the published example PVs are rechecked here. Node/time aggregates are
retained measurements, not independently certified physical computation.
"""
import argparse,copy,gzip,hashlib,json,random,sys,time
from pathlib import Path
from collections import Counter
from fractions import Fraction as F
sys.path.insert(0,str(Path.cwd()))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,state_sha,record_value
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import empty_mobility
from generic_chess.ai.evaluation.analyzer import profile_movement_atoms
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
from scripts.leaper_microgames import role_stop_requested

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def replay(c,r):return GameSession.replay(c,deserialize_game_record(json.dumps(r)))
def match(s,r):
 choices=[a for a in s.legal_actions()if action_to_dict(a)==r]
 assert len(choices)==1
 return choices[0]

def main():
 parser=argparse.ArgumentParser();parser.add_argument('data',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();p=json.loads(gzip.decompress(args.data.read_bytes()));assert p['format']=='AUX-ABC-compact-v1';cfg=p['config'];inputs=p['inputs'];summary=p['summary'];start=time.perf_counter();counts=Counter()
 worlds={w['world']:w for w in inputs['worlds']};compiled={w:compile_rule(ruleset_from_dict(r['rule']))for w,r in worlds.items()};byfp={c.ruleset_fingerprint:c for c in compiled.values()};foes={}
 for w,c in compiled.items():
  n=c.board_size;totals={t:sum(len(empty_mobility(n,0,Square(x,y),profile_movement_atoms(c,t)))for x in range(n)for y in range(n))for t in 'ABC'};foes[w]=[1,float(F(totals['B'],totals['A'])),float(F(totals['C'],totals['A'])),0,0,0]
 openings={(o['world'],o['prefix']):o for o in inputs['openings']}
 for o in inputs['openings']:
  seed=int.from_bytes(hashlib.sha256(f'AUX-ABC-prefix-v1:{cfg["seed"]}:{o["world"]}:{o["prefix"]}'.encode()).digest()[:8],'big');assert seed==o['seed'];rng=random.Random(seed);s=GameSession(compiled[o['world']])
  for step in range(8):
   if s.state.terminal_status.is_terminal:break
   actions=s.legal_actions();s.submit(actions[rng.randrange(len(actions))])
  assert canonical(record_value(s.to_record()))==canonical(o['initial_record'])and state_sha(s.state)==o['id'];assert s.state.terminal_status.is_terminal==o['terminal'];counts['prefixes']+=1
 decoded={}
 for i,r in enumerate(p['records']):
  decoded[i]=replay(byfp[r['ruleset_fingerprint']],r);counts['unique_records']+=1
 expected={(w,pr,a,b,c)for w in worlds for pr in range(cfg['prefixes'])for a in(0,1)for b,c in cfg['prices']};observed=set()
 for g in p['games']:
  if time.perf_counter()-start>900 or role_stop_requested():raise RuntimeError('VERIFY_CAP_OR_STOP')
  k=(g['world'],g['prefix'],g['role'],g['B'],g['C']);assert k in expected and k not in observed;observed.add(k);o=openings[g['world'],g['prefix']];record=p['records'][g['record']];assert record['ruleset_fingerprint']==worlds[g['world']]['fingerprint'];initial=o['initial_record'];assert record['actions'][:len(initial['actions'])]==initial['actions'];assert g['opening_id']==o['id']and g['opponent']==foes[g['world']]
  final=decoded[g['record']];value=FixedScaleSessionEnv(final,unit_type='A').terminal();utility=[-1,1]if value is None or g['censor']else[value*(1 if g['role']==0 else-1)]*2;assert utility==g['utility'];counts['controller_actions']+=len(record['actions'])-len(initial['actions']);counts['reported_queries']+=g['query_count'];counts['reported_nodes']+=g['nodes'];assert sum(g['depth_histogram'].values())==g['query_count'];counts['terminal_prefix_views']+=o['terminal'];counts['slots']+=1
  if 'query_examples'in g:
   s=replay(compiled[g['world']],initial);assert len(g['query_examples'])==g['query_count']
   for q in g['query_examples']:
    assert q['id']==state_sha(s.state)and q['actor']==s.state.position.side_to_move and q['ply']==s.state.ply_count;r=q['receipt'];assert r['complete']and r['action']is not None;pv=copy.copy(s)
    for a in r['pv']:pv.submit(match(pv,a));counts['example_PV_edges']+=1
    env=FixedScaleSessionEnv(pv,unit_type='A');v=env.terminal()
    if v is None:
     weights=[1,g['B'],g['C'],0,0,0]if q['actor']==g['role']else g['opponent'];assert tuple(r['pv_phi'])==env.features()and Model(weights).raw(env.features())==r['value'];assert not r['pv_terminal']and len(r['pv'])==r['completed_depth']
    else:assert r['pv_terminal']and r['value']==MATE*v
    assert r['pv'][0]==r['action'];s.submit(match(s,r['action']));counts['published_queries']+=1
   assert canonical(record_value(s.to_record()))==canonical(record)
 assert len(expected)==cfg['planned_games']and len(observed)+len(summary['missing'])==len(expected)
 assert counts['reported_queries']==summary['queries']and counts['reported_nodes']==summary['nodes'];assert counts['controller_actions']==summary['queries'],'completed served-action panel only'
 # Recompute every finite point contrast from actual rule outcomes.
 lookup={(g['world'],g['prefix'],g['role'],g['B'],g['C']):g['utility']for g in p['games']};frames=[(w,pr,a)for w in worlds for pr in range(cfg['prefixes'])for a in(0,1)]
 for row in p['analysis']['points']:
  sums=[0,0];dif=[0,0]
  for w,pr,a in frames:
   u=lookup.get((w,pr,a,row['B'],row['C']),[-1,1]);v=lookup.get((w,pr,a,1.,1.),[-1,1])
   for j in(0,1):sums[j]+=u[j];dif[j]+=0 if(row['B'],row['C'])==(1.,1.)else u[j]-v[1-j]
  assert row['mean_bounds']==[str(F(x,len(frames)))for x in sums]and row['unit_difference_bounds']==[str(F(x,len(frames)))for x in dif]
 result=dict(status='PASS',seconds=time.perf_counter()-start,counts=counts,scope='All compact GameRecords,prefixlaw,slotoutcomes andfinitecontrasts rechecked;only metadata-selected publishedPVexamples. Full privatequeryreader receipt is distinct;allcosts here are reconciled reportedmetadata. Shared Core,not independentrules engine orallleaf search proof.');args.output.write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)

if __name__=='__main__':main()
