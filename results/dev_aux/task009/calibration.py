"""Synthetic corruption sentinels calibrate a multiplicity-preserving table oracle."""
import sys,json,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.core import search_runtime as r
from generic_chess.core.transition import apply_action
from generic_chess.session.session import GameSession
compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));session=GameSession(compiled)
def entries(rt):return [(h,e.identity,int(e.count)) for h,bucket in rt._occurrences.items() for e in bucket]
def oldset(rt):return frozenset(entries(rt))
def multiset(rt):return frozenset(collections.Counter(entries(rt)).items())
rows=[]
for kind in ['increment_existing','add_fresh_child','duplicate_identical','move_bucket']:
 rt=r.SearchPathRuntime.from_state(session.state,compiled,history_witnesses=session._search_witnesses)
 rt.legal_actions();before_set=oldset(rt);before_multi=multiset(rt);projection=rt.repetition_counts
 saved={h:[r._Occurrence(e.identity,int(e.count)) for e in bucket] for h,bucket in rt._occurrences.items()}
 h,bucket=next(iter(rt._occurrences.items()));e=bucket[0]
 if kind=='increment_existing':e.count+=1
 elif kind=='add_fresh_child':
  child=apply_action(session.state,rt.legal_actions()[0],compiled)
  ident=r._runtime_position_identity(child.position,compiled);ch=r._full_runtime_hash(child.position,compiled)
  rt._occurrence_add(ident,ch)
 elif kind=='duplicate_identical':bucket.append(r._Occurrence(e.identity,int(e.count)))
 else:
  moved=r.RuntimeHash(h.lo^1,h.hi);assert moved not in rt._occurrences
  rt._occurrences[moved]=rt._occurrences.pop(h)
 row={'sentinel':kind,'set_oracle_detected':oldset(rt)!=before_set,'multiset_oracle_detected':multiset(rt)!=before_multi,'root_projection_changed':rt.repetition_counts!=projection,'entries_before':sum(n for item,n in before_multi),'entries_after':len(entries(rt))}
 assert row['multiset_oracle_detected']
 assert row['set_oracle_detected']==(kind!='duplicate_identical')
 rt._occurrences=saved;assert multiset(rt)==before_multi
 row['restored_after_sentinel']=True;rows.append(row)
out={'complete':True,'scope':'four deliberately corrupt private-state sentinels, oracle calibration only; no natural duplicate-entry defect inferred','rows':rows}
(Path(__file__).parent/'calibration.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
