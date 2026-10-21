"""Existing opening-win preference as a descriptive stratum, no filtering/refill."""
from pathlib import Path
import json,time
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.filters import run_soft_filters
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from scripts.research_record import record_value,write_record
base=Path('artifacts/price-regions-20261021');d=json.loads((base/'mixed-scale-state-48.json').read_text());out=base/'opening-filter-strata.json'
if out.exists():raise FileExistsError(out)
rows=[]
for r in d['setup']:
 t=time.perf_counter();c=compile_ruleset_for_execution(ruleset_from_dict(r['definition']));s=GameSession(c);owner=s.state.position.side_to_move
 results=run_soft_filters(GeneratorConfig(seed=r['seed'],board_size=8,require_no_opening_win_in_one=True),c,{p.type_id:p for p in c.piece_types})
 filtered=next(x for x in results if x.name=='opening_has_no_win_in_one');wins=[str(a) for a,x in legal_successors(s.state,c) if x.terminal_status.winner==owner]
 assert filtered.passed==(not bool(wins))
 rows.append(dict(seed=r['seed'],filter=record_value(filtered),winning_first_actions=wins,opening_actions=len(s.legal_actions()),seconds=time.perf_counter()-t,
     observed_game_plies=[g['outcome']['plies'] for g in d['games'] if g['seed']==r['seed']]))
write_record(out,dict(scope='Descriptive existing filter on all6already-played rules. No game deleted/relabelled, no new rule sample or activation; passing does not establish balance.',rows=rows))
print([(r['seed'],r['filter']['passed'],len(r['winning_first_actions'])) for r in rows])
