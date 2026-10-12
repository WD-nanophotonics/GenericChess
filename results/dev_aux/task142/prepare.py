"""Declaredcontinuation of failedstate-read batch; verifiedprefixcache, sametotalbudget."""
import json,hashlib,difflib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task142';O.mkdir(exist_ok=True)
old=R/'results/dev_aux/task140';audit=json.loads((R/'results/dev_aux/task143/prefix140.json').read_bytes());assert audit['complete'] and audit['verified_calls']==130
status=json.loads((old/'status.json').read_bytes());D=json.loads((old/'declaration.json').read_bytes());D.update(task_id='142',old_task140='INTERRUPTED130actualtrain0heldout, preserved',source_controller_sha256=audit['source_controller_sha256'],source_driver_sha256=hashlib.sha256((old/'run.py').read_bytes()).hexdigest(),old_actual_seconds=status['wall_seconds'],deadline_seconds=1800-status['wall_seconds'],original_total_budget_seconds=1800,new_premise='JSONdecode inonlyruntimeJSONreadsite stop_check; allsix currentflags nowvalid/notstopped, ownstatesunchanged. Primaryrolloutmtimecoincides with failure, suggests transientrewrite but originalerrorlackedfilename so exactfileunproven. Addown boundedread3attempts withpath/errorjournal, requirevalidparsebeforecontinue; neverclearorignorevalidstop. Ordinaryconcurrencyallowed.',read_recovery='3attempts50ms apart onlyonJSONDecodeError/OSError, currentvalidflagsrequired; persistentfailure raises namedpath, no assumptionallowed',cache='130independentlyreplayedactualcalls copiedexactly withSHA/context/weights checks;noenginererun;globalendpointsstillbeforeANYheldout',scope=D['scope']+' Originalfailureisinputreadavailability, notserioususer-requiredissue. No schedulepause orclockreset.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');(O/'fixtures.json').write_bytes((old/'fixtures.json').read_bytes())
source=(old/'run.py').read_text();new=source.replace("O=R/'results/dev_aux/task140'","O=R/'results/dev_aux/task142'")
new=new.replace("def execute():","CACHE=json.loads((R/'results/dev_aux/task140/controller.json').read_bytes())['calls']\n\ndef execute():",1)
new=new.replace("stop=lambda:A.stop_check(R);stop();","""def stop():
  for root in (R,R.parent/'GenericChess 2'):
   for name in ('rollout','advisor','slack'):
    p=root/f'.local_agent/{name}.json'
    for attempt in range(3):
     try:
      value=json.loads(p.read_bytes())
      if not isinstance(value,dict):raise ValueError('stop-state notobject:'+str(p))
      if value.get('user_paused') or value.get('stopped'):raise A.PersistentStop('persistentuserstop:'+str(p))
      break
     except (json.JSONDecodeError,OSError) as ex:
      with (R/'.local_agent/alignment-build/flag-read-recovery.jsonl').open('a',encoding='utf-8') as recovery:
       recovery.write(json.dumps(dict(path=str(p),attempt=attempt,error=type(ex).__name__+': '+str(ex),at=datetime.datetime.now(datetime.timezone.utc).isoformat()))+'\\n')
      if attempt==2:raise RuntimeError('unreadablestopafter3attempts:'+str(p)) from ex
      time.sleep(.05)
 stop();""",1)
new=new.replace(" if (O/'events.jsonl').exists()", " assert hashlib.sha256((R/'results/dev_aux/task140/controller.json').read_bytes()).hexdigest()==D['source_controller_sha256']\n if (O/'events.jsonl').exists()",1)
needle="""     else:
      if e is None:e=M.start(binary,aligned,deadline,stop)"""
replacement="""     elif len(calls)<len(CACHE):
      cached=CACHE[len(calls)]
      assert cached['context']==x and cached['weights']==w and cached['result']['opening']==fixture['moves']
      calls.append(dict(cached,provenance='CACHED_ACTUAL_TASK140',source_call_index=len(calls)))
      rs.append(cached['result']['reward']);j.record('cached_actual_callback',source_call_index=len(calls)-1,context=x,source_controller_sha256=D['source_controller_sha256'])
     else:
      if e is None:e=M.start(binary,aligned,deadline,stop)"""
assert needle in new;new=new.replace(needle,replacement,1)
new=new.replace("actual_games=new,excluded_input_slots", "actual_games=new+len(CACHE),new_actual_games=new,cached_actual_games=len(CACHE),old_actual_seconds=D['old_actual_seconds'],inclusive_old_new_seconds=D['old_actual_seconds']+time.monotonic()-started,excluded_input_slots",1)
(O/'run.py').write_text(new,encoding='utf-8');(O/'changed_read_contract.patch').write_text(''.join(difflib.unified_diff(source.splitlines(True),new.splitlines(True),fromfile='task140/run.py',tofile='task142/run.py')),encoding='utf-8')
print(json.dumps(dict(prepared=True,cached=130,new_budget_seconds=D['deadline_seconds'],same_total_budget_seconds=1800)))
