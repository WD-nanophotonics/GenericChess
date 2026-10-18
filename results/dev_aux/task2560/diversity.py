"""All TRAIN initial records and legal prefix dilution; no root filtering."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2529.training_audit import terminal
D=Path('results/dev_aux/task2558');A=Path('results/dev_aux/task2560')
def run():
 p=json.loads((D/'plan.json').read_text());cc={g:compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{g}.json').read_text())))for g in p['generator_seeds']};by=defaultdict(lambda:dict(c=Counter(),roots=set(),families=set(),positions=set(),terminal_families=set()));cache={}
 for line in(D/'games.jsonl').open():
  g=json.loads(line);k=g['generator_seed'],g['method'],g['seed'];a=by[k];c=a['c'];f=g['family'];r=g['initial_record'];raw=json.dumps(r,sort_keys=True,separators=(',',':'));h=hashlib.sha256(raw.encode()).hexdigest();ck=g['generator_seed'],f
  if ck not in cache:
   s=GameSession.replay(cc[ck[0]],deserialize_game_record(raw));cache[ck]=dict(record_sha=h,position_sha=hashlib.sha256(repr(s.state.position).encode()).hexdigest(),terminal=terminal(s))
  v=cache[ck];assert v['record_sha']==h;c['games']+=1;c['zero_queries']+=g['queries']==0;c['already_terminal_games']+=v['terminal']is not None;c['prefix_actions']+=len(r['actions']);a['roots'].add(h);a['positions'].add(v['position_sha']);a['families'].add(f)
  if v['terminal']is not None:a['terminal_families'].add(f)
 rows=[dict(rule=k[0],method=k[1],seed=k[2],counts=dict(a['c']),families=len(a['families']),distinct_full_history_roots=len(a['roots']),distinct_positions_including_aux=len(a['positions']),already_terminal_families=len(a['terminal_families']))for k,a in sorted(by.items())]
 out=dict(status='PASS_ALL_TRAIN_ROOTS_RETAINED_DIVERSITY_ACCOUNTED',rows=rows,registered_recipe='gs*1000000+family, sorted legal random prefix4; histories retain complete rules; positions are auxiliary-sensitive dataclass repr, not an equivalence quotient',unique_rule_family_records=len(cache),scope='Shared family recipes across initializations/methods/roles are correlated. Different learned policies consume different number of families under equalnodecap. No nonterminal/state/outcome filtering or strict unseen/population independence claim; position grouping omits full history intentionally only as a descriptive duplicate count, never as training/search cache.')
 (A/'diversity.json').write_text(json.dumps(out,indent=2));print(json.dumps(dict(status=out['status'],arms=len(rows),unique_rule_family_records=len(cache))))
if __name__=='__main__':run()
