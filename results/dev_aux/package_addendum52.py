from pathlib import Path
import zipfile,json,hashlib,ast,shutil
R=Path.cwd();D=R/'results/dev_aux';p=D/'ARCHIVE_MANIFEST_20261015_52.json';m=json.loads(p.read_bytes());extras=[D/'task1718/analyze.py',D/'task1718/result.json',D/'prepare_cost52.py',D/'prepare_report52.py',D/'package_segment52.py'];records=[];restore=R/'.local_agent/archive_restore52';out=D/'ACTUAL_MATURE_20261015_52_03.zip'
with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in extras:
  rel=f.relative_to(R).as_posix();b=f.read_bytes()
  if f.suffix=='.py':ast.parse(b.decode('utf-8-sig'))
  else:json.loads(b)
  assert b'@gmail.com' not in b and b'xoxb-' not in b and b'Bearer ' not in b;records.append({'path':rel,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});z.write(f,rel)
with zipfile.ZipFile(out) as z:
 assert z.testzip() is None
 for rec in records:
  target=restore/rec['path'];target.parent.mkdir(parents=True,exist_ok=True)
  with z.open(rec['path']) as inp,target.open('wb') as dst:shutil.copyfileobj(inp,dst)
  assert hashlib.sha256(target.read_bytes()).hexdigest()==rec['sha256']
m['archives'].append({'path':out.relative_to(R).as_posix(),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'members':records,'scope':'Latezeroqueryinteractions+executedcost/report/packagebuilders; exactbytesbeforepublication.'});m['members']+=len(records);m['raw_bytes']+=sum(x['bytes'] for x in records);m['validation']['AST_valid']+=4;m['validation']['JSON']+=1;p.write_text(json.dumps(m,indent=2))
qa=json.loads((D/'QA_20261015_52.json').read_bytes());qa['archives'].update(members=m['members'],raw_bytes=m['raw_bytes']);(D/'QA_20261015_52.json').write_text(json.dumps(qa,indent=2));print('ALL_ARCHIVES',m['members'],m['raw_bytes'],[(x['path'],x['bytes']) for x in m['archives']])
# Uniqueprivate memoir, currenttasks are nextsegmentactionable, neverautoresumepatrol.
memo='''State: ACTIVE52 finalreview; sidemissiononly; heartbeatPAUSED; noautoresume.
Segment:52 01f6148f-897b-457f-b8c1-68eba4ed679d start2026-10-14T23:27:53.568302+00:00 noreset.
Main: Canjointprice learning improve robust8WDL? | newdriver explicitrule/node/leaf-native-capturemode keys plusverifiedoneclear and1706single-stockDraw; freeze fresh8TRAIN/DEV andfixedopmixture beforequeries | actualWLD/UNKNOWN, independentACK/PV/cycle/selector andfamilygain | <=1200s/40000go,nohumanfit/DEVwinner, old52negativesstay.
Backup1: Doesrootdistribution cause P-holder loss? | predeclare fresh4RNP strata balancedPawnowner/distance/ownstock andsame64budget pricesfixed52TRAIN | pairedphysicalWDL andpoststrata counts | independentnewrootorbits, noselectbyoutcome.
Backup2: Whichsearchchoices explain price effects? | use1715matchedfinite3gaps andoldP-holdercountercases tofreezeonebridge control | exactfinitevalue vsactualwholepolicyWDL andcost | no optimalWDL/rootmovecausalityclaim fromfinite3gap.
Evidence:1679gain.0859375positive;1694randomendsbelowunit;1700completeD3gain.1328125;17118gain.0234375uncertain,strongop0;1714aligned8gain.015625uncertain;1717oneclear64rawqueries exact,no wallratio;1713stockproofcostforecast only. ScienceOPEN.
''';assert len(memo.encode('utf8'))<=2048 and len(memo.splitlines())<=20;(R/'.local_agent/NEXT_WORK.md').write_bytes(memo.encode('utf8'))
