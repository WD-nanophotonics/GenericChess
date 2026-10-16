"""Posthoc headroom diagnosis, never a changed reward or DEV selector."""
from pathlib import Path
from collections import Counter,defaultdict
import json,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,uci
OUT=Path('results/dev_aux/task2104')
def key(raw):return ''.join(raw[:-1])+str(raw[-1])
def run():
 start=time.perf_counter();labels={key(r['board']):r for r in(json.loads(x)for x in Path('results/dev_aux/task2073/labels.jsonl').read_text(encoding='utf-8').splitlines())};p=json.loads(Path('results/dev_aux/task2092/run-plan.json').read_text(encoding='utf-8'));games=[json.loads(x)for x in Path('results/dev_aux/task2092/games.jsonl').read_text(encoding='utf-8').splitlines()];steps=defaultdict(list)
 for line in Path('results/dev_aux/task2092/moves.jsonl').read_text(encoding='utf-8').splitlines():
  r=json.loads(line);steps[r['slot']].append(r)
 value={'WIN':1,'DRAW':0,'LOSS':-1};rootlabels=Counter();matches=0;choices=Counter();by_source=defaultdict(Counter)
 for g in games:
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['roots'][g['family']]['rules']).read_text(encoding='utf-8')));s=GameSession(c);l=labels[key(actor_state(s.state))];rootlabels[l['label']]+=1;v=value[l['label']]if g['candidate_side']==0 else-value[l['label']];matches+=v==g['score'];actions=deserialize_game_record(json.dumps(g['record'])).actions
  for step,a in zip(steps[g['slot']],actions):
   row=labels[key(actor_state(s.state))];q={e['action']:-e['child_value']for e in row['actions']};regret=max(q.values())-q[uci(a)];metric=by_source[step['source']];metric['decisions']+=1;metric['positional_WDL_suboptimal']+=regret>0;metric['regret_sum']+=regret;metric['nonflat_frontiers']+=len(set(q.values()))>1;metric['prior_repeated_history']+=max(n for _,n in s.state.repetition_counts)>1;s.submit(a)
 # TRAIN-only new5piece diagnostic. DO NOT inspect plannedDEV labels/outcomes.
 roots=[r for r in json.loads(Path('results/dev_aux/task2100/inputs.json').read_text(encoding='utf-8'))['roots']if r['phase']=='TRAIN'];wanted={key(r['root']):r for r in roots};new=[]
 for line in Path('results/dev_aux/task2098/labels.jsonl').open(encoding='utf-8'):
  r=json.loads(line);k=key(r['board'])
  if k not in wanted:continue
  q=[-e['child_value']for e in r['actions']];new.append(dict(family=wanted[k]['family'],label=r['label'],rank=r['rank'],legal_actions=len(q),nonflat_true_position_WDL=len(set(q))>1,winning_preserving_actions=sum(v==max(q)for v in q)))
 assert len(new)==32
 result=dict(status='COMPLETE_POSTHOC_DISTRIBUTION_HEADROOM',old2092_rootlabels=dict(rootlabels),old2092_actual_match_canonical_optimal_root=matches,total_games=len(games),old2092_positional_decisions={k:dict(v)for k,v in by_source.items()},new2100_TRAIN_only_roots=Counter(r['label']for r in new),new2100_TRAIN_only_nonflat=sum(r['nonflat_true_position_WDL']for r in new),new2100_DEV_labels_read=0,seconds=time.perf_counter()-start,scope='FreshrootWDLexact; per-move positionalWDL is NOT arbitraryhistorylabel. No reward/selector/policy/root/budget change. NewrootdiagnosticTRAINonly; DEVunread. A perfectroot-result match hereexplains noobservedmodelheadroom, notuniversalstrength.')
 (OUT/'TRAIN-root-diagnostic.json').write_text(json.dumps(new,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
