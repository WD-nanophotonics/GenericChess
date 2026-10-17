
"""All planned TRAIN cells, family clustering, fixed baseline and actual divergence mechanisms."""
from pathlib import Path
from collections import Counter
import json,time
import numpy as np
OUT=Path('results/dev_aux/task2486')
def run():
 t=time.perf_counter();f=Path('results/dev_aux/task2481');p=json.loads((f/'plan.json').read_text());slots=json.loads((f/'slots.json').read_text());games={g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())};ds=[json.loads(x)for x in(f/'decisions.jsonl').read_text().splitlines()];sel=json.loads(Path('results/dev_aux/task2482/selection.json').read_text());by={s['slot']:[d for d in ds if d['slot']==s['slot']]for s in slots};rows=[];arrays={}
 for row in sel['rows']:
  price=row['price'];blocks=[]
  for family in range(16):
   ss=[s for s in slots if s['root']==family and[s['ratio'],s['hand_ratio']]==price];assert len(ss)==2
   bb=[]
   for s in ss:
    g=games.get(s['slot']);v=None if g is None else g['reward'];bb.append((-1.,1.)if v is None else(v,v))
   blocks.append([sum(b[i]for b in bb)/2 for i in(0,1)])
  arrays[tuple(price)]=np.asarray(blocks)
  rows.append(dict(price=price,counts=row['counts'],bounds=row['bounds'],family_bounds=blocks))
 baseline=tuple(sel['baseline']);selected=tuple(sel['selected']);a=arrays[selected];b=arrays[baseline];lo=a[:,0]-b[:,1];hi=a[:,1]-b[:,0];rng=np.random.default_rng(862486);indices=rng.integers(0,16,size=(10000,16));gain=dict(mean_bounds=[float(lo.mean()),float(hi.mean())],per_family_bounds=np.stack((lo,hi),axis=1).tolist(),descriptive_family_bootstrap=[float(np.quantile(lo[indices].mean(axis=1),.025)),float(np.quantile(hi[indices].mean(axis=1),.975))])
 def choose(omit=None,initial=baseline):
  vals={k:np.delete(v,omit,axis=0).mean(axis=0)if omit is not None else v.mean(axis=0)for k,v in arrays.items()};eligible=[k for k,v in vals.items()if v[0]>vals[initial][1]];return min(eligible,key=lambda k:(-vals[k][0],k))if eligible else initial
 lofo=[dict(omitted_family=i,selected=list(choose(i)))for i in range(16)]
 starts=[dict(initial=list(x),closed_table_selected=list(choose(initial=x)))for x in arrays]
 pairs=[]
 if selected!=baseline:
  for family in range(16):
   for role in(0,1):
    ss=[next(s for s in slots if s['root']==family and s['candidate_color']==role and[s['ratio'],s['hand_ratio']]==list(price))for price in(baseline,selected)];gs=[games.get(s['slot'])for s in ss];first=None
    if all(g is not None for g in gs):
     for d,e in zip(by[ss[0]['slot']],by[ss[1]['slot']]):
      if d['choice']==e['choice']:continue
      assert d['root_record']==e['root_record']and d['root_state_sha']==e['root_state_sha']
      depths=[None if x['normal_receipt']is None else x['normal_receipt']['completed_depth']for x in(d,e)]
      first=dict(ply=d['ply'],sources=[d['source'],e['source']],normal_depths=depths,side=d['side'],candidate=d['is_candidate'],root_state_sha=d['root_state_sha'],choices=[d['choice'],e['choice']],classification='MATCHED_CANDIDATE_D4_PRICE_ACTION'if all(x['is_candidate']and x['source']=='FULL_SESSION_MATERIAL_SEARCH'and x['normal_receipt']['completed_depth']==4 for x in(d,e))else'PROOF_TIMING_CENSOR_OR_FOE_NOT_PURE_PRICE');break
    gain_pair=None if any(g is None or g['reward']is None for g in gs)else gs[1]['reward']-gs[0]['reward']
    entries=[sum(d['is_candidate']and d['source']in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY')for d in by[s['slot']])for s in ss]
    pairs.append(dict(family=family,role=role,slots=[s['slot']for s in ss],outcomes=[None if g is None else g['outcome']for g in gs],gain=gain_pair,first_divergence=first,candidate_verified_entries=entries))
 contexts=[]
 for family in range(16):
  for role in(0,1):
   ss=[s for s in slots if s['root']==family and s['candidate_color']==role];gg=[games.get(s['slot'])for s in ss];first=[next((d for d in by[s['slot']]if d['is_candidate']),None)for s in ss]
   outcomes=[None if g is None else g['outcome']for g in gg];closed=all(g is not None and g['reward']is not None for g in gg)
   records={json.dumps(g['record'],sort_keys=True)for g in gg if g is not None};initial_roots={d['root_state_sha']for d in first if d is not None}
   contexts.append(dict(family=family,role=role,prices=[[s['ratio'],s['hand_ratio']]for s in ss],outcomes=outcomes,all_six_returned_terminal=closed,distinct_actual_outcomes=len(set(outcomes))if closed else None,distinct_full_records=len(records),all_six_records_identical=closed and len(records)==1,first_candidate_shared_root=len(initial_roots)==1 and all(d is not None for d in first),first_candidate_choices=[None if d is None else d['choice']for d in first],first_candidate_sources=[None if d is None else d['source']for d in first]))
 depths=Counter((d['is_candidate'],d['normal_receipt']['completed_depth'])for d in ds if d['normal_receipt']is not None)
 r=dict(status='CLOSED_ALL_PLANNED_CANDIDATE_D4_FOE_D3_TRAIN_ANALYSIS',selected=list(selected),baseline=list(baseline),actual_games=len(games),planned_games=len(slots),unreturned=len(slots)-len(games),outcomes=dict(Counter(g['outcome']for g in games.values())),committed_moves=sum(g['plies']for g in games.values()),normal_depths=[dict(candidate=k[0],depth=k[1],count=v)for k,v in depths.items()],rows=rows,all32_contexts_six_price_information=contexts,price_sensitive_terminal_contexts=sum(x['all_six_returned_terminal']and x['distinct_actual_outcomes']>1 for x in contexts),price_invariant_identical_fullrecord_contexts=sum(x['all_six_records_identical']for x in contexts),selected_minus_baseline=gain,leave_one_family_out=lofo,all_six_start_closed_table_sensitivity=starts,first_divergence_pairs=pairs,actual_candidate_measured_seconds=sum(d['measured_seconds']for d in ds if d['is_candidate']),actual_foe_measured_seconds=sum(d['measured_seconds']for d in ds if not d['is_candidate']),actual_game_seconds=sum(g['seconds']for g in games.values()),seconds=time.perf_counter()-t,scope='ALL16TRAINfamilyblocks and192plannedslots. Missing/Uworstbounds, noignoringpartialcap. Sixfixedprices/Nboth1/CandidateD4vsfixedoldD3foe, actualterminalW-L only. LOFO/bootstrap/startstable are TRAINsensitivity, notselectonholdout/notindependentretraining/convergence/populationconfidence. No fresh8reservequeries regardlessselector. Moreproofentriesnotmediation/all-defenseWINlabels. Candidate12s/65536cost differsfromoldD3, notpurepricebenefit acrossdepths/no defaultadoption.')
 (OUT/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items()if k not in('first_divergence_pairs','all_six_start_closed_table_sensitivity','leave_one_family_out','all32_contexts_six_price_information')}))
if __name__=='__main__':run()
