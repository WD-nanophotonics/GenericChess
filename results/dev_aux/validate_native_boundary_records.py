"""Offline independent consistency review of auxiliary Native boundary records."""
from pathlib import Path
import ast,collections,hashlib,json
R=Path(__file__).resolve().parent

def read(task,name='result.json'):
    return json.loads((R/f'task{task:03d}'/name).read_bytes())
def main():
    files=0;size=0
    for task in range(69,91):
        b=R/f'task{task:03d}'
        for name,expected in read(task,'manifest.json').items():
            p=b/name;raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected,(task,name);files+=1;size+=len(raw)
            if p.suffix=='.py' and not name.startswith('failed_'):ast.parse(raw)
    calls=0;seconds=0
    for task,n in ((70,4),(71,4),(76,16),(78,16),(80,16),(81,64),(82,48),(84,4)):
        x=read(task);assert x['complete'] and len(x['rows'])==n;calls+=n
        for row in x['rows']:
            if 'root_restored' in row:assert row['root_restored']
            if 'work' in row:
                w=row['work'];assert w.get('physical_push',0)==w.get('physical_pop',0)
                assert row['provider_fallbacks']==row['provider_operational_failures']==0
            seconds+=row.get('caller_seconds',0)
    profile=read(83);assert profile['decision']['reason']=='complete';assert hashlib.sha256((R/'task083/executed_probe.py').read_bytes()).hexdigest()==profile['executed_probe_sha256'];calls+=1;seconds+=profile['caller_seconds']
    for task,expected in ((73,False),(74,True)):
        x=read(task);assert x['complete'] and len(x['rows'])==2;assert all(r['Python_ply_matches_Native']==expected and r['position_restored'] and r['Native_snapshot_restored'] for r in x['rows'])
    for task in (75,77):
        x=read(task);assert x['complete'] and x['records']==68 and x['score_mismatches']==x['owner_map_mismatches']==0
    x=read(79);assert x['synthetic_states']==144 and x['evaluations']==432 and not x['mismatches']
    x=read(80,'audit.json');assert all(p['queries'][0]==p['queries'][1] and all(p['equal'].values()) for p in x['pairs'])
    x=read(82,'audit.json');assert x['completed_D2_counts_outof8']=={'1':{'frozen_python_leaf':0,'raw_eager_terminal':0},'10':{'frozen_python_leaf':4,'raw_eager_terminal':4},'30':{'frozen_python_leaf':6,'raw_eager_terminal':8}} and len(x['gains'])==2 and not x['losses']
    assert read(85)['AST_equal_after_declared_field_mapping']
    for row in read(86)['rows']:assert row['python_score']!=row['rawNative_score'] and not all(row['map_equal'])
    x=read(87);assert x['scalar_checks']==490 and x['map_mismatches']==0 and all(not r['scalar_mismatches'] and r['root_unchanged'] for r in x['rows'])
    for row in read(88)['rows']:assert row['common_semantic_score']==row['rawNative_score']!=row['old_geometry_score']
    assert read(89)['complete']
    for row in read(90)['rows']:assert row['Core_score']==row['raw_score'] and row['Core_maps']==row['Native_maps'] and row['target9attacked'] != row['blocker']
    return {'complete':True,'manifest_files':files,'manifest_bytes':size,'scientific_search_calls':calls,'recorded_caller_seconds_where_available':seconds,'scope':'Offline record/hash/source consistency review,not newsearch/productregression or continuousuptime proof.'}
if __name__=='__main__':print(json.dumps(main(),indent=2))
