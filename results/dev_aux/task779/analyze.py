import json,hashlib,copy,re
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task779'
for n in [775,778]:assert json.loads((R/f'results/dev_aux/task{n}/result.json').read_bytes())['status'].startswith('PASS_')
d=json.loads((R/'results/dev_aux/task769/execution_inputs.json').read_bytes());old=[json.loads(t) for t in (R/'results/dev_aux/task769/games.jsonl').open(encoding='utf-8')];new=[json.loads(t) for t in (R/'results/dev_aux/task777/games.jsonl').open(encoding='utf-8')];key=lambda g:(g['opponent'],tuple(g['weights']),json.dumps(g['root'],sort_keys=True),g['color']);allg={key(g):(g,dict(file=f'results/dev_aux/task{n}/games.jsonl',line=i)) for n,gs in [(769,old),(777,new)] for i,g in enumerate(gs,1)};assert len(allg)==448
planned=[(opp,tuple(p['weights']),json.dumps(f,sort_keys=True),c) for opp in d['opponents'] for p in d['profiles'] for pool in d['pools'] for f in pool['roots'] for c in [0,1]];assert set(planned)==set(allg)
# Partialold12queries vsactualnewfirstmissinggame non-time prefix equality, notreusepartialTT orclaimsoldgamecompleted.
raw=[json.loads(t) for t in (R/'results/dev_aux/task769/queries.jsonl').open(encoding='utf-8')];extra=raw[sum(len(g['queries']) for g in old):];assert len(extra)==12
for n in [360,364,381]:__import__('sys').path.insert(0,str(R/f'results/dev_aux/task{n}'))
import audit as V
def sem(q):
 x=V.bare(copy.deepcopy(q));x.pop('seconds',None);x['lines']=[re.sub(r'\b(?:nps|time) \d+',lambda m:m[0].split()[0]+' OMIT',s) for s in x['lines']];return x
assert [sem(q) for q in extra]==[sem(q) for q in new[0]['queries'][:12]]
by={}
for opp in d['opponents']:
 for p in d['profiles']:
  games=[allg[(opp,tuple(p['weights']),json.dumps(f,sort_keys=True),c)][0] for pool in d['pools'] for f in pool['roots'] for c in [0,1]]
  for name in p['names']:by[(opp,name)]=games
rows=[]
def state(g,cap):
 if len(g['actions'])<=cap and not g['termination']['kind'].startswith('cap'):
  w=g['termination']['winner'];return 'true_draw' if w is None else 'true_win' if w==g['color'] else 'true_loss'
 q=g['quantity12'] if cap==12 else g['quantity24'];return 'unfinished_more' if q>0 else 'unfinished_less' if q<0 else 'unfinished_equal'
def real(s):return (s=='true_win')-(s=='true_loss')
def proxy(s):return (s=='unfinished_more')-(s=='unfinished_less')
for opp in d['opponents']:
 for method in ['A','B','C']:
  for start in ['unit','random2514']:
   aa=by[(opp,start+'-initial')];bb=by[(opp,method+'-'+start+'-endpoint')];assert len(aa)==len(bb)==32 and [(g['root'],g['color']) for g in aa]==[(g['root'],g['color']) for g in bb]
   for cap in [12,24]:
    pairs=[(state(x,cap),state(y,cap)) for x,y in zip(aa,bb)];rd=[real(y)-real(x) for x,y in pairs];pd=[proxy(y)-proxy(x) for x,y in pairs];total=[r+p for r,p in zip(rd,pd)];qty=[F(y['quantity12' if cap==12 else 'quantity24']-x['quantity12' if cap==12 else 'quantity24'],19) for x,y in zip(aa,bb)];fam=sorted({g['root']['source_family'] for g in aa});rows.append(dict(opponent=opp,method=method,start=start,cap=cap,cells=32,real=str(F(sum(rd),32)),proxy=str(F(sum(pd),32)),sign=str(F(sum(total),32)),quantity=str(sum(qty)/32),enter_loss=sum(x!='true_loss' and y=='true_loss' for x,y in pairs),leave_loss=sum(x=='true_loss' and y!='true_loss' for x,y in pairs),masked_damage=[dict(family=aa[i]['root']['source_family'],color=aa[i]['color'],before=x,after=y) for i,(x,y) in enumerate(pairs) if (x=='true_win' and y=='unfinished_more') or (x=='unfinished_less' and y=='true_loss')],by_family=[dict(family=f,sign=str(F(sum(z for z,g in zip(total,aa) if g['root']['source_family']==f),2)),real=str(F(sum(z for z,g in zip(rd,aa) if g['root']['source_family']==f),2)),proxy=str(F(sum(z for z,g in zip(pd,aa) if g['root']['source_family']==f),2)),quantity=str(sum(z for z,g in zip(qty,aa) if g['root']['source_family']==f)/2)) for f in fam]))
out=dict(status='ALL448_ORIGINAL_CASES_ANALYSED_AFTER_SEPARATE_TECHNICAL_COMPLETION',rows=rows,original769_success=False,original769_fuse_failed_and_kept=True,complete_original_predeclared_case_list=True,closed_original_games=198,new_completion_games=250,unclosed_original_go=12,unclosed_vs_new12prefix_all_non_time_exact=True,source_sha256={str(n):{name:hashlib.sha256((R/f'results/dev_aux/task{n}'/name).read_bytes()).hexdigest() for name in ['games.jsonl','queries.jsonl','price_acks.json']} for n in [769,777]},new_go=0,scope='ALLpredetermined448logicalcases/NEW16families/7uniqueprices/2opponents reconstructedafterordinarytechnicalrecovery, no original120fuse-success/unexposed-budgetstatus restoration. Originalcohort conditionedonlyfixedsourceblindrootgenerator and frozenmodels, no selection/extra sample afterpartiallabels; exposure/failedbudgetretained. Old12unfinishedqueriesduplicateprefixcostcounted, no completedgame rerun. Independent geometry finitecase-scope notglobalIID/WDL/valueproof; allnegative/families/sixstates kept.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(opponent=x['opponent'],method=x['method'],start=x['start'],cap=x['cap'],real=x['real'],proxy=x['proxy'],sign=x['sign'],quantity=x['quantity'],enter=x['enter_loss'],masked=len(x['masked_damage'])) for x in rows if x['cap']==24]))
