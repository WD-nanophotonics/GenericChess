"""Independent finite Core consumer of opening-capacity witnesses.

Reconstructs fixed literal controls from a saved test generator, freezes FULL
RuleSet/record before Core, then checks every actual first action and the exact
claimed reply. Same Core implementation; not an independent Core proof, WDL or
quality test. Saves failures and every observation before assertions.
"""
import json,hashlib,runpy
from pathlib import Path
from scripts.research_record import write_record,record_value
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.leaper_opening_capacity import opening_escape_capacity
from scripts.leaper_opening_structure import structural_opening_witness
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint

def run(out):
    out=Path(out);assert not out.exists();out.mkdir();generator=Path('tests/development/test_leaper_opening_structure.py');cases=[('ordinary',{}),('mixed-mate',{'mixed':True}),('mixed-far',{'mixed':True,'far':True}),('clock-one',{'maxply':1})];write_record(out/'frozen.json',{'cases':cases,'generator_sha256':hashlib.sha256(generator.read_bytes()).hexdigest(),'generator_text':generator.read_text(encoding='utf-8-sig'),'slots':'four fixedcase descriptors,all actualfirstactions onlyfor PASS;no replacement/fitting','max_Core_first_moves':128,'claim':'finite one-ply reply witness validation only'})
    build=runpy.run_path(str(generator))['build'];results=[];count=0
    for name,kw in cases:
        r=build(rule_only=True,**kw);fp=compute_fingerprint(ruleset_from_dict(r));row={'id':name,'RuleSet':r,'fingerprint':fp,'record':{'schema_version':1,'ruleset_fingerprint':fp,'actions':[],'resigned_by':None}};write_record(out/(name+'-input.json'),row);c,s=make_session(row);w=opening_escape_capacity(s.state,c);p=structural_opening_witness(s.state,c);result={'name':name,'capacity':w,'parity':p,'first_moves':[]}
        if w['status']=='SUFFICIENT_ONE_PLY_REPLY':
            for a in s.legal_actions():
                assert count<128;child=type(s).replay(c,s.to_record());child.submit(a);count+=1;source=a.from_square.rank*8+a.from_square.file;target=a.to_square.rank*8+a.to_square.file;witness=next(x for x in w['witnesses'] if x['source']==source and x['target']==target);dst=witness['defender_empty_escape'];reply=next((x for x in child.legal_actions() if x.to_square.rank*8+x.to_square.file==dst and c.types_by_id[x.actor_type_id].is_anchor),None);v={'action':record_value(a),'record_after':record_value(child.to_record()),'terminal':record_value(child.state.terminal_status),'claimed_reply':record_value(reply)};result['first_moves'].append(v);write_record(out/(name+'-observed.json'),result);assert not child.state.terminal_status.is_terminal and reply is not None
                # Consume the claimed actual legal reply under full Core history.
                child.submit(reply);v['reply_record']=record_value(child.to_record())
        results.append(result);write_record(out/(name+'-observed.json'),result)
    summary={'cases':[(x['name'],x['capacity']['status'],x['parity']['status'],len(x['first_moves'])) for x in results],'Core_first_moves':count,'Core_claimed_reply_moves':count,'new_Player':0,'newgames':0,'scope':'same-author distinctconsumer,shared Core,4 synthetic fixedrules;not unreachable-history certification or classwide formalproof'};write_record(out/'summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':run('.local_agent/threat-751b9f58/capacity-reader')
