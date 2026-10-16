"""Checked publication copy, preserving immutable exact local originals."""
from pathlib import Path
import zipfile,json,re,hashlib
BASE=Path('results/dev_aux');OUT=BASE/'task2089'
EMAIL=r'[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
CREDENTIAL=r'(?:xox[bp]-|ghp_|github_pat_|sk-proj-)[A-Za-z0-9_-]{15,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'
ALLOWED_CONTACT_ONLY={'.venv/Lib/site-packages/_pytest/_io/pprint.py','.venv/Lib/site-packages/chess/__init__.py'}
def digest(b):return hashlib.sha256(b).hexdigest()
def run():
 original=BASE/'SOURCE_REPRO_20261016_70.zip';public=BASE/'SOURCE_REPRO_20261016_70_PUBLIC.zip';changes=[];omitted=[]
 with zipfile.ZipFile(original)as src:
  manifest_name=next(n for n in src.namelist()if n.startswith('MANIFEST70'));manifest=json.loads(src.read(manifest_name));payload={n:src.read(n)for n in manifest['files']}
 for name,raw in list(payload.items()):
  if name=='results/dev_aux/task1831/MATERIAL_ENGINE_SOURCE_59.zip':
   omitted.append(dict(member=name,sha256=digest(raw),bytes=len(raw),reason='Duplicate historicalNativebuild-sourcearchive isnot neededfor source-onlyconsumerreplay; exactoriginal retainedlocally andinhistoricalrepository. No Nativebinaryisdelivered/rebuilt bythiscapsule.'));del payload[name];continue
  text=raw.decode('utf-8',errors='strict');matches=re.findall(EMAIL,text)
  if matches:
   if name not in ALLOWED_CONTACT_ONLY or len(matches)!=1:raise ValueError('unexpectedcontactrequiringreview '+name)
   clean=re.sub(EMAIL,'[upstream contact omitted in publication copy]',text).encode('utf-8');payload[name]=clean;changes.append(dict(member=name,optional_contact_values_removed=1,original_sha256=digest(raw),publication_sha256=digest(clean),change='Optionalcommentcontact or __email__ metadata only; COPYRIGHT/LICENSE/algorithm unchanged. Exact originalprivate/ignored.'))
 assert len(changes)==2
 manifest['omitted_duplicate_native_build_archive']=omitted
 manifest['files']={n:dict(bytes=len(b),sha256=digest(b))for n,b in sorted(payload.items())};manifest['publication_copy']=dict(optional_upstream_contacts_removed=2,changes=changes,scope='No GenericChess code/data/scientific records changed; original immutable sourcecapsule retainedignored. This publicationcopy is independentlyreplayed.')
 with zipfile.ZipFile(public,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for n,b in sorted(payload.items()):z.writestr(n,b)
  z.writestr(manifest_name,json.dumps(manifest,indent=2))
 members=[];findings=[]
 for archive in(public,BASE/'EVIDENCE_20261016_70.zip'):
  with zipfile.ZipFile(archive)as z:
   assert z.testzip()is None
   for n in z.namelist():
    raw=z.read(n);text=raw.decode('utf-8',errors='strict')
    if re.search(EMAIL,text)or re.search(CREDENTIAL,text)or re.search(r'From: [^\n]{0,100}<[^\n>]+@[^\n>]+>',text):findings.append(dict(archive=archive.name,member=n))
    if n.startswith('.local_agent/')or Path(n).is_absolute()or'..'in Path(n).parts:raise ValueError('privateorunsafepath')
    members.append(dict(archive=archive.name,member=n,bytes=len(raw),sha256=digest(raw)))
 assert not findings
 result=dict(status='PASS_EVERY_ARCHIVE_MEMBER_ACTUAL_CONTENT_REVIEW',members_read_and_sha_checked=len(members),bytes_inspected=sum(x['bytes']for x in members),emails_or_credentials_or_raw_account_headers_remaining=0,publication_source=public.as_posix(),publication_source_sha256=digest(public.read_bytes()),evidence_archive=(BASE/'EVIDENCE_20261016_70.zip').as_posix(),evidence_sha256=digest((BASE/'EVIDENCE_20261016_70.zip').read_bytes()),optional_contact_redactions=changes,all_executed_project_source_and_scientific_data_unchanged=True,omitted_duplicate_native_build_archives=omitted,members=members,reason='Corrective actualcontentreview afterautomaticrejection. Continuinguserauthorization covers checkedprojectGitpublication; no private rawSlack/account/credentials selected. Publicdependencycopyright/licenseattribution retained.')
 (OUT/'review.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k not in('members','optional_contact_redactions')}))
if __name__=='__main__':run()
