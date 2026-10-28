"""Exposure extraction controls: executable text remains data; gaps survive."""
import gzip,json
from scripts.leaper_exposure_inventory import inspect
from scripts.leaper_motion_signature import motion_family_signature

def rule(offsets=((1,0),(0,1))):
    return {'piece_types':[{'is_anchor':True,'movement_atoms':[{'kind':'leap','offset':list(o)} for o in offsets]}]}

def test_literal_capsule_and_nonexecuted_payload(tmp_path):
    r=rule();p=tmp_path/'bundle.json.gz';p.write_bytes(gzip.compress(json.dumps({'members':[{'path':'a.json','text':json.dumps({'RuleSet':r})},{'path':'not-data.py','text':'raise RuntimeError("never execute")'}]}).encode()))
    x=inspect([str(p)]);assert len(x['rules'])==1 and not x['gaps'];assert x['rules'][0]['motion_signature']==motion_family_signature(r)

def test_nonleap_size_and_invalid_json_are_explicit_gaps(tmp_path):
    r=rule();r['piece_types'][0]['movement_atoms'][0]['kind']='ray';p=tmp_path/'r.json';p.write_text(json.dumps(r));q=tmp_path/'bad.json';q.write_text('{');z=tmp_path/'big.json.gz';z.write_bytes(gzip.compress(b' '*200))
    x=inspect([str(p),str(q),str(z)],maximum_bytes=100);assert len(x['gaps'])==3 and not x['rules']

def test_dihedral_actor_names_quotient_preserves_anchor_distinction():
    a=rule();b=rule(((0,-1),(-1,0)));assert motion_family_signature(a)==motion_family_signature(b)
    b['piece_types'][0]['is_anchor']=False;assert motion_family_signature(a)!=motion_family_signature(b)
