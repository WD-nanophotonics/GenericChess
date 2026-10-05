"""Certificate verification on exposed affine leaves; no game expansion."""
import hashlib,json,sys
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.shared_min_envelope_certificate import min_envelope_margin_lower,affine_box_min
from scripts.material_leaf_choice import inventory_features
from scripts.research_state_replay import read_game_state
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/shared_min_envelopes_20261006.json'
SOURCES=('scripts/audit_shared_min_envelopes.py','scripts/shared_min_envelope_certificate.py',
 'docs/research/SHARED_COEFFICIENT_MINIMAX_PROTOCOL.md','scripts/material_leaf_choice.py',
 'scripts/research_state_replay.py','docs/research/data/shogi_shared_hand_search_20261006.json',
 'docs/research/data/shogi_promotion_use_20261005.json')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed arithmetic certificate control')
    start=monotonic();pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
    r=dict(complete=False,source_sha256=pins,leaf_rows=0,pair_terms=0,public_transitions=0,
           runtime_pushes=0,source_queries=0,comparisons=[])
    try:
        old=json.loads((ROOT/SOURCES[-2]).read_text());tree=json.loads((ROOT/SOURCES[-1]).read_text())
        for raw in (old,tree):
            assert raw['complete'] and raw['source_hashes_unchanged']
            for path,pin in raw['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
        w={t:F(v,100000) for t,v in old['searches'][0]['integer_weights'].items()}
        box=((F(0),F(1)),(F(0),F(1)));branches={};actions={}
        for key,branch in tree['branches'].items():
            rows=[];keys=[]
            for action,leaf in branch['leaves'].items():
                f=inventory_features(read_game_state(leaf['state']).position,{'K'})
                assert all((location=='board' and kind in w) or (location=='hand' and kind in ('P','R')) for location,kind in f)
                row=(sum((w[kind]*n for (location,kind),n in f.items() if location=='board'),F(0)),F(f.get(('hand','P'),0)),F(f.get(('hand','R'),0)))
                rows.append(row);keys.append(action);r['leaf_rows']+=1
                assert r['leaf_rows']<=64 and monotonic()-start<15
            assert rows;branches[key]=rows;actions[key]=keys
        candidate=old['searches'][0]['selected'];assert candidate in branches
        r.update(candidate=candidate,box=box,affine_rows=branches,leaf_actions=actions)
        for baseline,rows in branches.items():
            if baseline==candidate:continue
            minimal=next((j for j,b in enumerate(rows) if all(affine_box_min(tuple(a[k]-b[k] for k in range(3)),box)>=0 for a in rows)),None)
            if minimal is None:raise ValueError('no global-min leaf; needs a separately supplied proof')
            proof=tuple(F(int(j==minimal)) for j in range(len(rows)))
            r['pair_terms']+=len(branches[candidate])*len(rows);assert r['pair_terms']<=4096
            result=min_envelope_margin_lower(branches[candidate],rows,box,[proof]*len(branches[candidate]))
            assert result['lower']>0
            r['comparisons'].append(dict(baseline=baseline,minimal_leaf=actions[baseline][minimal],proof=proof,**result))
        # A genuinely switching envelope where a corner-only check is wrong.
        switched=min_envelope_margin_lower([(0,0)],[(0,1),(1,-1)],[(0,1)],[(F(1,2),F(1,2))])
        assert switched['lower']==-F(1,2)
        r['switching_control']=dict(corner_margin=0,interior_margin=-F(1,2),proof=switched)
        r['complete']=len(r['comparisons'])==len(branches)-1
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in pins.items())
    write_record(OUT,r)
    print(json.dumps({k:record_value(v) for k,v in r.items() if k not in ('source_sha256','affine_rows','leaf_actions','comparisons')}))
