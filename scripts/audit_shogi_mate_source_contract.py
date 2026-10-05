"""Validate already acquired complete file slices; no engine or source-label query."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/shogi_mate_source_contract_20261006.json'
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('source contract extraction never rerun')
    directory=ROOT/'.local_agent/mate_source_20261006';manifest=json.loads((directory/'manifest.json').read_text())
    assert not manifest['complete'] and manifest['error']=='ValueError: source acquisition bytes/time cap'
    assert manifest['commit']=='c1b80eaa09fe13d5f12b1599d1ae4d53c224de30' and len(manifest['files'])==4
    texts={}
    for item in manifest['files']:
        data=(directory/item['local']).read_bytes();assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'];texts[item['path']]=data.decode('utf-8-sig')
    picker=texts['source/mate/mate_move_picker.h'];solver=texts['source/mate/mate_solver.cpp'];dfpn=texts['source/mate/mate_dfpn.hpp'];engine=texts['source/engine/yaneuraou-mate-engine/yaneuraou-mate-search.cpp']
    checks=dict(attacker_checks='generateMoves<CHECKS_ALL>' in picker,defender_evasions='generateMoves<EVASIONS_ALL>' in picker,legality_filtered='!pos.legal(ml)' in picker,underpromotion_flag='GEN_ALL' in picker,
       odd_solver_countercheck_restriction='if (pos.gives_check(m2))' in solver and 'goto NEXT_CHECK;' in solver,checked_attacker_oneply_incomplete='return !pos.in_check() ? mate_1ply(pos) : Move::none();' in solver,
       pv_single_child='or_node ? pick_the_best<true,proof,current>(node) : pick_the_best<false,proof,current>(node)' in dfpn,
       unresolved_distinct='checkmate none' in engine,restricted_nonmate_distinct='checkmate nomate' in engine,timeout_distinct='checkmate timeout' in engine)
    assert all(checks.values())
    r=dict(complete=True,scope='source-opportunity metadata only; no exported proof/source label admitted',commit=manifest['commit'],acquisition_complete=False,acquisition_error=manifest['error'],acquisition_read_bytes=manifest['bytes'],complete_source_bytes=sum(x['bytes'] for x in manifest['files']),external_files=manifest['files'],observed_checks=checks,engine_queries=0,source_goal_queries=0,public_transitions=0,source_ready_for_independent_goal_adapter=False,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('scripts/audit_shogi_mate_source_contract.py','docs/research/SHOGI_MATE_SOURCE_PREFLIGHT.md','docs/research/SHOGI_MATE_SOURCE_CONTRACT.md')})
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('external_files','source_sha256')}))
