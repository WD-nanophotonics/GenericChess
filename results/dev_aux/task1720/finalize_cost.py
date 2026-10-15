from pathlib import Path
import json,hashlib,zipfile,ast,subprocess,datetime
R=Path.cwd();B=R/'results/dev_aux';O=B/'task1759';O.mkdir(exist_ok=False);costp=B/'COST_20261015_53.json';original=costp.read_bytes();(R/'.local_agent/cost53-initial-summary.json').write_bytes(original)
cost=json.loads(original);counts={}
for task in (1730,1739):counts[task]=len(json.loads((B/f'task{task}/qualification.json').read_bytes())['perft'])
assert counts=={1730:16,1739:40}
for z in cost['runs']:
 if z['task'] in counts:z['actual_perft']=counts[z['task']]
cost['actual_perft']=sum(z['actual_perft'] for z in cost['runs'])+json.loads((B/'task1746/result.json').read_bytes())['actual_perft'];assert cost['actual_perft']==328;cost['perft_accounting_correction']='Initial272count omitted16+40 qualifiercalls absentfromadaptiveproducerresultfields; correctedfromsavedqualificationarrays,0reruns.'
costp.write_text(json.dumps(cost,indent=2))
correction=dict(status='CORRECTED_FROM_ACTUAL_SAVED_QUALIFICATION_ARRAYS',initial_summary_sha256=hashlib.sha256(original).hexdigest(),initial_perft=272,omitted_counts=counts,correct_actual_perft=328,actual_go_unchanged=183814,episodes_unchanged=13376,new_queries_or_reruns=0,source='Originalexecutedpackage.py retained inbaseZIP; summary-fieldassumption corrected here beforepublication. Privateinitialsummary retained. All actualNativeperft rawrecords alreadyinbaseZIP.')
(O/'cost_correction.json').write_text(json.dumps(correction,indent=2))
qpath=B/'QA_20261015_53.json';qa=json.loads(qpath.read_bytes());qa['actual_perft_verified']=328;qa['perft_correction']='task1759/cost_correction.json';qa['AST_valid']+=1;qa['JSON_valid']+=1;qpath.write_text(json.dumps(qa,indent=2))
failures=dict(status='FAILURES_AND_CORRECTIONS_RETAINED',items=[dict(kind='Slackwrapperimport',failure='Unwrappedactualtoolresult rejected',impact='No send/retry/game',fix='Exacttoolresultpreservedinsupportedwrapperandreadbackreconciled'),dict(kind='preexecutionASTbuilder',failure='rngsubstring matchedprngLatininitialization, IndentationError',impact='Generatedcandidate notexecuted; reconstructionexplicit1750',fix='Newlineanchoredbootstrapsection; originalaudits retained; newaudits pass'),dict(kind='privacypublicationcopy',failure='Checkercontainedspecificprivateaccount/path example',impact='Neverpublished; exactsourcepreservedignoredprivate',fix='Genericregexpatterns; outgoingactualcontent reviewed nohits'),dict(kind='perftsummaryaccounting',failure='272omittedadaptive16+40realchecks',impact='Noexperimentrerun orscientificgainchange',fix='Corrected328fromsavedqualificationarrays, rawproofs intact'),dict(kind='oldmodeldocstring',failure='8x8modeldoc says16squares',impact='Actual65tuple/W8sourcehash andsemantics unchanged',fix='Currentdeclarations/report explicitlycorrect; oldexecutedsource notrewritten')])
(B/'FAILURES_20261015_53.json').write_text(json.dumps(failures,indent=2))
files=[(Path(__file__).resolve(),'results/dev_aux/task1720/finalize_cost.py'),(O/'cost_correction.json','results/dev_aux/task1759/cost_correction.json')]
dest=B/'ACTUAL_MATURE_20261015_53_08.zip';assert not dest.exists();mm=[]
with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zz:
 for p,name in files:zz.writestr(name,p.read_bytes())
with zipfile.ZipFile(dest) as zz:
 assert zz.testzip() is None
 for p,name in files:
  raw=zz.read(name);assert raw==p.read_bytes();target=R/'.local_agent/archive_restore53'/name;assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);mm.append(dict(name=name,role='reviewed_accounting_addendum',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),archive=dest.name))
manifestp=B/'ARCHIVE_MANIFEST_20261015_53.json';manifest=json.loads(manifestp.read_bytes());manifest['members']+=mm;manifest['total_members']+=len(mm);manifest['total_raw_bytes']+=sum(m['bytes'] for m in mm);manifest['archives'].append(dict(file=dest.name,bytes=dest.stat().st_size,sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),members=len(mm)));manifestp.write_text(json.dumps(manifest,indent=2))
summary="""# DEV_AUX current scope —2026-10-15 segment53

ScienceOPEN; sidemissiononly; heartbeatPAUSED; manualresearch exactduration inSESSION53.
TrueWDL RNPcooperative learning converges2testedinitials R1440/P1440,N/B720; sameinitialP limits.
Fresh48DEVgain.083333 positive; NEWfixed256familyreplicate.07128995[.040039,.102539],1UNKNOWN.
RNB3Latininitialpaths split; TRAINselectedR720/B360 DEVgain0, nothumanprice recovery.
Identicalrelativeprices change9/11of96Native rootchoices undercommonhalfscale; D3ordinalsets unchanged.
Complete4/8KRK WDL/DTM +ALLindependentactorfrontiers+160Nativeperft showmanyforcedwinscycle.
PhysicalDTMhandoff converts118RNP/114RNB oldcycles tomates, butfixedgaininteractionsuncertain.
RNBhybridgridwinnerR1440/B720 exposedDEV+.041667CIcross0; notfreshvalidation orinitialconvergence.
183814NEWNativego13376controllercases328perft;64894previouspaidchoicesseededhybrids explicitly.
EightZIPexactraw/sourcearchives restoredverified; rawSlack/privateoriginals ignored; outgoingPII/credentials excluded.
No primary/product/default/UI writes orfullChess/Shogi/Genericdomain claim; failures/caps preserved.
Next: actualNativeconversion-versus-exactDTM budgetcurve beforemate-visible mixed-stock learning roots.
Evidence:SEGMENT_20261015_53.md,COST/QA/FAILURES/ARCHIVE_MANIFEST53,1724/1735/1743/1754/1755/1756/1757/1758.

"""
p=R/'docs/research/LOCAL_MAINLINE.md';text=p.read_text(encoding='utf-8-sig');text=summary+text[text.index('# Current local research mainline'):];p.write_text(text,encoding='utf-8')
p=R/'AGENTS.md';text=p.read_text(encoding='utf-8-sig');a=text.index('# DEV_AUX current scope —2026-10-15 segment52');b=text.index('## Current user publication grant2026-10-15',a);text=text[:a]+summary+'\n'+text[b:];p.write_text(text,encoding='utf-8')
p=R/'docs/operations/COLLABORATION_LOG.md';entry="""## DEV_AUX2026-10-15 segment53

Own sidemission independent trueWDL research: newglobaltable/opponentmixture pressurelearning remainsuncertain; newRNPcooperative actualtwoinitiallearning improvesfresh48families andfixed256familyreplicate+.07128995[.040039,.102539]. SameinitialP andunhumanP/N2 limits kept. RNB3Latininitials split andDEV0 retained. Cost183814newNativego13376controllercases328perft, actualnamedold64894querycacheseeding forphysicalhandoff, notfreefromscratch.

Dot readfixed52report e4634d72, not53 artifacts/independentexecution. Adopted all17single-coordinate TRAINedge diagnosis atsame-statefirstdivergence, withoutresponsive-rootselection ornewgo. CompleteKRK rule/DTM andallactorproof showquietconversion failure; physicaltable-policycontrols turn118RNP/114RNBcyclesintomates butrelativegaininteractions remainuncertain. Common-ratio scale changesactualNativeactions, fullD3order invariant. Nohumanfit orsurrogatewins.

PRIMARY_SANDBOX independently discusses sourcePV/bound-ordering risk atfixed08d7fb81409551a46608d7f57a07dca324ba6f8c initsownSlackthread. Readonlycontext; DEV_AUXdidnotexecuteitsC/builds/tests, takeitsassignment, modifyitsstate/defaults/UI orrequestquietCPU. NoextraAgent/fees/merges. Ordinaryconcurrency allowed; timinginterpretationlimited.

Current20261015 publicationgrant carriedintoownmanuals: anycheckedprojectcontent permitted onestablishedGit/Slack, actualPII/credentials excluded; exactsensitiveoriginals preservedignored. Ownscience/raw/sourceZIPs restoredbyte-exact; preparationAST/wrapper/privacyexample/perft-accounting corrections documented withouttrialrerun. Remainingdecision: cheapNativeconversion-DTMcurve todesignmate-visible mixed-stock learning, notlongerunchangedcycles. ScienceOPEN, patrolPAUSED.

""";p.write_text(entry+p.read_text(encoding='utf-8-sig'),encoding='utf-8')
memo=f"""State: ACTIVE53 publicationcheckpoint; sidemissiononly; heartbeatPAUSED. Grant20261015 permits checkedproject Git/Slack anyorigin; actualPII/credentials excluded, originals private.
Segment:53 51bfcdcd-68a1-457d-9ce5-e9aab0988ff4 start2026-10-15T02:02:06.356103+00:00 noreset.
Main: Which cheapNativebudget canconvert rule-knownwins? | freeze64KRKstates stratifiedexactDTM4/8/16/24, bothcolors, fixedprices/requestednodes64/4096/16384 | actualphysicalWDL/DTMprogress/workcurve | bounded600s,nopricefit/oraclewinnerlabels; usecurveforNEXTmixedstockrootlaw.
Backup1: DoesRNPgain dependonPawnpromotiondistance? | freezeNEWprice/WDLblindcooperative near/farPawn-distance strata andfixed1730TRAINC/unit | physicalWDLbydeclaredstratum/UNKNOWN/cost | freshfullPawnframes,noDEVwinner/noquantityfallback.
Backup2: Does smallergeometry supply identifiableRNBtrueWDL? | declare4x4closedRNB rootlaw and3Latininitials withall16D4colorframes, qualifybeforelearning | actualWDL/rootresponse/endpointdispersion | boundednewstudy, changedgeometryexplicit/notstandardChessprices.
Evidence:1735fresh48+.083333;1754NEW256+.07128995[.040039,.102539];1743RNBsplitDEV0;1740commonratiosNativeactionschange;1741/1749completeKRK;1757handoffrelativeinteractionsuncertain. ScienceOPEN, report53/eightZIPrestored.
""";assert len(memo.encode())<=2048;(R/'.local_agent/NEXT_WORK.md').write_text(memo,encoding='utf-8')
print('FINAL_COST',cost['actual_new_native_go'],cost['new_controller_episode_records'],cost['actual_perft']);print('ARCHIVES',len(manifest['archives']),manifest['total_members'],manifest['total_raw_bytes'])

