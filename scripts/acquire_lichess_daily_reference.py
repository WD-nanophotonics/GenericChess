"""One fixed external reference acquisition, not model/external-game action."""
from pathlib import Path
from datetime import datetime, timezone
from time import monotonic
import hashlib
import json
import urllib.request
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'docs/research/data/lichess_daily_source_20261006.json'
BYTES = OUT.with_suffix('.response')
PROTOCOL = 'docs/research/LICHESS_DAILY_REFERENCE_PROTOCOL.md'
URL = 'https://lichess.org/api/puzzle/daily'


def main():
    if OUT.exists() or BYTES.exists(): raise FileExistsError('single acquisition never retried')
    start = monotonic()
    sources = ('scripts/acquire_lichess_daily_reference.py', PROTOCOL,
               'scripts/chess_approx_static_inventory.py', 'scripts/chess_exact_contact_family.py',
               'docs/research/data/chess_zero_target_correction_20261005.json')
    r = dict(complete=False, url=URL, requested_at=datetime.now(timezone.utc).isoformat(),
             http_requests=1, source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})
    OUT.write_text(json.dumps(r, indent=2)+'\n', encoding='utf-8')
    try:
        request = urllib.request.Request(URL, headers={'Accept': 'application/json', 'User-Agent': 'GenericChess-research-reference/1.0'})
        with urllib.request.urlopen(request, timeout=20) as response:
            r['http_status'] = response.status
            body = response.read(65537)
            r['response_headers'] = {key: response.headers.get(key) for key in ('Content-Type', 'Date', 'ETag')}
        BYTES.write_bytes(body); r['bytes'] = len(body); r['response_sha256'] = hashlib.sha256(body).hexdigest()
        if len(body) > 65536: raise ValueError('64KiB source cap')
        r['payload'] = json.loads(body)
        if r['http_status'] != 200 or not isinstance(r['payload'], dict): raise ValueError('JSON200 object required')
        r['complete'] = True
    except Exception as error: r['error'] = f'{type(error).__name__}: {error}'
    r['seconds'] = monotonic()-start
    r['source_hashes_unchanged'] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == digest for p, digest in r['source_sha256'].items())
    OUT.write_text(json.dumps(r, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in r.items() if k not in ('source_sha256', 'payload')}))


if __name__ == '__main__': main()
