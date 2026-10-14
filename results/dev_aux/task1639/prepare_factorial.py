from pathlib import Path
import json
R=Path.cwd();O=R/'results/dev_aux/task1655';O.mkdir(exist_ok=False);old=json.loads((R/'results/dev_aux/task1651/plan.json').read_bytes());sel=json.loads((R/'results/dev_aux/task1652/selection.json').read_bytes())['selected']['POOLED']
plan={'status':'FROZEN_2X2_SEARCH_OPPONENT_FACTORIAL_BEFORE_NEWQUERIES','families':[f for f in old['families'] if f['phase']=='DEV'],'profiles':[(720,720,720),sel],'search_nodes':[64,4096],'opponents':['UNIFORM','TACTICAL50'],'H':48,'seeds_per_color':4,'single_seconds':2800,'max_new_go':120000,'expected_seconds':1200,'binary':old['binary'],'binary_sha256':old['binary_sha256'],'variant_ini':old['variant_ini'],'no_mate_proof':'task1649','selection':'Fixed1652POOLEDphysicalTRAIN endpoint; noDEVselection. ExistingDEV exposedmechanism, notfreshgeneralization holdout.','tactical_policy':'Eachopponentmove uniformwithprob1/2, otherwise uniformamonglexmax(immediatephysicalmate, avoidownmateinone, checkingopponent, capturecount1). No materialprices. One uniformu selectsmixturebranch, conditional2u mod1 chooseslist, fulllegalmovespreserved.','objective':'PhysicalwinbyH-minusphysicallossbyH, rule-no-mateDrawstop, UNKNOWNseparateinfinitepayoffbounds. Budget/opponentgain interactions; no all-defenseproof/fullgamehumanvalue claim.','reuse':'Exact64UNIFORMgames from1652 DEV reused byteprovenance; coldquerycache keyed(nodes,R,N,B,state), 4096neveraliases64. No unchangedgame rerun. Allnew/failedrawruns preserved; nocapextension.'}
(O/'plan.json').write_text(json.dumps(plan,indent=2))
s=(R/'results/dev_aux/task1639/physical_train.py').read_text(encoding='utf-8-sig')
s=s.replace("task1652'","task1656'").replace('task1651/plan.json','task1655/plan.json').replace('deadline=start+1800','deadline=start+2800').replace('queries<180000','queries<120000').replace("'seconds_cap':1800,'max_go':180000","'seconds_cap':2800,'max_go':120000")
s=s.replace("sorted((R/'results/dev_aux/task1644').glob('*choices.jsonl'))","sorted((R/'results/dev_aux/task1644').glob('*choices.jsonl'))+sorted((R/'results/dev_aux/task1652').glob('*choices.jsonl'))")
s=s.replace("key=tuple(x['price']),tuple(x['state'])","key=64,tuple(x['price']),tuple(x['state'])").replace("T.fen(key[1])==x['position']","T.fen(key[2])==x['position']").replace("T.moves(key[1])","T.moves(key[2])")
s=s.replace('def choose(s,price):','def choose(s,price,nodes):').replace('(price,s) in cache','(nodes,price,s) in cache').replace("cache[price,s]","cache[nodes,price,s]").replace("e.send('go nodes 64')","e.send('go nodes '+str(nodes))").replace("'command':'go nodes 64'","'command':'go nodes '+str(nodes),'nodes':nodes").replace("'event':'SEND_INTENT','price':price","'event':'SEND_INTENT','nodes':nodes,'price':price").replace("'event':'SENT','price':price","'event':'SENT','nodes':nodes,'price':price")
s=s.replace('def evaluate(price,phase,families,seeds,H):','def evaluate(price,phase,families,seeds,H,nodes,opponent):')
s=s.replace('choose(s,price) if len(ll)>1','choose(s,price,nodes) if len(ll)>1')
s=s.replace("else:move=ll[min(int(u*len(ll)),len(ll)-1)][0]", """else:
      choices=ll;quantile=u
      if opponent=='TACTICAL50' and u<.5:
       scored=[]
       for m,t in ll:
        replies=T.moves(t);mate=not replies and T.attacked(t,t[4*t[8]],1-t[8]);losing=any(not T.moves(q) and T.attacked(q,q[4*q[8]],1-q[8]) for a,q in replies)
        score=(int(mate),int(not losing),int(T.attacked(t,t[4*t[8]],1-t[8])),int(sum(z!=16 for z in t[:8])<sum(z!=16 for z in s[:8])));scored.append((score,m,t))
       best=max(a for a,m,t in scored);choices=[(m,t) for a,m,t in scored if a==best];quantile=2*u
      elif opponent=='TACTICAL50':quantile=2*u-1
      move=choices[min(int(quantile*len(choices)),len(choices)-1)][0]""")
s=s.replace("row={'price':price","row={'nodes':nodes,'opponent':opponent,'price':price")
s=s.replace("out={'price':price","out={'nodes':nodes,'opponent':opponent,'price':price")
start=s.index(" for phase in ['TRAIN1','TRAIN2']:")
end=s.index("except BaseException",start)
s=s[:start]+""" oldgames=[json.loads(line) for line in (R/'results/dev_aux/task1652/games.jsonl').open()]
 for nodes in plan['search_nodes']:
  for opponent in plan['opponents']:
   for price in map(tuple,plan['profiles']):
    phase=str(nodes)+'_'+opponent
    if nodes==64 and opponent=='UNIFORM':
     rows=[dict(x,nodes=64,opponent='UNIFORM',phase=phase,reused_game=True,source='task1652') for x in oldgames if tuple(x['price'])==price and x['phase']=='DEV']
     assert len(rows)==1024
     for x in rows:gf.write(json.dumps(x)+'\\n')
     gf.flush();z={'nodes':nodes,'opponent':opponent,'price':price,'phase':phase,'H':48,'games':1024,'lower':sum(x['lower'] for x in rows)/1024,'upper':sum(x['upper'] for x in rows)/1024,'finite_net':sum(x['payoff'] or 0 for x in rows)/1024,'categories':dict(collections.Counter(x['category'] for x in rows)),'reused_game':True};dev.append(z);print(z,flush=True)
    else:dev.append(evaluate(price,phase,plan['families'],4,48,nodes,opponent))
"""+s[end:]
s=s.replace("plan['opponent']+'; '+plan['labels']","plan['objective']")
(R/'results/dev_aux/task1639/factorial.py').write_text(s,encoding='utf8')
print('FACTORIAL_FIXED_PRICES',plan['profiles'])

