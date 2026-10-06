"""Closed, exposed saved-root retention diagnostic; no Core execution."""
from pathlib import Path
from time import monotonic
from fractions import Fraction as F
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.retention_probe import probe_values
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/chess_retention_information_20261006.json'
SOURCES=('scripts/audit_chess_retention_information.py','scripts/retention_probe.py',
 'docs/research/CHESS_RETENTION_INFORMATION_PROTOCOL.md','scripts/research_record.py',
 'docs/research/data/chess_multimode_response_20261006.json',
 'docs/research/data/chess_multimode_source_replay_20261006.json')


def main():
    if OUT.exists():raise FileExistsError('closed diagnostic never rerun')
    start=monotonic();r=dict(complete=False,rows=0,branches={},comparisons={},
      public_transitions=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
      status='exposed-root diagnostic, not strength validation')
    try:
        raw=json.loads((ROOT/SOURCES[-2]).read_text());ind=json.loads((ROOT/SOURCES[-1]).read_text())
        for old in (raw,ind):
            if not old['complete'] or not old['source_hashes_unchanged']:raise ValueError('incomplete input')
            for p,pin in old['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('input pin drift')
        board=raw['root']['position']['board'];tags=[(i,p) for i,p in enumerate(board) if p and p['owner']==0 and p['current_type_id']!='K']
        tags.sort(key=lambda ip:ip[1]['current_type_id'])
        if [(i,p['base_type_id'],p['current_type_id'],p['promoted']) for i,p in tags]!=[(25,'P','P',False),(5,'R','R',False)]:raise ValueError('restricted identity premises changed')
        r['tags']=[dict(square=i,physical=p) for i,p in tags]
        for key,branch in raw['replies'].items():
            if sorted(branch['all_actions'])!=sorted(row['action'] for row in branch['rows']):raise ValueError('response coverage incomplete')
            child=raw['children'][key]['position']['board']
            if any(child[i]!=p for i,p in tags):raise ValueError('root action moved tracked resource')
            rows={}
            for leaf in branch['rows']:
                state=leaf['state'];end=state['position']['board'];vector=[]
                if state['terminal_status']['status']!='ongoing':raise ValueError('terminal task not admitted')
                for i,p in tags:
                    hits=[j for j,x in enumerate(end) if x==p]
                    if hits not in ([i],[]):raise ValueError('physical identity transported or duplicated')
                    vector.append(int(hits==[i]))
                rows[leaf['action']]=tuple(vector);r['rows']+=1
                if r['rows']>128 or monotonic()-start>=15:raise ValueError('128 rows/15sec cap')
            r['branches'][key]=dict(action_vectors=rows,**probe_values(rows))
        for law,selection in raw['selections_before_labels'].items():
            candidate=selection['selected'];other=raw['selections_before_labels']['unit'];comparisons={}
            for target in ('hidden','revealed'):
                value=r['branches'][candidate][target];canonical=value-r['branches'][other['selected']][target]
                margins=[value-r['branches'][k][target] for k in other['tie_set']]
                comparisons[target]=dict(canonical_margin=canonical,tie_margin=(min(margins),max(margins)))
            r['comparisons'][law]=comparisons
        r['window_gain_unchanged']=all(v['window']==[0,0] for v in raw['goal_intervals'].values())
        r['complete']=r['rows']==87
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items())
    write_record(OUT,r)
    print(json.dumps(record_value({k:v for k,v in r.items() if k not in ('source_sha256','branches')})))
    print(json.dumps(record_value({k:{kk:vv for kk,vv in b.items() if kk!='action_vectors'} for k,b in r['branches'].items()})))


if __name__=='__main__':main()
