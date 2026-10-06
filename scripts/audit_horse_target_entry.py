"""Native target-coordinate classes, not full per-world reachability."""
from pathlib import Path
from time import monotonic
import hashlib
import json
import sys
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts.horse_target_entry import incoming_sources, blockers_eliminating_all_entries
from scripts.research_record import write_record
OUT = ROOT/'docs/research/data/horse_target_entry_20261006.json'
SOURCES = ('scripts/audit_horse_target_entry.py', 'scripts/horse_target_entry.py',
           'docs/research/HORSE_TARGET_ENTRY_PROTOCOL.md', 'scripts/research_record.py',
           'docs/research/data/horse_zero_obstruction_20261006.json',
           'docs/research/data/horse_target_graph_20261006.json')


def main():
    if OUT.exists(): raise FileExistsError('target-entry lemma never rerun')
    start = monotonic()
    r = dict(complete=False, rows=[], offset_checks=0, intersections=0,
             forward_nodes=0, public_transitions=0, geometry_queries=0, source_queries=0,
             source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        old = json.loads((ROOT/SOURCES[-2]).read_text()); graph = json.loads((ROOT/SOURCES[-1]).read_text())
        for raw in (old, graph):
            if not raw['complete'] or not raw['source_hashes_unchanged']: raise ValueError('qualified prior evidence required')
            for p, digest in raw['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest() != digest: raise ValueError('input drift')
        for target in range(90):
            edges = incoming_sources(target)
            blockers = blockers_eliminating_all_entries(target)
            r['offset_checks'] += 8; r['intersections'] += len(edges)
            r['rows'].append(dict(target=target, incoming=edges, all_entry_blockers=blockers))
            if old['cumulative_terms']+r['offset_checks']+r['intersections'] > 5000 or monotonic()-start >= 15:
                raise ValueError('original cumulative term/15sec cap')
        if r['intersections'] != graph['full_analytic_prefix']['direct']//87:
            raise ValueError('independent incoming-edge count contradicts qualified prefix')
        found = [{'target': row['target'], 'blocker': b, 'sources': 88} for row in r['rows'] for b in row['all_entry_blockers']]
        if found != old['corner_entry']: raise ValueError('not exactly previously known corner-entry obstructions')
        r['entry_zero_worlds'] = sum(x['sources'] for x in found)
        r['cumulative_terms'] = old['cumulative_terms']+r['offset_checks']+r['intersections']
        r['cumulative_forward_nodes'] = graph['forward_nodes']
        r['full_reachability_complement_proved'] = False
        r['complete'] = True
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    write_record(OUT, r)
    print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'rows')}))


if __name__ == '__main__': main()
