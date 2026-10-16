from pathlib import Path
import json,zipfile,uuid,subprocess,sys,sysconfig,hashlib,time,os
R=Path.cwd();P=R/".local_agent/playability-mu-20261016";D=R/"docs/archive/playability_mu_20261016";m=json.loads((D/"manifest.json").read_bytes())
assert hashlib.sha256((D/"evidence.zip").read_bytes()).hexdigest()==m["archive_sha256"]
dest=P/("public-copy-"+uuid.uuid4().hex[:8]);dest.mkdir();start=time.perf_counter()
with zipfile.ZipFile(D/"evidence.zip")as z:
 assert z.testzip()is None
 for item in m["members"]:
  b=z.read(item["path"]);assert hashlib.sha256(b).hexdigest()==item["sha256"];f=dest/item["path"];assert f.resolve().is_relative_to(dest.resolve());f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b)
support=json.loads((D/"support-manifest.json").read_bytes())
assert support["base_archive_sha256"]==m["archive_sha256"]
assert hashlib.sha256((D/"common-parent-support.zip").read_bytes()).hexdigest()==support["archive_sha256"]
with zipfile.ZipFile(D/"common-parent-support.zip")as z:
 assert z.testzip()is None
 for item in support["members"]:
  b=z.read(item["path"]);assert hashlib.sha256(b).hexdigest()==item["sha256"];f=dest/item["path"];assert f.resolve().is_relative_to(dest.resolve())and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(b)
source=dest/"source";src=source/"generic_chess/_native";out=source/"generic_chess"/("_native_core"+sysconfig.get_config_var("EXT_SUFFIX"))
cmd=[str(R/".venv/Lib/site-packages/ziglang/zig.exe"),"cc","-target","x86_64-windows-gnu","-shared","-O2","-I"+sysconfig.get_path("include"),"-I"+str(src),"-L"+str(Path(sys.base_prefix)/"libs"),"-lpython312",*[str(f)for f in sorted(src.glob("*.c"))],"-o",str(out)]
cache=P/"zig-public-copy-cache";cache.mkdir(exist_ok=True)
r=subprocess.run(cmd,capture_output=True,timeout=120,env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(cache)));(P/"public-copy-build-private.log").write_bytes(r.stdout+r.stderr);assert r.returncode==0
r=subprocess.run([sys.executable,"-S",str(dest/"research/consumer.py"),str(dest/"research"),"all"],cwd=source,capture_output=True,timeout=900)
(P/"public-copy-consumer-private.log").write_bytes(r.stdout+r.stderr);assert r.returncode==0,(r.stdout[-1000:],r.stderr[-2000:])
actual=json.loads((dest/"research/consumer-all.json").read_bytes());normal=json.loads(zipfile.ZipFile(D/"evidence.zip").read("research/consumer-all.json"));assert actual["counts"]==normal["counts"],(actual,normal)
x=dict(complete=True,archive_sha256=m["archive_sha256"],members=m["member_count"],support_members=support["member_count"],support_archive_sha256=support["archive_sha256"],initial_restore_failure_preserved=True,normal_source_sha256=hashlib.sha256((src/"native_module.c").read_bytes()).hexdigest(),actual_native_rebuilt=True,python_without_site=True,module_origins_asserted=True,normal_counts_match=True,normal_reference="Actualcompletedpost+interaction+matrixstageunion; nofabricatednormalwholepass",receipt=actual,seconds=time.perf_counter()-start,scope="Actualcorrectednew-directory publication-source normalNative rebuild andoneFULLsearch-disabledreceiptpass. No newstudysearch/game/proof/training/activation. SameWindows/Python/Zig/Core/compiler/host, notindependentWDL/newmachine orhistoricalclockauthentication.")
assert x["normal_source_sha256"]==m["normal_module_sha256"]=="39230230e1f51e44c158b4bbfebe23e3721211c56e897916a5cfe65d1144fd17"
(D/"publication-replay.json").write_bytes((json.dumps(x,indent=2)+"\n").encode());(P/"public-copy-replay.json").write_bytes((json.dumps(x,indent=2)+"\n").encode())
print("SOURCE_COPY_PASS",m["member_count"],actual["counts"],x["seconds"],flush=True)
