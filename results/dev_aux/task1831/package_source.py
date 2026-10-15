"""Reconstruct the exact experimental material engine source closure.

No inherited precompiled objects. All text members have per-file SHA256; only
uci.cpp differs from the pinned alignment-order source snapshot. Compiler is an
explicit external dependency, retained raw build logs stay Git-ignored locally.
"""
from pathlib import Path
import hashlib,json,zipfile
OUT=Path('results/dev_aux/task1831')
def sha(data):return hashlib.sha256(data).hexdigest()
base=Path('.local_agent/alignment-order/source');old=json.loads(Path('results/dev_aux/task147/build.json').read_bytes());meta=json.loads(Path('results/dev_aux/task137/declaration.json').read_bytes())
contents={p.relative_to(base).as_posix():p.read_bytes() for p in base.rglob('*') if p.is_file()}
assert len(contents)==72
for row in old['sources']:assert sha(contents[row['source']])==row['sha256']
contents['uci.cpp']=Path('.local_agent/leaf-rnbp-46/source/uci.cpp').read_bytes()
assert sha(contents['uci.cpp'])==json.loads(Path('results/dev_aux/task1454/plan.json').read_bytes())['new_uci_sha256']
with zipfile.ZipFile('.local_agent/alignment-build/fairy-source.zip') as upstream:
    licenses=[n for n in upstream.namelist() if n.rsplit('/',1)[-1] in ('Copying.txt','COPYING','LICENSE','AUTHORS')]
    assert licenses
    for name in licenses:contents['LICENSES/'+name.rsplit('/',1)[-1]]=upstream.read(name)
# Check for this machine's private paths/account address before publication.
for name,data in contents.items():
    for marker in json.loads(Path('.local_agent/publication_exclusions59.json').read_text()):
        assert marker.encode() not in data,name
manifest=dict(upstream='https://github.com/fairy-stockfish/Fairy-Stockfish',upstream_pin=meta['source_pin'],modified=True,
    description='Actual modified material-only Fairy source used by1825, alignment-order base plus leafRNBP uci override. GPL source attribution retained. Not unmodified Stockfish, not NNUE.',
    sources=[x['source'] for x in old['sources']],flags=old['flags'],link_flags=['-pthread','-static'],
    original_binary_sha256='0263e8d6e9677b82e179c0d1a61ea5080df3275aba3464569e040eb222a20fe9',
    compiler_sha256=json.loads(Path('results/dev_aux/task1454/plan.json').read_bytes())['compiler_sha256'],
    files={name:dict(bytes=len(data),sha256=sha(data)) for name,data in contents.items()},
    scope='Source/build closure, compiler/runtime must be installed separately; no bit-identical binary or fresh-machine acceptance claim.')
with zipfile.ZipFile(OUT/'MATERIAL_ENGINE_SOURCE_59.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
    for name,data in contents.items():z.writestr('source/'+name,data)
    z.writestr('manifest.json',json.dumps(manifest,indent=2).encode())
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(dict(files=len(contents),raw_bytes=sum(map(len,contents.values())),zip_bytes=(OUT/'MATERIAL_ENGINE_SOURCE_59.zip').stat().st_size,sha256=sha((OUT/'MATERIAL_ENGINE_SOURCE_59.zip').read_bytes()))))
