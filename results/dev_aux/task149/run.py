"""Actualsamebinaryprice-table ablation qualification and frozen64root searches."""
import json,os,time,sys,importlib.util,hashlib
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task149';O.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('composition136for139',R/'results/dev_aux/task136/run.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M);A=M.A
def start(binary,alignment,deadline,stop):
 old=os.environ.get('GENERICCHESS_ALIGN_SEARCH_PRICES');os.environ['GENERICCHESS_ALIGN_SEARCH_PRICES']=str(alignment)
 try:e=A.UCI(binary,R,deadline,stop)
 finally:
  if old is None:os.environ.pop('GENERICCHESS_ALIGN_SEARCH_PRICES',None)
  else:os.environ['GENERICCHESS_ALIGN_SEARCH_PRICES']=old
 e.backend='FAIRY_EXPERIMENTAL_TABLE_TOGGLE:'+hashlib.sha256(binary.read_bytes()).hexdigest();e.alignment=alignment
 return e
def configure(e,w,config,deadline,stop):
 probes=A.configure(e,w,config,deadline,stop)
 e.send('setoption name UCI_Variant value aux_short');reply=e.ready()
 ack=[x for x in reply if x.startswith('info string DEV_AUX alignment ')]
 if len(ack)!=1:raise ValueError('missingexactprice-tableack')
 f=ack[0].split();assert int(f[4])==e.alignment
 prices={int(s.split(':')[0]):tuple(map(int,s.split(':')[1:])) for s in f[5:]}
 mg=(126,781,825,1276,2538);eg=(208,854,915,1380,2682)
 expected={i+1:(w[k],w[k]) if e.alignment else (mg[i],eg[i]) for i,k in enumerate('PNBRQ')}
 if prices!=expected:raise ValueError('searchpricesmismatch:'+str(prices))
 e.send('ucinewgame');e.ready()
 return probes,dict(raw=ack[0],prices={str(k):list(v) for k,v in prices.items()},alignment=e.alignment)
def freeze():
 if (O/'declaration.json').exists():raise FileExistsError('frozen')
 one=json.loads((R/'results/dev_aux/task133/declaration.json').read_bytes());two=json.loads((R/'results/dev_aux/task135/declaration.json').read_bytes())
 roots=[dict(id='old-'+r['id'],fen=chess.Board().fen(),history=r['history'],expected_fen=r['fen'],scope='exposedfirstdivergence') for r in one['roots']]
 for i,f in enumerate(two['train'][:4]):
  for color in (True,False):
   fen=f['white_fen' if color else 'black_fen'];roots.append(dict(id=f'composition-o{i}-c{int(color)}',fen=fen,history=[],expected_fen=fen,scope='syntheticinitial'))
 build=json.loads((R/'results/dev_aux/task147/build.json').read_bytes());assert build['status']=='COMPLETE'
 d=dict(task_id='149',roots=roots,profiles={**one['profiles'],'nonmonotonic':dict(P=208,K=0,N=2000,B=52,R=396,Q=510)},alignment_arms=[2,3],searches=96,node_limit=1024,deadline_seconds=600,binary_relative=build['binary_relative'],binary_sha256=build['binary_sha256'],build_sha256=hashlib.sha256((R/'results/dev_aux/task147/build.json').read_bytes()).hexdigest(),scope='Samebinarycandidateleaf/tables/recaptureconstants/budget; onlySEEattackerpriceordering2vs3changes. Bothretainfixedmargins, geometricSEEapproximationandotherpriors. Actuallegalsearchqualification, nolearningorstrengthclaim.',qualification='5actualleafreadbacks perroot plusPNBRQ MG/EGexacttableack; freshownedprocess peralignment/profile;ucinewgameperroot; fullinitialFEN/history; actualUCIinfo/legality retained.')
 (O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print(json.dumps(dict(frozen=True,roots=len(roots),searches=96)))
def execute():
 d=json.loads((O/'declaration.json').read_bytes());binary=R/d['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==d['binary_sha256'];started=time.monotonic();deadline=started+d['deadline_seconds'];stop=lambda:A.stop_check(R);stop();rows=[];complete=False
 if (O/'result.json').exists():raise FileExistsError('frozenexecution')
 try:
  for arm,w in d['profiles'].items():
   for aligned in ((2,3) if arm=='unit' else (3,2)):
    e=start(binary,aligned,deadline,stop)
    try:
     for root in d['roots']:
      probes,ack=configure(e,w,O/'variant.ini',deadline,stop)
      b=chess.Board(root['fen'])
      for text in root['history']:b.push_uci(text)
      assert b.fen()==root['expected_fen']
      move,meta=M.search(e,b.copy(stack=True),deadline,stop)
      rows.append(dict(profile=arm,weights=w,alignment=aligned,root_id=root['id'],move=move.uci(),metadata=meta,leaf_probes=probes,table_ack=ack))
    finally:e.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
 out=dict(complete=complete,rows=rows,wall_seconds=time.monotonic()-started,declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),binary_sha256=d['binary_sha256'])
 if not complete:out['error']=error
 A.atomic_json(O/'result.json',out);summary=dict(complete=complete,searches=len(rows),wall_seconds=out['wall_seconds'],pairs=[])
 if complete:
  for arm in d['profiles']:
   for root in d['roots']:
    pair=[next(x for x in rows if x['profile']==arm and x['root_id']==root['id'] and x['alignment']==align) for align in (2,3)]
    summary['pairs'].append(dict(profile=arm,root_id=root['id'],actions=[x['move'] for x in pair],same_action=pair[0]['move']==pair[1]['move'],reported_nodes=[x['metadata']['reported_nodes'] for x in pair],depth=[x['metadata']['reported_depth'] for x in pair]))
  summary['changed_actions']=sum(not p['same_action'] for p in summary['pairs'])
 A.atomic_json(O/'summary.json',summary);print(json.dumps(summary,indent=2));return 0 if complete else 3
if __name__=='__main__':
 if sys.argv[1:]==['freeze']:freeze()
 else:sys.exit(execute())
