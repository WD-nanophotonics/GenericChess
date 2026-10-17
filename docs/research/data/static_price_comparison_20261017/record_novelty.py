from pathlib import Path
import json,hashlib,sys,time
roots,queries,out=map(Path,sys.argv[1:]);start=time.monotonic()
raw=queries.read_bytes();assert hashlib.sha256(raw).hexdigest()=="82389eed5674fd6996a1c2c5041fb9cfb3dbe68ce4e841b5d90e778152bf1f3d"
def key(record):return hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":")).encode()).hexdigest()
old=set();counts={}
for line in raw.splitlines():
 q=json.loads(line)
 for field in ("record_before","record_after"):
  if q.get(field)is not None:old.add(key(q[field]))
rows=[];seen=set()
for r in json.loads(roots.read_bytes())["rows"]:
 k=key(r["record"]);rows.append(dict(rule=r["rule"],family=r["family"],record_sha256=k,duplicate_previous_root=k in seen,overlap_saved89_train_record=k in old,terminal_before_game=r["terminal_before_game"]));seen.add(k)
result=dict(status="COMPLETE_EXACT_RECORD_SCOPE_CHECK",attempted_roots=len(rows),unique_complete_records=len(seen),duplicate_draws=sum(r["duplicate_previous_root"]for r in rows),overlap_saved89_train_records=sum(r["overlap_saved89_train_record"]for r in rows),unique_saved89_before_after_records=len(old),rows=rows,seconds=time.monotonic()-start,scope="Canonical complete GameRecord equality, not Position-only equality, unreachable-state proof or unseenrule/holdout independence. All32roots retained and originalfitness unchanged. Distinctrecord doesnotexclude samePosition or earlierunrecordedTRAIN exposure.")
assert result["seconds"]<30
out.write_bytes((json.dumps(result,indent=2)+"\n").encode());print(json.dumps({k:v for k,v in result.items()if k!="rows"}))
