"""Review, exact-byte package/restore, and bounded research cost accounting."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,hashlib,ast,zipfile,subprocess,re,shutil
R=Path.cwd();B=R/'results/dev_aux';jobs=[1722,1723,1728,1730,1736,1739,1745,1748,1752];audits=[1724,1731,1735,1738,1743,1754,1755,1756,1740,1741,1746,1749,1757,1758];runs=[];qa={}
for n in jobs:
 z=json.loads((B/f'task{n}/result.json').read_bytes());assert z['status'] in ('PASS','COMPLETE') and z['exit_code']==0,(n,z['status'],z.get('error'))
 runs.append(dict(task=n,actual_new_native_go=z['actual_go'],new_controller_episode_records=z.get('actual_games',0),seconds=z['seconds'],reported_nodes=z.get('actual_reported_nodes'),old_paid_choice_cache_entries=z.get('old_paid_choice_cache_entries',0),actual_perft=z.get('perft',0),exit_code=z['exit_code']))
for n in audits:
 z=json.loads((B/f'task{n}/result.json').read_bytes());assert z['status'].startswith(('PASS','COMPLETE')),(n,z['status']);qa[str(n)]=z['status']
# Probe qualification adds48perft; separateKRK160 from1746.
perft=sum(z['actual_perft'] for z in runs)+json.loads((B/'task1746/result.json').read_bytes())['actual_perft']
cost=dict(status='ACTUAL_RECORDED_COSTS',runs=runs,actual_new_native_go=sum(z['actual_new_native_go'] for z in runs),new_controller_episode_records=sum(z['new_controller_episode_records'] for z in runs),actual_perft=perft,reported_nodes_known=sum(z['reported_nodes'] or 0 for z in runs),old_paid_query_entries_seeded_for_hybrid=sum(z['old_paid_choice_cache_entries'] for z in runs),complete_D3_subproblems=261360,KRK_exact_rule_edges=sum(x['counts']['edges'] for x in json.loads((B/'task1741/result.json').read_bytes())['results']),reuse='HybridNativechoices1730/1739paidpreviously, samefrozenroots exposed. Newcontrollercases are notnewindependentrootdraws or all-new Nativegames. Probe72go includes24originalprotocolreplays nottraining. PriorN/Bproof128.421s/model/nativequalification sunkcostnotfreefromscratch.',conditions='Ordinaryconcurrentprojects allowed, noquietwindow orspeedupclaim. AllThreads1/Hash16NNUEoff fixednodes; actualnodeovershoots anddepths audited. Engineering, audits, consultation andpublication partofAgenttime, notincluded ineachproducerseconds.')
(B/'COST_20261015_53.json').write_text(json.dumps(cost,indent=2))
files=[]
for d in sorted(B.glob('task*')):
 try:n=int(d.name[4:])
 except ValueError:continue
 if 1719<=n<=1758:
  for p in d.rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':files.append((p,p.relative_to(R).as_posix(),'new_experiment'))
support=['results/dev_aux/task1675/rules.py','results/dev_aux/task1688/rules.py','results/dev_aux/task1675/qualify_literal.py','results/dev_aux/task1688/qualify_literal_fixed.py','results/dev_aux/task1706/proof4.json','results/dev_aux/task1706/proof8.json','results/dev_aux/task1706/result.json','results/dev_aux/task166/run.py','results/dev_aux/task157/run.py','results/dev_aux/task139/run.py','results/dev_aux/task136/run.py','results/dev_aux/task127/run.py','results/dev_aux/task109/adapter.py','results/dev_aux/task104/short_game.py']
for name in support:files.append((R/name,name,'reused_support'))
engine=R/'.local_agent/alignment-order/source'
for p in engine.rglob('*'):
 if p.is_file():files.append((p,'engine_source/common/'+p.relative_to(engine).as_posix(),'pinned_engine_source'))
files.append((R/'.local_agent/leaf-rnbp-46/source/uci.cpp','engine_source/leaf_rnbp_uci.cpp','pinned_atomic_command_overlay'))
licensebase=R/'.local_agent/alignment-see/source/Fairy-Stockfish-9f778da667f6e07dae1e85d3e2ea204fc6dee94d'
for name in ('COPYING','AUTHORS'):
 if (licensebase/name).is_file():files.append((licensebase/name,'engine_source/'+name,'public_upstream_license_attribution'))
expected_bad='results/dev_aux/task1750/reconstructed_failed_generated_candidate.py';astvalid=0;expectedbad=[];jsons=0;jsonlines=0;hits=[];members=[]
email=re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
for p,name,role in files:
 raw=p.read_bytes();assert not name.startswith(('/', '\\')) and '..' not in Path(name).parts
 if p.suffix=='.py':
  try:ast.parse(raw.decode('utf-8-sig'));astvalid+=1;assert name!=expected_bad
  except IndentationError:
   assert name==expected_bad;expectedbad.append(name)
 if p.suffix=='.json':json.loads(raw);jsons+=1
 if p.suffix=='.jsonl':
  for line in raw.splitlines():
   if line.strip():json.loads(line);jsonlines+=1
 if p.suffix not in ('.bin',):
  text=raw.decode('utf-8-sig',errors='replace')
  for token in email.findall(text):
   # Licensed upstream attribution mustremain; flagforhumanreview, no privateaccount exports allowed.
   hits.append(dict(member=name,kind='email',value=token,role=role))
  patterns=[('credential',r'\b(?:xox[bp]-[A-Za-z0-9-]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{25,})\b'),('private_key',r'-{5}BEGIN [A-Z ]*PRIVATE KEY-{5}'),('personal_user_path',r'C:\\Users\\[^\\\r\n ]+\\')]
  for kind,pattern in patterns:
   for token in re.findall(pattern,text):hits.append(dict(member=name,kind=kind,value=token,role=role))
 members.append(dict(path=p,name=name,role=role,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
assert not hits,hits
assert expectedbad==[expected_bad]
restore=R/'.local_agent/archive_restore53';assert not restore.exists();assert subprocess.run(['git','check-ignore','-q',str(restore/'probe')],cwd=R).returncode==0;restore.mkdir()
groups=[];group=[];total=0
for m in members:
 if group and total+m['bytes']>160*1024*1024:groups.append(group);group=[];total=0
 group.append(m);total+=m['bytes']
if group:groups.append(group)
archives=[];manifest=[]
for i,group in enumerate(groups,1):
 dest=B/f'ACTUAL_MATURE_20261015_53_{i:02d}.zip';assert not dest.exists()
 with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zz:
  for m in group:zz.writestr(m['name'],m['path'].read_bytes())
 assert dest.stat().st_size<50*1024*1024
 with zipfile.ZipFile(dest) as zz:
  assert zz.testzip() is None
  for m in group:
   data=zz.read(m['name']);assert hashlib.sha256(data).hexdigest()==m['sha256'] and len(data)==m['bytes'];target=restore/m['name'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert hashlib.sha256(target.read_bytes()).hexdigest()==m['sha256'];manifest.append({k:v for k,v in m.items() if k!='path'}|dict(archive=dest.name))
 archives.append(dict(file=dest.name,bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),members=len(group)))
# Large loose records stayprivateatGitdelivery; exactbytes arepublishedinsidecheckedZIPs.
exclude=R/'.git/info/exclude';old=exclude.read_text(encoding='utf-8-sig')
large=[m['name'] for m in members if m['role']=='new_experiment' and m['bytes']>100000]
with exclude.open('a',encoding='utf-8') as ff:
 for name in large:
  pattern='/'+name
  if pattern not in old:ff.write('\n'+pattern)
q=dict(status='PASS_REVIEWED_ACTUAL_EVIDENCE_PACKAGE',audit_statuses=qa,AST_valid=astvalid,expected_reconstructed_failure_sources=expectedbad,JSON_valid=jsons,JSONL_records_valid=jsonlines,privacy_pattern_hits=hits,private_raw_slack_published=False,review_scope='Actualoutgoingnewtechnicalrecords/support/source only, no personaluser/account profiles orcredentials. Publiclicensedupstreamsourceattribution retained. Noorigin-basedpermissiongate; grant20261015recorded.',all_archive_bytes_restored_verified=True,source_AST_failure='Onepreexecutionbuilder mismatch preserved/reconstructed1750; fixedbeforetrial. OnewrongunwrappedSlackimport corrected withactualrawresult wrapper; noresend. No priorresults/caps rewritten.',duration_quality='Structural/sessionduration gate separate, actualscience remainsOPEN. No humanprice/fullGeneric orfalseNativewallratio/optimalPVclaim.')
(B/'QA_20261015_53.json').write_text(json.dumps(q,indent=2))
(B/'ARCHIVE_MANIFEST_20261015_53.json').write_text(json.dumps(dict(archives=archives,total_raw_bytes=sum(m['bytes'] for m in members),total_members=len(members),members=manifest,raw_canonical='Exactexecutedsource/resultbytes inZIP, verifiedprivaterestore; GitloosesmalltextmaynormalizeCRLF. No privateSlack/account/credential originals published.'),indent=2))
print('COST',cost);print('QA',{k:v for k,v in q.items() if k!='audit_statuses'});print('ARCHIVES',archives,'RAW',sum(m['bytes'] for m in members),'MEMBERS',len(members))

