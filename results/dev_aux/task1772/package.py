"""Segment54 reviewed evidence accounting; no experiment or transport actions."""
import json
from pathlib import Path
R=Path('results/dev_aux')
results={t:json.loads((R/f'task{t}/result.json').read_text()) for t in range(1761,1772)}
visits={}
for t in [1761,1762,1764,1767,1769]:visits[t]=sum(json.loads(x)['nodes'] for x in (R/f'task{t}/calls.jsonl').read_text().splitlines())
cost=dict(segment=54,session_id='c73e1870-639b-4cee-ad72-1ee6406d9fcc',actual_native_go=sum(results[t].get('actual_native_go',results[t].get('actual_new_native_go',0)) for t in [1763,1765,1766,1768,1770,1771]),
 actual_native_reported_nodes=sum(results[t]['actual_native_reported_nodes'] for t in [1763,1765,1766,1768])+sum(x['native_nodes'] for x in results[1771]['summary'].values()),
 controller_episode_records=sum(results[t]['games'] for t in [1763,1765,1766,1768]),early_incomplete_episode_rows=1,
 actual_native_perft=sum(json.loads((R/f'task{t}/native_qualification.json').read_text())['actual_perft'] for t in [1763,1765,1768]),proof_benchmark_visits=visits,job_seconds={t:r['seconds'] for t,r in results.items()},
 interpretation='Job wall sum differs from Agent elapsed/exclusive CPU. Concurrent bounded runs and ordinary machine load occurred. Generic visits and Native nodes differ; actual Native overshoots retained.',
 model_tokens='Not independently measured; no fabricated per-thread token count. Engineering/testing/evidence/consultation overhead included in session time.',limits='Single runs<=1200s; no extra model workers/fees/security changes. Caps and incomplete evidence retained.')
(R/'COST_20261015_54.json').write_text(json.dumps(cost,indent=2))
failures=dict(segment=54,records=[
 dict(task=1766,kind='declared_go_cap',episode_records=750,planned=2048,actual_native_go=10000,recovery='Six orphan Native observations recovered as a legal contiguous prefix with0newgo; original cohort stays partial. Future per-step and in-flight journals added.'),
 dict(task=1768,kind='declared_wall_cap1200s',episode_records=1178,planned=1216,early_incomplete_rows=1,full_paired_DEV_families=61,planned_DEV_families=64,recovery='Journal and all missing-data bounds retained. No cap extension or rerun.'),
 dict(kind='native_node_overshoot',example1763_max_extra=17,recovery='Actual counters and reported_node_overrun preserved; no equal-primitive-work claim.'),
 dict(task=1765,kind='pooled_original_cell_summary',recovery='Raw TRAIN+DEV pooled cells unchanged; independent audit writes DEV-only cells and validates TRAIN-only selection. Later entry separates phases.'),
 dict(kind='inconsistent_root_terminal_contract',recovery='Reject stale imported terminal status; regression passes and earlier executed sources preserved.'),
 dict(kind='PN_depth_metadata',recovery='Current PN completed_depth0, separate peak_depth; executed earlier sources kept.'),
 dict(kind='fixture_and_interrupt_assumptions',recovery='Correct illegal/adjacent kings, wrong target, non-multi-defense and in-check pass fixtures. Legacy transition is atomic; semantic execution has internal checkpoints.56final tests pass.'),
 dict(kind='unsent_request_and_schema_corrections',recovery='Routing-incomplete PREPARED request frozen unsent. Schema-invalid calls sent nothing. Fresh labeled question sent once and exact receipt/thread bound privately.'),
 dict(kind='supported_tool_recovery',recovery='Oversized private Slack write split into exact chunks; default-sandbox copy repeated with authorized escalation. No bypass.'),
 dict(kind='cost_writer_schema',recovery='Tail exposes actual_new_native_go rather than actual_native_go; accounting corrected before any delivery.')])
(R/'FAILURES_20261015_54.json').write_text(json.dumps(failures,indent=2))
qa=dict(segment=54,focused_tests=56,failures=0,errors=0,exhaustive_KRK_valid_roots=3496,public_KRK_certificate_nodes=results[1764]['proof_nodes_publicly_replayed'],unfamiliar_roots=922,unfamiliar_reference_states=6310,false_wins_observed=0,
 public_game_audits={t:json.loads((R/f'task{t}/audit.json').read_text())['status'] for t in [1763,1765,1766,1768]},science_complete=False,
 privacy='Checked project source/results only. Exact raw Slack/receipts/account and machine test metadata remain Git-ignored .local_agent; credentials and personal inputs excluded.',
 boundaries='DEV_AUX sidemission only. Primary41e69e1dd8ab2c459239175d0c4091f90dffb389 read-only context; no product/default/UI change; heartbeat PAUSED.')
(R/'QA_20261015_54.json').write_text(json.dumps(qa,indent=2))
print(cost)
