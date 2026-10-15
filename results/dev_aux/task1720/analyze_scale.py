"""Observed common-scale causal policy pairs, fixed roots/opponents/budgets."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,collections,random,re
R=Path.cwd();O=R/'results/dev_aux/task1740';O.mkdir(exist_ok=False);D=R/'results/dev_aux/task1736';p=json.loads((D/'start.json').read_bytes())['plan'];games=[json.loads(l) for l in (D/'games.jsonl').open()];g={(tuple(x['price']),x['family'],x['color'],x['opponent']):x for x in games};bridge={(tuple(x['high']),x['family'],x['color']):x for x in json.loads((R/'results/dev_aux/task1733/records.json').read_bytes())};pairs=[];summaries=[];rng=random.Random(2026701541)
for high,low in p['scale_pairs']:
 high=tuple(high);low=tuple(low)
 for f in p['families']:
  for color in (0,1):
   for op in p['opponents']:
    a=g[high,f['family'],color,op['id']];b=g[low,f['family'],color,op['id']];ta=a['trajectory'];tb=b['trajectory'];i=0
    while i<min(len(ta),len(tb)) and ta[i]['move']==tb[i]['move']:assert ta[i]['state']==tb[i]['state'];i+=1
    same=i==len(ta)==len(tb);div=None
    if not same:
     assert i<len(ta) and i<len(tb) and ta[i]['state']==tb[i]['state'];div=dict(ply=i,state=ta[i]['state'],full_move=ta[i]['move'],half_move=tb[i]['move'])
    br=bridge[high,f['family'],color];rootfull=ta[0]['move'];roothalf=tb[0]['move'];vals=br['high_action_values']
    pairs.append(dict(high=high,low=low,family=f['family'],color=color,opponent=op['id'],same_trajectory=same,first_same_state_divergence=div,root_full=rootfull,root_half=roothalf,root_same=rootfull==roothalf,full_D3_value_fullmove=vals[rootfull],full_D3_value_halfmove=vals[roothalf],full_payoff=a['payoff'],half_payoff=b['payoff'],half_minus_full=b['payoff']-a['payoff'],full_category=a['category'],half_category=b['category']))
 for opid in ['MIXTURE']+[o['id'] for o in p['opponents']]:
  rows=[x for x in pairs if tuple(x['high'])==high and (opid=='MIXTURE' or x['opponent']==opid)];ids=sorted({x['family'] for x in rows});v={f:sum(x['half_minus_full'] for x in rows if x['family']==f)/sum(x['family']==f for x in rows) for f in ids};boot=[]
  for _ in range(10000):
   ff=rng.choices(ids,k=len(ids));boot.append(sum(v[f] for f in ff)/len(ff))
  boot.sort();summaries.append(dict(high=high,low=low,opponent=opid,pairs=len(rows),rootchanges=sum(not x['root_same'] for x in rows),trajectorychanges=sum(not x['same_trajectory'] for x in rows),improved=sum(x['half_minus_full']>0 for x in rows),worsened=sum(x['half_minus_full']<0 for x in rows),half_minus_full=sum(v.values())/len(v),family95=[boot[249],boot[9749]],root_D3_value_changes=sum(x['full_D3_value_fullmove']!=x['full_D3_value_halfmove'] for x in rows)))
oldgames=[json.loads(l) for l in (R/'results/dev_aux/task1723/games.jsonl').open() if json.loads(l)['phase'].startswith('TRAIN')];og={(tuple(x['price']),x['family'],x['color'],x['opponent']):x for x in oldgames};equalgames=0
for high,low in p['scale_pairs']:
 for f in p['families']:
  for color in (0,1):
   for op in p['opponents']:
    key=tuple(high),f['family'],color,op['id'];a=g[key];b=og[key];assert a['trajectory']==b['trajectory'] and a['payoff']==b['payoff'] and a['category']==b['category'];equalgames+=1
oldchoices={(x['nodes'],tuple(x['price']),tuple(x['state'])):x for x in map(json.loads,(R/'results/dev_aux/task1723/choices.jsonl').open())};matched=0
clean=lambda raw:[re.sub(r'\b(?:time|nps) \d+','TIME_OR_NPS',s) for s in raw]
for x in map(json.loads,(D/'choices.jsonl').open()):
 key=x['nodes'],tuple(x['price']),tuple(x['state'])
 if key in oldchoices:
  y=oldchoices[key];assert x['move']==y['move'] and clean(x['uci_info'])==clean(y['uci_info']);matched+=1
(O/'pairs.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in pairs));out=dict(status='PASS_FIXEDRATIO_SCALE_CHOICE_WDL_AND_CONFIG_REPLAY',summaries=summaries,fullscale_original_TRAIN_games_exact=equalgames,overlapping_cold_queries_raw_exact_except_time_nps=matched,actual_new_native_go=0,interpretation='Halvingall4prices preservesrelativevalues andcompleteD3argmax, butNativewholeconsumer can changeactions/WDL. Nominalnodesfixed, actualwork/depth canchange. Not proofwhichconstant causesit, not optimalWDL/materialoracle orhumanpriceclaim. Pairedfamily48, notrootopponent count independent. TRAINexposeddiagnostic, no scale fit.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

