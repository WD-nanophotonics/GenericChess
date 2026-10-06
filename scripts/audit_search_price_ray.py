from pathlib import Path
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record,record_value
from scripts.research_state_replay import read_game_state
from scripts.material_leaf_choice import inventory_features
from scripts.search_price_ray import affine_line_certificate
INPUTS=('docs/research/data/chess_q1_root_20261006.json','docs/research/data/chess_q1_reference_local_20261006.json')
OUT=ROOT/'docs/research/data/search_price_ray_20261006.json'
SOURCES=('scripts/audit_search_price_ray.py','scripts/search_price_ray.py','docs/research/SEARCH_PRICE_RAY_PROTOCOL.md',
 'docs/research/SEARCH_PRICE_INFORMATION.md','scripts/research_record.py','scripts/research_state_replay.py','scripts/material_leaf_choice.py')+INPUTS


def main():
    if OUT.exists():raise FileExistsError('saved-tree audit never rerun')
    start=monotonic();r=dict(complete=False,states=0,feature_entries=0,game_transitions=0,compiled_queries=0,
      rows={},source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        for file in INPUTS:
            old=json.loads((ROOT/file).read_text())
            if not old['complete'] or not old['source_hashes_unchanged']:raise ValueError('qualified saved tree required')
            for p,pin in old['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('original source drift')
            states=[old['root']]
            for row in old['children'].values():states.append(row['state']);states.extend(x['state'] for x in row['replies'].values())
            vectors=[]
            for row in states:
                if r['states']>=100 or r['feature_entries']+5>512 or monotonic()-start>=15:raise ValueError('saved arithmetic cap')
                s=read_game_state(row)
                if s.terminal_status.is_terminal or any(h.total() for h in s.position.hands):raise ValueError('ongoing native-board proof scope')
                f=inventory_features(s.position,{'K'});vectors.append(tuple(f.get(('board',m),0) for m in 'PNBRQ'))
                r['states']+=1;r['feature_entries']+=5
            models=list(old['policies']);weights=[tuple(old['policies'][m]['integer_weights'][t] for t in 'PNBRQ') for m in models]
            certificate=affine_line_certificate(vectors,weights)
            if not certificate['full_choice_invariant']:raise ValueError('expected known positive Pawn ray not qualified')
            r['rows'][file]=dict(vectors=vectors,models=models,certificate=certificate,
              full_ties={m:old['policies'][m]['full_ties'] for m in models},
              premise='fixed complete ongoing min/max material tree; no strategic outcome inference')
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps(record_value({k:v for k,v in r.items() if k not in ('source_sha256','rows')})))


if __name__=='__main__':main()
