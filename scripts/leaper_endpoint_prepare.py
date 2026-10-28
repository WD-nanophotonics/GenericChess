"""Freeze ONE new executable-family threat-ordering endpoint before Core.

Not a replacement/resumption of stopped th7 qualifiers. No outcomes are read.
Every actor type starts on board and the ordinary schema has no creation path.
Families are the first eight literal bitmasks of three fixed orbit additions;
there is no retry, seed search or sample-until-admitted path.
"""
import copy,gzip,hashlib,json
from pathlib import Path
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from scripts.leaper_structural_layout import layout,KING
from scripts.leaper_motion_signature import motion_family_signature
from scripts.leaper_empty_geometry_signature import empty_geometry_signature
from scripts.research_record import write_record

def orbit(a,b):
    return sorted({(sx*x,sy*y) for x,y in ((a,b),(b,a)) for sx in (-1,1) for sy in (-1,1)})

def families():
    for bits in range(8):
        offsets=[set(orbit(1,0))|set(orbit(1,1)),set(orbit(2,1))|set(orbit(2,0)),set(orbit(2,2))|set(orbit(1,0))]
        for i,o in enumerate(((3,0),(3,1),(3,2))):
            if bits&(1<<i):offsets[i].update(orbit(*o))
        yield bits,[dict(type_id=t,name=t,is_anchor=t=='K',is_promotable=False,promotion_target_ids=[],movement_atoms=[dict(kind='leap',offset=list(o)) for o in sorted(moves)]) for t,moves in zip(('K','A','B','C'),(KING,*offsets))]

def freeze(out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    source=Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz');base=json.loads(gzip.decompress(source.read_bytes()))['rows'][0]['RuleSet'];rows=[];rejected=[]
    for family,types in families():
        for li,scan in enumerate(('row','column')):
            recipe=layout(types,scan=scan)
            if recipe['status']!='GEOMETRY_LAYOUT_ONLY':rejected.append(dict(family=family,layout=li,recipe=recipe));continue
            rule=copy.deepcopy(base);rule.pop('initial_setup_options',None);rule.update(board_size=8,max_ply=96,repetition_limit=4,metadata={},initial_position=[[None]*8 for _ in range(8)],promotion_allowed={},promotion_forced={},piece_types=types,drop_allowed={t:[[False]*64,[False]*64] for t in ('A','B','C')})
            for p in recipe['placements']:
                x,y=p['square'];assert rule['initial_position'][y][x] is None;rule['initial_position'][y][x]=dict(owner=p['owner'],base_type_id=p['type'],current_type_id=p['type'],promoted=False)
            fp=compute_fingerprint(ruleset_from_dict(rule));rows.append(dict(id=f'endpoint8-f{family}-h{li}',family=family,layout=li,RuleSet=rule,fingerprint=fp,record=dict(schema_version=1,ruleset_fingerprint=fp,actions=[],resigned_by=None),recipe=recipe,motion_signature=motion_family_signature(rule),empty_geometry_signature=empty_geometry_signature(rule),initialized_types=['K','A','B','C'],creatable_types=[],exposure='prospective DEVELOPMENT;partial archive noncollision does not certify holdout/semantic novelty'))
    write_record(out/'inputs.json',dict(study='endpoint8-new-20261029',rows=rows,rejected=rejected,base_schema_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),Core_calls_before_save=0,Player_calls_before_save=0,family_formula='bits0..7;A=orbit10+11+(30 if bit0);B=orbit21+20+(31 if bit1);C=orbit22+10+(32 if bit2);K=8neighbors',selection='all16 fixed literal recipes;any failure STOP whole;no replacement'))
    return rows,rejected
