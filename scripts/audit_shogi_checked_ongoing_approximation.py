"""Saved actual full table, no gameplay/action-list repetition."""
from dataclasses import replace
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.terminal import TerminalResult,TerminalStatus
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.public_goal_intervals import PublicGame
from scripts.research_state_replay import read_game_state
from scripts.shogi_checked_ongoing_contact import checked_ongoing_choice,SCOPE
from scripts.shogi_exact_twenty_family import exact_twenty_choice
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/shogi_checked_ongoing_approximation_20261005.json'
SOURCES=('scripts/audit_shogi_checked_ongoing_approximation.py','scripts/shogi_checked_ongoing_contact.py','docs/research/SHOGI_CHECKED_ONGOING_APPROXIMATION_PROTOCOL.md','docs/research/data/shogi_exact_family_execution_20261005.json','scripts/research_state_replay.py','scripts/shogi_exact_twenty_family.py','scripts/shogi_contact_interval_choice.py','scripts/resource_mode_context.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('saved checked scope audit never rerun')
    start=monotonic();r=dict(complete=False,public_transitions=0,source_queries=0,enumerated=0,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        raw=json.loads((ROOT/SOURCES[3]).read_text());assert raw['complete'] and set(raw['children'])==set(raw['all_actions'])
        children={k:read_game_state(v) for k,v in raw['children'].items()};game=PublicGame(compile_ruleset_for_execution(build_standard_shogi_ruleset()))
        r['old_strict']=exact_twenty_choice(children,game,owner=0,duration='both',complete=True)
        r['explicit_approximate']=checked_ongoing_choice(children,game,owner=0,duration='both',complete=True,approximation_scope=SCOPE)
        r['unrequested']=checked_ongoing_choice(children,game,owner=0,duration='both',complete=True)
        key=next(iter(children));child=children[key]
        stale=dict(children);stale[key]=replace(child,terminal_status=TerminalResult(TerminalStatus.CHECKMATE,0))
        r['stale_control']=checked_ongoing_choice(stale,game,owner=0,duration='both',complete=True,approximation_scope=SCOPE)
        if r['old_strict']['complete'] or r['unrequested']['complete'] or r['stale_control']['complete']:raise ValueError('scope bypass')
        for law,row in r['explicit_approximate']['by_law'].items():
            if not row['complete'] or row['selected']!=raw['approximate_checked_ablation'][law]['selected'] or row['checked_ongoing_choices']!=raw['checked_children']:raise ValueError('saved approximation mismatch')
        r['complete']=r['explicit_approximate']['complete'] and len(children)==69
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','old_strict','explicit_approximate','unrequested','stale_control')}))
