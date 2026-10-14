from pathlib import Path
import json,time,chess,hashlib,importlib.util,os
R=Path.cwd();O=R/'results/dev_aux/task1492';O.mkdir(exist_ok=False)
plan={'question':'Are frozen pawn contact roots already forced wins within3/5 plies independent of prices?','root_file':'results/dev_aux/task1470/roots.json','H3_indices':list(range(96)),'H5_indices':list(range(8))+list(range(48,56)),'max_seconds':600,'max_nodes':2000000,'scope':'Mechanism only, exposed frozen input; no humanfit/no new validation. WIN_WITHIN_H true is actual terminal force; false means cannot force win withinH, never draw/loss/infiniteWDL. No material leaf evaluation, no TT/history shortcut. Root turn attempts win, opponent all defenses.'};(O/'plan.json').write_text(json.dumps(plan,indent=2))
sp=importlib.util.spec_from_file_location('owned166',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
roots=json.loads((R/plan['root_file']).read_bytes())['roots'];start=time.monotonic();deadline=start+plan['max_seconds'];nodes=0;nextid=0;rows=[];error=None
f=(O/'certificate_nodes.jsonl').open('w',encoding='utf8')
def terminal(b):
 legal=sorted(m.uci() for m in b.legal_moves)
 if not legal:return {'kind':'CHECKMATE' if b.is_check() else 'STALEMATE','winner':not b.turn if b.is_check() else None},legal
 if b.is_insufficient_material():return {'kind':'SUFFICIENT_MATERIAL_INSUFF_DRAW','winner':None},legal
 if b.is_repetition(3):return {'kind':'THREEFOLD_AUTO','winner':None},legal
 if b.halfmove_clock>=100:return {'kind':'FIFTY_MOVE_AUTO','winner':None},legal
 return None,legal
def solve(b,depth,side):
 global nodes,nextid
 if time.monotonic()>deadline or nodes>=plan['max_nodes']:raise TimeoutError('frozen time/node fuse')
 if nodes%2048==0 and P.stop():raise InterruptedError('actual user stop')
 nodes+=1;nid=nextid;nextid+=1;t,ll=terminal(b);children=[]
 if t is not None:ans=t['winner']==side
 elif depth==0:ans=False
 else:
  own=b.turn==side;ans=not own
  for u in ll:
   b.push_uci(u)
   try:child,cid=solve(b,depth-1,side)
   finally:b.pop()
   children.append([u,cid,child])
   if child==own:ans=own;break
 rec={'id':nid,'fen':b.fen(),'history':[m.uci() for m in b.move_stack],'remaining':depth,'side':side,'terminal':t,'legal':ll,'children':children,'win_within_H':ans}
 f.write(json.dumps(rec,separators=(',',':'))+'\n');return ans,nid
try:
 for H,indices in [(3,plan['H3_indices']),(5,plan['H5_indices'])]:
  for index in indices:
   root=roots[index];b=chess.Board(root['fen8']);side=b.turn;actions=[]
   for u in root['legal']:
    b.push_uci(u)
    try:win,nid=solve(b,H-1,side)
    finally:b.pop()
    actions.append({'move':u,'win_within_H':win,'certificate_id':nid});f.flush()
    with (O/'closed_actions.jsonl').open('a',encoding='utf8') as a:a.write(json.dumps({'H':H,'index':index,'seed':root['seed'],'action':actions[-1]})+'\n')
   rows.append({'H':H,'index':index,'root':root,'winning_actions':[a['move'] for a in actions if a['win_within_H']],'actions':actions});print('CLOSED',H,index,'wins',sum(a['win_within_H'] for a in actions),'nodes',nodes,flush=True)
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:f.flush();os.fsync(f.fileno());f.close()
out={'status':'COMPLETE' if error is None else 'PARTIAL_PRESERVED','error':error,'closed_roots':len(rows),'nodes':nodes,'seconds':time.monotonic()-start,'rows':rows,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':plan['scope']};(O/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='rows'})
