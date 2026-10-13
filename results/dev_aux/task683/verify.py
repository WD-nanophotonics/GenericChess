from pathlib import Path
import json,math
R=Path.cwd();O=R/'results/dev_aux/task683';ref=json.loads((R/'results/dev_aux/task560/result.json').read_bytes())['source_prior'];axes=json.loads((R/'results/dev_aux/task634/declaration.json').read_bytes())['axes'];rows=[]
for t,label in [(635,'robustfast_materoots'),(646,'quantity_materoots'),(664,'quantity_joint_fullarmy'),(671,'quantity_coordinate_fullarmy')]:
 for e in json.loads((R/f'results/dev_aux/task{t}/endpoints.json').read_bytes())['endpoints']:
  for stage,w in [('initial',e['initial']),('endpoint',e['endpoint'])]:
   pairs=[dict(a=a,b=b,source_sign=(ref[a]>ref[b])-(ref[a]<ref[b]),candidate_sign=(w[a]>w[b])-(w[a]<w[b])) for i,a in enumerate([1,2,3,4,7,5,6]) for b in [1,2,3,4,7,5,6][i+1:]];rows.append(dict(route=label,start=e['start'],stage=stage,weights=w,base7_pair_ordering_agreements=sum(x['source_sign']==x['candidate_sign'] for x in pairs),base7_total_pairs=21,base7_ties=sum(x['candidate_sign']==0 for x in pairs),all_base_order_pairs=pairs,rook_below_or_equal_pawn=w[6]<=w[1],bishop_below_or_equal_pawn=w[5]<=w[1],promotions_with_negative_material_difference=[dict(base=a,promoted=b,base_price=w[a],promoted_price=w[b],delta=w[b]-w[a]) for a,b in [(1,9),(2,10),(3,11),(4,12),(5,13),(6,14)] if w[b]<w[a]],source_all12_logMSE=sum(math.log(w[a]/ref[a])**2 for a in axes)/12,source_base6_logMSE=sum(math.log(w[a]/ref[a])**2 for a in axes if a<8)/6))
old=json.loads((O/'result.json').read_bytes());assert rows==old['rows'];print('ALL16_MODEL_DESCRIPTORS_EXACT_RECOMPUTE_PASS')
