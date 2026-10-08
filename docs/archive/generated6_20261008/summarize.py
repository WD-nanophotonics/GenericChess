"""Rebuild the compact published summary from immutable archived raw records."""
import hashlib
import json
import zipfile
from pathlib import Path

p = Path(__file__).parent
with zipfile.ZipFile(p / 'sources-raw.zip') as archive:
    def read(name):
        return json.loads(archive.read('.local_agent/generated6-20261008/' + name + '.json'))
    analysis = read('analysis')
    extension = read('extension')
    profile = read('profile')
    result = dict(
        complete=True,
        producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        archive='../../archive/generated6_20261008/index.json',
        archive_sha256=hashlib.sha256((p / 'sources-raw.zip').read_bytes()).hexdigest(),
        scope='Four declared fresh6x6 hybrid rules; original capture-first route and separately declared semantic-first coverage/10sec extensions. All synthetic exposed development. Fixed Native attack evaluator/TT/order/q0; legality varies alone. Original terminals, zero coverage and caps remain archived. No strength or material utility claim.',
        inputs=analysis['inputs'],
        search_rows=analysis['search_rows'],
        event_frontiers=len(read('event-frontiers')['cases']),
        event_frontier_seconds=read('event-frontiers')['seconds'],
        transformation_rows=[{k: v for k, v in x.items() if k != 'rows'}
                             for x in analysis['transformation_rows']],
        extension_references=extension['references'],
        extension_searches=[dict(source=x['source'], all_equal=x['all_equal'],
            cells=[dict(native=y['native'], repeat=y['repeat'], wall_seconds=y['wall_seconds'],
                        nodes=y['decision']['nodes'], score=y['decision']['score'],
                        completed_depth=y['decision']['completed_depth']) for y in x['searches']])
            for x in extension['cases']],
        profile=dict(scope=profile['scope'], wall_seconds=profile['wall_seconds'],
                     parity=profile['prior_decision_equal'],
                     top_exclusive_functions=profile['functions_by_exclusive_time'][:12]))
output = p.parent.parent / 'research/data/generated6_20261008.json'
output.write_bytes((json.dumps(result, indent=2) + '\n').encode('utf-8'))
