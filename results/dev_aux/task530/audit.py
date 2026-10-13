import json,sys,time,hashlib,random,math
import cshogi as C
from fractions import Fraction
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task530';O.mkdir(exist_ok=True);sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
sys.path.insert(0,str(R/'results/dev_aux/task522'));import importlib.util
# Only frozen checker functions, no top-level production audit.
text=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8');a=text.index('text=(R/');b=text.index('nativegames=0',a);d=json.loads((R/'results/dev_aux/task529/declaration.json').read_bytes());d['seed_base']=d['random_seed_base'];exec(compile(text[a:b],'independent_transport_helpers','exec'));nativegames=0;pv=0;draws=0;go=0;orphans=0;t0=time.perf_counter();checks=[]
for gname,qname in [('games.jsonl','queries.jsonl'),('games_resumed.jsonl','queries_resumed.jsonl'),('games_final.jsonl','queries_final.jsonl')]:
 folder=R/'results/dev_aux/task529';games=[json.loads(x) for x in (folder/gname).open(encoding='utf-8')];raw=[json.loads(x) for x in (folder/qname).open(encoding='utf-8')];expected=[]
 for g in games:
  protocol_game(g)
  if any(a.get('random_draw') is not None for a in g['actions']):n,qs,nd=random_audit(g);pv+=n;draws+=nd;expected.extend(qs)
  else:pv+=V.game(g);expected.extend(V.bare(q) for q in g['queries'])
 assert expected==raw[:len(expected)]
 for q in raw[len(expected):]:pv+=V.query(q);assert q['nodes_limit']==8192 and q['reset_policy']=='cold_per_query';orphans+=1
 nativegames+=len(games);go+=len(raw);checks.append(dict(game_file=gname,query_file=qname,complete_journaled_games=len(games),actualgo=len(raw),orphan_go=len(raw)-len(expected)))
r=json.loads((R/'results/dev_aux/task529/result.json').read_bytes());table=tables(r['price_acks']);assert r['actual_games']==56 and r['actual_go']==890
out=dict(status='PASS_NATIVE_TRANSPORT',complete_journaled_games=nativegames,actual_go=go,orphan_go=orphans,PV_move_checks=pv,random_draws=draws,fulltable_entries=table,price_ack_scope='56resumedgames only; first8constructorack arrays notsaved, leaf cachedstate/rule/PV independentlychecked, no fabricated startup/ACK.',journals=checks,seconds=time.perf_counter()-t0,scope='ALL64completedgame rules/fullhistory/RNG/PV/warm-coldperrole queryindex/rawjournals plus10orphanqueries fromtwoordinaryimportfailures. Existingcontrols notrerun; prospective estimates corrected afterobserved costs. Sourcefixedmatchesallwithin-case non-time responses as529 result and supplementalfirst4case table.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
