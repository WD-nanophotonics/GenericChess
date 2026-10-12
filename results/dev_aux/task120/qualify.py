"""Requalify preserved pure-material Fairy after user changes Smart App Control."""
import hashlib,json,math,sys,time,winreg
from pathlib import Path
import chess
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'results/dev_aux/task109'))
import adapter
BINARY=ROOT/'.local_agent/material-selfplay/fairy-material.exe'
EXPECTED='477628ae141c6e5fb7dcb562e31e3bc40eab95b20c8b966ece131a1dbf090999'
PROFILES=[dict(P=208,N=73,B=901,R=149,Q=397,K=0),dict(P=208,N=701,B=89,R=997,Q=131,K=0)]
def smart_control_state():
 with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\CI\Policy') as key:return winreg.QueryValueEx(key,'VerifiedAndReputablePolicyState')[0]
def main():
 stop=lambda:adapter.stop_check(ROOT);stop();state=smart_control_state()
 if state!=0:raise RuntimeError('Await actual user-disabled Smart App Control state; no launch attempted, state='+str(state))
 digest=hashlib.sha256(BINARY.read_bytes()).hexdigest()
 if digest!=EXPECTED:raise RuntimeError('Preserved source-bound binary changed')
 if (OUT/'qualification.json').exists():raise FileExistsError('Fresh qualification evidence required; no overwrites/retries')
 start=time.monotonic();deadline=start+180;rows=[];processes=[]
 result=dict(complete=False,binary_sha256=digest,weights=[{k.lower():w[k] for k in 'PNBRQ'} for w in PROFILES],rows=rows,smart_app_control_state_before=state,source_pin='9f778da667f6e07dae1e85d3e2ea204fc6dee94d',scope='Actual pure-material Fairy UCI qualification after explicit human configuration change; retained SEE/order/pruning priors; old4551 record unchanged')
 try:
  for i,w in enumerate(PROFILES):
   engine=None
   try:
    adapter.guard(deadline,stop);engine=adapter.UCI(BINARY,ROOT,deadline,stop)
    engine.backend='ACTUAL_FAIRY_MATERIAL:'+digest
    processes.append({'profile':i,'handshake':engine.handshake})
    probes=adapter.configure(engine,w,OUT/f'profile{i}.ini',deadline,stop)
    processes[-1]['fresh_white_leaf_probes']=probes
    for kind in 'pnbrq':
     for side in ['w','b']:
      adapter.guard(deadline,stop)
      fen=f'7k/8/8/3{kind.upper()}4/8/8/8/K7 {side} - - 0 1';board=chess.Board(fen);assert board.is_valid()
      engine.send('position fen '+fen);engine.send('eval');reply=engine.ready()
      values=[s for s in reply if s.startswith('Final evaluation')]
      if len(values)!=1:raise ValueError('Actual leaf trace ambiguous')
      value=float(values[0].split()[2]);expected=w[kind.upper()]/208
      if not math.isfinite(value) or abs(value-expected)>.011:raise ValueError('Actual profile/side leaf effect mismatch')
      engine.send('go nodes 512');lines=engine.until(lambda s:s.startswith('bestmove '));move=lines[-1].split()[1]
      if chess.Move.from_uci(move) not in board.legal_moves:raise ValueError('Actual mature search returned illegal move')
      engine.ready();rows.append(dict(variant=i,type=kind,side=side,fen=fen,final_eval_pawns=value,expected_white_pawns=expected,bestmove=move,search_info=lines,configured_nodes=512))
   finally:
    if engine:engine.close()
  result['complete']=True
 except BaseException as err:result['error']=type(err).__name__+': '+str(err)
 result.update(wall_seconds=time.monotonic()-start,processes=processes,actual_search_probe_count=len(rows),mature_selfplay_games=0)
 adapter.atomic_json(OUT/'qualification.json',result)
 if result['complete']:adapter.validated_entry(BINARY,OUT/'qualification.json')
 print(json.dumps({k:result[k] for k in ['complete','actual_search_probe_count','wall_seconds','binary_sha256']}|({'error':result['error']} if 'error' in result else {})))
 return 0 if result['complete'] else 3
if __name__=='__main__':sys.exit(main())