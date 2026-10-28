"""Bounded independent replay of NEW published opening-capacity replies.

No producer, structural generator, Player, qualifier, game campaign or solver.
"""
import argparse,gzip,json,subprocess,hashlib
from pathlib import Path,PurePosixPath
from collections import Counter
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.verify_published_boolean_returns import diagnostic_action
from scripts.research_record import record_value
SOURCE='31060392c62f051aeb851ccf3ee96365ea177c20'
BASE='docs/research/data/leaper_threat_admission_20261029/'
def raw(path):return subprocess.check_output(['git','show',SOURCE+':'+path])
def sha(b):return hashlib.sha256(b).hexdigest()
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def verify():
    mb=raw(BASE+'manifest.json');m=json.loads(mb);b=raw(BASE+m['bundle']['path']);assert sha(b)==m['bundle']['sha256'] and len(b)==m['bundle']['bytes'];d=json.loads(gzip.decompress(b))
    rows={x['path']:x for x in d['members']};declared={x['path']:x for x in m['members']};assert len(rows)==len(d['members'])==len(declared)==94 and set(rows)==set(declared)
    data={}
    for path,x in rows.items():
        assert not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts
        body=x['text'].encode('utf8');assert sha(body)==declared[path]['sha256']==x['sha256'] and len(body)==declared[path]['bytes']==x['bytes'];data[path]=body
    cases=[];first=reply=0
    for name in ['ordinary','mixed-far','mixed-mate','clock-one']:
        inp=json.loads(data[f'capacity-reader/{name}-input.json']);obs=json.loads(data[f'capacity-reader/{name}-observed.json']);rules=ruleset_from_dict(inp['RuleSet']);assert compute_fingerprint(rules)==inp['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rules);initial=GameSession.replay(c,deserialize_game_record(json.dumps(inp['record'])));assert initial.state.ply_count==0
        if name in ('ordinary','mixed-far'):
            assert obs['capacity']['status']=='SUFFICIENT_ONE_PLY_REPLY'
            legal=initial.legal_actions();assert Counter(enc(record_value(a)) for a in legal)==Counter(enc(x['action']) for x in obs['first_moves'])
            for x in obs['first_moves']:
                s=GameSession.replay(c,initial.to_record());a=diagnostic_action(x['action'],c.ruleset_fingerprint);s.submit(a);first+=1
                assert record_value(s.to_record())==x['record_after'] and record_value(s.state.terminal_status)==x['terminal'] and not s.state.terminal_status.is_terminal
                r=diagnostic_action(x['claimed_reply'],c.ruleset_fingerprint);assert c.types_by_id[r.actor_type_id].is_anchor
                assert r.to_square.rank*c.board_size+r.to_square.file in obs['capacity']['initial_safe']
                s.submit(r);reply+=1;assert record_value(s.to_record())==x['reply_record']
        else:
            assert obs['capacity']['status']=='UNKNOWN' and obs['first_moves']==[]
            if name=='clock-one':assert c.max_ply==1
        cases.append(dict(id=name,fingerprint=c.ruleset_fingerprint,status=obs['capacity']['status'],saved_first_moves=len(obs['first_moves']),max_ply=c.max_ply,repetition_limit=c.repetition_limit))
    assert first==reply==19
    return dict(source=SOURCE,manifest_sha256=sha(mb),bundle_sha256=sha(b),byte_bound_members=94,cases=cases,actual_saved_first_moves_replayed=first,actual_saved_anchor_replies_replayed=reply,publisher_original_quality_status=m['original_quality_status'],scope='New frozen reader only. All19actual legal first actions in the2sufficient cases and19claimed replies/full records independently replayed under sharedCore;2UNKNOWN controls stayUNKNOWN. No independent proof of all future positions/compiler families, no exposure census rerun, no64qualification/32game dispatch or completedWDL label. Earlier8Playerreturns/atlas only byte-bound here,not rerun or newly strength-validated.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();v=verify();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes((json.dumps(v,indent=2)+'\n').encode());print(json.dumps(v,indent=2))
