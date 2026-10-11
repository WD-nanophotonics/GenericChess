"""Own fixed-window launch check; no scheduler/lock or hard-duration guarantee."""
import argparse,json,math,subprocess,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def stamp(value):
 result=datetime.fromisoformat(value.replace('Z','+00:00'))
 if result.tzinfo is None:raise ValueError('UTC/offset required')
 return result.astimezone(timezone.utc)
def window(value):
 start,end=map(stamp,value.split('/'))
 if end<=start:raise ValueError('window end must follow start')
 return start,end
def assess(now,estimate,reserve,windows):
 if now.tzinfo is None:raise ValueError('aware current time required')
 if not math.isfinite(estimate) or estimate<=0 or not math.isfinite(reserve) or reserve<0:
  raise ValueError('finite positive estimate/nonnegative reserve required')
 now=now.astimezone(timezone.utc);anticipated=now+timedelta(seconds=estimate+reserve)
 for start,end in windows:
  if start<=now<end:return False,'active fixed source/doc window'
  if now<start and anticipated>=start:return False,'insufficient completion margin'
 return True,'outside known windows with declared margin'
def overlapping(start,end,windows):
 return [(a.isoformat(),b.isoformat()) for a,b in windows if max(start,a)<min(end,b)]
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--window',action='append',default=[])
 parser.add_argument('--expected-seconds',required=True,type=float)
 parser.add_argument('--reserve-seconds',type=float,default=30)
 parser.add_argument('--record',required=True)
 parser.add_argument('command',nargs=argparse.REMAINDER)
 args=parser.parse_args()
 if Path.cwd().resolve()!=ROOT:raise ValueError('explicit own checkout cwd required')
 target=(ROOT/args.record).resolve()
 if not any(target.is_relative_to(ROOT/p) for p in ('results/dev_aux','.local_agent')):
  raise ValueError('record must stay inside own evidence/state')
 windows=[window(v) for v in args.window]
 command=args.command[1:] if args.command[:1]==['--'] else args.command
 if not command:raise ValueError('command argv required')
 started=datetime.now(timezone.utc)
 allowed,reason=assess(started,args.expected_seconds,args.reserve_seconds,windows)
 record=dict(scope='operational launch timestamps, not performance sample',command_argv=command,
  started_at=started.isoformat(),estimated_seconds=args.expected_seconds,reserve_seconds=args.reserve_seconds,
  fixed_windows=[(a.isoformat(),b.isoformat()) for a,b in windows],allowed=allowed,reason=reason)
 target.parent.mkdir(parents=True,exist_ok=True)
 if not allowed:
  record['status']='DEFERRED_WITHOUT_LAUNCH';target.write_bytes((json.dumps(record,indent=2)+'\n').encode())
  print(reason);return 75
 result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
 ended=datetime.now(timezone.utc)
 record.update(ended_at=ended.isoformat(),child_returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
 violations=overlapping(started,ended,windows);record['overlap_windows']=violations
 record['status']='RESOURCE_OVERLAP' if violations else 'COMPLETED_OUTSIDE_WINDOWS'
 target.write_bytes((json.dumps(record,indent=2)+'\n').encode())
 sys.stdout.write(result.stdout);sys.stderr.write(result.stderr)
 if violations:
  print('unexpected overlap recorded; no automatic retry/extension',file=sys.stderr);return 76
 return result.returncode
if __name__=='__main__':raise SystemExit(main())
