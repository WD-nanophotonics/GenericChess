import json,time,sys,copy,random,hashlib,importlib.util,os
from pathlib import Path
import chess
R=Path.cwd();sys.path.insert(0,str(R));O=R/'results/dev_aux/task276';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists()
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import record_value
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P)
s=importlib.util.spec_from_file_location('codec',R/'results/dev_aux/task253/codec.py');C=importlib.util.module_from_spec(s);s.loader.exec_module(C);P.stop();assert hashlib.sha256((R/'generic_chess/_native_core.cp312-win_amd64.pyd').read_bytes()).hexdigest()==D['native_binary_sha256'];start=time.monotonic();deadline=start+180;c=compile_semantic_ruleset(build_western_chess_ruleset());n=compile_native_semantic_rules(c);cache={};signatures={};calls=[];metrics=[];trips=[];arms={a:[] for a in D['arms']};totalbytes={a:0 for a in D['arms']};io={a:0 for a in D['arms']}
def sig(ss,b):return ss.state,ss.history,ss.result,ss._search_witnesses,b.fen(),tuple(m.uci() for m in b.move_stack)
def make(f):
 ss=GameSession(c);b=P.board(f)
 for text in f['history']:ss.submit(next(a for a in ss.legal_actions() if uci(a)==text))
 return ss,b
ts=time.monotonic()
for i,f in enumerate(D['roots']):ss,b=make(f);cache[i]=ss,b;signatures[i]=sig(ss,b)
setup=time.monotonic()-ts
with (O/'journal.jsonl').open('xb') as journal:
 for i,f in enumerate(D['roots']):
  for opponent in D['opponents']:
   for color in (True,False):
    ti=len(trips);order=D['arms'][ti%3:]+D['arms'][:ti%3];rows=[]
    for arm in order:
     P.A.guard(deadline,P.stop);ts=time.monotonic();ss,b=make(f) if arm=='replay_dense' else (copy.copy(cache[i][0]),cache[i][1].copy(stack=True));prefix=time.monotonic()-ts;assert sig(ss,b)==signatures[i];e=SemanticSearchEngine(c,n,board_values=D['weights'],hand_values={k:0 for k in n.type_ids},dynamic_values=None,tt_megabytes=0);rng=random.Random(D['random_seeds'][i]);actions=[];searches=[];oppo=[];ts=time.monotonic()
     for ply in range(8):
      P.A.guard(deadline,P.stop)
      if b.is_game_over(claim_draw=False):break
      aa={uci(a):a for a in ss.legal_actions()};assert sorted(aa)==sorted(m.uci() for m in b.legal_moves)
      if b.turn==color:
       before=sig(ss,b);v=e.search(ss,SearchLimits(max_depth=2,max_nodes=None,max_time_seconds=3,quiescence_max_depth=0),root_window_pruning=False);assert sig(ss,b)==before;assert v.completed_depth==2;m=chess.Move.from_uci(uci(v.action));searches.append(dict(ply=ply,root_fen=b.fen(),full_history=[m.uci() for m in b.move_stack],result=record_value(v)))
      elif opponent=='random':m=rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()))
      else:m,v=P.P.unit2ply(b.copy(stack=True),deadline,P.stop);oppo.append(v)
      ss.submit(aa[m.uci()]);b.push(m);actions.append(m.uci())
     playseconds=time.monotonic()-ts;score=P.G.score(b,color,len(actions),8);record=dict(root=i,color=color,opponent=opponent,random_seed=D['random_seeds'][i],opening_history=f['history'],actions=actions,search_records=searches,opponent_records=oppo,final_fen=b.fen(),score=score,generic_terminal=record_value(ss.result));assert sig(cache[i][0],cache[i][1])==signatures[i];ts=time.monotonic()
     if arm=='clone_journal':
      encoded=C.encode(record);entry=dict(sequence=len(arms[arm]),sha256=hashlib.sha256(C.canonical(record)).hexdigest(),record=encoded);line=C.canonical(entry)+b'\n';journal.write(line);journal.flush();os.fsync(journal.fileno());totalbytes[arm]+=len(line);arms[arm].append(encoded)
     else:
      arms[arm].append(record);P.A.atomic_json(O/(arm+'.json'),dict(complete=False,calls=arms[arm]));totalbytes[arm]+=(O/(arm+'.json')).stat().st_size
     io[arm]+=time.monotonic()-ts;row=dict(triple=ti,arm=arm,record=C.encode(record));calls.append(row);rows.append(record);metrics.append(dict(triple=ti,arm=arm,prefix_seconds=prefix,play_seconds=playseconds,last_io_seconds=time.monotonic()-ts))
    def non_time(v):
     if isinstance(v,dict):return {k:non_time(z) for k,z in v.items() if 'elapsed' not in k and k not in ('wall_seconds','seconds')}
     if isinstance(v,list):return [non_time(z) for z in v]
     return v
    assert non_time(rows[0])==non_time(rows[1])==non_time(rows[2]);trips.append(dict(triple=ti,root=i,color=color,opponent=opponent,order=order,all_non_time_fields_equal=True));print(ti,len(calls),round(time.monotonic()-start,3),flush=True)
entries=[json.loads(line) for line in (O/'journal.jsonl').read_bytes().splitlines()];assert len(entries)==8
for j,z in enumerate(entries):assert z['sequence']==j;raw=C.decode(z['record']);assert hashlib.sha256(C.canonical(raw)).hexdigest()==z['sha256'] and raw==C.decode(arms['clone_journal'][j])
for arm in ('replay_dense','clone_dense'):assert json.loads((O/(arm+'.json')).read_bytes())['calls']==arms[arm]
out=dict(complete=True,actual_games=len(calls),actual_Native_queries=sum(len(C.decode(z['record'])['search_records']) for z in calls),all_matched_triples=trips,calls=calls,metrics=metrics,cache_setup_seconds=setup,total_record_write_bytes=totalbytes,total_record_io_seconds=io,seconds=time.monotonic()-start,scope=D['scope']);P.A.atomic_json(O/'result.json',out);print(json.dumps({k:out[k] for k in ('complete','actual_games','actual_Native_queries','cache_setup_seconds','total_record_write_bytes','total_record_io_seconds','seconds')},indent=2))
