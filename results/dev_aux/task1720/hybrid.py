"""Physical KRK policy handoff, preserves Native prefix; no winning adjudication."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,time,importlib.util,array,hashlib,collections
R=Path.cwd();sp=importlib.util.spec_from_file_location('D',R/'results/dev_aux/task1720/driver.py');D=importlib.util.module_from_spec(sp);sp.loader.exec_module(D)
p=json.loads((R/sys.argv[1]).read_bytes());wdl=(R/p['rank_wdl']).read_bytes();rank=array.array('H');rank.frombytes((R/p['rank_dtm']).read_bytes());proof=json.loads((R/p['rank_proof']).read_bytes());assert hashlib.sha256(wdl).hexdigest()==proof['wdl_sha256'] and hashlib.sha256(rank.tobytes()).hexdigest()==proof['rank_sha256'] and proof['model_sha256']==p['model_sha256']
def lookup(s):
 ps=[v for v in s[:-1] if v not in('.','K','k')]
 if len(ps)!=1 or ps[0].upper()!='R':return None
 owner=int(ps[0].islower());n=tuple(v.swapcase() for v in s[:-1])+(1-s[-1],) if owner else tuple(s);k=n[:-1].index('K');b=n[:-1].index('k');r=n[:-1].index('R');i=(((k*64+b)*64+r)*2+n[-1]);assert wdl[i]!=255
 return dict(id=i,owner=owner,R_turn=n[-1]==0,wdl=wdl[i],DTM=rank[i])
class Hybrid(D.Driver):
 def __init__(self,plan,out):
  super().__init__(plan,out);self.tablefile=(out/'table_choices.jsonl').open('w');self.tablecalls=0
 def tablemove(self,s,ll):
  a=lookup(s)
  if a is None or not a['R_turn'] or a['wdl']!=1:return None
  eligible=[]
  for u,t in ll:
   b=lookup(t);assert b is not None
   if b['wdl']==2 and b['DTM']==a['DTM']-1:eligible.append(u)
  assert eligible;u=min(eligible);self.tablefile.write(json.dumps(dict(state=s,move=u,parent=a,eligible=eligible))+'\n');self.tablefile.flush();self.tablecalls+=1;return u
 def game(self,price,f,color,op,phase):
  s=tuple(f['roots'][color]);c=s[-1];path=[];visited={};pay=None;repeat=None
  for ply in range(self.plan['H']+1):
   self.guard();ll=self.T.moves(s)
   if not ll:
    pay=(-1 if s[-1]==c else 1) if self.T.attacked(s,self.T.king(s,s[-1]),1-s[-1]) else 0;cat='PHYSICAL_MATE' if pay else 'PHYSICAL_STALE';break
   if self.stockdraw(s):pay=0;cat='PROVED_SINGLE_STOCK_DRAW';break
   if s in visited:pay=0;cat='PROVED_POLICY_CYCLE_DRAW';repeat=[visited[s],ply];break
   if ply==self.plan['H']:cat='UNRESOLVED';break
   visited[s]=ply;own=s[-1]==c;pp=price if own else op['price'];nodes=self.plan['candidate_nodes'] if own else op['nodes']
   u=self.tablemove(s,ll) if len(ll)>1 else None
   if u is not None:policy='EXACT_KRK_RANK_MOVE'
   elif len(ll)>1:u=self.choose(s,pp,nodes);policy='NATIVE'
   else:u=ll[0][0];policy='FORCED'
   path.append(dict(state=s,move=u,own=own,policy_source=policy));s=dict(ll)[u]
  row=dict(price=price,phase=phase,family=f['family'],color=color,opponent=op['id'],opponent_price=op['price'],opponent_nodes=op['nodes'],root=f['roots'][color],H=self.plan['H'],trajectory=path,end=s,category=cat,payoff=pay,repeat=repeat,lower=-1 if pay is None else pay,upper=1 if pay is None else pay,policy_id=self.plan['policy_id']);self.log('games',row);self.rows.append(row);return row
 def close(self):
  self.tablefile.close();super().close()
d=Hybrid(p,R/sys.argv[2]);old=R/f"results/dev_aux/task{p['source_native_run']}";oldplan=json.loads((old/'start.json').read_bytes())['plan'];assert all(p[k]==oldplan[k] for k in ('model_sha256','binary_sha256','variant_sha256','candidate_nodes','opponents'));assert hashlib.sha256((old/'choices.jsonl').read_bytes()).hexdigest()==p['reused_native_choice_sha256'];assert json.loads((R/f"results/dev_aux/task{p['source_native_audit']}/result.json").read_bytes())['status'].startswith('PASS')
reused=0
for z in map(json.loads,(old/'choices.jsonl').open()):
 assert tuple(z['domain'])==d.domain;s=tuple(z['state']);assert z['move'] in dict(d.T.moves(s));d.cache[d.domain,z['nodes'],tuple(z['price']),s]=z['move'];reused+=1
train=[];dev=[];selected={};error=None
try:
 assert json.loads((R/'results/dev_aux/task1749/result.json').read_bytes())['status']=='PASS_EXHAUSTIVE_INDEPENDENT_KRK_RULE_EQUIVALENCE'
 d.start_engine()
 for price in sorted(map(tuple,p['prices'])):train.append(d.evaluate(price,'TRAIN'))
 score={price:sum(x['payoff'] or 0 for x in d.rows if x['phase']=='TRAIN' and tuple(x['price'])==price) for price in map(tuple,p['prices'])}
 selected['POOLED']=min(score,key=lambda q:(-score[q],q));selected['FIXED_NATIVE']=tuple(p['fixed_native_candidate'])
 (d.O/'selection.json').write_text(json.dumps(dict(selected=selected,integer_scores={str(q):v for q,v in score.items()}),indent=2))
 for price in sorted(set(selected.values())|{tuple(p['baseline'])}):dev.append(d.evaluate(price,'DEV'))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:d.close()
out=dict(status='COMPLETE' if error is None else 'PARTIAL_PRESERVED',error=error,actual_go=d.queries,old_paid_choice_cache_entries=reused,cache_hits=d.hits,table_moves=d.tablecalls,actual_reported_nodes=d.newnodes,seconds=time.perf_counter()-d.start,exit_code=d.e.p.poll() if d.e else None,TRAIN=train,DEV=dev,selected=selected,actual_games=len(d.rows),source_sha256=D.sha('results/dev_aux/task1720/hybrid.py'),scope='Physicaltablemoves afterKRK, notwinninglabels. Sameexposedrootsnewpolicy; oldNativechoicespaidpreviously andprefixreplayed, notfreshNativegamecostorindependentholdout.')
(d.O/'result.json').write_text(json.dumps(out,indent=2));print('FINAL',{k:v for k,v in out.items() if k not in ('TRAIN','DEV')})

