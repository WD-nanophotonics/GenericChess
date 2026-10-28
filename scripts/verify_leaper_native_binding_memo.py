"""Independent actual Core legal-set/binding consumer for the new memo."""
from collections import Counter
import json,time
from pathlib import Path
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.semantic_executor import semantic_engine_for,_semantic_public_action
from scripts.leaper_native_binding_memo import NativeBindingMemo
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.research_record import record_value,write_record
from scripts.leaper_relative_history_pilot import record_interval,stamp

def run(inputs,out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);rows=json.loads(Path(inputs).read_text())['rows'];results=[];tick=time.perf_counter();total=0
    for row in rows:
        begin=stamp();c,s=make_session(row);n=NativeSemanticLegalityProvider.try_create(c);m=NativeBindingMemo(n);assert m.admitted;core=semantic_engine_for(c);checks=0;states=0;owners=Counter();walk=[]
        with m.installed():
            for step in range(8):
                if s.state.terminal_status.is_terminal:break
                if total>=30000 or time.perf_counter()-tick>=180:raise RuntimeError('finitebindingcap')
                pos=s.state.position;pairs=n(pos,s.state.ply_count);hot=n(pos,s.state.ply_count);assert pairs==hot
                reference=[(_semantic_public_action(core,a),(a,b)) for a,b in core.iter_legal_action_bindings(pos,full_frontier=True)]
                assert Counter(a for a,b in pairs)==Counter(a for a,b in reference),'completeCoreactionmultiset'
                reference_bindings={a:b for a,b in reference}
                for public,(action,binding) in pairs:
                    fresh=m.original(pos,action,n.pattern_by_id[action.pattern_id]);assert binding==fresh==reference_bindings[public][1];assert action==reference_bindings[public][0];checks+=1;total+=1;owners[binding.actor_owner]+=1
                states+=1;actions=s.legal_actions()
                if not actions:break
                a=actions[(5*step+1)%len(actions)];walk.append(record_value(a));s.submit(a)
        d={'id':row['id'],'status':'PASS','complete_Core_frontiers':states,'bindings':checks,'owners':dict(owners),'memo_metrics':m.metrics,'full_final_record':record_value(s.to_record()),'walk':walk,'claim':'actualNative/independentCorecurrentlegalsyntaxandcompletebindingequality;not WDL/strength'};write_record(out/(row['id']+'.json'),d);results.append(d);record_interval(begin,stamp(),'validation',str(out/(row['id']+'.json')),out)
    summary={'status':'PASS','roots':len(results),'complete_Core_frontiers':sum(x['complete_Core_frontiers'] for x in results),'bindings':total,'memo_hits':sum(x['memo_metrics']['hits'] for x in results),'seconds':time.perf_counter()-tick,'Playercalls':0};write_record(out/'summary.json',summary);print(summary);return summary
