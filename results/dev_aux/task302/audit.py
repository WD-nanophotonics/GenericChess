import json,time,hashlib,importlib.util
from pathlib import Path
import numpy as np
import chess
R=Path.cwd();O=R/'results/dev_aux/task302';O.mkdir(exist_ok=False);D=json.loads((R/'results/dev_aux/task301/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task301/result.json').read_bytes());T=json.loads((R/'results/dev_aux/task258/tree.json').read_bytes());assert X['complete'];start=time.monotonic();TAG='$dev_aux_constant_telemetry_v1'
def hook(d):
 if set(d)=={TAG}:z=d[TAG];return [z['value']]*z['count']
 return d
X=json.loads((R/'results/dev_aux/task301/result.json').read_bytes(),object_hook=hook);packs={}
for t in T['roots']:
 feats=[];terminal=[];mask=[];bst=[];blen=[];ast=[];alen=[];actions=[]
 for a in t['actions']:
  ast.append(len(bst));actions.append(a['move']);alen.append(len(a['branches']))
  for br in a['branches']:
   bst.append(len(feats));ld=[br['terminal']] if 'terminal' in br else [ch['leaf'] for ch in br['children']];blen.append(len(ld))
   for v in ld:feats.append(v.get('vector',[0]*5));terminal.append(v.get('terminal',0));mask.append('terminal' in v)
 F=np.array(feats,dtype=np.int64);K=np.array(mask,dtype=bool);F[K]=0
 packs[t['root']]=dict(F=F,term=np.array(terminal,dtype=np.int64),mask=K,bs=np.array(bst),bl=np.array(blen),as_=np.array(ast),al=np.array(alen),actions=actions)
def evaluate(p,w):
 leaf=p['F']@np.array([w[k] for k in 'PNBRQ'],dtype=np.int64);leaf[p['mask']]=p['term'][p['mask']];bv=np.maximum.reduceat(leaf,p['bs']);av=np.minimum.reduceat(bv,p['as_']);best=int(av.max());return best,dict(zip(p['actions'],map(int,av))),leaf,bv,av
# Exact one-sided directional derivatives of this finite max/min tree: lexicographic (basevalue,slope).
def slopes(p,leaf,bv,av,sign):
 ss=sign*p['F'];ss=np.where((leaf==np.repeat(bv,p['bl']))[:,None],ss,-10**9);bd=np.maximum.reduceat(ss,p['bs'],axis=0);bd=np.where((bv==np.repeat(av,p['al']))[:,None],bd,10**9);ad=np.minimum.reduceat(bd,p['as_'],axis=0);return (sign*ad[av==av.max()].max(axis=0)).tolist()
checks=[];points=[]
for case in X['cases']:
 f=next(f for f in D['roots'] if f['id']==case['root']);p=packs[case['root']];base=case['variants']['base'];baseval,scores,leaf,bv,av=evaluate(p,case['weights']);dp=slopes(p,leaf,bv,av,1);dm=slopes(p,leaf,bv,av,-1);basevec=None
 for var,z in case['variants'].items():
  best,aa,_,_,_=evaluate(p,z['weights']);raw=z['result'];assert raw['score']==best and aa[z['action']]==best and raw['completed_depth']==3 and not raw['used_fallback']
  b=chess.Board(f['initial_fen'])
  for text in f['history']:b.push_uci(text)
  actor=b.turn;pv=[]
  for a in raw['principal_variation']:
   fr=a['from_square'];to=a['to_square'];text=chess.square_name(chess.square(fr['file'],fr['rank']))+chess.square_name(chess.square(to['file'],to['rank']))+(a.get('promotion_target_id') or '').lower();m=chess.Move.from_uci(text);assert m in b.legal_moves;b.push(m);pv.append(text)
  oo=b.outcome(claim_draw=False) if b.is_checkmate() or b.is_stalemate() else None;vec=[len(b.pieces(i+1,actor))-len(b.pieces(i+1,not actor)) for i in range(5)];literal=(0 if oo.winner is None else 100000000-len(pv) if oo.winner==actor else -100000000+len(pv)) if oo is not None else sum(z['weights'][k]*v for k,v in zip('PNBRQ',vec));assert raw['score']==literal and (len(pv)==3 or oo is not None)
  if var=='base':basevec=[0]*5 if oo is not None else vec
  checks.append(dict(root=case['root'],profile=case['profile'],variant=var,score=best,action=z['action'],PV_leaf=literal,historical=z['historical']))
 assert basevec is not None
 axes=[]
 for i,k in enumerate('PNBRQ'):
  plus=case['variants'][k+'+'];minus=case['variants'][k+'-'];fdp=plus['result']['score']-baseval;fdm=baseval-minus['result']['score'];axes.append(dict(piece=k,PV_branch_slope=basevec[i],exact_positive_directional=dp[i],exact_negative_directional=dm[i],oneunit_positive=fdp,oneunit_negative=fdm,nondifferentiable=dp[i]!=dm[i],PV_matches_both_exact=basevec[i]==dp[i]==dm[i],PV_matches_both_oneunit=basevec[i]==fdp==fdm,action_changes_plus=plus['action']!=base['action'],action_changes_minus=minus['action']!=base['action']))
 points.append(dict(root=case['root'],profile=case['profile'],base_score=baseval,base_action=base['action'],PV_slope=basevec,axes=axes))
out=dict(complete=True,actual_new_query_checks=sum(not z['historical'] for z in checks),historical_base_checks=sum(z['historical'] for z in checks),all_exact_score_action_PV_checks=len(checks),points=len(points),axes=sum(len(p['axes']) for p in points),exact_nondifferentiable_axes=sum(a['nondifferentiable'] for p in points for a in p['axes']),exact_PV_gradient_mismatch_axes=sum(not a['PV_matches_both_exact'] for p in points for a in p['axes']),oneunit_PV_slope_mismatch_axes=sum(not a['PV_matches_both_oneunit'] for p in points for a in p['axes']),details=points,checks=checks,seconds=time.monotonic()-start,proof='Finite tree leaves affinew orweightindependentterminal. For direction+e_i, leavespair(basevalue,slope_i); max/min lexicographic pair propagation givesexactrightderivative for sufficientlysmallpositiveepsilon. Direction-e_i usesnegativeleafslopes andnegatesthe finalderivative. Equalityofright/leftrequired fordifferentiabilityalongaxis. CanonicalchosenPV maygiveonlyonebranchslope at ties. NumPyint64 hasatmost1e8 terminal/finiteprice, exactintegerarithmetic/nooverflow inthisdeclaredscope.',scope='204newNative+16qualifiedreused base exactchecks;20oldcapturestates/prices, no training/adoption/humanfit. Nondifferentiabilityoroneunitbreakpoint isnotitselfproofTDLeaf fails orallfixedpricesimpossible. Thisiscompleteq0; matureselective cp neednot equalPVleaf (old210/208 remains).')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('details','checks')},indent=2))