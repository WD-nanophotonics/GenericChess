from pathlib import Path
import json,ast,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1695'
plan=json.loads((R/'results/dev_aux/task1677/plan.json').read_bytes());plan.update(status='FROZEN_COMPLETE_DEPTH3_CANDIDATE_SEARCH_CONTROL',candidate_search='Completefullwidthnegamax depth3, terminalbeforeleaf, samepurematerialprices, lexfirsttie, noq/SEE/heuristicpruning. Exactprice-state-depthsubvaluecache capped120000entries, priceindependentlegalcachecapped60000. FixedopponentactualNativecold64 unit720 asbefore. Differentworkconditions, notsamebudgetcausalclaim.',depth=3,max_expanded=4000000,max_legal_children=30000000,expected_seconds=240,seconds_cap=1200,max_go=30000,cache='Nativeopunit720qualifedON4choices mayreuse1678, fullsearchnewprice/state/depthcache noNativeownchoicesreuse.',primary_selector='Same12grid TRAIN1/2 andPOOLED truepolicyWDL finite96, lexprice tie; DEV selectedendpoints+baseline+fixedoriginalNativeTRAINcandidate1440/720/720/360, noDEVselection.',labels='Actualterminal,barekingsDraw,repeatedfullstate underfixedcompleteD3candidate andcachedNativeunit64opcycleDraw; UNKNOWNby96 independentbounds. Nooraclewinninglabels/quantityreward.',fixed_native_candidate=[1440,720,720,360])
(O/'plan.json').write_text(json.dumps(plan,indent=2))
s=(R/'results/dev_aux/task1675/learn.py').read_text(encoding='utf-8-sig').replace("task1678'","task1696'").replace('task1677/plan.json','task1695/plan.json');s=s.replace("cache={};queries=0;hits=0;","cache={};queries=0;hits=0;own_cache={};legal_cache={};sub_cache={};expanded=0;legal_children=0;full_hits=0;own_calls=0;")
s=s.replace("BASE=tuple(plan['baseline'])","""BASE=tuple(plan['baseline'])
for oldline in (R/'results/dev_aux/task1678/choices.jsonl').open():
 old=json.loads(oldline)
 if tuple(old['price'])!=BASE:continue
 s0=tuple(old['state']);assert old['fen']==T.fen(s0) and old['move'] in dict(T.moves(s0));cache[BASE,s0]=old['move']
of=(O/'full_choices.jsonl').open('w')
def legal(s):
 global legal_children
 if s in legal_cache:return legal_cache[s]
 ll=T.moves(s);legal_children+=len(ll);assert legal_children<=plan['max_legal_children']
 if len(legal_cache)<60000:legal_cache[s]=ll
 return ll
def reverse(v):return -v+1 if v>31000 else -v-1 if v<-31000 else -v
def full(s,d,price):
 global expanded,full_hits
 key=price,s,d
 if key in sub_cache:full_hits+=1;return sub_cache[key]
 expanded+=1
 if expanded%1024==0:P.stop();assert time.monotonic()<deadline and expanded<=plan['max_expanded']
 ll=legal(s)
 if not ll:out=(-32000 if T.attacked(s,T.king(s,s[16]),1-s[16]) else 0,None)
 elif T.bare(s):out=(0,None)
 elif d==0:
  weights=dict(zip('RNBP',price));v=sum((1 if p.isupper() else -1)*weights.get(p.upper(),0) for p in s[:16] if p!='.');out=(v if s[16]==0 else -v,None)
 else:
  vv=[(reverse(full(t,d-1,price)[0]),u) for u,t in ll];out=max(vv,key=lambda z:(z[0],tuple(-ord(c) for c in z[1])))
 if len(sub_cache)<120000:sub_cache[key]=out
 return out
def choose_full(s,price):
 global own_calls
 own_calls+=1;key=price,s
 if key in own_cache:return own_cache[key]
 before=expanded;before_hits=full_hits;v,u=full(s,plan['depth'],price);assert u in dict(legal(s));scores=[{'move':m,'score':reverse(full(t,plan['depth']-1,price)[0])} for m,t in legal(s)];assert u==min(scores,key=lambda z:(-z['score'],z['move']))['move'];of.write(json.dumps({'price':price,'state':s,'fen':T.fen(s),'move':u,'value':v,'depth':plan['depth'],'scores':scores,'new_expanded':expanded-before,'subcache_hits':full_hits-before_hits})+'\\n');of.flush();own_cache[key]=u;return u
""")
s=s.replace("u=choose(s,pp) if len(ll)>1 else ll[0][0]","u=(choose_full(s,pp) if s[16]==c else choose(s,pp)) if len(ll)>1 else ll[0][0]")
s=s.replace("sorted(set(selected.values())|{BASE})","sorted(set(selected.values())|{BASE,tuple(plan['fixed_native_candidate'])})")
s=s.replace("for f in (cf,gf,af,jf):f.close()","for f in (cf,gf,af,jf,of):f.close()")
s=s.replace("'selected':selected,'TRAIN':TRAIN","'own_calls':own_calls,'unique_full_choices':len(own_cache),'expanded_subproblems':expanded,'exact_subcache_hits':full_hits,'legal_children_generated':legal_children,'legal_cache_entries':len(legal_cache),'subcache_entries':len(sub_cache),'selected':selected,'TRAIN':TRAIN")
(O/'learn.py').write_text(s,encoding='utf8');ast.parse(s);print('FROZEN_FULL3',plan['max_expanded'],plan['seconds_cap'])
