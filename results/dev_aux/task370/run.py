import sys,json,time,hashlib,copy
from pathlib import Path
from fractions import Fraction
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G
O=R/'results/dev_aux/task370';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task364/declaration.json').read_text(encoding='utf-8'));control=json.loads((R/'results/dev_aux/task369/declaration.json').read_text(encoding='utf-8'));assert control['new_executable_sha256']==hashlib.sha256(A.EXE.read_bytes()).hexdigest();roots=[f for f in d['roots'] if f['phase']=='train'];axes=[2,3,4,5,6,7,9,10,11,12,13,14];decl={'initial_profiles':d['profiles'],'training_roots':roots,'development_roots_frozen_unread_outcomes':[f for f in d['roots'] if f['phase']=='development'],'axis_order':axes,'proposal_order':'base theneach axis half,double; int half tiesup, clip32..4096','max_rounds':2,'selection':'exactmeanFrozenGoal; firstmax base-firstties; stop firstnonstrictimprovement; otherwiseupdate thennext round; never extend2','cap':24,'nodes':1024,'fixed_opponent':d['profiles'][0]['weights'],'goal':d['goal'],'source_sha':d['source_sha'],'executable_sha256':control['new_executable_sha256'],'pilot_reuse':'exact16task369games; sameexecutable/queryconditions/root/color/goal; no changingtrajectory reuse','estimated_cost':'max800logical games, projected~1000s from20.375s/16gamecontrol;2400sfuse; no >1hour expected/run or extra workers','scope':'quantityproxy parameter optimization, no trueWDL/human recovery claim; see scoped boardonlyapprox; enteringKingexcluded; fixedthresholds remain'};(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8')
def ck(w,f,c):return json.dumps([w,f['initial_sfen'],f['history'],c,1024,24,d['goal'],decl['executable_sha256']],separators=(',',':'))
cache={}
for i,l in enumerate((R/'results/dev_aux/task369/games.jsonl').read_text(encoding='utf-8').splitlines()):
 g=json.loads(l);cache[ck(g['weights'],g['root'],g['color'])]=(g,{'file':'results/dev_aux/task369/games.jsonl','line':i+1})
rounds=[];ends=[];t0=time.monotonic();newgames=0;newgo=0;hits=0
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 eu=A.Engine(decl['fixed_opponent'],qj)
 try:
  for profile in d['profiles']:
   w=list(profile['weights']);start=list(w)
   for rd in range(2):
    candidates=[{'label':'base','weights':list(w)}]
    for axis in axes:
     for mode in ['half','double']:
      v=list(w);v[axis]=max(32,min(4096,(v[axis]+1)//2 if mode=='half' else v[axis]*2));candidates.append({'label':f'{axis}-{mode}','weights':v})
    cr=[]
    for ci,p in enumerate(candidates):
     v=p['weights'];missing=any(ck(v,f,c) not in cache for f in roots for c in (0,1));ec=A.Engine(v,qj) if missing else None;rs=[];refs=[]
     try:
      for f in roots:
       for c in (0,1):
        k=ck(v,f,c)
        if k in cache:g,ref=cache[k];hits+=1
        else:
         g=G.game(ec,eu,v,f,c,gj,deadline=t0+2400);newgames+=1;newgo+=len(g['queries']);ref={'file':'results/dev_aux/task370/games.jsonl','line':newgames};cache[k]=(g,ref)
        rs.append(g);refs.append(ref)
     finally:
      if ec:ec.close()
     score=sum((Fraction(g['goal']) for g in rs),Fraction())/len(rs);row={'label':p['label'],'weights':v,'mean_goal':str(score),'mean_quantity':str(sum(Fraction(g['raw_quantity']) for g in rs)/len(rs)),'true_rule_wins':sum(g['termination']['winner']==g['color'] for g in rs),'true_rule_losses':sum(g['termination']['winner'] is not None and g['termination']['winner']!=g['color'] for g in rs),'sources':refs};cr.append(row);print(profile['name'],rd,ci,p['label'],score,'new',newgames,'sec',round(time.monotonic()-t0),flush=True)
     (O/'progress.json').write_text(json.dumps({'rounds':rounds,'active_family':profile['name'],'active_round':rd,'candidates':cr,'new_games':newgames,'new_go':newgo,'cache_hits':hits,'seconds':time.monotonic()-t0},indent=2),encoding='utf-8')
    scores=[Fraction(x['mean_goal']) for x in cr];best=max(range(len(scores)),key=lambda i:scores[i]);rr={'family':profile['name'],'round':rd,'start_weights':list(w),'candidates':cr,'selected_index':best,'selected_label':cr[best]['label'],'strict_gain':str(scores[best]-scores[0])};rounds.append(rr)
    if scores[best]<=scores[0]:break
    w=list(cr[best]['weights'])
   ends.append({'family':profile['name'],'initial':start,'endpoint':w,'rounds_executed':rd+1,'stop':'no_strict_gain' if scores[best]<=scores[0] else 'max2rounds'})
 finally:eu.close()
endpoints={'frozen_before_anydevelopment_outcomes_or_humancomparison':True,'endpoints':ends,'rounds':rounds,'actual_new_games':newgames,'actual_new_go':newgo,'cache_hits':hits,'seconds':time.monotonic()-t0};(O/'endpoints.json').write_text(json.dumps(endpoints,indent=2),encoding='utf-8');print('ENDPOINTS',json.dumps({k:v for k,v in endpoints.items() if k!='rounds'}),flush=True)