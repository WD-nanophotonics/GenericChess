"""One finite abstract counterexample to depth implying decision quality.

Calls the actual iterative mainline over a declared toy runtime. No real rules,
Native backend, Player, game campaign, training or timing/speed experiment.
"""
from contextlib import contextmanager
from types import SimpleNamespace as N
from unittest.mock import patch
from pathlib import Path
import hashlib,json,argparse
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.terminal import TerminalResult,TerminalStatus
from scripts.research_record import record_value

EDGES={'R':(('A','A1'),('B','B1')),'A1':(('a','A2'),),'B1':(('b','B2'),),'A2':(('win','AW'),),'B2':(('lose','BL'),)}
SEAT0_HEURISTIC={'R':0,'A1':10,'B1':0,'A2':-10,'B2':10}
WINNERS={'AW':0,'BL':1}

def control():
    outputs=[]
    def node(name,path=()):
        ply=len(path);terminal=TerminalResult(TerminalStatus.RULE_LOSS,WINNERS[name]) if name in WINNERS else TerminalResult(TerminalStatus.ONGOING)
        return N(name=name,path=path,ply_count=ply,position=N(side_to_move=ply%2),terminal_status=terminal)
    class Runtime:
        def __init__(self):self.state=node('R');self.depth=0;self.stats=None
        @property
        def terminal_status(self):return self.state.terminal_status
        def attach_stats(self,stats):self.stats=stats
        def legal_actions(self,checkpoint=None):
            if checkpoint:checkpoint()
            return [a for a,_ in EDGES.get(self.state.name,())]
        def in_check(self,*args,**kwargs):return False
        def search_key(self):return ('DECLARED_TOY_COMPLETE_PATH',self.state.path)
        @contextmanager
        def pushed(self,action,checkpoint=None):
            if checkpoint:checkpoint()
            old=self.state;target=dict(EDGES[old.name])[action];self.state=node(target,old.path+(action,));self.depth+=1;self.stats.runtime_pushes+=1
            try:yield self
            finally:self.state=old;self.depth-=1;self.stats.runtime_pops+=1
    for stop_after in (1,2,None):
        rt=Runtime();stats=SearchStatistics();events=[];calls=[]
        token=N(stop=False);token.is_cancelled=lambda:token.stop
        def value(state):
            signed=SEAT0_HEURISTIC[state.name]*(1 if state.position.side_to_move==0 else -1);calls.append(dict(node=state.name,seat0=SEAT0_HEURISTIC[state.name],actor=state.position.side_to_move,returned=signed));return signed
        def progress(depth,nodes,qnodes):
            events.append(dict(completed_depth=depth,nodes=nodes,qnodes=qnodes))
            if stop_after==depth:token.stop=True
        with patch.object(S.SearchPathRuntime,'from_state',lambda *a,**kw:rt),patch.object(S,'_declaration_options',lambda *a:[]),patch.object(S,'semantic_engine_for',lambda c:None):
            got=S.run_root_search(rt.state,N(),N(evaluate=value),TranspositionTable(),SearchLimits(max_depth=3,max_nodes=10000,quiescence_max_depth=0,quiescence_hard_max_depth=0),token,stats,use_tt=False,use_ordering=False,tuning=S.SearchTuning(use_root_tactical=False),progress_callback=progress)
        assert rt.depth==0 and rt.state.name=='R' and stats.runtime_pushes==stats.runtime_pops
        assert stats.result_source=='main_iteration' and stats.result_ordinary_qdepth==0 and stats.qnodes==0
        outputs.append(dict(stop_after_completed_iteration=stop_after,returned=record_value(got),retained_depth=stats.completed_depth,declared_terminal_winner_after_selected_forced_chain=0 if got[0]=='A' else 1,progress=events,leaf_calls=calls,stats=record_value(stats)))
    assert [x['returned'][0] for x in outputs]==['A','B','A']
    assert [x['retained_depth'] for x in outputs]==[1,2,3]
    assert outputs[0]['returned'][1]==outputs[1]['returned'][1]==10
    assert outputs[0]['returned'][3]==outputs[1]['returned'][3]=='cancelled'
    assert outputs[2]['returned'][1]==S.MATE_SCORE-3
    b=Path(S.__file__).read_bytes();return dict(definition=dict(edges=EDGES,seat0_heuristic=SEAT0_HEURISTIC,terminal_winners=WINNERS),actual_search_source_sha256=hashlib.sha256(b).hexdigest(),actual_search_LF_sha256=hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest(),outputs=outputs,scope='Three actual iterative-return calls on a declared finite abstract runtime; forced-chain winners follow the toy definition, not Core/WDL certification of any Leaper. Same evaluator throughout, Q0, TT/order/pruning/root scan OFF. Stop signals are explicitly tied to completed iteration, NOT equal wall or node budgets or a measured faster evaluator. Therefore this refutes a universal completed-depth=>quality implication; it is not evidence that the real mask worsens play, that deeper search is generally worse, or that a product repair is required.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();result=control();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps([dict(depth=x['retained_depth'],action=x['returned'][0],score=x['returned'][1],source=x['stats']['result_source'],reason=x['returned'][3],toy_winner=x['declared_terminal_winner_after_selected_forced_chain']) for x in result['outputs']],indent=2))
