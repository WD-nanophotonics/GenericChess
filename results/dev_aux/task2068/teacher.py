"""Research-only exact canonical-root accessor; arbitrary histories stay UNKNOWN."""
from pathlib import Path
from dataclasses import dataclass
import json,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from scripts.generic_inventory_proof_transport import execution_differences
from scripts.generic_session_win_proof import replay_bound
from scripts.generic_proof_rnb_bridge import actor_state
@dataclass(frozen=True)
class TeacherLabel:
 quality:str
 value:int|None
 reason:str
 rank:int|None=None
 optimal_actions:tuple=()
class CanonicalTeacher:
 def __init__(self,census,labels,audit):
  self.census=Path(census);self.labels=Path(labels);self.audit=Path(audit)
  cp=json.loads((self.census/'plan.json').read_text());summary=json.loads((self.labels/'result.json').read_text());verified=json.loads((self.audit/'result.json').read_text())
  if verified['status']!='PASS_COMPLETE_COVERAGE_BELLMAN_RANK_CANONICAL_HISTORY' or verified['states']!=summary['states'] or verified['checked_edges']!=summary['edges']:raise ValueError('complete independent graph audit required')
  source=Path(cp['rules']).read_bytes()
  if hashlib.sha256(source).hexdigest()!=cp['rules_sha']:raise ValueError('ruleshashmismatch')
  self.reference=compile_ruleset_for_execution(deserialize_ruleset(source.decode('utf-8')));raw=(self.labels/'labels.jsonl').read_bytes();canonical=b'\n'.join(raw.splitlines())+b'\n'
  if hashlib.sha256(canonical).hexdigest()!=summary['labels_sha']:raise ValueError('labeldigestmismatch')
  rows=[json.loads(x)for x in raw.splitlines()];self.rows={self.key(r['board']):r for r in rows}
  if len(self.rows)!=summary['states']or summary['ranks_over96']!=0:raise ValueError('incomplete canonical WDL scope')
 @staticmethod
 def key(raw):return ''.join(raw[:-1])+str(raw[-1])
 def label(self,session):
  unknown=lambda reason:TeacherLabel('UNKNOWN',None,reason)
  if execution_differences(self.reference,session.compiled):return unknown('execution_rules_not_qualified')
  record=session.to_record()
  if record.actions or record.resigned_by is not None or getattr(record,'declaration',None)is not None or session.state.ply_count!=0:return unknown('noncanonical_history_not_qualified')
  try:replay_bound(session)
  except (ValueError,RuntimeError):return unknown('unreplayable_record')
  p=session.state.position
  if p.aux_state or any(h.total()for h in p.hands) or any(x is not None and(x.promoted or x.base_type_id!=x.current_type_id)for x in p.board):return unknown('state_features_outside_scope')
  r=self.rows.get(self.key(actor_state(session.state)))
  if r is None:return unknown('inventory_or_legality_outside_complete_graph')
  value={'WIN':1,'DRAW':0,'LOSS':-1}[r['label']]
  return TeacherLabel('EXACT_CANONICAL_FRESH_ROOT',value,'complete_Core_graph_and_rank_history_audit',r['rank'],tuple(e['action']for e in r['actions']if-e['child_value']==value))
