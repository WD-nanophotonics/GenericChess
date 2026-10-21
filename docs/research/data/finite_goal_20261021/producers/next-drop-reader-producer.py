"""Begin the next single-reader counterfactual; no new price search or games."""
from pathlib import Path
from dataclasses import replace
import json
from generic_chess.rules.schema import ruleset_from_dict,ruleset_to_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value,write_record
base=Path('artifacts/price-regions-20261021');source=json.loads((base/'d2-witness-localized.json').read_text());old=ruleset_from_dict(source['rule']);new=replace(old,drop_allowed={t:tuple(tuple(False for _ in mask) for mask in masks) for t,masks in old.drop_allowed.items()})
out=base/'next-drop-reader-plan.json';assert not out.exists();oc,nc=map(compile_ruleset_for_execution,(old,new));record=deserialize_game_record(json.dumps(source['record']));a=GameSession.replay(oc,record);b=GameSession(nc)
plan=dict(question='Does removing the only executable hand-deployment reader remove the natural D2 hand-price boundary, or expose a score-only artifact?',
 changed_premise='Only drop masks turned off in a NEW scoped game; complete promotion/other types/aux/history retained. Not a new fitness panel, old hand-price campaign rerun or generic target restriction.',
 source='d2-witness-localized.json',rule=ruleset_to_dict(new),planned_bounds=dict(nodes=30000,seconds=90,depth=2),
 immediate='Validate existing hand-reader proof scope, then reuse exact two-ply coefficient reduction; no WDL prerequisite or coefficient fit.',
 pending='No new D2 price calculation or game result executed; preserve all earlier frozen outcomes.')
try:
 for action in record.actions:b.submit(action)
 assert replace(a.state.position,ruleset_fingerprint=nc.ruleset_fingerprint)==b.state.position
 assert [(x.actor,x.action_signature,x.gave_check) for x in a.state.history]==[(x.actor,x.action_signature,x.gave_check) for x in b.state.history]
 assert GameSession.replay(nc,b.to_record()).state==b.state
 plan.update(preflight='accepted full18ply replay and physical state/events equal',record=json.loads(serialize_game_record(b.to_record())),
   old_legal_actions=len(a.legal_actions()),new_legal_actions=len(b.legal_actions()),history_entries=len(b.state.history))
except Exception as exc:plan.update(preflight='refused',error=type(exc).__name__+':'+str(exc))
write_record(out,plan);print(plan['preflight'],plan.get('old_legal_actions'),plan.get('new_legal_actions'),plan.get('history_entries'))
