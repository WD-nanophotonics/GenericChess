"""One-shot contract check over saved complete event tables; no game execution."""
import hashlib,json
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1]
INPUT='docs/research/data/compatible_contact_discriminator_20261005.json'
PROTOCOL='docs/research/CONTACT_REUSE_LOCAL_PROTOCOL.md'


def check(report):
    started=monotonic()
    original=json.loads((ROOT/INPUT).read_text(encoding='utf-8'))
    if not original['all_controls_complete'] or not original['source_hashes_unchanged']:
        raise ValueError('incomplete original observations')
    if any(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h for p,h in original['source_sha256'].items()):
        raise ValueError('frozen source drift')
    for row in original['rows']:
        for table in row['tables']:
            if not table['complete']:raise ValueError('incomplete node coverage')
            if any(x[1]!='own_anchor_safe' for x in table['excluded_dynamic']):
                raise ValueError('unqualified dynamic omission')
            node=table['node'];source=node['square']
            blockers={int(k):v for k,v in row['blockers'].items()}
            if source==59 or source in blockers:raise ValueError('invalid source world')
            present={**blockers,source:'own',59:'enemy'}
            absent={**blockers,source:'own'}
            sets={'actual':set(),'relaxed':set(),'contact':set()}
            for event in table['events']:
                if report['physical_key_tests']>=5000 or monotonic()-started>=15:
                    raise RuntimeError('saved-table test cap')
                report['physical_key_tests']+=1
                key=event['key']
                actor,current,src,dst,label,removals,result=key
                if (actor,current,src)!=(0,node['current'],source) or not 0<=dst<81:
                    raise ValueError('node/key identity mismatch')
                if label not in ('empty','enemy'):raise ValueError('unsupported target relation')
                if removals and (len(removals)!=1 or removals[0]!=[dst,'capture_to_hand']):
                    raise ValueError('unsupported physical removal')
                for cube in event['cubes']:
                    if any(not 0<=sq<81 or not allowed or any(x not in ('own','enemy','empty') for x in allowed)
                           for sq,allowed in cube):raise ValueError('malformed occupancy cube')
                def holds(world):
                    return world.get(dst,'empty')==label and any(
                        all(world.get(sq,'empty') in allowed for sq,allowed in cube)
                        for cube in event['cubes'])
                edge=(dst,result)
                if not removals:
                    if label!='empty':raise ValueError('enemy edge lacks removal')
                    if holds(present):sets['actual'].add(edge)
                    if holds(absent):sets['relaxed'].add(edge)
                elif dst==59 and holds(present):sets['contact'].add(edge)
            lost=sets['actual']-sets['relaxed'];new=sets['relaxed']-sets['actual']
            ok=not lost and (not new or bool(sets['contact']))
            report['nodes'].append(dict(row=row['name'],node=node,
                actual=sorted(sets['actual']),relaxed=sorted(sets['relaxed']),contact=sorted(sets['contact']),
                actual_not_relaxed=sorted(lost),relaxed_not_actual=sorted(new),contract=ok))
    report['all_visited_nodes_qualified']=all(n['contract'] for n in report['nodes'])
    report['complete']=True
    report['seconds']=monotonic()-started


if __name__=='__main__':
    output=ROOT/'docs/research/data/contact_reuse_saved_tables_20261005.json'
    if output.exists():raise ValueError('fresh result required; no rerun')
    pins=[INPUT,PROTOCOL,'scripts/audit_contact_reuse_saved_tables.py']
    report=dict(source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins},
                nodes=[],physical_key_tests=0,complete=False,
                scope=dict(saved_nodes_only=True,new_geometry=0,new_materializations=0,
                           public_transitions=0,goal_calls=0))
    try:check(report)
    except Exception as error:report['error']=f'{type(error).__name__}: {error}'
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
                                         for p,h in report['source_sha256'].items())
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','nodes')}))
    print(json.dumps(dict(nodes=len(report['nodes']),
                         qualified=sum(n['contract'] for n in report['nodes']),
                         removed=sum(len(n['relaxed_not_actual']) for n in report['nodes']))))
