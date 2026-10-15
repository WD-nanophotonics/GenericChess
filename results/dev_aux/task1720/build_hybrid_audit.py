from pathlib import Path
import ast,json,datetime
R=Path.cwd();s=(R/'results/dev_aux/task1720/audit_learning.py').read_text(encoding='utf-8-sig');s=s.replace('import json,ast,importlib.util,collections,random,time,functools,hashlib','import json,ast,importlib.util,collections,random,time,functools,hashlib,array')
pos=s.index("assert hashlib.sha256((R/plan['model'])")
seed=r'''
wdl=(R/plan['rank_wdl']).read_bytes();rank=array.array('H');rank.frombytes((R/plan['rank_dtm']).read_bytes());rp=json.loads((R/plan['rank_proof']).read_bytes());assert hashlib.sha256(wdl).hexdigest()==rp['wdl_sha256'] and hashlib.sha256(rank.tobytes()).hexdigest()==rp['rank_sha256']
assert json.loads((R/'results/dev_aux/task1749/result.json').read_bytes())['status']=='PASS_EXHAUSTIVE_INDEPENDENT_KRK_RULE_EQUIVALENCE'
def table(s):
 ps=[v for v in s[:-1] if v not in('.','K','k')]
 if len(ps)!=1 or ps[0].upper()!='R':return None
 owner=int(ps[0].islower());n=tuple(v.swapcase() for v in s[:-1])+(1-s[-1],) if owner else tuple(s);k=n[:-1].index('K');b=n[:-1].index('k');r=n[:-1].index('R');i=(((k*64+b)*64+r)*2+n[-1]);assert wdl[i]!=255
 return dict(id=i,owner=owner,R_turn=n[-1]==0,wdl=wdl[i],DTM=rank[i])
old=R/f"results/dev_aux/task{plan['source_native_run']}"
assert hashlib.sha256((old/'choices.jsonl').read_bytes()).hexdigest()==plan['reused_native_choice_sha256']
assert json.loads((R/f"results/dev_aux/task{plan['source_native_audit']}/result.json").read_bytes())['status'].startswith('PASS')
oldplan=json.loads((old/'start.json').read_bytes())['plan'];assert all(plan[k]==oldplan[k] for k in ('model_sha256','binary_sha256','variant_sha256','candidate_nodes','opponents'))
for x in map(json.loads,(old/'choices.jsonl').open()):
 assert tuple(x['domain'])==domain;cache[domain,x['nodes'],tuple(x['price']),tuple(x['state'])]=x['move']
assert len(cache)==run['old_paid_choice_cache_entries']
tabletrace=[json.loads(l) for l in (D/'table_choices.jsonl').open()];tableindex=0
'''
s=s[:pos]+seed+s[pos:]
oldline="  assert step['move']==(cache[domain,n,pp,s] if len(ll)>1 else ll[0][0]);visited.append(s);s=dict(ll)[step['move']];cc['plies']+=1;cc['promotions']+=len(step['move'])==5"
newline="""  assert x['policy_id']==plan['policy_id']
  if step['policy_source']=='EXACT_KRK_RANK_MOVE':
   parent=table(s);assert parent and parent['R_turn'] and parent['wdl']==1;eligible=[]
   for u,t in ll:
    child=table(t);assert child
    if child['wdl']==2 and child['DTM']==parent['DTM']-1:eligible.append(u)
   assert step['move']==min(eligible) and tabletrace[tableindex]==dict(state=list(s),move=step['move'],parent=parent,eligible=eligible);tableindex+=1;cc['tablemoves']+=1
  else:
   assert step['policy_source']==('NATIVE' if len(ll)>1 else 'FORCED')
   assert step['move']==(cache[domain,n,pp,s] if len(ll)>1 else ll[0][0])
  visited.append(s);s=dict(ll)[step['move']];cc['plies']+=1;cc['promotions']+=len(step['move'])==5"""
assert oldline in s;s=s.replace(oldline,newline)
a=s.index("if run['TRAIN']:")
replace="""assert tableindex==len(tabletrace)==run['table_moves']
scores={tuple(p):sum(x['payoff'] or 0 for x in groups[tuple(p),'TRAIN']) for p in plan['prices']}
assert len(run['TRAIN'])==len(plan['prices'])
sel={'POOLED':min(scores,key=lambda p:(-scores[p],p)),'FIXED_NATIVE':tuple(plan['fixed_native_candidate'])}
assert sel=={k:tuple(v) for k,v in run['selected'].items()}
expected=set(sel.values())|{tuple(plan['baseline'])};devphase='DEV'
assert {p for p,ph in groups if ph==devphase}==expected
assert len(games)==run['actual_games'] and cc['new_reported_nodes']==run['actual_reported_nodes']
"""
bad=s[:a]+replace+s[s.index("rng=random.Random",a):]
F=R/'results/dev_aux/task1750';F.mkdir(exist_ok=False);(F/'reconstructed_failed_generated_candidate.py').write_text(bad)
try:ast.parse(bad);raise AssertionError('expectedfailedbuilder')
except IndentationError as ex:(F/'failure.json').write_text(json.dumps(dict(status='PREEXECUTION_AST_BUILDER_FAILURE_REPRODUCED',error=str(ex),cause='Unanchoredrngsubstring matchedprnginLatininitializer instead ofbootstrapsection.',impact='Failedcandidate notwritten/executed originally; noNative/game rerun. Thisreconstructedmemorycandidate saved now, notclaimedoriginalexecutionfile.',fix='Require newline-anchoredbootstrap section andASTbeforewriting/execution.'),indent=2))
b=s.index("\nrng=random.Random",a)+1;s=s[:a]+replace+s[b:]
s=s.replace("PASS_INDEPENDENT_ACTOR_PV_ALL_EXCHANGE_TRAJECTORIES_ACK_DOMAIN_CYCLE_AND_SELECTION","PASS_HYBRID_PHYSICAL_PLAY_ALL_PV_RANK_ACTIONS_TERMINALS_AND_SELECTION").replace("Actualadaptiveproposal path reconstructed wherepresent; fixedpilotprice notfitted.","Rule rankchoosers verifiedeverymove; noKRK WDLadjudication; priorpaidNativecache boundchecked, actualnewNativework only. Exposedmechanismnotfreshholdout.")
ast.parse(s);(R/'results/dev_aux/task1720/audit_hybrid.py').write_text(s,encoding='utf-8')
h=R/'results/dev_aux/task1720/hybrid.py';z=h.read_text(encoding='utf-8-sig').replace("p=json.loads((R/'results/dev_aux/task1747/plan.json').read_bytes())","p=json.loads((R/sys.argv[1]).read_bytes())").replace("d=Hybrid(p,R/'results/dev_aux/task1748')","d=Hybrid(p,R/sys.argv[2])")
z=z.replace(" score={tuple(z['price']):sum(x['payoff'] or 0 for x in d.rows if x['phase']=='TRAIN' and x['price']==z['price']) for z in train}\n # d.rows price is a tuple; keep exact normalized comparison.\n","")
z=z.replace("try:\n d.start_engine()","try:\n assert json.loads((R/'results/dev_aux/task1749/result.json').read_bytes())['status']=='PASS_EXHAUSTIVE_INDEPENDENT_KRK_RULE_EQUIVALENCE'\n d.start_engine()")
ast.parse(z);h.write_text(z,encoding='utf-8');print('CORRECTED_HYBRID_AND_AUDIT_AST_PASS')

