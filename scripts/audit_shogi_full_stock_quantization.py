"""Frozen two-law arithmetic audit, no game observations."""
import hashlib,json,sys
from pathlib import Path
from fractions import Fraction as F
from itertools import combinations
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.shogi_exact_contact_family import exact_board_means
from scripts.shogi_contact_interval_choice import shogi_contact_intervals
from scripts.shogi_static_inventory import quantize,SCALE
from scripts.resource_mode_context import resource_ledger
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.ai.evaluation.config import MAX_STATIC_EVAL,MATE_THRESHOLD,MATE_SCORE
OUT=ROOT/'docs/research/data/shogi_full_stock_quantization_20261006.json'
SOURCES=('scripts/audit_shogi_full_stock_quantization.py','docs/research/SHOGI_FULL_STOCK_QUANTIZATION_PROTOCOL.md','scripts/shogi_static_inventory.py','scripts/shogi_exact_contact_family.py','scripts/shogi_contact_interval_choice.py','scripts/resource_mode_context.py','generic_chess/rules/standard_shogi.py','generic_chess/ai/evaluation/config.py','docs/research/data/shogi_full_contact_distance_20261005.json','docs/research/data/shogi_coordinate_comparison_20261005.json','docs/research/data/shogi_random_deployment_20261005.json')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('two fixed arithmetic rows only')
    start=monotonic();pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
    r=dict(complete=False,rows=[],source_sha256=pins,public_transitions=0,source_queries=0,distance_worlds=0)
    try:
        c=compile_ruleset_for_execution(build_standard_shogi_ruleset());ledger=resource_ledger(c,c.initial_position,'shogi')
        stock={t:n for t,n in ledger['inventory'].items() if not c.support.type_metadata[t].is_anchor};n=sum(stock.values());assert n==38
        r.update(stock=stock,ordinary_tokens=n,scale=SCALE,max_absolute_score=n*SCALE,static_limit=MAX_STATIC_EVAL,mate_threshold=MATE_THRESHOLD,mate_score=MATE_SCORE,leaf_rounding_error=F(n,2*SCALE),pair_rounding_error=F(n,SCALE),held_endpoint_enclosure=F(n,SCALE))
        assert n*SCALE<MAX_STATIC_EVAL<MATE_THRESHOLD<MATE_SCORE
        for law in ('geometric_half','linear_mixture'):
            means=exact_board_means(law);weights={t:x/means['TR'] for t,x in means.items()};ints={t:quantize(x) for t,x in weights.items()}
            errors={t:F(ints[t],SCALE)-x for t,x in weights.items()};assert all(abs(x)<=F(1,2*SCALE) for x in errors.values())
            pairs=[dict(first=a,second=b,exact_sign=(weights[a]>weights[b])-(weights[a]<weights[b]),integer_sign=(ints[a]>ints[b])-(ints[a]<ints[b])) for a,b in combinations(sorted(weights),2)]
            intervals=shogi_contact_intervals(law);held={t:dict(exact=[lo,hi],integer_outer=[lo.numerator*SCALE//lo.denominator,-(-hi.numerator*SCALE//hi.denominator)]) for (loc,t),(lo,hi) in intervals.items() if loc=='hand'}
            row=dict(law=law,weights=weights,integer_weights=ints,errors=errors,pairs=pairs,order_preserved=all(x['exact_sign']==x['integer_sign'] for x in pairs),held_intervals=held)
            r['rows'].append(row);assert len(pairs)==78 and len(held)==7 and row['order_preserved']
            assert monotonic()-start<15
        r['complete']=len(r['rows'])==2
    except Exception as error:r['error']=repr(error)
    finally:
        r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in pins.items())
        OUT.write_text(json.dumps(r,indent=2,default=str)+'\n',encoding='utf-8');print(json.dumps(dict(complete=r['complete'],rows=len(r['rows']),seconds=r['seconds'],error=r.get('error'))))
