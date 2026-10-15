"""Package exact research source/evidence; preserve every original and failure."""
from pathlib import Path
import hashlib,json,zipfile,sys
OUT=Path('results/dev_aux');source={}
with zipfile.ZipFile(OUT/'SOURCE_REPRO_FINAL_20261015_58.zip') as base:
    for name in base.namelist():
        if not name.endswith('/') and name!='SOURCE_MANIFEST58.json':source[name]=base.read(name)
# Overlay exact current bytes, including old modules whose working newline
# bytes differ from Git normalization; ZIP bytes are execution-source authority.
for name in list(source):
    p=Path(name)
    if p.is_file():source[name]=p.read_bytes()
new=['scripts/generic_session_proof_player.py','scripts/generic_session_native_material.py','scripts/generic_session_win_proof_batch_pn.py','tests/development/test_generic_session_proof_player.py','tests/development/test_generic_session_batch_pn.py','results/dev_aux/task109/adapter.py']
for name in new:source[name]=Path(name).read_bytes()
for task in range(1822,1834):
    folder=OUT/f'task{task}'
    for p in folder.rglob('*'):
        if p.is_file() and p.suffix in ('.py','.json','.ini') and '__pycache__' not in p.parts:
            # Large actual calls/results are supplied in evidence, input/rule/
            # code/explicit before-fix snapshots remain in source closure.
            if p.name in ('rules.json','plan.json','qualification-plan.json','player_before_phase_receipts.py','failed_receipt_edit.py','original_pn.py') or p.suffix in ('.py','.ini'):
                source[p.as_posix()]=p.read_bytes()
evidence={}
for task in range(1822,1834):
    for p in (OUT/f'task{task}').rglob('*'):
        if p.is_file() and p.suffix in ('.json','.jsonl','.py','.ini') and '__pycache__' not in p.parts:evidence[p.as_posix()]=p.read_bytes()
for prefix in ('QA_','COST_','FAILURES_'):
    p=OUT/(prefix+'20261015_59.json');evidence[p.as_posix()]=p.read_bytes()
# Actual outgoing source/evidence content review: no local account exports or
# private paths/credentials. Public upstream attribution is retained separately.
for collection in (source,evidence):
    for name,data in collection.items():
        assert not name.startswith('.local_agent/') and '..' not in Path(name).parts
        for marker in json.loads(Path('.local_agent/publication_exclusions59.json').read_text()):
            assert marker.encode() not in data,name
manifest=[]
for label,files in [('SOURCE_REPRO_20261015_59.zip',source),('EVIDENCE_20261015_59.zip',evidence)]:
    members={name:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()) for name,data in sorted(files.items())}
    detail=dict(files=members,python=sys.version.split()[0],scope='Same-host independent source/test/witness/offline-audit restoration. Mature source and all-object rebuild separately packaged; binary/compiler external. Not fullNative learning rerun or fresh-machine/OS acceptance.',frozen_game_player_source='results/dev_aux/task1828/player_before_phase_receipts.py',current_player_adds_phase_receipts=True)
    with zipfile.ZipFile(OUT/label,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(files.items()):z.writestr(name,data)
        z.writestr('MANIFEST59.json',json.dumps(detail,indent=2).encode())
    with zipfile.ZipFile(OUT/label) as z:
        assert z.testzip() is None
        for name,row in members.items():assert hashlib.sha256(z.read(name)).hexdigest()==row['sha256']
    raw=(OUT/label).read_bytes();manifest.append(dict(path=label,files=len(files),bytes=len(raw),raw_bytes=sum(map(len,files.values())),sha256=hashlib.sha256(raw).hexdigest()))
engine=OUT/'task1831/MATERIAL_ENGINE_SOURCE_59.zip';manifest.append(dict(path=engine.relative_to(OUT).as_posix(),bytes=engine.stat().st_size,sha256=hashlib.sha256(engine.read_bytes()).hexdigest(),source_files=74,scope='Modified mature engine all-source build closure inclGPL attribution, no binary/compiler'))
(OUT/'ARCHIVE_MANIFEST_20261015_59.json').write_text(json.dumps(dict(status='SEALED_EXACT_BYTES',archives=manifest,private_layer_excluded=True,current_working_tests=221,restoration='PENDING'),indent=2),encoding='utf-8');print(json.dumps(manifest))
