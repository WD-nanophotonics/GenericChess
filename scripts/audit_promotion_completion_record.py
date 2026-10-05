"""Recorded census-total qualification without modifying the failed producer."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/promotion_completion_record_20261005.json'
EXTRA=('scripts/audit_promotion_completion_record.py','docs/research/PROMOTION_COMPLETION_RECORD_SCOPE.md','scripts/audit_promotion_mobility_completion.py','docs/research/data/promotion_mobility_completion_20261005.json')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('record qualifier never rerun')
    old=json.loads((ROOT/EXTRA[3]).read_text());assert old['error']=="KeyError: 'worlds'" and old['new_worlds']==0
    record=json.loads((ROOT/'docs/research/data/promotion_mobility_gate_20261005.json').read_text())
    for row in record['rows']:assert sum(row['census']['histogram'].values())+row['census']['unreachable']==row['census']['total']==504
    source=(ROOT/EXTRA[2]).read_text().replace("row['census']['worlds']","row['census']['total']").replace("OUT=ROOT/'docs/research/data/promotion_mobility_completion_20261005.json'","OUT=ROOT/'docs/research/data/promotion_completion_record_20261005.json'")
    namespace={'__name__':'__main__','__file__':str(ROOT/EXTRA[2])};exec(compile(source,str(ROOT/EXTRA[2]),'exec'),namespace)
    r=namespace['r'];r['cumulative_seconds']+=old['seconds'];r['record_envelope']='total field and independent histogram mass'
    r['source_sha256'].update({p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in EXTRA})
    write_record(OUT,r)
