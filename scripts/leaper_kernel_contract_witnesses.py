"""Finite pure-Leaper interface counterexamples; not a new solver/search/game."""
import copy,json,time,hashlib
from pathlib import Path
from collections import defaultdict
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.leaper_relative_history_pilot import record_interval,native_identity
from scripts.leaper_ordinary_geometry import ordinary_leap_geometry
from scripts.research_record import write_record,record_value
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import apply_action
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from tools.local_agent import session
from tools.local_agent.common import read_json

def freeze(inputs,out):
    rows=json.loads(Path(inputs).read_text())['rows'];maxply=[];aliases=[]
    for row in rows:
        r=copy.deepcopy(row);r['RuleSet']['max_ply']=4;r['fingerprint']=compute_fingerprint(ruleset_from_dict(r['RuleSet']));r['record']['ruleset_fingerprint']=r['fingerprint'];maxply.append(r)
    for row in rows[::2][:4]:
        r=copy.deepcopy(row);a=next(t for t in r['RuleSet']['piece_types'] if t['type_id']=='A');a['movement_atoms']+=copy.deepcopy(a['movement_atoms']);r['fingerprint']=compute_fingerprint(ruleset_from_dict(r['RuleSet']));r['record']={'schema_version':1,'ruleset_fingerprint':r['fingerprint'],'actions':[],'resigned_by':None};aliases.append(r)
    data={'maxply':maxply,'aliases':aliases,'cap_seconds':360,'max_transitions':1024,'Player_calls':0,'games':0,'purpose':'Falsify actual-ply-frontier==preavailability and destination-mask==full public action multiset;not existingbug/strength/generalproof'}
    write_record(Path(out),data);return data

def run(inputs,out):
    out=Path(out);assert not out.exists();out.mkdir(parents=True);data=freeze(inputs,out/'frozen-before-Core.json');tick=time.perf_counter();begin=session.now().isoformat();rows=[];count=0;failure=None
    def bound(needed=1):
        flags=read_json(Path('.local_agent/rollout.json'))
        assert not any(flags.get(k) for k in ('user_paused','stopped','research_stopped','stop_requested')),'userstop'
        assert time.perf_counter()-tick<360,'360scap';assert count+needed<=1024,'1024transitioncap'
    try:
        for row in data['maxply']:
            bound();c,s=make_session(row);assert ordinary_leap_geometry(c) is not None
            p=NativeSemanticLegalityProvider.try_create(c,strict=True);assert p is not None
            r=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,legal_binding_provider=p,check_provider=p.in_check,availability_provider=p.has_legal_action,use_plain_leaper_local_hash=True)
            root=s.to_record();findings=[]
            for a in r.legal_actions():
                bound();expected=apply_action(s.state,a,c);count+=1
                with r.pushed(a):
                    assert r.position==expected.position and r.terminal_status==expected.terminal_status
                    raw=p(r.position,r.ply_count);available=p.has_legal_action(r.position);core_available=semantic_engine_for(c).has_legal_action(r.position)
                    findings.append({'action':record_value(a),'terminal':record_value(r.terminal_status),'actual_ply_frontier':len(raw),'pre_availability':available,'Core_pre_availability':core_available,'checked':r._frames[-1].child_in_check,'incorrect_fused_no_action':not raw and available is True})
                assert s.to_record()==root
            r.assert_balanced();rows.append({'id':row['id'],'kind':'maxply','findings':findings});write_record(out/'rows.json',rows)
        for row in data['aliases']:
            bound();c,s=make_session(row);assert ordinary_leap_geometry(c) is not None
            groups=defaultdict(list)
            for a in s.legal_actions():groups[(a.from_square,a.to_square,a.actor_type_id,a.promotion_target_id)].append(a)
            witnesses=[]
            for actions in groups.values():
                if len(actions)<2:continue
                bound(2);a,b=actions[:2];left=apply_action(s.state,a,c);right=apply_action(s.state,b,c);count+=2
                assert left.position==right.position and left.history[-1].action_signature!=right.history[-1].action_signature
                witnesses.append({'a':record_value(a),'b':record_value(b),'same_full_position':True,'full_history_signatures':[left.history[-1].action_signature,right.history[-1].action_signature]})
            rows.append({'id':row['id'],'kind':'aliases','public_action_count':len(s.legal_actions()),'coordinate_projection_count':len(groups),'witnesses':witnesses});write_record(out/'rows.json',rows)
    except Exception as e:failure={'type':type(e).__name__,'error':str(e),'at':session.now().isoformat()};write_record(out/'failure.json',failure)
    m=[r for r in rows if r['kind']=='maxply'];a=[r for r in rows if r['kind']=='aliases'];summary={'status':'COMPLETE_FINITE_CONTRACT_WITNESSES' if failure is None and len(rows)==20 else 'INCOMPLETE_UNKNOWN','failure':failure,'rows':len(rows),'direct_public_Core_transitions':count,'maxply_root_groups':len(m),'frontier_availability_disagreements':sum(f['incorrect_fused_no_action'] for r in m for f in r['findings']),'alias_root_groups':len(a),'alias_groups_with_witness':sum(bool(r['witnesses']) for r in a),'Player_calls':0,'games':0,'native_binary':native_identity(),'seconds':time.perf_counter()-tick};write_record(out/'summary.json',summary);record_interval(begin,session.now().isoformat(),'validation',str(out/'summary.json'),out);print(json.dumps(summary));return summary
if __name__=='__main__':
    import sys;run(sys.argv[1],sys.argv[2])
