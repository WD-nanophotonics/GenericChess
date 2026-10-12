"""ActualfiniteSEE/specialmove observations, sourceexplicitapproximation preserved."""
import json,time,hashlib,sys,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task153'
s=importlib.util.spec_from_file_location('M153',R/'results/dev_aux/task139/run.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M);A=M.A
D=json.loads((O/'declaration.json').read_bytes());w=D['weights'];binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256']
def material(b,color):return sum(w[chess.piece_symbol(t).upper()]*(len(b.pieces(t,color))-len(b.pieces(t,not color))) for t in range(1,6))
def oracle(b,target,color,base):
 v=material(b,color)-base;choices=[v];children=[];declines=[m.uci() for m in b.legal_moves if not(b.is_capture(m) and m.to_square==target)]
 if not declines:raise ValueError('no legaldecline; preservefixturefailure')
 for m in sorted(b.legal_moves,key=lambda x:x.uci()):
  if b.is_capture(m) and m.to_square==target:
   b.push(m);value,node=oracle(b,target,color,base);b.pop();children.append(dict(move=m.uci(),value=value,child=node));choices.append(value)
 result=(max if b.turn==color else min)(choices)
 return result,dict(fen=b.fen(),decline_value=v,legal_declines=declines,children=children,value=result)
def trace(e,b):
 e.send('position fen '+b.fen());e.send('eval');lines=e.ready();final=[x for x in lines if x.startswith('Final evaluation')]
 if len(final)!=1:raise ValueError('missingtrace')
 if 'none' in final[0]:return dict(status='UNAVAILABLE',raw=final[0],in_check=b.is_check(),expected_white_pawns=material(b,True)/208)
 measured=float(final[0].split()[2]);expected=material(b,True)/208;assert abs(measured-expected)<=.011
 return dict(status='MEASURED',raw=final[0],expected_white_pawns=expected,measured_white_pawns=measured)
if (O/'result.json').exists():raise FileExistsError('frozen')
started=time.monotonic();deadline=started+D['deadline_seconds'];stop=lambda:A.stop_check(R);rows=[];complete=False
try:
 for mode in D['modes']:
  e=M.start(binary,mode,deadline,stop)
  try:
   for f in D['fixtures']:
    probes,ack=M.configure(e,w,O/'variant.ini',deadline,stop);b=chess.Board(f['fen']);color=b.turn;m=chess.Move.from_uci(f['move']);assert b.is_valid() and m in b.legal_moves
    before=trace(e,b);base=material(b,color);afterboard=b.copy(stack=True);afterboard.push(m);value,tree=oracle(afterboard,m.to_square,color,base);after=trace(e,afterboard)
    e.send('position fen '+f['fen']);e.ready();answers=[]
    for t in f['thresholds']:
     e.send(f'devauxsee {f["move"]} {t}');reply=e.ready();lines=[x for x in reply if x.startswith('info string DEV_AUX SEE ')];assert len(lines)==1;v=bool(int(lines[0].split()[-1]))
     answers.append(dict(threshold=t,actual=v,oracle=value>=t,raw=lines[0]))
    rows.append(dict(fixture=f,mode=mode,price_probes=probes,table_ack=ack,before_leaf=before,after_leaf=after,immediate_material_gain=material(afterboard,color)-base,oracle_value=value,oracle_tree=tree,answers=answers))
  finally:e.close()
 complete=True
except BaseException as ex:error=type(ex).__name__+': '+str(ex)
out=dict(complete=complete,binary_sha256=D['binary_sha256'],rows=rows,wall_seconds=time.monotonic()-started,scope='Restrictedtargetcapture only; specialmoveSEE0isexplicitshortcut. Unavailablein-checkevaltrace isreported, noillegalstateforcing. No fullSEEorWDLclaim.')
if not complete:out['error']=error
A.atomic_json(O/'result.json',out)
summary=dict(complete=complete,queries=sum(len(r['answers']) for r in rows),seconds=out['wall_seconds'],measured_leaf_traces=sum(r[k]['status']=='MEASURED' for r in rows for k in ('before_leaf','after_leaf')),unavailable_leaf_traces=sum(r[k]['status']=='UNAVAILABLE' for r in rows for k in ('before_leaf','after_leaf')),cases=[dict(id=r['fixture']['id'],mode=r['mode'],oracle=r['oracle_value'],immediate_gain=r['immediate_material_gain'],mismatches=[a['threshold'] for a in r['answers'] if a['actual']!=a['oracle']]) for r in rows])
A.atomic_json(O/'summary.json',summary);print(json.dumps(summary,indent=2));sys.exit(0 if complete else 3)
