"""Literal full-history Core replay of published depth/PV/support evidence."""
import sys,json,gzip,time,argparse,copy
from pathlib import Path
from collections import Counter
from fractions import Fraction as F
sys.path.insert(0,str(Path.cwd()))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,state_sha
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.ai.evaluation.config import MATE_SCORE
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
from scripts.leaper_microgames import role_stop_requested
pa=argparse.ArgumentParser();pa.add_argument('natural',type=Path);pa.add_argument('mechanisms',type=Path);pa.add_argument('--output',type=Path,required=True);pa.add_argument('--residual-only',action='store_true');args=pa.parse_args();n=json.loads(gzip.decompress(args.natural.read_bytes()));p=json.loads(gzip.decompress(args.mechanisms.read_bytes()));compiled={fp:compile_rule(ruleset_from_dict(r))for fp,r in n['rules'].items()};roots={e['id']:e for e in n['manifest']};labels={r['id']:r for r in n['rows']};support={(r['id'],r['depth']):r for r in p['support_rows']};byid={};counts=Counter();start=time.perf_counter()
def replay(c,r):return GameSession.replay(c,deserialize_game_record(json.dumps(r)))
def match(s,r):
 a=[a for a in s.legal_actions()if action_to_dict(a)==r];assert len(a)==1;return a[0]
def exact(c,st,left,ply):
 counts['literal_visits']+=1
 if counts['literal_visits']%8192==0 and(time.perf_counter()-start>900 or role_stop_requested()):raise RuntimeError('VERIFY_CAP_OR_STOP')
 if st.terminal_status.is_terminal:return terminal_score(st.terminal_status,st.position.side_to_move,ply)
 if not left:
  raw=sum((1 if z.owner==0 else-1)for z in st.position.board if z and z.current_type_id!='K');return raw*(1 if st.position.side_to_move==0 else-1)
 return max(-exact(c,ch,left-1,ply+1)for a,ch in legal_successors(st,c))
for q in p['depth_rows']:
 byid.setdefault(q['id'],[]).append(q)
for hid,queries in ([]if args.residual_only else byid.items()):
 if time.perf_counter()-start>900 or role_stop_requested():raise RuntimeError('VERIFY_CAP_OR_STOP')
 e=roots[hid];c=compiled[e['fingerprint']];s=replay(c,e['record']);assert state_sha(s.state)==hid;t=labels[hid];actual=[action_to_dict(a)for a in s.legal_actions()];assert actual==t['actions']
 for q in queries:
  assert q['complete']and q['completed_depth']==q['depth'];assert q['action']is not None and q['wdl']==t['labels'][q['action']]and q['best']==t['root_wdl'];pv=copy.copy(s)
  for raw in q['pv']:pv.submit(match(pv,raw));counts['PV_edges']+=1
  env=FixedScaleSessionEnv(pv,unit_type='A');v=env.terminal()
  if v is None:assert len(q['pv'])==q['depth']and Model(q['weights']).raw(env.features())==q['value']
  else:assert q['value']==MATE*v
  assert q['pv'][0]==actual[q['action']];counts['queries']+=1
 for d in (2,4):
  values=[-exact(c,ch,d-1,1)for a,ch in legal_successors(s.state,c)];r=support[hid,d];assert values==r['scores'];selected=[j for j,v in enumerate(values)if v==max(values)];assert selected==r['selected'];bad=sum(t['labels'][j]<t['root_wdl']for j in selected);assert r['unsafe']==(0<bad<len(selected))and r['forced']==(bad==len(selected));assert F(r['expected_error'])==F(bad,len(selected));counts['literal_supports']+=1
 counts['roots']+=1
 if counts['roots']%100==0:print('ROOTS',counts['roots'],'visits',counts['literal_visits'],'seconds',time.perf_counter()-start,flush=True)
e=roots[p['residual_depth']['id']];c=compiled[e['fingerprint']];s=replay(c,e['record'])
for d in (6,8):
 values=[-exact(c,ch,d-1,1)for a,ch in legal_successors(s.state,c)];row=next(r for r in p['residual_depth']['rows']if r['depth']==d);assert list(map(F,values))==[F(v[2])for v in row['scores']];selected=[j for j,v in enumerate(values)if v==max(values)];assert selected==row['sets'][2];counts['residual_literal_supports']+=1;print('RESIDUAL',d,'visits',counts['literal_visits'],flush=True)
result=dict(status='PASS',seconds=time.perf_counter()-start,counts=counts,residual_only=args.residual_only,scope='Saved D2/D4PVs and literal Unit fullhistorytrees viaCore,plus residualD6/D8. Residual-only mode checks onlythetwo lattertrees. No graphhistory shortcut, independentengine or experiential labels. ActionWDL requires separate completegraph/rankhistoryverification.');args.output.write_text(json.dumps(result,indent=2));print('FINAL',json.dumps(result),flush=True)
