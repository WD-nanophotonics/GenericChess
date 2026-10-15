from pathlib import Path
import json,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1732';O.mkdir(exist_ok=False)
p=json.loads((R/'results/dev_aux/task1719/plan.json').read_bytes());C=tuple(json.loads((R/'results/dev_aux/task1723/selection.json').read_bytes())['selected']['POOLED']);B=tuple(p['baseline'])
pairs=[(B,tuple(v//2 for v in B)),(C,tuple(v//2 for v in C))];profiles=sorted({q for pair in pairs for q in pair});names={str(q):'aux53scale_'+'_'.join(map(str,q)) for q in profiles};ini=(R/'results/dev_aux/task1688/variant.ini').read_text()
for q,n in names.items():
 r,nv,b,pv=eval(q,{'__builtins__':{}});v=f'p:{pv} n:{nv} b:{b} r:{r} q:1664';ini+=f'\n[{n}:aux_pawn8]\npieceValueMg = {v}\npieceValueEg = {v}\n'
(O/'variant.ini').write_text(ini,encoding='ascii');families=[]
for f in p['families']:
 if f['phase'].startswith('TRAIN'):families.append(dict(f,phase='SCALE_CONTROL',origin_phase=f['phase']))
p.update(status='FROZEN_RATIO_PRESERVING_GLOBAL_SCALE_CONTROL',families=families,root_exclusions=[1692,1702],root_kind='PRESSURE_RNP',fixed_profiles=profiles,scale_pairs=pairs,variant_ini='results/dev_aux/task1732/variant.ini',variant_sha256=hashlib.sha256((O/'variant.ini').read_bytes()).hexdigest(),variant_names=names,seconds_cap=600,max_go=24000,expected_seconds=180,selector='Fixedunitratio and53pooledTRAINratio at scales1and1/2, no newtraining/scale winner. ALL48exposedTRAINfamilies, bothcolorsandfixedop64/4096, 768games.',objective='Do identical relative4piece ratios produce differentNative actions/actualWDL under fixed4096budget becausefixed searchconstants/consumer scale? Opponentalwaysfullunit720; notscaled. No resourceparity/uniqueleaf-cause claim.',scope='Matchedrelativepricecontrol onpreviouslyexposedTRAINonly; no freshholdout. Materialleafclamp inactive atthis3nonkingstock; compare completeD3 scale-invariant argmax onall96roots as ordinalbridge, notoptimalWDL.',selection_source='Fixed1723/selection.json pooledTRAIN andunit only, noDEVfitting')
(O/'plan.json').write_text(json.dumps(p,indent=2));print('FROZEN_SCALE',profiles,len(families))

