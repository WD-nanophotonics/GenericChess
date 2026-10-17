from pathlib import Path
import sys,json,os,subprocess,time,xml.etree.ElementTree as ET
R=Path.cwd();STOP_ROOT=Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(R))).resolve();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/paid-td-20261017';X=D/'exact';O=X/'results/dev_aux';start=time.monotonic();outputs=['task2541/'+n for n in ['training-audit.json','evaluation-audit.json','diagnostics.json','search-verification.json','roots.json','information.json','early-credit.json','training-audit-first-rule.json','interaction.json','unchanged.json']]+['task2544/audit.json']
for n in outputs:
 p=O/n;assert p.exists();p.rename(p.with_name(p.name+'.sealed-original'))
targets=['results/dev_aux/task2492/test_learning.py','results/dev_aux/task2492/test_episode.py','results/dev_aux/task2501/test_search.py','results/dev_aux/task2504/test_bounded.py','results/dev_aux/task2511/test_generic.py','results/dev_aux/task2512/test_methods.py','results/dev_aux/task2517/test_root.py','results/dev_aux/task2523/test_exposure.py'];args=['-q','-o','addopts=','--import-mode=importlib','--confcutdir=.','-p','no:cacheprovider','--basetemp',str(D/'pytest-temp'),'--junitxml',str(D/'tests.xml')]+targets
code='import sys,pathlib;sys.path[:0]='+repr([str(X),str(R/'.venv/Lib/site-packages')])+';from results.dev_aux.task2392.reader import SharedDeleteStopReader;stop=SharedDeleteStopReader(pathlib.Path('+repr(str(STOP_ROOT))+'));assert all(p.resolve().is_relative_to(pathlib.Path('+repr(str(STOP_ROOT))+')/".local_agent")for p in stop.paths);stop();import pytest;assert pytest.main('+repr(args)+')==0;'
for mod in ('training_audit','evaluation_audit','diagnostics','roots','information','early_credit','interaction','unchanged'):code+='from results.dev_aux.task2541.'+mod+' import run as again;again();'
code+='from results.dev_aux.task2541.training_audit import run as early;early(prefix_rule=271001);from results.dev_aux.task2544.audit import run as followup;followup();from results.dev_aux.task2541.search_verification import run as sv;sv(stop_root='+repr(str(STOP_ROOT))+');'
code+='assert all(pathlib.Path(v.__file__).resolve().is_relative_to(pathlib.Path.cwd())for k,v in sys.modules.items()if (k.startswith("generic_chess")or k.startswith("results.dev_aux"))and getattr(v,"__file__",None));'
compile(code,'dispatcher','exec');(D/'exact-dispatcher.py.txt').write_bytes(code.encode());env={**os.environ,'PYTHONPATH':'','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
with(D/'reproduction.log').open('w',encoding='utf8')as log:
 child=subprocess.Popen([sys.executable,'-S','-X','utf8','-c',code],cwd=X,env=env,stdout=log,stderr=subprocess.STDOUT)
 while child.poll()is None:
  try:
   assert time.monotonic()-start<600,'Frozenqualificationcap'
   for n in('rollout','advisor','slack'):
    f=json.loads((STOP_ROOT/'.local_agent'/(n+'.json')).read_bytes());assert not f.get('user_paused')and not f.get('stopped'),'EXPLICIT_STOP'
  except BaseException:child.terminate();child.wait();raise
  time.sleep(.25)
 assert child.returncode==0,'Inspectprivate reproduction.log'
rows=[];legal=0
for n in outputs:
 a=json.loads((O/n).read_bytes());b=json.loads((O/(n+'.sealed-original')).read_bytes())
 for k in('audit_seconds','seconds'):a.pop(k,None);b.pop(k,None)
 assert a==b,n;c=a.get('counts',{});legal+=sum(c.get(k,0)for k in('prefix_plies','training_plies','legal_prefix_plies','legal_play_plies'));rows.append(dict(output=n,status=a['status'],all_non_time_fields_equal=True))
suite=ET.parse(D/'tests.xml').getroot().find('testsuite');assert suite.attrib['tests']=='38'and suite.attrib['errors']==suite.attrib['failures']=='0';write_json(D/'reproduction-result.json',dict(status='PASS_EXTRACTED38_AND_ELEVEN_REGENERATED_OUTPUTS',source_sha='3792d83068d5d0e61a0a33ebbf6850b414202c6f',payloads=205,tests=38,skipped=int(suite.attrib['skipped']),outputs=rows,logical_legal_plies=legal,seconds=time.monotonic()-start,scope='ActuallyexecutedAUX92publishedsource/owner-authoredaudits,notPRIMARYindependentmath. All11sealedoutputsPARKEDfirst;Python-S/emptyPYTHONPATH/extractedoriginasserted. PrivatePRIMARYdispatcher bindsactualPRIMARYflags/assertseverystoppathwithinPRIMARY,notfakeflags/AUXcheckoutreads. OriginalTRAIN/EVALnotrerun;64unprunedD2verificationqueriesnotnewfitness.'))
print('AUX92_REPRODUCTION_PASS',38,len(rows),legal,round(time.monotonic()-start,3),flush=True)
