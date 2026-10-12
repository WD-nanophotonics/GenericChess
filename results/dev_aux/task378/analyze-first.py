import json,math,time,statistics,hashlib
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task378';O.mkdir(exist_ok=True);t0=time.monotonic();ends=json.loads((R/'results/dev_aux/task370/endpoints.json').read_text(encoding='utf-8'));cache={}
def read(task):return [json.loads(x) for x in (R/'results/dev_aux'/f'task{task}'/'games.jsonl').read_text(encoding='utf-8').splitlines()]
for task in [369,370]:
 for g in read(task):cache[(tuple(g['weights']),g['root']['seed'],g['color'])]=g
roots=json.loads((R/'results/dev_aux/task364/declaration.json').read_text(encoding='utf-8'))['roots'];trainroots=[r for r in roots if r['phase']=='train']
def stats(gs):
 n=len(gs);mean=sum((Fraction(g['goal']) for g in gs),Fraction())/n;mate=Fraction(32*sum(0 if g['termination']['winner'] is None else 1 if g['termination']['winner']==g['color'] else -1 for g in gs),n);quantity=sum((Fraction(g['raw_quantity'],19) if g['termination']['kind']=='cap24' else Fraction(0) for g in gs),Fraction())/n;assert mean==mate+quantity;return {'games':n,'mean_goal':str(mean),'rule_contribution':str(mate),'cutoff_quantity_contribution':str(quantity),'mean_raw_quantity':str(sum(Fraction(g['raw_quantity']) for g in gs)/n),'wins':sum(g['termination']['winner']==g['color'] for g in gs),'losses':sum(g['termination']['winner'] is not None and g['termination']['winner']!=g['color'] for g in gs),'draws':sum(g['termination']['kind']=='fourfold_draw' for g in gs),'terminal_games':sum(g['termination']['kind']!='cap24' for g in gs)}
def compare(a,b):
 am={(g['root']['seed'],g['color']):g for g in a};bm={(g['root']['seed'],g['color']):g for g in b};assert am.keys()==bm.keys();ds=[Fraction(bm[k]['goal'])-Fraction(am[k]['goal']) for k in am];jack=[]
 for seed in sorted({k[0] for k in am}):
  vv=[Fraction(bm[k]['goal'])-Fraction(am[k]['goal']) for k in am if k[0]!=seed];jack.append({'removed_seed':seed,'mean_goal_delta':str(sum(vv,Fraction())/len(vv))})
 return {'initial':stats(a),'endpoint':stats(b),'mean_goal_delta':str(sum(ds,Fraction())/len(ds)),'mean_raw_quantity_delta':str(sum(Fraction(bm[k]['raw_quantity']-am[k]['raw_quantity']) for k in am)/len(am)),'positive_cells':sum(x>0 for x in ds),'negative_cells':sum(x<0 for x in ds),'zero_cells':sum(x==0 for x in ds),'identical_trajectories':sum(am[k]['actions']==bm[k]['actions'] for k in am),'leave_one_root_deltas':jack}
comparisons=[];panels={'training':None,'development1024':read(377),'development8192':read(380),'single_seed_neighbourhood1024':read(373)}
for p in ends['endpoints']:
 for name,gs in panels.items():
  if gs is None:
   a=[cache[(tuple(p['initial']),f['seed'],c)] for f in trainroots for c in (0,1)];b=[cache[(tuple(p['endpoint']),f['seed'],c)] for f in trainroots for c in (0,1)]
  else:a=[g for g in gs if g['weights']==p['initial']];b=[g for g in gs if g['weights']==p['endpoint']]
  comparisons.append({'family':p['family'],'panel':name,**compare(a,b)})
# Descriptive fixed mature-source prior, read only AFTERall endpoints frozen. Not humanholdout/fitting target.
ref=[0,90,315,405,495,855,990,540,0,540,540,540,540,945,1395,0];axes=[2,3,4,5,6,7,9,10,11,12,13,14];references=[]
for p in ends['endpoints']:
 references.append({'family':p['family'],'initial':p['initial'],'endpoint':p['endpoint'],'initial_log_ratio_MSE_to_Apery_source_prior':statistics.mean(math.log(p['initial'][i]/ref[i])**2 for i in axes),'endpoint_log_ratio_MSE_to_Apery_source_prior':statistics.mean(math.log(p['endpoint'][i]/ref[i])**2 for i in axes)})
rounds=[]
for rr in ends['rounds']:
 cand=rr['candidates'];sel=cand[rr['selected_index']];base=cand[0];rows=[]
 for c in cand:
  gs=[]
  for source in c['sources']:
   file=R/source['file'];ls=file.read_text(encoding='utf-8').splitlines();g=json.loads(ls[source['line']-1]);assert g['weights']==c['weights'];gs.append(g)
  st=stats(gs);assert st['mean_goal']==c['mean_goal'];assert st['mean_raw_quantity']==c['mean_quantity'];assert st['wins']==c['true_rule_wins'] and st['losses']==c['true_rule_losses'];rows.append({'label':c['label'],'stats':st})
 expected=max(range(len(cand)),key=lambda i:Fraction(cand[i]['mean_goal']));assert expected==rr['selected_index'];assert str(Fraction(sel['mean_goal'])-Fraction(base['mean_goal']))==rr['strict_gain'];rounds.append({'family':rr['family'],'round':rr['round'],'selected':sel['label'],'strict_gain':rr['strict_gain'],'all_candidates':rows,'interpretation':'rule +/-32 event has4mean units in8cells; price/quantity ranking separate, no rereselect'})
summary=[]
for task in [364,365,367,369,370,377,373,380]:
 file=R/'results/dev_aux'/f'task{task}'/('endpoints.json' if task==370 else 'result.json');d=json.loads(file.read_text(encoding='utf-8'));gs=read(task);summary.append({'task':task,'games':len(gs),'actual_go':sum(1 for _ in (file.parent/'queries.jsonl').open(encoding='utf-8')),'seconds':d['seconds'],'rule_terminal_games':sum(g['termination']['kind']!='cap24' for g in gs)})
result={'status':'PASS exactgoals/selection','seconds':time.monotonic()-t0,'comparisons':comparisons,'source_prior_reference':{'source':'fixedc1b80eaa source/evaluate.h Apery(WCSC26)materialenum; notindependenthumanconsensus','prices':ref,'read_for_descriptivecomparison_afterendpointfreeze':True,'rows':references},'rounds':rounds,'physical_cost_rows':summary,'physical_completed_games':sum(x['games'] for x in summary),'physical_journalled_go':sum(x['actual_go'] for x in summary),'physical_gameproducer_seconds':sum(x['seconds'] for x in summary),'other_go':'36110+36310 qualification,3601 smoke whosemetadata onlytooloutput;371/372/376price-state/SEEcallsNOTgo;379zero newgo/fits','decision':'Bothinitials improve training proxy, fail samebudget development anddo notapproachsourceprior. Higherbudgetresourcecurve changesoutcomes butdoesnotvalidatelearnedhumanvalues. Nearseedcohort raisesrealterminalfeedback, singlefamilycannot bevalidation; no addedrounds/reselection.'};(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'cost':summary,'comparisons':[{k:v for k,v in x.items() if k in ['family','panel','mean_goal_delta','mean_raw_quantity_delta']} for x in comparisons],'reference':references,'seconds':result['seconds']}),flush=True)