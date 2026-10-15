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
O=Path('results/dev_aux/task1937')
def run():
 beg=time.perf_counter();pairs=json.loads(Path('results/dev_aux/task1934/inputs.json').read_text())['pairs'];rows=[json.loads(x) for x in Path('results/dev_aux/task1936/queries.jsonl').read_text().splitlines()];assert 0<len(rows)<=416;compiled={};actor=RoyalActor(4);leaves=edges=0
 for r in rows:
  pair=pairs[r['pair']];c=compiled.setdefault(pair['rules'],compile_ruleset_for_execution(deserialize_ruleset(Path(pair['rules']).read_text())));root=GameSession.replay(c,deserialize_game_record(json.dumps(pair['common_record'])));assert set(v['action'] for v in r['values'])<=set(uci(a) for a in root.legal_actions());assert not r['complete'] or set(v['action'] for v in r['values'])==set(uci(a) for a in root.legal_actions())
  for vector,path in r['leaf_witnesses'].items():
   record={**pair['common_record'],'actions':pair['common_record']['actions']+path};s=GameSession.replay(c,deserialize_game_record(json.dumps(record)));assert s.result.status is SessionStatus.ONGOING;counts={t:sum(1 if p.owner==0 else -1 for p in s.state.position.board if p is not None and p.current_type_id==t) for t in ('R','N')};assert str((counts['R'],counts['N']))==vector;leaves+=1;edges+=len(path)
   # A different literal actor replays ALL actual path edges too.
   astate=actor_state(root.state)
   for action in deserialize_game_record(json.dumps(record)).actions[len(pair['common_record']['actions']):]:
    legal=dict(actor.moves(astate));assert uci(action) in legal;astate=legal[uci(action)]
   assert astate==actor_state(s.state)
 index={(r['pair'],r['depth'],r['ratio']):r for r in rows};plan=json.loads(Path('results/dev_aux/task1936/plan.json').read_text());summary=[];envelopes=[];checks=0
 vec=list(product(range(-1,2),range(-2,3)))
 for depth in plan['depths']:
  bestchanges=[];strictswitch=[];canonicalswitch=[]
  for pair in pairs:
   panel=[index[(pair['pair'],depth,r)] for r in plan['prices']];assert all(x['complete'] for x in panel)
   actions=[v['action'] for v in panel[0]['values']];assert all([v['action'] for v in q['values']]==actions for q in panel)
   forms={}
   for action in actions:
    fs=[]
    for r in plan['open_representatives']:
     q=index[pair['pair'],depth,r];score=next(v['score'] for v in q['values'] if v['action']==action)
     possible=[(dr,dn) for dr,dn in vec if Fraction(score,720)==Fraction(r)*dr+dn]
     if abs(score)==1000000:form={'terminal':score}
     else:assert len(possible)==1;form={'dR':possible[0][0],'dN':possible[0][1]}
     fs.append(form)
    forms[action]=fs
    for j,r in enumerate(plan['crossings']):
     expected=next(v['score'] for v in index[pair['pair'],depth,r]['values'] if v['action']==action)
     for form in fs[j:j+2]:
      val=form.get('terminal',720*(Fraction(r)*form.get('dR',0)+form.get('dN',0)));assert val==expected;checks+=1
   if len({tuple(q['best_actions']) for q in panel})>1:bestchanges.append(pair['pair'])
   if any(not(set(x['best_actions'])&set(y['best_actions'])) for x,y in combinations(panel,2)):strictswitch.append(pair['pair'])
   if len({q['best_actions'][0] for q in panel})>1:canonicalswitch.append(pair['pair'])
   envelopes.append(dict(pair=pair['pair'],depth=depth,root_action_forms=forms,best_sets={q['ratio']:q['best_actions'] for q in panel}))
  adjacent=[]
  for x,y in zip(plan['open_representatives'],plan['open_representatives'][1:]):
   ids=[p['pair'] for p in pairs if set(index[p['pair'],depth,x]['best_actions'])!=set(index[p['pair'],depth,y]['best_actions'])]
   adjacent.append(dict(left=x,right=y,changed_best_sets=ids))
  summary.append(dict(depth=depth,best_set_changes=bestchanges,disjoint_best_sets=strictswitch,canonical_first_action_changes=canonicalswitch,adjacent_chambers=adjacent))
 out=dict(status='PASS_FULL_PRICE_ENVELOPES_PUBLIC_AND_LITERAL_REPLAY',queries=len(rows),complete_queries=sum(r['complete'] for r in rows),independent_public_leaf_records=leaves,literal_path_edges=edges,boundary_continuity_checks=checks,summary=summary,envelopes=envelopes,prices=plan['prices'],open_representatives=plan['open_representatives'],crossings=plan['crossings'],seconds=time.perf_counter()-beg,scope='ALL16 exposed DESIGN roots; finite material-minimax action envelopes and canonical ordinal choices, NOT WDL improvements or fresh validation. Utility forms are exact inside mechanically derived open chambers by leaf-order lemma; independently evaluated boundaries checked from both sides. Terminal draw and zero material share utility zero. No selective cohort retention/price optimization.')
 with (O/'result.json').open('x') as f:json.dump(out,f,indent=2)
 print(json.dumps({k:out[k] for k in ['status','queries','independent_public_leaf_records','literal_path_edges','boundary_continuity_checks','seconds']}));print(json.dumps(summary))
if __name__=='__main__':run()
