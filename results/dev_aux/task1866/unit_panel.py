"""Frozen common-state price-unit diagnostic, not learning or WDL evidence."""
from pathlib import Path
import json,hashlib,time,copy,sys
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_native_material import SessionKRNMaterialProvider,_load_transport
OUT=Path('results/dev_aux/task1866')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def freeze():
 old=json.loads(Path('results/dev_aux/task1848/plan.json').read_text());native=copy.deepcopy(old['native_plan']);base=Path('results/dev_aux/task1824/variant.ini').read_text().split('[aux55_4_')[0].replace('aux55base','aux61base');names={}
 profiles=[]
 for n in (180,360,720,1440):
  for ratio in (.5,1.,2.):
   r=int(n*ratio);values=(r,n,n,n);name=f'aux61unit_{r}_{n}';names[str(values)]=name;profiles.append(dict(R=r,N=n,ratio=ratio,scale=n/720,values=values,name=name));base+=f'\n[{name}:aux61base]\npieceValueMg = p:{n} n:{n} b:{n} r:{r} q:{2*n}\npieceValueEg = p:{n} n:{n} b:{n} r:{r} q:{2*n}\n'
 with (OUT/'variant-qualified.ini').open('x',encoding='utf-8') as f:f.write(base)
 old_variant=native['variant_ini'];native['variant_ini']=str(OUT/'variant-qualified.ini');native['variant_names']=names;native['files'].pop(old_variant);native['files'][str(OUT/'variant-qualified.ini')]=sha(OUT/'variant-qualified.ini')
 c=compile_ruleset_for_execution(deserialize_ruleset(Path(old['rules']).read_text()));roots=json.loads(Path(old['roots']).read_text())['roots'];states=[];slots=[]
 for family in range(32):
  for prefix in (False,True):
   s=GameSession(c,roots[family]['setup'])
   if prefix:s.submit(s.legal_actions()[0])
   assert s.result.winner is None
   states.append(dict(index=len(states),family=family,prefix=prefix,record=json.loads(serialize_game_record(s.to_record())),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest()))
 for state in states:
  for ratio in (.5,1.,2.):
   for control in ('nodes64','nodes4096','depth5'):
    ps=[p for p in profiles if p['ratio']==ratio]
    if (state['index']+int(2*ratio)+len(control))%2:ps.reverse()
    for profile in ps:slots.append(dict(slot=len(slots),state=state['index'],profile=profile,control=control))
 plan=dict(status='FROZEN_BEFORE_NATIVE',question='Can arbitrary common scoreunits change material-only mature search at identical ratios/fullstates/caps?',scope='All32already-exposed1846families, fresh and firstpubliclegalprefix, input-onlyordinal states; ratios.5/1/2 atN180/360/720/1440. No fitting, price selector, new reward games or humanholdout.',states=states,slots=slots,profiles=profiles,expected_go=len(slots),expected_perft=64,native=native,rules=old['rules'],rules_sha=sha(old['rules']),source_sha={p:sha(p) for p in [__file__,'scripts/generic_session_native_material.py','results/dev_aux/task109/adapter.py','scripts/generic_royal_actor.py','scripts/generic_proof_rnb_bridge.py']},seconds_cap=300,expected_seconds=60,normal_movetime='NONE in this diagnostic; fixedgo nodes64/nodes4096/depth5, outer300s fuse and10s replydeadline; retain engine node overshoot. This differs from actualpolicy100ms normalwall, no oldpolicy equivalence.',decision='If actions differ across common units, ratio-only policy identity is false under this engine/cap; distinguish different completed depth vs same-depth selective behavior and later exact material tie. Sourceaudit identifies possible margins, not isolated causality. No scale picked from outcomes.')
 write('plan.json',plan);print(json.dumps(dict(frozen=len(slots))))
class UnitProvider(SessionKRNMaterialProvider):
 def profile(self,values):
  values=tuple(values);r,n,b,p=values
  name=self.plan['variant_names'][str(values)];self.e.send('setoption name UCI_Variant value '+name);raw=self.e.ready()
  assert any(x.startswith(f'info string variant {name} files 4 ranks 4 ') for x in raw)
  self.e.send('devauxleafrnbp '+' '.join(map(str,values)));ack=self.e.ready()
  expected=f'info string DEV_AUX leafRNBP {r} {n} {b} {p} nativeP {p} nativeR {r} nativeN {n} nativeB {b} captureP {p} captureR {r} captureN {n} captureB {b}'
  assert expected in ack;self.log('PROFILE',values=values,raw=raw,ack=ack);self.current=values
  self.e.send('ucinewgame');self.log('CLEAR',values=values,raw=self.e.ready())
def run():
 from generic_chess.session.serialization import deserialize_game_record
 plan=json.loads((OUT/'plan.json').read_text());assert all(sha(p)==h for p,h in plan['source_sha'].items());c=compile_ruleset_for_execution(deserialize_ruleset(Path(plan['rules']).read_text()));t=_load_transport();p=UnitProvider({**plan['native'],'seconds_cap':300,'max_go':plan['expected_go']},OUT/'run',stop=lambda:t.stop_check(Path.cwd()));start=time.perf_counter();perfts=0;rows=[];status='COMPLETE'
 try:
  p.start()
  for state in plan['states']:
   s=GameSession.replay(c,deserialize_game_record(json.dumps(state['record'])));p.perft_one(s,(720,720,720,720));perfts+=1
  with (OUT/'queries.jsonl').open('x',encoding='utf-8') as f:
   for slot in plan['slots']:
    if time.perf_counter()-start>=plan['seconds_cap']:status='GLOBAL_CAP';break
    state=plan['states'][slot['state']];s=GameSession.replay(c,deserialize_game_record(json.dumps(state['record'])));root=s.to_record();p.profile(slot['profile']['values']);command,actual=p.position_command(s,s.state);p.e.send(command)
    control=slot['control'];go='go depth 5' if control=='depth5' else 'go nodes '+control[5:];beg=time.perf_counter();p.log('INTENT',query=p.queries,slot=slot['slot'],position=command,command=go,profile=slot['profile'],record=repr(root));p.e.send(go);p.log('SENT',query=p.queries);p.queries+=1
    raw=p.e.until(lambda x:x.startswith('bestmove '),max_lines=512);p.e.ready();seconds=time.perf_counter()-beg;move=raw[-1].split()[1];assert move in actual and s.to_record()==root
    info=[x.split() for x in raw if x.startswith('info depth ') and 'score' in x.split()];last=info[-1] if info else []
    def field(key):return last[last.index(key)+1] if key in last else None
    row=dict(**slot,move=move,action=action_to_dict(actual[move]),reported_nodes=int(field('nodes') or 0),completed_depth=int(field('depth') or 0),score_kind=field('score'),score_value=last[last.index('score')+2] if 'score' in last else None,seconds=seconds,raw=raw,state_sha=state['state_sha'],position=command,record=state['record'])
    f.write(json.dumps(row)+'\n');f.flush();rows.append(row)
    p.log('CHOICE',query=p.queries-1,move=move,reported_nodes=row['reported_nodes'],raw=raw,seconds=seconds)
    if len(rows)%384==0:print(json.dumps(dict(done=len(rows),seconds=time.perf_counter()-start)),flush=True)
 finally:p.close()
 write('completion.json',dict(status=status,queries=len(rows),expected=plan['expected_go'],perft=perfts,seconds=time.perf_counter()-start,source_unchanged=all(sha(p)==h for p,h in plan['source_sha'].items())))
if __name__=='__main__':{'freeze':freeze,'run':run}[sys.argv[1]]()
