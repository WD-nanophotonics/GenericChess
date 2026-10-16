from pathlib import Path
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2397.material import channels,material
from results.dev_aux.task2376.material import material as shared
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2397')
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());stop();f=Path('results/dev_aux/task2315');definition=deserialize_ruleset((f/'rules.json').read_text());c=compile_ruleset_for_execution(definition);exclude=frozenset(x.type_id for x in definition.piece_types if x.is_anchor);rs=json.loads((f/'result.json').read_text())['rows'];row=next(r for r in rs if r['setup']is None);other=next(r for r in rs if r['setup']=='swapped_bases');ready=GameSession.replay(c,deserialize_game_record(json.dumps(row['root_record'])));after=GameSession.replay(c,deserialize_game_record(json.dumps(row['actual_record'])));swap=GameSession.replay(c,deserialize_game_record(json.dumps(other['root_record'])));board={'R':1.5,'P':1.};hand={'R':.5,'P':2.};score=lambda s,target=0:material(s.state.position,target,board,hand,excluded_type_ids=exclude);assert score(after)-score(ready)==board['R']-hand['R'];assert score(ready)-score(swap)==hand['R']-hand['P'];assert after.result.status.value=='checkmate'
 for s in(ready,after,swap):
  stop();assert score(s,0)==-score(s,1);assert material(s.state.position,0,board,board,excluded_type_ids=exclude)==shared(s.state.position,0,board,excluded_type_ids=exclude)
 controls={}
 for kind,b,h,target in(('missing_active_hand_R',board,{'P':2.},0),('nonfinite_hand_R',board,{'P':2.,'R':float('nan')},0),('boolean_target',board,hand,True)):
  try:material(ready.state.position,target,b,h,excluded_type_ids=exclude)
  except ValueError:controls[kind]='REJECTED'
  else:raise AssertionError(kind)
 result=dict(status='PASS_ACTUAL_COMPOSITE_EXPLICIT_BOARD_HAND_CHANNELS',ready_channels=channels(ready.state.position,0,excluded_type_ids=exclude),swapped_channels=channels(swap.state.position,0,excluded_type_ids=exclude),probe_board=board,probe_hand=hand,actual_Rdrop_score_delta=score(after)-score(ready),Rhand_minus_Phand_same_currentboard=score(ready)-score(swap),controls=controls,seconds=time.perf_counter()-t,scope='Arbitraryfunctionalprobevalues, notlearned/humanprices/WDLfit. BoardCURRENTandhandBASEauthority, actualexistingcapture/promotion/aux-expiry/dropmatehistory. Separatehandvsboardweightsmayvaluedeploymentdifferently; no automaticzeroingforgenericno-dropguards. Equalmaps recover2376sharedmaterial; 2396 separatelydemonstratesdormanthandzeroonlimitedruleclass. Notactive2385/2394policy/price/defaultchange; no newproof/game.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
