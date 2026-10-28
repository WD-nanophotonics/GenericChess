"""One frozen local terminal certificate; no general WDL search or controller."""
import argparse,time
from pathlib import Path
from scripts.leaper_postexchange_source import load,sha,replay,stamp,stopped
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.verify_leaper_pvs_quality_pilot import action
from scripts.research_record import record_value,write_record
from scripts.leaper_check_extension_quality import record_interval


def record_session(compiled,record):
 """Clone either public GameRecord or its JSON value through the existing contract."""
 return replay(compiled,record_value(record))


def run(plan_path,out):
 plan=load(plan_path);assert sha(__file__)==plan['source_sha256']
 assert sha('.local_agent/postexchange-72bf6d79/source-scan/returns.json')==plan['input_sha256']
 assert not out.exists();out.mkdir();write_record(out/'frozen.json',plan)
 prepared=load('.local_agent/admission-b2d68177/comparison-prepared/inputs.json');row=next(x for x in prepared['rows'] if x['id']==plan['case_id']);c,_=make_session(row)
 begin=stamp();t=time.perf_counter();transitions=0;attempts=[];proof=None;halt=None
 class Cap(Exception):pass
 def check():
  if stopped() or time.perf_counter()-t>=plan['Core_batch_seconds'] or transitions>=plan['Core_transition_cap']:raise Cap('scoped_stop_or_frozen_cap')
 def child(record,a):
  nonlocal transitions
  check();s=record_session(c,record);s.submit(a);transitions+=1;return s
 try:
  root=replay(c,plan['child_record']);target=root.state.position.side_to_move
  for a in root.legal_actions():
   check();s=child(plan['child_record'],a);r=dict(action=record_value(a),replies=[],status='RUNNING');attempts.append(r)
   if s.state.terminal_status.is_terminal:
    r['status']='WIN' if s.state.terminal_status.winner==target else 'NO_CERTIFICATE'
   else:
    complete=True
    for reply in s.legal_actions():
     z=child(s.to_record(),reply);w=dict(reply=record_value(reply),winner_action=None,status='UNKNOWN');r['replies'].append(w)
     if z.state.terminal_status.is_terminal:w['status']='WIN' if z.state.terminal_status.winner==target else 'COUNTER_TO_THIS_CERTIFICATE'
     else:
      for win in z.legal_actions():
       end=child(z.to_record(),win)
       if end.state.terminal_status.is_terminal and end.state.terminal_status.winner==target:
        w.update(status='WIN',winner_action=record_value(win),terminal=record_value(end.state.terminal_status));break
      else:w['status']='COUNTER_TO_THIS_CERTIFICATE'
     if w['status']!='WIN':complete=False;break
    r['status']='WIN' if complete else 'NO_CERTIFICATE'
   if r['status']=='WIN':proof=r;break
  status='FORCED_TERMINAL_WIN_CERTIFICATE' if proof is not None else 'NO_WITNESS_WITHIN_FROZEN_TREE'
 except Cap as e:status='UNKNOWN';halt=str(e)
 except Exception as e:status='FAILED';halt=type(e).__name__+':'+str(e)
 result=dict(status=status,started_at=begin,ended_at=stamp(),elapsed_seconds=time.perf_counter()-t,Core_transitions=transitions,attempts=attempts,proof=proof,halt=halt,new_Player_calls=0,new_games=0,new_controller=False,claim='One saved noisy child only;not quiet superiority,a root correction,all-domain WDL or generic solver')
 write_record(out/'result.json',result);record_interval(begin,result['ended_at'],'analysis',str(out/'result.json'),out);print({k:v for k,v in result.items() if k not in ('attempts','proof')})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.plan,a.output)
