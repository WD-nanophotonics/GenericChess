"""Read saved public states; no source calls or replayed transitions."""
import hashlib, json, sys
from collections import Counter
from pathlib import Path
from time import monotonic
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.chess_certificate_request import chess_certificate_request
from scripts.research_state_replay import read_game_state
from scripts.research_record import write_record
from scripts.public_goal_intervals import PublicGame
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
OUT = ROOT/'docs/research/data/contact_depth2_source_admission_20261005.json'
SOURCES = ('scripts/audit_contact_depth2_source_admission.py',
    'docs/research/CONTACT_DEPTH2_SOURCE_ADMISSION_PROTOCOL.md',
    'scripts/chess_certificate_request.py','scripts/research_state_replay.py',
    'scripts/public_goal_intervals.py','docs/research/data/contact_depth2_dominance_20261005.json',
    'docs/research/data/chess_pinned_queen_mate_20261005.json')
if __name__ == '__main__':
    if OUT.exists(): raise FileExistsError('frozen source-admission record')
    start = monotonic()
    r = dict(complete=False, public_transitions=0, source_queries=0,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}, rows=[])
    c = compile_ruleset_for_execution(build_western_chess_ruleset()); game = PublicGame(c)
    choices = json.loads((ROOT/SOURCES[5]).read_text())
    original = json.loads((ROOT/SOURCES[6]).read_text())
    encoded = [(name, key, original['children'][key]) for name,key in choices['positive_depth2'].items()]
    encoded.append(('unit_enemy_successor', choices['rook_capture']['all_enemy_replies'][0], choices['rook_capture']['state']))
    for name,key,value in encoded:
        if monotonic()-start >= 15 or len(r['rows']) >= 16: raise TimeoutError('admission cap')
        state = read_game_state(value); t = game.terminal(state)
        inventory = Counter(p.current_type_id for p in state.position.board if p)
        row = dict(method=name, action=key, inventory=dict(inventory), board_tokens=sum(inventory.values()),
            ply=state.ply_count, history_records=len(state.history), terminal=t.status.value,
            installed_material_domain=inventory in (Counter(K=2,B=1), Counter(K=2,R=1)))
        try:
            request = chess_certificate_request(state,c)
            row.update(encoding_admitted=True, state_sha256=request['state_sha256'], source_verified=request['source_verified'])
        except ValueError as error:
            row.update(encoding_admitted=False, reason=str(error))
        r['rows'].append(row); write_record(OUT,r)
    r['complete'] = len(r['rows']) == 4
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r); print(json.dumps({k:v for k,v in r.items() if k != 'source_sha256'}))
