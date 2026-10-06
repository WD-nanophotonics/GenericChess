"""One public synthetic-FEN request after immutable local policy qualification."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.parse import urlencode
import hashlib,json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record
LOCAL='docs/research/data/chess_q1_reference_local_20261006.json'
OUT=ROOT/'docs/research/data/chess_q1_reference_external_20261006.json'
BODY=ROOT/'docs/research/data/chess_q1_reference_external_20261006.response.json'
SOURCES=('scripts/acquire_chess_q1_reference.py','docs/research/CHESS_Q1_REFERENCE_PREFLIGHT.md',LOCAL,'scripts/research_record.py')


def main():
    if OUT.exists() or BODY.exists():raise FileExistsError('one outcome acquisition; never retry')
    start=time.monotonic();r=dict(complete=False,request_attempts=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    write_record(OUT,r)
    try:
        local=json.loads((ROOT/LOCAL).read_text())
        if not local['complete'] or not local['source_hashes_unchanged']:raise ValueError('qualified prospective local policies required')
        for p,pin in local['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('frozen local drift')
        r['local_policy_record_sha256']=hashlib.sha256((ROOT/LOCAL).read_bytes()).hexdigest()
        r['initial_fen']=local['synthetic_initial_fen']
        r['request_url']='https://tablebase.lichess.org/standard?'+urlencode({'fen':r['initial_fen']})
        r['request_attempts']=1;r['sent_at_utc']=datetime.now(timezone.utc).isoformat();write_record(OUT,r)
        req=Request(r['request_url'],headers={'User-Agent':'GenericChess-research/1 (one synthetic position)','Accept':'application/json'})
        with urlopen(req,timeout=30) as response:
            r['http_status']=response.status;r['final_url']=response.url
            data=response.read(256*1024+1)
        if len(data)>256*1024:raise ValueError('response256KiB cap')
        BODY.write_bytes(data);r['response_bytes']=len(data);r['response_sha256']=hashlib.sha256(data).hexdigest()
        result=json.loads(data);rows=result['moves']
        moves={x['uci']:x for x in rows}
        if len(moves)!=len(rows) or set(moves)!=set(local['children']):raise ValueError('duplicate/missing/extraneous reference root actions')
        value={'win':1,'draw':0,'loss':-1}
        if result['category'] not in value or any(x['category'] not in value for x in rows):raise ValueError('ambiguous/unsupported category preserved as unknown')
        outcomes={k:-value[x['category']] for k,x in moves.items()}
        best=max(outcomes.values());ties=sorted(k for k,v in outcomes.items() if v==best)
        if best!=value[result['category']]:raise ValueError('parent/child orientation consistency')
        r.update(source_contract='Lichess standard50-move categories; NOT local F24F goal',
          local_history_contract='true synthetic initial history; no external repetition-history certificate',
          root_category=result['category'],root_owner_outcomes=outcomes,full_reference_ties=ties,
          policies={})
        for law,row in local['policies'].items():
            qt=row['full_ties'];ss=row['static_scores'];static=sorted(k for k,v in ss.items() if v==max(ss.values()))
            r['policies'][law]=dict(full_ties=qt,canonical=row['canonical'],canonical_outcome=outcomes[row['canonical']],
              minimum_tie_outcome=min(outcomes[k] for k in qt),maximum_tie_outcome=max(outcomes[k] for k in qt),
              all_ties_preserve_best=all(outcomes[k]==best for k in qt),static_full_ties=static,
              static_minimum_tie_outcome=min(outcomes[k] for k in static),static_maximum_tie_outcome=max(outcomes[k] for k in static))
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=time.monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps(r))


if __name__=='__main__':main()
