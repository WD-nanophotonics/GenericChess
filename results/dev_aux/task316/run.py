"""Diagnose same-name VariantPath immutability; actual readbacks, no go calls."""
import json,time,sys,math
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task313'));import run as Q
O=R/'results/dev_aux/task316';O.mkdir(exist_ok=False);Q.P.stop();start=time.monotonic();deadline=start+60;rows=[]
def setting(e,p):
 w=dict(P=p,N=208,B=208,R=208,Q=208,K=0);config=O/'probe-variant.ini';line=' '.join(k.lower()+':'+str(w[k]) for k in 'PNBRQ');config.write_text('[aux_short:chess]\npieceValueMg = '+line+'\npieceValueEg = '+line+'\n',encoding='utf-8');trans=[]
 for name,value in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(config)),('UCI_Variant','aux_short')]:
  e.send('setoption name '+name+' value '+str(value));trans.append(dict(name=name,value=value,reply=e.ready()))
 e.send('position fen 7k/8/8/3P4/8/8/8/K7 w - - 0 1');e.send('eval');rr=e.ready();e.send('ucinewgame');e.ready();return dict(requested=w,expected_white_pawns=p/208,eval_reply=rr,option_replies=trans)
e=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
try:
 for p in (200,216):rows.append(dict(process='same',**setting(e,p)))
finally:e.close()
e=Q.P.M.start(R/'.local_agent/alignment-order/fairy-order-toggle.exe',3,deadline,Q.P.stop)
try:rows.append(dict(process='fresh',**setting(e,216)))
finally:e.close()
vals=[float(next(s for s in z['eval_reply'] if s.startswith('Final evaluation')).split()[2]) for z in rows];assert vals==[.96,.96,1.04];acks=[[s for z in row['option_replies'] for s in z['reply'] if s.startswith('info string DEV_AUX alignment ')] for row in rows];assert '1:200:200' in acks[1][-1] and '1:216:216' in acks[2][-1]
cpp=R/'.local_agent/alignment-order/source/variant.cpp';lines=cpp.read_text().splitlines();evidence=lines[2170:2196];(O/'audit.json').write_text(json.dumps(dict(complete=True,actual_go_calls=0,processes=2,rows=rows,measured=vals,seconds=time.monotonic()-start,cause='VariantMap refuses duplicate aux_short name inside one process; ucinewgame resets search but does not reload variant prices. Freshprocess216 readback1.04 exact MG/EG216; prior sameprocessstill200.',source_sha256=Q.sha(cpp),source_excerpt=evidence,impact='315 stopped after2 actualP- queries; no P+ query. Old267/269 priceprofiles used distinctownedprocesses, source audit required. NEWpanelmustfreshprocessperweight, reuse2completed315queries and16base313.'),indent=2),encoding='utf-8');print(vals,round(time.monotonic()-start,3))