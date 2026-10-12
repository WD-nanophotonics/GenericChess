import json,sys,time,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task392';O.mkdir(exist_ok=True);t0=time.monotonic();partial='--partial' in sys.argv
if partial:
 folder=R/'results/dev_aux/task387';gb=(folder/'games.jsonl').read_bytes();qb=(folder/'queries.jsonl').read_bytes();gb=gb[:gb.rfind(b'\n')+1];qb=qb[:qb.rfind(b'\n')+1];games=[json.loads(x) for x in gb.splitlines()];queries=[json.loads(x) for x in qb.splitlines()];n=0;pv=0
 for g in games:pv+=V.game(g)
 expected=[V.bare(q) for g in games for q in g['queries']];assert queries[:len(expected)]==expected
 result=dict(status='PARTIAL_PASS',completed_games=len(games),checked_game_go=len(expected),actual_complete_raw_go=len(queries),uncompleted_game_query_tail=len(queries)-len(expected),all_PV_move_checks=pv,snapshot_games_bytes_sha256=hashlib.sha256(gb).hexdigest(),snapshot_queries_bytes_sha256=hashlib.sha256(qb).hexdigest(),seconds=time.monotonic()-t0,scope='completeJSONLprefixduringsoleproducer; not final allbatch audit orfuturefilehash',independent_backend='cshogi0.9.7/literalSFEN/fullhistory/ruleterminal/materialprice/PV/journal')
else:
 r=V.audit(387);result=dict(status='PASS',rows=[r],seconds=time.monotonic()-t0,independent_backend='cshogi0.9.7/literalSFEN/fullhistory/ruleterminal/materialprice/PV/journal; excludes not-executed claims')
(O/('partial.json' if partial else 'result.json')).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))