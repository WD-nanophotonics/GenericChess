"""Freeze literal full-rule threat panel BEFORE any Core admission."""
import copy,gzip,json,hashlib
from pathlib import Path
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from scripts.research_record import write_record

def prepare(out):
    out=Path(out);assert not out.exists();out.mkdir()
    draftpath=Path('docs/research/data/leaper_static_eval_20261029/fresh-family-draft.json');draft=json.loads(draftpath.read_text());base=json.loads(gzip.decompress(Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz').read_bytes()))['rows'][0]['RuleSet'];rows=[]
    for family in draft['proposed']:
        for layout,home in enumerate(draft['layouts']):
            r=copy.deepcopy(base);r.update(board_size=7,max_ply=96,repetition_limit=4,metadata={},initial_position=[[None]*7 for _ in range(7)],promotion_allowed={},promotion_forced={});r.pop('initial_setup_options',None)
            r['piece_types']=[dict(type_id=t,name=t,movement_atoms=[dict(kind='leap',offset=o) for o in offsets],is_anchor=t=='K',is_promotable=False,promotion_target_ids=[]) for t,offsets in zip(('K','A','B','C'),(family['anchor'],*family['actors']))];r['drop_allowed']={t:[[False]*49,[False]*49] for t in ('A','B','C')}
            for owner in (0,1):
                for typ,x,y in home:
                    if owner:x,y=6-x,6-y
                    assert r['initial_position'][y][x] is None;r['initial_position'][y][x]=dict(owner=owner,base_type_id=typ,current_type_id=typ,promoted=False)
            fp=compute_fingerprint(ruleset_from_dict(r));rows.append(dict(id=f'th7-f{family["family"]}-h{layout}',family=family['family'],layout=layout,RuleSet=r,fingerprint=fp,record=dict(schema_version=1,ruleset_fingerprint=fp,actions=[],resigned_by=None),exposure='DEVELOPMENT;finite signature audit only;not holdout'))
    assert len(rows)==16 and len({r['fingerprint'] for r in rows})==16
    write_record(out/'inputs.json',{'rows':rows,'draft_sha256':hashlib.sha256(draftpath.read_bytes()).hexdigest(),'Core_calls_before_save':0})
    return rows
if __name__=='__main__':prepare('.local_agent/threat-751b9f58/panel')
