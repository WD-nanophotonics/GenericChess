"""Transfer-check every old census state and edge under three new setup families.
Fresh synthetic Core states only; no GameSession/proof/win-probability labels.
"""
from pathlib import Path
from dataclasses import replace,fields
from collections import Counter
import hashlib,json,time
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state,legal_successors
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.terminal import TerminalResult,TerminalStatus,terminal_result
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_inventory_proof_transport import SetupTransportedNoWinFilter,execution_differences
from scripts.generic_session_native_material import _load_transport
OUT=Path('results/dev_aux/task1981')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 plan=json.loads((OUT/'plan.json').read_text());assert all(sha(p)==h for p,h in plan['source_sha'].items())
 old=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1872/rules.json').read_text()))
 rows=[json.loads(x) for x in Path('results/dev_aux/task1895/states.jsonl').read_text().splitlines()]
 cov=json.loads(Path('results/dev_aux/task1896/coverage.json').read_text());assert len(rows)==sum(cov['admissible_by_inventory'].values())
 start=time.perf_counter();t=_load_transport();results=[]
 for path in plan['targets']:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(path).read_text()));assert execution_differences(old,c)==()
  filt=SetupTransportedNoWinFilter('results/dev_aux/task1895','results/dev_aux/task1896/coverage.json',c)
  base=initial_state(c);edges=0;wins=Counter();counts=Counter()
  for i,row in enumerate(rows):
   if i%256==0:t.stop_check(Path.cwd());assert time.perf_counter()-start<60
   raw=row['board'];board=tuple(None if p=='.' else Piece(int(p.islower()),p.upper(),p.upper()) for p in raw[:-1])
   pos=replace(base.position,board=board,side_to_move=raw[-1]);key=repetition_identity_key(pos,c)
   state=GameState(pos,0,((key,1),),TerminalResult(TerminalStatus.ONGOING),(HistoryRecord(key,-1,'',False),));state=replace(state,terminal_status=terminal_result(state,c))
   children=() if state.terminal_status.is_terminal else legal_successors(state,c)
   actual={uci(a):child for a,child in children};assert sorted(actual)==row['actions'] and state.terminal_status.status.value==row['status'] and state.terminal_status.winner==row['winner']
   digest=hashlib.sha256(repr(sorted((name,actor_state(child),child.terminal_status.status.value,child.terminal_status.winner) for name,child in actual.items())).encode()).hexdigest();assert digest==row['successor_sha']
   counts[row['inventory']]+=1;wins[row['inventory']]+=row['winner'] is not None;edges+=len(actual)
  assert dict(counts)==cov['admissible_by_inventory'] and edges==cov['actual_legal_edges'] and wins['KK']==wins['KKN']==0 and wins['KKR']==80
  results.append(dict(rules=path,rules_sha=sha(path),fingerprint=c.ruleset_fingerprint,all_execution_fields_equal=True,compiled_differences=[f.name for f in fields(c) if getattr(c,f.name)!=getattr(old,f.name)],states=len(rows),edges=edges,winning_terminals=dict(wins)))
 result=dict(status='PASS_ALL_CENSUS_STATES_EDGES_NEW_RULES',targets=results,total_states=sum(x['states'] for x in results),total_edges=sum(x['edges'] for x in results),seconds=time.perf_counter()-start,source_unchanged=all(sha(p)==h for p,h in plan['source_sha'].items()),scope='Full old admissibleinputset/edges/terminalcomparison, new three rules. Source-derived monotone inventory closure and draw-only history justify noforcedWIN; not exactdraw/WDL/game labels. Initialentitycount is descriptive; initialsetup keys affect provenance only, which the filter replays in CURRENTrules. No running1979policy/default/integrationchange; originalexact-fingerprintfilter unchanged.')
 with (OUT/'result.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='targets'}))
if __name__=='__main__':run()
