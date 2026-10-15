"""Build all source objects in a new directory; never reuse historical objects."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time,zipfile
ap=argparse.ArgumentParser();ap.add_argument('--compiler',required=True);ap.add_argument('--destination',required=True);args=ap.parse_args()
root=Path.cwd().resolve();destination=Path(args.destination).resolve();assert destination.is_relative_to(root/'.local_agent')
destination.mkdir(exist_ok=False);source=destination/'source'
archive=Path('results/dev_aux/task1831/MATERIAL_ENGINE_SOURCE_59.zip')
with zipfile.ZipFile(archive) as z:
    manifest=json.loads(z.read('manifest.json'))
    for name,row in manifest['files'].items():
        assert '..' not in Path(name).parts and not Path(name).is_absolute()
        data=z.read('source/'+name);assert hashlib.sha256(data).hexdigest()==row['sha256']
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
compiler=Path(args.compiler).resolve();assert hashlib.sha256(compiler.read_bytes()).hexdigest()==manifest['compiler_sha256']
start=time.perf_counter();deadline=time.monotonic()+300;objects=[];results=[]
for index,name in enumerate(manifest['sources']):
    remaining=deadline-time.monotonic();assert remaining>0
    obj=destination/(str(index)+'.o');command=[str(compiler),*manifest['flags'],'-I',str(source),'-c',str(source/name),'-o',str(obj)]
    result=subprocess.run(command,cwd=root,capture_output=True,timeout=min(180,remaining))
    (destination/(str(index)+'.log')).write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,(name,result.returncode)
    objects.append(obj);results.append(dict(source=name,returncode=result.returncode,object_sha=hashlib.sha256(obj.read_bytes()).hexdigest()));print('COMPILED',name,flush=True)
binary=destination/'fairy-material-rebuilt.exe';result=subprocess.run([str(compiler),*map(str,objects),*manifest['link_flags'],'-o',str(binary)],cwd=root,capture_output=True,timeout=min(90,deadline-time.monotonic()))
(destination/'link.log').write_bytes(result.stdout+result.stderr);assert result.returncode==0
out=dict(status='BUILT_FROM_ALL_SOURCE_OBJECTS',sources=results,source_files=len(manifest['files']),seconds=time.perf_counter()-start,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),matches_old_binary=hashlib.sha256(binary.read_bytes()).hexdigest()==manifest['original_binary_sha256'],compiler_sha256=manifest['compiler_sha256'],scope='New objects from checked source ZIP; installed compiler reused, no old object reuse. Raw logs/private binary retained locally. Behavioral qualification separate.')
(destination/'build.json').write_text(json.dumps(out,indent=2),encoding='utf-8');Path('results/dev_aux/task1831/build.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='sources'}))
