"""Reuse exact query traces; derive finite selected-versus-consumed work only."""
import hashlib,json,sys
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.core.semantic_executor import SemanticEngine
from generic_chess.session.session import GameSession
from scripts.reserve_refresh_diagnostic import stopped
source=(B.parent/'task033/rank_merge.json').read_bytes();record=json.loads(source)
assert record['complete'] and len(record['rows'])==580
rows=[];summary={}
for game in ('western_chess','standard_shogi'):
 stopped();compiled=compile_ruleset_for_execution(build_builtin_ruleset(game));engine=SemanticEngine(compiled)
 root=GameSession(compiled).state.position;a,b=next(iter(engine.iter_legal_action_bindings(root)));child=engine._transition(root,a,b)
 for phase,pos in (('initial',root),('first_legal_child',child)):
  for owner in (0,1):
   for target in range(len(pos.board)):
    groups=compiled._incoming_attack_sources[(str(owner),target)]
    selected=[]
    for square,typed in groups.items():
     piece=pos.board[square]
     if piece is not None and piece.owner==owner:
      entries=typed.get(piece.current_type_id,())
      if entries:selected.append(entries)
    n=sum(map(len,selected));k=len(selected)
    old=next(r for r in record['rows'] if (r['game'],r['phase'],r['owner'],r['target'])==(game,phase,owner,target))
    consumed=old['binding_events'];assert 0<=consumed<=n
    if not old['result']:assert consumed==n
    rows.append({'game':game,'phase':phase,'owner':owner,'target':target,
     'total_compiled_sources_scanned':len(groups),'active_ranked_groups':k,'selected_rows_materialized_by_sort':n,
     'rows_consumed_until_original_return':consumed,'remaining_selected_rows':n-consumed,
     'original_result':old['result'],'callbacks':old['callbacks'],'query_not_rerun':True})
 for result in (False,True):
  rr=[r for r in rows if r['game']==game and r['original_result']==result]
  summary[game+'|'+str(result)]={'queries':len(rr),'selected_rows':sum(r['selected_rows_materialized_by_sort'] for r in rr),
   'consumed_rows':sum(r['rows_consumed_until_original_return'] for r in rr),
   'remaining_rows':sum(r['remaining_selected_rows'] for r in rr),
   'max_selected':max(r['selected_rows_materialized_by_sort'] for r in rr),
   'max_active_groups':max(r['active_ranked_groups'] for r in rr)}
out={'complete':True,'reused_query_record_sha256':hashlib.sha256(source).hexdigest(),'new_explicit_attack_query_pairs':0,'fixture_reconstruction_uses_semantic_legality_checks':True,'rows':rows,'summary':summary,
 'interpretation':'Only leftover selected rows are avoided by lazy iterator consumption; all compiled source occupancy/checkpoint scans are unchanged. Merge primes one row per nonempty group and does heap maintenance, so n-minus-consumed is not saved comparisons/allocations or predicted time.',
 'decision':'Finite trace supplies specific work premise for any future cost check; no caller timing or speed gain. Do not escalate full weighted caller on shape counts alone.'}
(B/'selection_work.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
