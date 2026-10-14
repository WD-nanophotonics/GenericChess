from pathlib import Path
import json,hashlib,ast
R=Path.cwd();O=R/'results/dev_aux/task1420';p=json.loads((R/'results/dev_aux/task1415/study.json').read_bytes());binary=R/'.local_agent/leaf-rnb-46/fairy-leaf-rnb.exe';root=R/p['root_file']
d={k:p[k] for k in ['H','nodes','max_seconds','expected_seconds','root_file','expected_games','profiles','random_seed_base']}
d.update(root_sha256=hashlib.sha256(root.read_bytes()).hexdigest(),root_range=[0,64],root_count=64,binary=str(binary.relative_to(R)),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),opponents=dict(unit_search=720,uniform_random=None),scope='Frozen64 fixedratios commonleafscore units. task1416/plan.json inheritedgenerator metadata notruntime; study1415+thiscanonicalmanifest govern. Primary interaction ofpairedgain2vs.5, not DEVfit. NativeRNB720 teacherfixed, no pruningrewrite.')
(O/'manifest.json').write_text(json.dumps(d,indent=2));src=(O/'runner.py').read_text(encoding='utf-8-sig');ast.parse(src);assert 'devauxleafrnb {leafR} {leafN} {leafB}' in src and 'leafN=leafN' in src and 'nativeN 720' in src
print('CANONICAL_SCALE1536_FROZEN')
