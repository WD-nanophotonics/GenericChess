from pathlib import Path
import json
R=Path.cwd();O=R/'results/dev_aux/task1431';O.mkdir(exist_ok=False)
P=R/'results/dev_aux/task1421';cert=json.loads((R/'results/dev_aux/task1424/certificate.json').read_bytes());gs=[json.loads(x) for x in (P/'games.jsonl').read_text().splitlines()]
rows=[]
for row in cert['rows']:
 seed=row['root']['seed'];choices={}
 for arm in ['U_Shalf','U_Sone','U_Stwo','V_Shalf','V_Sone','V_Stwo']:
  gg=[g for g in gs if g['arm']==arm and g['root']['seed']==seed and g['opponent']=='unit_search' and g['color']==g['actions'][0]['actor']];assert len(gg)==1
  g=gg[0];q=g['queries'][0];lines=q['metadata']['uci_info'];last=next((line for line in reversed(lines) if ' depth ' in ' '+line+' ' and ' nodes ' in ' '+line+' '),None)
  choices[arm]=dict(move=g['actions'][0]['move'],last_info=last,exactD2=row['profiles'][arm],in_D2_opt=g['actions'][0]['move'] in row['profiles'][arm]['opt'])
 rows.append(dict(seed=seed,choices=choices))
changes={role:sum(x['choices'][role+'_Shalf']['move']!=x['choices'][role+'_Stwo']['move'] for x in rows) for role in ['U','V']}
out=dict(status='MATURE_SCALE_CHOICES_VS_EXACT_D2',roots=16,rows=rows,changed_half_to_two=changes,new_go=0,scope='ActualfreshTT4096nodes candidatefirst action onpredeclaredfirst16 matchedallscaleprofiles. D2optsetsameacrossunits; matureactionchanges cannotattributeonly214/pruning, also nativeleaf/calibration/budget selective. D2membership ismechanism label notlongtermquality.')
(O/'result.json').write_text(json.dumps(out,indent=2));print('CHANGES',changes);print([{k:v for k,v in x.items() if k!='choices'} for x in rows if any(x['choices'][role+'_Shalf']['move']!=x['choices'][role+'_Stwo']['move'] for role in ['U','V'])])
