from pathlib import Path
import json,zipfile,hashlib,sys,sysconfig,subprocess,time,uuid,os
R=Path.cwd();P=R/".local_agent/matched-d2-20261016";D=R/"docs/archive/matched_d2_20261016";m=json.loads((D/"manifest.json").read_bytes());start=time.perf_counter()
assert hashlib.sha256((D/"evidence.zip").read_bytes()).hexdigest()==m["archive_sha256"]
dest=P/("source-copy-"+uuid.uuid4().hex[:8]);dest.mkdir()
with zipfile.ZipFile(D/"evidence.zip")as z:
 assert z.testzip()is None
 for item in m["members"]:
  b=z.read(item["path"]);assert hashlib.sha256(b).hexdigest()==item["sha256"];f=dest/item["path"];assert f.resolve().is_relative_to(dest.resolve());f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b)
source=dest/"source";src=source/"generic_chess/_native";out=source/"generic_chess"/("_native_core"+sysconfig.get_config_var("EXT_SUFFIX"));cache=P/"source-copy-zig-cache";cache.mkdir(exist_ok=True)
cmd=[str(R/".venv/Lib/site-packages/ziglang/zig.exe"),"cc","-target","x86_64-windows-gnu","-shared","-O2","-I"+sysconfig.get_path("include"),"-I"+str(src),"-L"+str(Path(sys.base_prefix)/"libs"),"-lpython312",*[str(f)for f in sorted(src.glob("*.c"))],"-o",str(out)]
r=subprocess.run(cmd,capture_output=True,timeout=120,env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(cache)));(P/"source-copy-build-private.log").write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout[-1000:],r.stderr[-2500:])
r=subprocess.run([sys.executable,"-S",str(dest/"research/consumer_all.py"),str(dest/"research")],cwd=source,capture_output=True,timeout=600);(P/"source-copy-consumer-private.log").write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout[-2000:],r.stderr[-3000:])
actual=json.loads((dest/"research/consumer-all.json").read_bytes());reference=json.loads(zipfile.ZipFile(D/"evidence.zip").read("research/consumer-all.json"));assert actual["complete"]and actual["counts"]==reference["counts"],(actual,reference)
x=dict(complete=True,archive_sha256=m["archive_sha256"],archive_members=m["member_count"],normal_module_sha256=hashlib.sha256((src/"native_module.c").read_bytes()).hexdigest(),normal_native_rebuilt=True,python_without_site=True,module_origins_asserted=True,all_counts_equal=True,actual=actual,seconds=time.perf_counter()-start,scope="Actualnew-directorypublication-source normalNative rebuild/full6consumersearchdisabledpass; no studysearch/game/proof/training/privateactivation. Normalreferenceactualfull+lateunion, sourcecopyisfreshwholepass. Samehost/Python/Zig/Core/compiler, notindependentWDL/clockauthentication.")
assert x["normal_module_sha256"]==m["normal_module_sha256"]=="39230230e1f51e44c158b4bbfebe23e3721211c56e897916a5cfe65d1144fd17"
for f in[P/"source-copy-replay.json",D/"publication-replay.json"]:f.write_bytes((json.dumps(x,indent=2)+"\n").encode())
print("SOURCE_COPY_PASS",x["seconds"],actual["counts"],flush=True)
