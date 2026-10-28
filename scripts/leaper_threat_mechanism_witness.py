"""One fixed legal two-ply mechanism witness, not a WDL/strength panel."""
import copy,gzip,json
from pathlib import Path
from scripts.research_record import write_record,record_value
from scripts.leaper_pvs_quality_pilot import make_session
from generic_chess.rules.schema import compute_fingerprint,ruleset_from_dict
from scripts.leaper_threat_ordering import ThreatOrderer

def prepare(out):
    out=Path(out);assert not out.exists();out.mkdir();r=json.loads(gzip.decompress(Path('docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz').read_bytes()))['rows'][0]['RuleSet'];r=copy.deepcopy(r);r.pop('initial_setup_options',None)
    king=[(x,y) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0)];w=[(-1,0),(1,0),(0,-1),(0,1)];n=[(x,y) for x in (-2,-1,1,2) for y in (-2,-1,1,2) if abs(x)+abs(y)==3]
    r.update(board_size=8,max_ply=96,repetition_limit=4,initial_position=[[None]*8 for _ in range(8)],metadata={},promotion_allowed={},promotion_forced={});r['piece_types']=[dict(type_id=t,name=t,is_anchor=t=='K',is_promotable=False,promotion_target_ids=[],movement_atoms=[dict(kind='leap',offset=list(o)) for o in v]) for t,v in [('K',king),('W',w),('N',n),('Z',[(8,8)])]];r['drop_allowed']={t:[[False]*64,[False]*64] for t in ('W','N','Z')}
    placements=[(0,'K',4,0),(0,'W',1,0),(1,'K',7,7),(1,'N',1,3),(1,'Z',3,2)]+[(0,'Z',x,y) for x,y in [(3,0),(3,1),(4,1),(5,1),(5,0)]]
    for owner,tid,x,y in placements:r['initial_position'][y][x]=dict(owner=owner,base_type_id=tid,current_type_id=tid,promoted=False)
    fp=compute_fingerprint(ruleset_from_dict(r));row={'id':'boxed-e1-b4-knight-one-witness','RuleSet':r,'fingerprint':fp,'record':dict(schema_version=1,ruleset_fingerprint=fp,actions=[],resigned_by=None)}
    write_record(out/'input-before-Core.json',{'row':row,'selection':'literal mechanism construction: Wb1-a1/c1;Nd3 blocked by inert actor;not exposure/holdout or replacement for stopped16root panel','question':'Does positive threatcoverage distinguish a legal quiet preventing an immediate mate from equalglobalcoverage quiet failing it?','cap':'one root,two fixed quiet arms,all actual opponent legal replies,one defense to checked branch;0Player/solver/game','game_truth':'only savedCore two-ply terminal and legal reply,not exactWDL for surviving arm'})
    return row

def run(out):
    out=Path(out);row=prepare(out);c,s=make_session(row);before=s.to_record();o=ThreatOrderer(c);actions=s.legal_actions();selected=[next(a for a in actions if a.from_square.file==1 and a.from_square.rank==0 and a.to_square.file==x and a.to_square.rank==0) for x in (0,2)];features=o.feature(s.state,selected);globalf=o.feature(s.state,selected,override_targets=(1<<64)-1);arms=[]
    for a in selected:
        child=type(s).replay(c,before);child.submit(a);arm={'action':record_value(a),'threat_delta':features['scores'][a],'global_delta':globalf['scores'][a],'after_quiet':record_value(child.state.terminal_status),'replies':[]}
        for reply in child.legal_actions():
            g=type(s).replay(c,child.to_record());g.submit(reply);obs={'reply':record_value(reply),'terminal':record_value(g.state.terminal_status),'record':record_value(g.to_record())}
            if reply.from_square.file==1 and reply.from_square.rank==3 and reply.to_square.file==2 and reply.to_square.rank==1:obs['legal_defenses']=[record_value(x) for x in g.legal_actions()]
            arm['replies'].append(obs);write_record(out/f'arm-{len(arms)}.json',arm)
        arm['immediate_opponent_wins']=sum(x['terminal']['winner']==1 and x['terminal']['status']!='ongoing' for x in arm['replies']);arms.append(arm)
    assert features['scores'][selected[1]]>features['scores'][selected[0]]
    assert arms[0]['global_delta']==arms[1]['global_delta']
    assert arms[0]['immediate_opponent_wins']>0 and arms[1]['immediate_opponent_wins']==0
    assert s.to_record()==before
    summary={'target_mask':features['target_mask'],'arms':[{k:v for k,v in a.items() if k!='replies'} for a in arms],'opponent_replies':[len(a['replies']) for a in arms],'scope':'one literal Core-valid two-ply mechanism fixture;surviving arm WDL UNKNOWN;not main-search correction,quality/game evidence or replacement'};write_record(out/'summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':run('.local_agent/threat-751b9f58/mechanism-witness')
