"""One fixed pure-Leaper full-policy game study; no search/default modification."""
from pathlib import Path
from datetime import datetime,timezone
import copy,gzip,json,time,hashlib
from scripts.leaper_pvs_quality_pilot import make_session,CallerDeadline,provider_metrics,metric_delta
from scripts.leaper_relative_history_pilot import memory_snapshot,native_identity
from scripts.research_record import record_value,write_record
from generic_chess.rules.schema import compute_fingerprint,ruleset_from_dict
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from tools.local_agent import session


def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def prepare(base):
 b=Path(base);assert not(b/'inputs.json').exists()
 source=Path('docs/research/data/leaper_bound_trials_20261031/q-bound-quality-20261031/inputs.json.gz')
 template=json.loads(gzip.decompress(source.read_bytes()))['rows'][0]['RuleSet']
 triples=[
  ([(1,0),(-1,0),(0,1),(0,-2)],[(1,1),(-1,1),(0,-1),(2,0)],[(1,0),(-1,-1),(0,2),(-2,0)]),
  ([(0,1),(0,-1),(1,1),(-2,0)],[(1,0),(-1,0),(-1,1),(0,2)],[(1,1),(-1,-1),(0,-2),(2,0)]),
  ([(1,1),(-1,1),(0,-1),(2,0)],[(1,0),(-1,0),(0,2),(0,-1)],[(1,-1),(-1,0),(0,1),(0,-2)]),
  ([(1,0),(0,1),(0,-2),(-1,-1)],[(1,1),(-1,1),(-1,-1),(0,-2)],[(2,0),(-2,0),(0,-1),(1,1)]),
  ([(1,1),(-1,0),(0,1),(-2,0)],[(0,-1),(1,0),(-1,1),(0,2)],[(2,0),(-1,-1),(0,-2),(1,-1)]),
  ([(1,0),(-1,1),(0,-1),(0,2)],[(1,1),(0,2),(-1,-1),(-2,0)],[(2,0),(-2,0),(1,-1),(0,1)])]
 home=[('K',0,0),('A',1,2),('A',3,2),('B',2,1),('B',4,1),('C',1,3)]
 write_record(b/'literal-before-Core.json',dict(triples=triples,home=home,mirror='(5-x,5-y)',board=6,max_ply=64,repetition_limit=4,selection='ALL6literalnewcombinationsbeforeCore;noscreen/rulefilter/replacement;DEVELOPMENTprimitiveexposure'))
 signatures=[tuple(tuple(sorted(map(tuple,atoms))) for atoms in triple) for triple in triples];assert len(set(signatures))==6
 for oldpath in [Path('.local_agent/runner-up-allocation-20261105/inputs.json'),Path('.local_agent/capture-rich-order-20261105/inputs.json'),Path('.local_agent/internal-iterative-order-20261105/qualified-inputs.json')]:
  for row in json.loads(oldpath.read_text(encoding='utf-8'))['rows']:
   sig=tuple(tuple(sorted(tuple(a['offset']) for a in typ['movement_atoms'])) for typ in row['RuleSet']['piece_types'][1:])
   assert sig not in signatures
 rows=[]
 for family,triple in enumerate(triples):
  r=copy.deepcopy(template);r.update(board_size=6,initial_position=[[None]*6 for _ in range(6)],max_ply=64,repetition_limit=4,metadata={})
  for typ,atoms in zip(r['piece_types'][1:],triple):typ['movement_atoms']=[dict(kind='leap',offset=list(a)) for a in atoms]
  for tid in r['drop_allowed']:r['drop_allowed'][tid]=[[False]*36,[False]*36]
  for owner in (0,1):
   for tid,x,y in home:
    if owner:x,y=5-x,5-y
    assert r['initial_position'][y][x] is None
    r['initial_position'][y][x]=dict(owner=owner,base_type_id=tid,current_type_id=tid,promoted=False)
  fp=compute_fingerprint(ruleset_from_dict(r))
  rows.append(dict(id=f'captureQ-f{family}',family=family,RuleSet=r,fingerprint=fp,record=dict(schema_version=1,ruleset_fingerprint=fp,actions=[],resigned_by=None),exposure='literalnewmovementcombinationsDEVELOPMENT;notheldout/populationsample'))
 write_record(b/'inputs.json',dict(rows=rows))


def run(base):
 b=Path(base);f=json.loads((b/'frozen.json').read_text(encoding='utf-8'));assert sha(__file__)==f['producer_sha256'] and sha(b/'inputs.json')==f['input_sha256']
 for p,h in f['sources'].items():assert sha(p)==h
 rows=json.loads((b/'inputs.json').read_text(encoding='utf-8'))['rows'];t0=time.perf_counter();games=[];count=0;error=None
 try:
  for gi,slot in enumerate(f['game_slots']):
   if session.stopped():raise RuntimeError('userstop')
   if time.perf_counter()-t0+335>=4000:raise RuntimeError('batchdispatchcap')
   if datetime.now(timezone.utc)>=datetime.fromisoformat(f['deadline_utc']):raise RuntimeError('wholedeadline')
   row=rows[slot['family']];c,s=make_session(row);players={};game_tick=time.perf_counter();paths=[];eligible=True;censor=None
   while s.result.status.value=='ongoing':
    if session.stopped():raise RuntimeError('userstop')
    if memory_snapshot().get('rss_bytes',0)>1610612736:raise RuntimeError('RSScap')
    if time.perf_counter()-game_tick+5.2>=333:censor='gamecap';break
    if time.perf_counter()-t0+5.2>=4000:censor='batchcap';break
    if datetime.now(timezone.utc)>=datetime.fromisoformat(f['deadline_utc']):censor='wholedeadline';break
    if len(paths)>=64:censor='unexpected ongoing after64plies';break
    actor=s.state.position.side_to_move;on=actor==slot['ONseat'];before=s.to_record();start=stamp();tick=time.perf_counter();cpu=time.process_time()
    if actor not in players:
     players[actor]=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True,use_capture_only_qsearch=on),use_native_semantic_legality=True,use_native_semantic_availability=True,use_native_semantic_check=True)
    p=players[actor];pm=provider_metrics(p);remaining=5-(time.perf_counter()-tick);assert pm['present'] and remaining>0
    limits=SearchLimits(max_depth=64,max_nodes=2000000,max_time_seconds=remaining,quiescence_max_depth=4,quiescence_hard_max_depth=8)
    d=p.choose_action(s,limits,cancel_token=CallerDeadline(tick+5));end=stamp();wall=time.perf_counter()-tick
    path=b/f'return-{count:04}.json'
    assert not path.exists()
    r=dict(slot=count,game=gi,family=slot['family'],ply=len(paths),actor=actor,on=on,started_at=start,ended_at=end,wall_seconds=wall,cpu_seconds=time.process_time()-cpu,record_before=record_value(before),decision=record_value(d),actual_limits=record_value(limits),actual_tuning=record_value(p._tuning),provider_delta=metric_delta(pm,provider_metrics(p)),timing_eligible=wall<=5.1)
    write_record(path,r);paths.append(path.name);count+=1
    if start<end:session.record_work(start,end,'research',str(path))
    assert before==s.to_record() and d.runtime_depth_balanced and d.native_legality_fallbacks==d.native_legality_operational_failures==0
    assert d.nodes+d.qnodes<=2000000
    eligible=eligible and r['timing_eligible']
    if d.action is None or d.action not in s.legal_actions():censor='nolegalACTION';break
    s.submit(d.action)
    print(json.dumps(dict(game=gi,turn=len(paths),actor=actor,on=on,depth=d.completed_depth,Qcheck=d.checking_move_qactions,seconds=wall,status=s.result.status.value)),flush=True)
   terminal=s.result.status.value not in ('ongoing','no_contest');winner=s.result.winner if terminal else None
   value=None if not terminal or censor else (0 if winner is None else 1 if winner==slot['ONseat'] else -1)
   g=dict(game=gi,slot=slot,initial_record=row['record'],returns=paths,final_record=record_value(s.to_record()),literal_result=record_value(s.result),actual_terminal=terminal,ONvalue=value,eligible=eligible and terminal and censor is None,censor=censor,wall_seconds=time.perf_counter()-game_tick)
   write_record(b/f'game-{gi:02}.json',g);games.append(g)
   print(json.dumps(dict(GAME_COMPLETE=gi,plies=len(paths),ONvalue=value,eligible=g['eligible'],result=g['literal_result'])),flush=True)
   if censor in ('batchcap','wholedeadline','nolegalACTION'):raise RuntimeError(censor)
 except Exception as e:error=type(e).__name__+':'+str(e)
 pairs=[]
 for family in range(6):
  pair=[g for g in games if g['slot']['family']==family]
  exact=len(pair)==2 and all(g['eligible'] for g in pair)
  value=sum(g['ONvalue'] for g in pair) if exact else None
  pairs.append(dict(family=family,games=len(pair),complete_eligible=exact,ONnet=value))
 success=len(games)==12 and all(p['complete_eligible'] for p in pairs) and sum(p['ONnet'] for p in pairs)>=2 and sum(p['ONnet']>0 for p in pairs)>=3
 result=dict(status='SCOPED_DEVELOPMENT_POSITIVE' if success else 'NO_GO_OR_INCONCLUSIVE',games=len(games),queries=count,NOT_RUN=list(range(len(games),12)),pairs=pairs,error=error,wall_seconds=time.perf_counter()-t0,default='UNCHANGED',claim='finiteexposedcohortonly;notcrossrule/populationstrength;UNKNOWNnotDRAW,no tuning/refill')
 write_record(b/'summary.json',result);print(json.dumps(result));return result
if __name__=='__main__':
 import sys
 (prepare if sys.argv[1]=='prepare' else run)(sys.argv[2])
