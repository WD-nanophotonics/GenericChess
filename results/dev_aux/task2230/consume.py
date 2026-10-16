"""Closed stronger-normal journal/public Session consumer, no new games/refit."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,numpy as np
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.result import SessionStatus
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
OUT=Path('results/dev_aux/task2230')
def run():
 p=json.loads((OUT/'plan.json').read_text());done=json.loads((OUT/'completion.json').read_text());games=[json.loads(l)for l in(OUT/'games.jsonl').read_text().splitlines()];moves=[json.loads(l)for l in(OUT/'moves.jsonl').read_text().splitlines()];assert done['status']=='COMPLETE'and len(games)==p['expected_games']==384 and len(moves)==done['decisions'];ms=defaultdict(list)
 for m in moves:ms[m['slot']].append(m)
 inputs={t:{r['family']:r for r in json.loads(Path(f'results/dev_aux/task{t}/inputs.json').read_text())['roots']}for t in p['contexts']};depths=Counter();steps=0
 for g in games:
  root=inputs[g['context']][g['family']];assert root['split']=='DEV';c=compile_ruleset_for_execution(deserialize_ruleset(Path(root['rules']).read_text()));s=GameSession(c);actions=deserialize_game_record(json.dumps(g['record'])).actions;assert len(actions)==g['moves']==len(ms[g['slot']])
  for a,m in zip(actions,ms[g['slot']]):
   assert m['root_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest()and m['is_candidate']==(s.state.position.side_to_move==g['candidate_color']);cfg=p['candidate'if m['is_candidate']else'opponent'];assert m['normal_visits']<=cfg['normal_nodes']
   if m['source']=='FULL_SESSION_MATERIAL_SEARCH':depths[(g['context'],m['is_candidate'],m['normal_depth'])]+=1
   s.submit(a);assert m['after_state_sha']==hashlib.sha256(repr(s.state).encode()).hexdigest();steps+=1
  assert s.result.status.value==g['status']and s.result.winner==g['winner'];assert g['reward']==(0 if s.result.winner is None else 1 if s.result.winner==g['candidate_color']else-1)and s.result.status is not SessionStatus.ONGOING
 summary={};rng=np.random.default_rng(2026101676)
 for context in p['contexts']:
  gg=[g for g in games if g['context']==context];baseline={(g['family'],g['opponent_ratio'],g['candidate_color']):g for g in gg if g['ratio']==1.};families=defaultdict(list)
  for g in gg:
   if g['ratio']==2.:families[g['family']].append(g['reward']-baseline[(g['family'],g['opponent_ratio'],g['candidate_color'])]['reward'])
  v=np.array([sum(x)/len(x)for x in families.values()]);boot=v[rng.integers(0,len(v),size=(10000,len(v)))].mean(axis=1)
  summary[context]=dict(profiles={str(r):dict(n=sum(g['ratio']==r for g in gg),WLD={o:sum(g['ratio']==r and g['outcome']==o for g in gg)for o in'WLD'},mean_W_minus_L=sum(g['reward']for g in gg if g['ratio']==r)/sum(g['ratio']==r for g in gg))for r in(1.,2.)},paired_family_gain=float(v.mean()),descriptive_bootstrap95=[float(x)for x in np.quantile(boot,[.025,.975])],family_effects={str(k):sum(x)/len(x)for k,x in families.items()})
 result=dict(status='PASS_STRONGER_NORMAL_ACTUAL_MOVES_AND_OUTCOMES',games=len(games),actual_moves=steps,normal_depth_counts=[dict(context=c,is_candidate=can,completed_depth=d,count=n)for(c,can,d),n in depths.items()],summary=summary,scope=p['scope']+' Matchedexposed-layoutresource/ruletransferonly; actualdepthcountsrequired, no requested-depth substitution. Descriptivefamilybootstrapnotall-domaincertainty.')
 (OUT/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
