"""Saved tree joint uncertainty, no additional game events or fitted law."""
import hashlib,json,sys
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.multiaffine_envelope_certificate import cube_min,min_envelope_lower
from scripts.material_leaf_choice import inventory_features
from scripts.research_state_replay import read_game_state
from scripts.shogi_exact_contact_family import exact_board_means
from scripts.research_record import record_value,write_record
OUT=ROOT/'docs/research/data/shared_law_hand_20261006.json'
SOURCES=('scripts/audit_shared_law_hand.py','scripts/multiaffine_envelope_certificate.py',
 'docs/research/SHARED_LAW_HAND_PROTOCOL.md','scripts/material_leaf_choice.py',
 'scripts/research_state_replay.py','scripts/shogi_exact_contact_family.py',
 'docs/research/data/shogi_full_contact_distance_20261005.json',
 'docs/research/data/shogi_coordinate_comparison_20261005.json',
 'docs/research/data/shogi_promotion_use_20261005.json',
 'docs/research/data/diagnostic_moment_bounds_20261006.json')
CANDIDATE='legacy_029:g21:a7-a8=TP'

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('closed joint uncertainty check')
    start=monotonic();r=dict(complete=False,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
      leaf_rows=0,pair_vertex_evaluations=0,pair_terms=0,comparisons=[],
      runtime_pushes=0,public_transitions=0,source_queries=0,candidate=CANDIDATE)
    def check():
        r['pair_vertex_evaluations']+=1
        if r['pair_vertex_evaluations']>4096 or monotonic()-start>=15:raise RuntimeError('4096 pair-vertices/15sec cap')
    try:
        tree=json.loads((ROOT/SOURCES[-2]).read_text());diag=json.loads((ROOT/SOURCES[-1]).read_text())
        for raw in (tree,diag):
            assert raw['complete'] and raw['source_hashes_unchanged']
            for path,pin in raw['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
        linear=exact_board_means('linear_mixture');geometric=exact_board_means('geometric_half')
        denominator=(linear['TR'],geometric['TR']-linear['TR']);assert min(linear['TR'],geometric['TR'])>0
        branches={};actions={}
        for key,branch in tree['branches'].items():
            rows=[];names=[]
            for name,leaf in branch['leaves'].items():
                features=inventory_features(read_game_state(leaf['state']).position,{'K'})
                assert all(location=='board' and kind in linear or location=='hand' and kind in ('P','R') for location,kind in features)
                board0=sum((linear[k]*n for (location,k),n in features.items() if location=='board'),F(0))
                board1=sum(((geometric[k]-linear[k])*n for (location,k),n in features.items() if location=='board'),F(0))
                hp,hr=features.get(('hand','P'),0),features.get(('hand','R'),0)
                rows.append((board0,board1,hp*denominator[0],hp*denominator[1],hr*denominator[0],hr*denominator[1],F(0),F(0)))
                names.append(name);r['leaf_rows']+=1;assert r['leaf_rows']<=64
            branches[key]=rows;actions[key]=names
        assert CANDIDATE in branches
        r.update(rows=branches,leaf_actions=actions,denominator=denominator)
        write_record(OUT,r)
        for key,baseline in branches.items():
            if key==CANDIDATE:continue
            minimal=next((j for j,b in enumerate(baseline) if all(cube_min(tuple(a[k]-b[k] for k in range(8)),check)>=0 for a in baseline)),None)
            if minimal is None:raise ValueError('no globally minimum baseline leaf; separately supplied proof needed')
            proof=tuple(F(int(j==minimal)) for j in range(len(baseline)))
            r['pair_terms']+=len(branches[CANDIDATE])*len(baseline);assert r['pair_terms']<=4096
            result=min_envelope_lower(branches[CANDIDATE],baseline,[proof]*len(branches[CANDIDATE]),check)
            assert result['lower']>0
            r['comparisons'].append(dict(baseline=key,minimal_leaf=actions[key][minimal],proof=proof,
                normalized_lower=result['lower']/max(linear['TR'],geometric['TR']),**result));write_record(OUT,r)
        means0={k:F(v) for k,v in diag['rows'][1]['exact_means'].items()}
        means1={k:F(v) for k,v in diag['rows'][0]['exact_means'].items()}
        diff0=means0['S']-means0['C'];diff1=means1['S']-means1['C']
        assert diff0>0>diff1
        r['diagnostic_SC_crossover']=diff0/(diff0-diff1)
        assert 0<r['diagnostic_SC_crossover']<1
        r['complete']=len(r['comparisons'])==len(branches)-1
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:record_value(v) for k,v in r.items() if k not in ('source_sha256','rows','leaf_actions','comparisons')}))
    for row in r['comparisons']:print(json.dumps(record_value({k:v for k,v in row.items() if k not in ('proof','row_bounds')})))
