"""Freeze all eligible return-prediction profiles and new reachable-root deployment."""
import json,hashlib,importlib.util
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task179';O.mkdir(exist_ok=True)
if (O/'declaration.json').exists():raise FileExistsError('frozen')
sp=importlib.util.spec_from_file_location('F179',R/'results/dev_aux/task166/freeze.py');F=importlib.util.module_from_spec(sp);sp.loader.exec_module(F)
fits=json.loads((R/'results/dev_aux/task173/analysis.json').read_bytes());assert fits['complete'];profiles={'unit':dict(P=208,N=208,B=208,R=208,Q=208,K=0)};exclusions=[]
for result in fits['results']:
 name=result['opponent']+'-'+('bounded' if result['target'].startswith('bounded') else 'quantity')
 if not result['all_positive_material_coefficients'] or result['Pnormalized'] is None:exclusions.append(dict(profile=name,reason='nonpositive or undefined P'));continue
 w={k:round(208*result['Pnormalized'][k]) for k in 'PNBRQ'};w['K']=0
 if any(not 52<=w[k]<=3328 for k in 'NBRQ'):exclusions.append(dict(profile=name,reason='outside declared domain, no clipping',weights=w));continue
 profiles[name]=w
all_roots=[F.make(2026103000+i) for i in range(8)];roots=[r for r in all_roots if not r.get('excluded')];bad=[r for r in all_roots if r.get('excluded')];assert roots
D=dict(task_id='179',question='Do positive training-only return-regression material profiles yield actual short-policy gains on fresh roots?',profiles=profiles,excluded_profiles=exclusions,roots=roots,excluded_roots=bad,opponents=['random','unit2ply'],random_seeds=[2026203000+i for i in range(len(roots))],cap=16,games=len(roots)*4*len(profiles),planned_games=8*4*len(profiles),excluded_slots=len(bad)*4*len(profiles),deadline_seconds=180,binary_sha256='c378f0b3fc9f99d48e3089294a7c6adf5d5215bcac070200424d0d24f4d4b460',model_source_sha256=hashlib.sha256((R/'results/dev_aux/task173/analysis.json').read_bytes()).hexdigest(),root_rule='Exactlysame count-preserving20plyuniform legalnoncapture/nonpromotion prelude,8newfixedseeds; failbeforeoutputs excludedallarms/noresample; fullprelude+subsequenthistory retained.',profile_rule='All6fitmodel outputs, unitbaseline. Eligibility onlypositive/Pdefined/domain; Pnormalize/round mechanically, no humanreference, no choosebestheldout/error/profile. Predictionimprovement doesnotitself justifypolicygain.',reward='Unchanged Task104 true-terminal100+speed elseunitquantity15; boundedterminal1 andfinalquantity diagnostics separate; quantity-trained profiles keepthisrealoutcome distinction.',agent='c378mode3/1thread16MiB/go nodes1024;5actualleafprobes+exacttableack/resetpergame; oneengine, serialafter175.',cost='Atmost224actual16plygames estimated40–60s from84pilot14.547s;180sfuse, noadditionalengineworker/fees.',decision='Allpairedprofiles/opponents/components retained onfreshroots. Positivebenefit onlyscopeddeployment, notuniversalhumanprices; negative/zero returns retainprediction-vs-policy gap. No product promotion.',scope='Methodfamily exposed by169 and173, fresh geometry only; noindependentdiscovery orCore/Native/NNUEteacher labels.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8')
source=(R/'results/dev_aux/task166/run.py').read_text(encoding='utf-8').replace('task166','task179')
source=source.replace("for profile in ('learned','reversed'):","for profile in (p for p in d['profiles'] if p!='unit'):").replace("for oi in range(8):","for oi in range(len(d['roots'])):")
source=source.replace("d=json.loads((O/'declaration.json').read_bytes());","assert json.loads((R/'results/dev_aux/task175/status.json').read_bytes())['status']=='COMPLETE'\n d=json.loads((O/'declaration.json').read_bytes());")
compile(source,'run179','exec');(O/'run.py').write_text(source,encoding='utf-8')
print(json.dumps(dict(frozen=True,games=D['games'],profiles=len(profiles),roots=len(roots),excluded_slots=D['excluded_slots'])))
