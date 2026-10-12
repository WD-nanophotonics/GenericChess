"""Pinned portabletoolchain/source preparation for experimentalprice-table toggle."""
import json,hashlib,zipfile,time
from pathlib import Path
R=Path.cwd();B=R/'.local_agent/alignment-build';O=R/'results/dev_aux/task137';O.mkdir(exist_ok=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
started=time.monotonic();tool=B/'llvm-mingw.zip';source=B/'fairy-source.zip'
assert tool.stat().st_size==190836485
assert digest(tool)=='317492c456aa27ee607a5919f1d2d38dcdc1112516a24d0bf4b00d078f52d17a'
def extract(p,target):
 target=target.resolve()
 with zipfile.ZipFile(p) as z:
  for name in z.namelist():
   out=(target/name).resolve()
   if not out.is_relative_to(target):raise ValueError('unsafearchivepath')
  z.extractall(target)
extract(tool,B/'toolchain');extract(source,B/'source')
src=next((B/'source').glob('Fairy-Stockfish-*'))/'src'
compiler=next((B/'toolchain').glob('*/bin/clang++.exe'))
old=json.loads((R/'results/dev_aux/task091/declaration.json').read_bytes())
verified=[]
for name in ('psqt.cpp','movepick.cpp','position.cpp','uci.cpp'):
 assert digest(src/name)==old['files'][name];verified.append(name)
# Preserveoriginalunpatchedsource and apply exactretainedpurematerialpatch.
original=(src/'evaluate.cpp').read_bytes();expected=(R/'.local_agent/material-selfplay/evaluate.cpp').read_bytes()
assert b'GENERICCHESS_MATERIAL_DEVELOPMENT' not in original
needle=b'Value Eval::evaluate(const Position& pos) {'
start=expected.index(b'#ifdef GENERICCHESS_MATERIAL_DEVELOPMENT')
end=expected.index(b'#endif',start)+len(b'#endif\r\n\r\n')
block=expected[start:end]
assert (expected[:start]+expected[end:]).replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n')
modified=expected
(src/'evaluate.cpp').write_bytes(modified)
decl=dict(task_id='137',question='Does changingonlystandardPNBRQPieceValue to candidateconfiguredMG/EG affect actual search under samebinary/leaf/horizonbudget?',source_pin='9f778da667f6e07dae1e85d3e2ea204fc6dee94d',source_zip_sha256=digest(source),source_url='https://codeload.github.com/fairy-stockfish/Fairy-Stockfish/zip/9f778da667f6e07dae1e85d3e2ea204fc6dee94d',toolchain_url='https://github.com/mstorsjo/llvm-mingw/releases/download/20261006/llvm-mingw-20261006-ucrt-x86_64.zip',toolchain_bytes=tool.stat().st_size,toolchain_sha256=digest(tool),compiler_relative=str(compiler.relative_to(R)),source_relative=str(src.relative_to(R)),original_materialpatch_sha256=old['files']['material.patch'],materialsource_sha256=digest(src/'evaluate.cpp'),matchingretained_files=verified,ablation='sameexperimentalbinary; processenvGENERICCHESS_ALIGN_SEARCH_PRICES0vs1; PSQTinit sets standardPNBRQ PieceValue MG/EG to explicitcandidatevariantprices onlywhen1; sameleaf/capturetables/fixedmargins retained',scope='One inheritedprice-table family, affectsSEE/order/nonpawnmaterial/qfutility together; NOTSEE-only, notallprior-free. No productsource/default/UIchange. Experimentalbinary optinonly, ownprocess.',control='8Task133exposedroots plus8Task135compositionrootsturns;2fixedprofilesunit/learned;2alignmentarms=64actualsearches; configurationreadback+completehistory+reset;1024nodes;600sfuse; prices/leafackmustvalidatebeforesearch',cost='190.8MBportabletoolchaindownload+source, one serialboundedbuild estimated<15min;64searchesthenexpected<30s. Engineeringcostseparate; noextra workers/fees; nohourprojectrun.')
(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8')
print(json.dumps(dict(prepared=True,seconds=time.monotonic()-started,compiler=str(compiler),source=str(src),verified=verified)))
