"""Scoped equivalent-encoding Core consumer check; no model or rules default change."""
from pathlib import Path
from dataclasses import replace
from copy import copy
import json,random,time,sys,hashlib,os
R=Path.cwd();sys.path.insert(0,str(R))
from tools.local_agent.common import write_json,read_json,STATE
from generic_chess.rules.schema import ruleset_from_dict,ruleset_to_dict
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.core.identity import position_identity_key
from generic_chess.session.session import GameSession
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from scripts.research_record import record_value
STOP_ROOT=Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(R))).resolve();D=Path(os.environ.get('GC_NEUTRALITY_DATA_DIR',str(STATE/'rule-neutrality-20261017'))).resolve();P=read_json(D/'plan.json');start=time.perf_counter()
def poll():
 assert time.perf_counter()-start<P['limits']['seconds'],'FROZEN_TIME_CAP'
 for n in ('rollout','advisor','slack'):
  v=read_json(STOP_ROOT/'.local_agent'/(n+'.json'));assert not v.get('stopped')and not v.get('user_paused'),'EXPLICIT_STOP'
rules=ruleset_from_dict(read_json(D/'rule-ray.json'))
changed=[]
for p in rules.piece_types:
 atoms=tuple(LeapAtom(a.direction)if isinstance(a,RayAtom)and a.direction in((-1,2),(1,2))else a for a in p.movement_atoms)if p.type_id=='A'else p.movement_atoms
 changed.append(replace(p,movement_atoms=atoms))
other=replace(rules,piece_types=tuple(changed));cs=[compile_ruleset(x)for x in(rules,other)];ss=[GameSession(c)for c in cs];fps=[c.ruleset_fingerprint for c in cs];assert fps[0]!=fps[1]
write_json(D/'rule-ray.json',ruleset_to_dict(rules));write_json(D/'rule-leap.json',ruleset_to_dict(other))
profiles=[build_ruleset_profile(c,EvaluationConfig())for c in cs];a=[record_value(p.piece_profiles['A'])for p in profiles];assert a[0]['movement_signature']!=a[1]['movement_signature'];assert {k:v for k,v in a[0].items()if k!='movement_signature'}=={k:v for k,v in a[1].items()if k!='movement_signature'}
keymap={fps[1]:fps[0]};rows=[];edges=0;rng=random.Random(170017)
def norm(x,key=None):
 if isinstance(x,str):return keymap.get(x,x)
 if isinstance(x,dict):return {keymap.get(k,k):norm(v,k)for k,v in x.items()}
 if isinstance(x,list):
  out=[norm(v)for v in x];return sorted(out,key=repr)if key=='repetition_counts'else out
 return x
def snap(s):return record_value(dict(state=s.state,history=s.history,witnesses=s._search_witnesses,record=s.to_record(),result=s.result,declarations=s.available_declarations()))
def check(left,right):
 assert len(left._search_witnesses)==len(right._search_witnesses)
 for p,q in zip(left._search_witnesses,right._search_witnesses):
  assert replace(q,ruleset_fingerprint=fps[0])==p
  lk=position_identity_key(p,cs[0]);rk=position_identity_key(q,cs[1]);assert keymap.get(rk,lk)==lk;keymap[rk]=lk
 l=snap(left);r=snap(right);assert l==norm(r)
 return hashlib.sha256(json.dumps(l,sort_keys=True).encode()).hexdigest()
for i in range(P['limits']['states']):
 poll();h=check(*ss);acts=[tuple(sorted(s.legal_actions(),key=repr))for s in ss];assert acts[0]==acts[1]
 children=[]
 for action in acts[0]:
  poll();childrenpair=[copy(s)for s in ss]
  for s in childrenpair:s.submit(action)
  childhash=check(*childrenpair);edges+=1;children.append(dict(action=record_value(action),child_sha256=childhash,terminal=record_value(childrenpair[0].result)))
 chosen=acts[0][rng.randrange(len(acts[0]))]if acts[0]else None
 rows.append(dict(index=i,root=record_value(ss[0].to_record()),paired_root=record_value(ss[1].to_record()),full_root_sha256=h,legal_count=len(acts[0]),children=children,chosen=record_value(chosen)))
 if chosen is None:break
 for s in ss:s.submit(chosen)
for s,c in zip(ss,cs):
 restored=GameSession.replay(c,s.to_record());assert snap(restored)==snap(s)
write_json(D/'core-result.json',dict(status='PASS_SCOPED_COMPLETE_STATE_ISOMORPHISM',rows=rows,states=len(rows),child_edges=edges,seconds=time.perf_counter()-start,profiles=a,rule_fingerprints=fps,key_isomorphism=keymap,scope='One existing generated rule;8legalprefixstates/alllegalchildren; explicit complete key/fingerprint relabeling, nohistorytruncation. Numeric A profiles equal, syntactic signatures/fingerprints intentionallydifferent. Not all-state/all-domain equivalence or utility evidence.'))
print('PASS',len(rows),'states',edges,'children',round(time.perf_counter()-start,3),'seconds')
