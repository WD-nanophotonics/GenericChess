"""Independent complete prefix/split and actual-history WIN-strategy admission."""
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
from copy import copy
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,uci,orbit
from scripts.generic_session_win_proof import SessionChoice,execute
from results.dev_aux.task2246.entry_proofs import build
from results.dev_aux.task2199.semantic_graph import verify_graph,GraphStrategyCursor
from results.dev_aux.task2181.run import encode
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2260')
def key(b):return ''.join(b[:-1])+str(b[-1])
def run():
 assert not(OUT/'started.json').exists();p=json.loads((OUT/'plan.json').read_text());start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());(OUT/'started.json').write_text(json.dumps(dict(plan=p)))
 def cancel():stop();return time.perf_counter()-start>=p['cap_seconds']
 rows={};indices={}
 for i,line in enumerate(Path('results/dev_aux/task2249/labels.jsonl').open(encoding='utf-8')):
  if i%1024==0 and cancel():raise TimeoutError('original_audit_cap')
  l=json.loads(line);rows[key(l['board'])]=l;indices[l['index']]=l
 roots=json.loads(Path('results/dev_aux/task2258/inputs.json').read_text())['roots'];prior={r['group']for r in json.loads(Path('results/dev_aux/task2251/inputs.json').read_text())['roots']};groups=set();v={'WIN':1,'LOSS':-1,'DRAW':0};legal_edges=0;proofs=[]
 with(OUT/'certificates.jsonl').open('x',encoding='utf-8')as cf:
  for r in roots:
   if cancel():raise TimeoutError('original_audit_cap')
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')));s=GameSession.replay(c,deserialize_game_record(json.dumps(r['record'])));actions=s.to_record().actions;assert len(actions)==1 and uci(actions[0])==r['prefix'];assert hashlib.sha256(repr(s.state).encode()).hexdigest()==r['state_sha'];assert list(actor_state(s.state))==r['board'];group=min(key(t)for t in orbit(tuple(r['board'])));assert group==r['group']and group not in prior and group not in groups;groups.add(group);digest=hashlib.sha256(('RN78-both-roles-prefix-choice:'+group).encode()).hexdigest();assert digest==r['order_sha']and r['split']==('DEV'if int(digest[:8],16)%3==0 else'TRAIN')
   l=rows[key(actor_state(s.state))];assert l['label']==r['target_label']and l['rank']==r['canonical_rank'];utilities=[];legal={uci(a):a for a in s.legal_actions()};assert set(legal)=={e['action']for e in l['actions']}and len(legal)>=2
   for name,a in legal.items():
    t=copy(s);execute(t,SessionChoice('ACTION',action=a));assert t.result.status is SessionStatus.ONGOING;utilities.append(-v[rows[key(actor_state(t.state))]['label']]);legal_edges+=1
   assert len(set(utilities))>=2 and max(utilities)==v[l['label']]
   if l['label']=='WIN':
    assert l['rank']>=5;target=s.state.position.side_to_move;cert,work=build(s,SimpleNamespace(rows=rows,indices=indices),target,p,cancel);receipt=verify_graph(s,cert,max_nodes=p['verify_nodes'],seconds=p['verify_seconds'],cancel=cancel);assert receipt['verified'];cursor=GraphStrategyCursor(s,cert,max_nodes=p['verify_nodes'],seconds=p['cursor_seconds'],cancel=cancel);cf.write(json.dumps(dict(family=r['family'],certificate=encode(cert)))+'\n');cf.flush();moves=0
    while s.result.status is SessionStatus.ONGOING:
     if cancel():raise TimeoutError('original_audit_cap')
     before=copy(s)
     if s.state.position.side_to_move==target:choice=cursor.choose(s)
     else:
      row=rows[key(actor_state(s.state))];name=max(row['actions'],key=lambda e:(indices[e['child']]['rank'],e['action']))['action'];choice=SessionChoice('ACTION',action={uci(a):a for a in s.legal_actions()}[name])
     execute(s,choice);cursor.observe(before,choice,s);moves+=1
    assert s.result.winner==target;proofs.append(dict(family=r['family'],builder=work,verification=receipt,moves=moves,winner=target,record=json.loads(serialize_game_record(s.to_record()))))
 strata=Counter((r['split'],r['target_label'])for r in roots);assert strata=={('TRAIN','WIN'):16,('TRAIN','DRAW'):16,('DEV','WIN'):8,('DEV','DRAW'):8};assert len(proofs)==24
 (OUT/'actual_conversions.json').write_text(json.dumps(proofs,separators=(',',':')));result=dict(status='PASS_ALL_PREFIXES_ACTION_GRADIENTS_AND_24_ACTUAL_WIN_GRAPHS',roots=48,checked_actual_children=legal_edges,verified_WIN_graphs=24,actual_cursor_conversions=24,actual_conversion_moves=sum(p['moves']for p in proofs),seconds=time.perf_counter()-start,scope='ALLfrozen48prefixesand24WINroots; no root/price/exclusion changes. All-defensepositivecertificate/fullactualroot-history/currentcursor verified andactualmateconverted. Tableassistedcandidateconstruction explicit; no onlinegenericdiscovery/budget/default/pricebenefitclaim. DRAWdescriptorsremaincanonicalreference,notactualhistoryreward. Sharedexistingverifier code not independentprover implementation. Graphreference exposure explicit.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
