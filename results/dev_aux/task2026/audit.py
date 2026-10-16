"""Independent KRNB raw Native/fullhistory legality replay, zero new search."""
from pathlib import Path
import json,hashlib
from collections import Counter
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
ROOT=Path('results/dev_aux/task2025');OUT=Path('results/dev_aux/task2026')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return [json.loads(x)for x in Path(p).read_text().splitlines()]
def run():
 p=read(ROOT/'plan.json');r=read(ROOT/'result.json');rows=lines(ROOT/'queries.jsonl');events=lines(ROOT/'run/transport.jsonl');c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));actor=RoyalActor(6)
 assert r['status']=='PASS_SCOPED_KRNB_NATIVE_FEASIBILITY'and r['queries']==len(rows)==48 and len(r['perfts'])==48 and r['games']==r['learning']==0
 assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in p['source_sha'].items())
 perfts=[e for e in events if e['event']=='PERFT'];intents=[e for e in events if e['event']=='INTENT'];choices=[e for e in events if e['event']=='CHOICE'];sent=[e for e in events if e['event']=='SENT'];assert len(perfts)==len(intents)==len(choices)==len(sent)==48
 def position(state):
  s=GameSession.replay(c,deserialize_game_record(json.dumps(state['record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==state['state_sha'];legal={uci(a)for a in s.legal_actions()};assert legal==set(dict(actor.moves(actor_state(s.state))))
  root=GameSession(c,s.to_record().initial_setup_key);path=[uci(a)for a in s.to_record().actions];command='position fen '+actor.fen(actor_state(root.state))+(' moves '+' '.join(path)if path else'');return s,legal,command
 for i,(case,q,b,ch,pf,pr)in enumerate(zip(rows,intents,sent,choices,perfts,r['perfts'])):
  state=p['states'][i//3];values=p['profiles'][i%3];s,legal,command=position(state)
  assert case['state']==pr['state']==state['index']and case['values']==pr['values']==values
  assert case['action']in legal and case['state_sha']==state['state_sha']
  assert q['query']==b['query']==ch['query']==i and q['position']==pf['position']==command and q['root_record']==repr(s.to_record())
  assert q['R']==ch['R']==values and ch['requested_nodes']==64 and q['command'].startswith('go nodes 64 movetime ')
  assert case['action']==ch['move'] and case['reported_nodes']==ch['reported_nodes']
  parsed={line.split(':')[0].strip():int(line.split(':')[1])for line in pf['raw']if ':'in line and line.split(':')[0].strip()in legal};assert set(parsed)==legal and all(n==1 for n in parsed.values())and pr['legal']==len(legal)
 profile=None;cleared=False;acks=0
 for e in events:
  if e['event']=='PROFILE':
   profile=e['values'];rr,n,bb,pp=profile;assert f'info string DEV_AUX leafRNBP {rr} {n} {bb} {pp} nativeP {pp} nativeR {rr} nativeN {n} nativeB {bb} captureP {pp} captureR {rr} captureN {n} captureB {bb}'in e['ack'];acks+=1;cleared=False
  elif e['event']=='CLEAR':assert profile==e['values'];cleared=True
  elif e['event']=='INTENT':assert profile==e['R']and cleared;cleared=False
 result=dict(status='PASS_ALL_KRNB_NATIVE_FEASIBILITY_RECEIPTS',families=8,public_history_states=16,perfts=48,queries=48,profile_acks=acks,price_changed_choice_states=sum(len({x['action']for x in rows[3*i:3*i+3]})>1 for i in range(16)),reported_nodes=sum(x['reported_nodes']for x in rows),games=0,training=0,scope='ALLroot+firstlegalprefix/3mechanicalBprofiles/fullrootFEN+actualhistory/Core-literal-frontier/actualleaf-native-captureACK/Nativego64receipts. ScopedisolatedKRNB6provider, originalKRNproviderunchanged. LegalNativechoices/profileactivation not W-Lgain/humanvalue/fullgenerateddomain or independentNativebuild;0newsearch in audit.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':run()
