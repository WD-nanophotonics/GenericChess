"""Consume saved complete proofs through uniform value/action cutoff gate."""
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.shared_parameter_order import certify_order
from scripts.research_record import record_value,write_record
OUT=ROOT/'docs/research/data/shared_parameter_order_20261006.json'
SOURCES=('scripts/audit_shared_parameter_order.py','scripts/shared_parameter_order.py',
 'scripts/multiaffine_envelope_certificate.py','scripts/research_record.py',
 'docs/research/SHARED_PARAMETER_ORDER_PROTOCOL.md',
 'docs/research/SHARED_PARAMETER_WINDOW_CONTRACT.md',
 'docs/research/data/shared_law_hand_20261006.json')

def main():
    if OUT.exists():raise FileExistsError('order consumer audit never rerun')
    started=monotonic();r=dict(complete=False,vertices=0,rows=[],public_transitions=0,
      runtime_pushes=0,source_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        r['vertices']+=1
        if r['vertices']>4096 or monotonic()-started>=15:raise ValueError('4096 vertices/15sec order gate')
    try:
        old=json.loads((ROOT/SOURCES[-1]).read_text())
        if not old['complete'] or not old['source_hashes_unchanged']:raise ValueError('qualified full proof table required')
        for p,pin in old['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('old source drift')
        branches={k:[tuple(map(F,row)) for row in rows] for k,rows in old['rows'].items()}
        denominator=tuple(map(F,old['denominator']))+(F(0),)*6
        candidate=old['candidate']
        for row in old['comparisons']:
            baseline=row['baseline'];proof=tuple(map(F,row['proof']))
            result=certify_order(branches[candidate],branches[baseline],
              first_kind='min',second_kind='min',denominator=denominator,
              retained_id=candidate,discarded_id=baseline,
              proofs=[proof]*len(branches[candidate]),checkpoint=check)
            if result['normalized_lower']!=F(row['normalized_lower']) or not result['canonical_action_prune_proved']:
                raise ValueError('saved proof failed new uniform gate')
            r['rows'].append(dict(candidate=candidate,baseline=baseline,**result))
        r['complete']=len(r['rows'])==4
        r['not_proved']='production PVS/TT/int integration, unobserved branches, avoided Core cost or goal improvement'
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-started
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps(record_value({k:v for k,v in r.items() if k not in ('source_sha256','rows')})))
    for row in r['rows']:print(json.dumps(record_value(row)))

if __name__=='__main__':main()
