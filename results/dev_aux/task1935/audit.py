"""Actual public leaf witnesses and complete root-set contrast, all frozen roots."""
from pathlib import Path
from itertools import product,combinations
from fractions import Fraction
from collections import defaultdict
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_royal_actor import RoyalActor
O=Path('results/dev_aux/task1935')
def run():
 beg=time.perf_counter();pairs=json.loads(Path('results/dev_aux/task1934/inputs.json').read_text())['pairs'];rows=[json.loads(x) for x in Path('results/dev_aux/task1934/queries.jsonl').read_text().splitlines()];assert 0<len(rows)<=96;compiled={};actor=RoyalActor(4);leaves=edges=0
 for r in rows:
  pair=pairs[r['pair']];c=compiled.setdefault(pair['rules'],compile_ruleset_for_execution(deserialize_ruleset(Path(pair['rules']).read_text())));root=GameSession.replay(c,deserialize_game_record(json.dumps(pair['common_record'])));assert set(v['action'] for v in r['values'])<=set(uci(a) for a in root.legal_actions());assert not r['complete'] or set(v['action'] for v in r['values'])==set(uci(a) for a in root.legal_actions())
  for vector,path in r['leaf_witnesses'].items():
   record={**pair['common_record'],'actions':pair['common_record']['actions']+path};s=GameSession.replay(c,deserialize_game_record(json.dumps(record)));assert s.result.status is SessionStatus.ONGOING;counts={t:sum(1 if p.owner==0 else -1 for p in s.state.position.board if p is not None and p.current_type_id==t) for t in ('R','N')};assert str((counts['R'],counts['N']))==vector;leaves+=1;edges+=len(path)
   # A different literal actor replays ALL actual path edges too.
   astate=actor_state(root.state)
   for action in deserialize_game_record(json.dumps(record)).actions[len(pair['common_record']['actions']):]:
    legal=dict(actor.moves(astate));assert uci(action) in legal;astate=legal[uci(action)]
   assert astate==actor_state(s.state)
 index={(r['pair'],r['depth'],r['ratio']):r for r in rows};summary=[]
 for law in ('protected_rook_N_contact',):
  for depth in (2,4,6):
   ids=[p['pair'] for p in pairs if p['law']==law];changes=[];orders=[];disjoint=[];crossleaves=[];unresolved=[]
   for i in ids:
    a,b=index.get((i,depth,2.5)),index.get((i,depth,3.5))
    if a is None or b is None or not a['complete'] or not b['complete']:unresolved.append(i);continue
    assert a['state_sha']==b['state_sha'];va={v['action']:v['score'] for v in a['values']};vb={v['action']:v['score'] for v in b['values']};assert set(va)==set(vb)
    if set(a['best_actions'])!=set(b['best_actions']):changes.append(i)
    if not set(a['best_actions'])&set(b['best_actions']):disjoint.append(i)
    if any((va[x]>va[y])-(va[x]<va[y])!=(vb[x]>vb[y])-(vb[x]<vb[y]) for x,y in combinations(va,2)):orders.append(i)
    keys=set(a['leaf_witnesses'])|set(b['leaf_witnesses'])
    if {'(1, -2)','(0, 1)'}<=keys or {'(-1, 2)','(0, -1)'}<=keys:crossleaves.append(i)
   summary.append(dict(law=law,depth=depth,all_roots=ids,unresolved_pair_queries=unresolved,best_set_changes=changes,disjoint_best_sets=disjoint,any_root_action_order_changes=orders,roots_with_actual_visited_rho3_leaf_pair=crossleaves))
 vec=list(product(range(-1,2),range(-2,3)));cross=sorted({Fraction(b[1]-a[1],a[0]-b[0]) for a,b in combinations(vec,2) if a[0]!=b[0] and Fraction(b[1]-a[1],a[0]-b[0])>0})
 out=dict(status='PASS_ALL_SAVED_PROTECTEDROOK_RECORDS_PARTIALS_RETAINED',expected_queries=96,queries=len(rows),complete_queries=sum(r['complete'] for r in rows),independent_public_leaf_records=leaves,literal_path_edges=edges,new_inventory_leaf_order_crossings=[str(v) for v in cross],summary=summary,seconds=time.perf_counter()-beg,conclusion='SeeALL16protectedRrootcounts/setsatall3predeclareddepths. Algebraiccrossings/actualleafpairs/internalorderchanges/optimalrootsetsareseparate. LeavesnotexhaustivewithsoundABcuts; rootvaluescomplete. NotactualW-Lvalue.',scope='DotadvisedcheckwasexecutedAFTER1920learningalreadyfrozen/active. Notaretroactivegate orrootfilter, no DEVread/selection. All32preserved. CostincludesordinaryownconcurrentNativelearning; no benchmarkratio. Nottrainingreward/actualWDLgame, no uniquecontinuouspriceimpossibilityclaim.')
 with (O/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({k:out[k] for k in ['status','independent_public_leaf_records','literal_path_edges','new_inventory_leaf_order_crossings','seconds']}));print(json.dumps(summary))
if __name__=='__main__':run()
