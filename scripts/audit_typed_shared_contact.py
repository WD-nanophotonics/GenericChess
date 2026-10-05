"""Saved membership qualification of new actor-bound first-hit adapter."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.audit_contact_typed_geometry_valid import build
from generic_chess.rules.compiler import compile_ruleset_for_execution
from scripts.shared_contact_prefix import Profile
from scripts.nonpromotable_contact_prefix import NonpromotableContactPrefix
from scripts.typed_shared_contact_prefix import TypedNonpromotableContactPrefix
from scripts.full_contact_distances import qualify_target_free
OUT=ROOT/'docs/research/data/typed_shared_contact_20261005.json'
SOURCES=('scripts/audit_typed_shared_contact.py','scripts/typed_shared_contact_prefix.py','docs/research/TYPED_SHARED_CONTACT_PROTOCOL.md','scripts/audit_contact_typed_geometry_valid.py','docs/research/data/contact_typed_geometry_valid_20261005.json','scripts/nonpromotable_contact_prefix.py','scripts/shared_contact_prefix.py','scripts/full_contact_distances.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen typed shared qualification')
    start=monotonic();r=dict(complete=False,rows=[],candidates=0,public_transitions=0,enumerated=0,source_queries=0,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec')
    try:
        c=compile_ruleset_for_execution(build());saved=json.loads((ROOT/SOURCES[4]).read_text());assert saved['complete']
        for owner in (0,1):
            profiles=(Profile('X','X'),Profile('Y','Y'))
            old=NonpromotableContactPrefix(c,profiles,owner=owner,checkpoint=check)
            new=TypedNonpromotableContactPrefix(c,profiles,owner=owner,checkpoint=check)
            qualify_target_free(old);qualify_target_free(new)
            assert new.c is c
            r['candidates']+=old.stats['geometry_candidates']+new.stats['geometry_candidates']
            if r['candidates']>5000:raise ValueError('candidate cap')
            for row in saved['rows']:
                if row['owner']!=owner:continue
                p=Profile(row['type'],row['type']);s,d,b=(row[k] for k in ('source','target','blocker'))
                before=bool(old.pair_success(p,s,d)[0]&(1<<b));after=bool(new.pair_success(p,s,d)[0]&(1<<b))
                r['rows'].append(dict(owner=owner,type=row['type'],source=s,target=d,blocker=b,actual=row['actual'],untyped=before,typed=after))
                if after!=row['actual']:raise ValueError('saved membership mismatch')
        r['old_mismatches']=sum(x['actual']!=x['untyped'] for x in r['rows']);r['complete']=len(r['rows'])==8 and r['old_mismatches']==4
    except Exception as err:r['error']=f'{type(err).__name__}: {err}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    OUT.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in r.items() if k not in ('rows','source_sha256')}))
