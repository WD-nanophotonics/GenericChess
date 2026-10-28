"""Bounded research observer: actual budget-passed main child entry.

In-memory, single writer, reversible hooks only. No new legality/evaluation/TT
probes or budget checks. AST adds a callback AFTER the existing first negamax
budget check and wraps its own returns (never nested helper returns). Wrappers
retain the existing action iterator and its on-yield callbacks. Any dropped
witness/unsupported path is explicit UNKNOWN, never proof of zero activity.
"""
import ast,inspect,textwrap
from collections import Counter
from contextlib import contextmanager
from unittest.mock import patch
import generic_chess.ai.alphabeta.search as search
from generic_chess.ai.alphabeta.ordering import MoveOrderer
from scripts.leaper_threat_ordering import ThreatOrderer
from generic_chess.core.actions import action_to_dict

class ObserveSequence:
    def __init__(self,sequence,frame):self.sequence=sequence;self.frame=frame
    def __len__(self):return len(self.sequence)
    def __getitem__(self,key):return self.sequence[key]
    def __iter__(self):
        for rank,action in enumerate(self.sequence):
            self.frame['yielded']=(rank,action)
            yield action

class _Instrument(ast.NodeTransformer):
    def __init__(self):self.depth=0;self.entry_hooks=0;self.returns=[];self.conditions=[]
    def visit_FunctionDef(self,node):
        self.depth+=1
        if self.depth==1:self.generic_visit(node)
        self.depth-=1;return node
    def visit_If(self,node):
        self.conditions.append(ast.unparse(node.test));node.test=self.visit(node.test);node.body=[self.visit(x) for x in node.body];node.orelse=[self.visit(x) for x in node.orelse];self.conditions.pop();return node
    def visit_Expr(self,node):
        if ast.unparse(node.value)=='ctx.budget.check(ctx.stats)' and self.entry_hooks==0:
            self.entry_hooks+=1
            return [node,ast.copy_location(ast.Expr(ast.Call(ast.Attribute(ast.Name('_endpoint_observer',ast.Load()),'after_budget',ast.Load()),[ast.Name('ctx',ast.Load())],[])),node)]
        return node
    def visit_Return(self,node):
        # Nested functions are not visited by visit_FunctionDef.
        label='expanded_return'
        if any('entry' in x for x in self.conditions):label='TT_return'
        elif 'terminal.is_terminal' in self.conditions:label='terminal_return'
        elif 'winning is not None' in self.conditions:label='declaration_return'
        elif 'depth <= 0' in self.conditions:label='leaf_return'
        elif 'alpha >= beta' in self.conditions:label='window_cutoff_return'
        self.returns.append({'line':node.lineno,'source':label,'conditions':list(self.conditions)})
        node.value=ast.Call(ast.Attribute(ast.Name('_endpoint_observer',ast.Load()),'returned_value',ast.Load()),[ast.Constant(label),node.value or ast.Constant(None)],[]);return node

class EntryObserver:
    def __init__(self,query_id,limit=256):
        self.query_id=query_id;self.limit=limit;self.stack=[];self.sequence=0;self.root_attempt=0;self.roots=[];self.witnesses=[];self.dropped=0;self.errors=[];self.counts=Counter();self.accepted=None;self.proof_candidates=[];self.actual_provenance=[];self.instrumentation=None
    def error(self,exc):
        if len(self.errors)<8:self.errors.append(type(exc).__name__+':'+str(exc))
    def after_budget(self,ctx):
        try:
            f=self.stack[-1];assert f['ctx'] is ctx
            f['entered']=True;self.counts[(f['attempt'],'entered')]+=1
            if f['parent'] is not None:
                parent=f['parent'];parent['children']+=1;self.counts[(f['attempt'],'child_entry')]+=1
                if f['rank_changed']:
                    self.counts[(f['attempt'],'changed_rank_child_entry')]+=1
                    witness={'query':self.query_id,'call_id':f['id'],'parent_id':parent['id'],'root_attempt':f['attempt'],'requested_iteration':f['iteration'],'ply':f['ply'],'action':action_to_dict(f['action']),'baseline_rank':f['baseline_rank'],'candidate_rank':f['candidate_rank'],'repeat_for_same_parent_action':f['repeated'],'entry':'AFTER_ORIGINAL_BUDGET_CHECK','return':None,'source':None}
                    if len(self.witnesses)<self.limit:self.witnesses.append(witness);f['witness']=witness
                    else:self.dropped+=1
        except Exception as e:self.error(e)
    def returned_value(self,label,value):
        try:
            f=self.stack[-1];f['return_source']=label;self.counts[(f['attempt'],label)]+=1
        except Exception as e:self.error(e)
        return value
    def order(self,sequence,baseline):
        if not self.stack:return sequence
        try:
            f=self.stack[-1]
            if not isinstance(sequence,(list,tuple)) or not isinstance(baseline,(list,tuple)):
                self.error(ValueError('nonmaterialized sequence;not consumed for observation'));return sequence
            # Direct indexing never advances _ObservedActions.__iter__.
            f['baseline']=tuple(baseline[i] for i in range(len(baseline)));f['candidate']=tuple(sequence[i] for i in range(len(sequence)));f['yielded']=None
            self.counts[(f['attempt'],'order_calls')]+=1
            return ObserveSequence(sequence,f)
        except Exception as e:self.error(e);return sequence
    @contextmanager
    def installed(self):
        original=search.negamax;tree=ast.parse(textwrap.dedent(inspect.getsource(original)));transform=_Instrument();tree=transform.visit(tree);ast.fix_missing_locations(tree);assert transform.entry_hooks==1
        namespace={};exec(compile(tree,original.__code__.co_filename,'exec'),search.__dict__,namespace);instrumented=namespace['negamax'];self.instrumentation={'entry_hooks':transform.entry_hooks,'returns':transform.returns,'nested_helpers_excluded':True}
        old_base=MoveOrderer.order;old_threat=ThreatOrderer.order;old_prov=search._set_result_provenance;observer=self
        def base_order(orderer,*a,**kw):
            result=old_base(orderer,*a,**kw)
            if observer.stack:observer.stack[-1]['latest_baseline']=result
            return result if isinstance(orderer,ThreatOrderer) else observer.order(result,result)
        def threat_order(orderer,*a,**kw):
            result=old_threat(orderer,*a,**kw)
            baseline=observer.stack[-1].get('latest_baseline',result) if observer.stack else result
            return observer.order(result,baseline)
        def negamax(*args,**kw):
            state,depth,alpha,beta,ply,ctx=args[:6];action=kw.get('prev_action',args[6] if len(args)>6 else None);parent=observer.stack[-1] if observer.stack else None
            if parent is None:observer.root_attempt+=1
            observer.sequence+=1;f={'id':observer.sequence,'ctx':ctx,'parent':parent,'attempt':observer.root_attempt,'iteration':depth if parent is None else parent['iteration'],'depth':depth,'ply':ply,'action':action,'entered':False,'children':0,'return_source':None,'rank_changed':False,'repeated':False,'baseline_rank':None,'candidate_rank':None}
            if parent is not None and parent.get('yielded') is not None:
                rank,yielded=parent['yielded']
                if yielded==action:
                    ranks=[i for i,a in enumerate(parent.get('baseline',())) if a==action]
                    # Full identity, preserve duplicate ambiguity explicitly.
                    if len(ranks)==1:f.update(baseline_rank=ranks[0],candidate_rank=rank,rank_changed=ranks[0]!=rank)
                    else:observer.error(ValueError('ambiguous duplicate semantic action occurrence'))
                    seen=parent.setdefault('action_entries',Counter());f['repeated']=seen[(rank,action)]>0;seen[(rank,action)]+=1
            observer.stack.append(f)
            try:
                result=instrumented(*args,**kw)
                observer.counts[(f['attempt'],'normal_return')]+=1
                if f.get('witness') is not None:f['witness'].update(returned_score=result.score,return_='NORMAL',source=f['return_source']);f['witness']['return']='NORMAL'
                if parent is not None and parent['ply']==0 and -result.score>=search.MATE_THRESHOLD:
                    if len(observer.proof_candidates)<observer.limit:observer.proof_candidates.append({'call_id':f['id'],'root_attempt':f['attempt'],'action':action_to_dict(action),'score':-result.score,'returned_normally':True})
                    else:observer.dropped+=1
                return result
            except BaseException as exc:
                observer.counts[(f['attempt'],'abort_after_entry' if f['entered'] else 'abort_before_entry')]+=1
                if f.get('witness') is not None:f['witness']['return']='ABORT';f['witness']['exception']=type(exc).__name__+':'+str(exc)
                raise
            finally:
                if parent is None:
                    if len(observer.roots)<observer.limit:observer.roots.append({'attempt':f['attempt'],'iteration':f['iteration'],'call_id':f['id'],'entered':f['entered'],'return_source':f['return_source'],'children':f['children']})
                    else:observer.dropped+=1
                assert observer.stack.pop() is f
        def provenance(stats,source,ctx=None):
            result=old_prov(stats,source,ctx)
            try:
                event={'source':source,'root_attempt':observer.root_attempt,'completed_depth_at_hook':stats.completed_depth}
                if source=='main_iteration':observer.accepted=observer.root_attempt
                if source=='completed_root_win' and ctx is not None and ctx.root_completed_win is not None:
                    proof=ctx.root_completed_win[0];event['proof_action']=action_to_dict(proof.best_action);event['proof_score']=proof.score;event['observed_matching_returns']=[p for p in observer.proof_candidates if p['action']==event['proof_action'] and p['score']==proof.score]
                observer.actual_provenance.append(event)
            except Exception as e:observer.error(e)
            return result
        sentinel=object();prior=getattr(search,'_endpoint_observer',sentinel);search._endpoint_observer=self
        try:
            with patch.object(search,'negamax',negamax),patch.object(MoveOrderer,'order',base_order),patch.object(ThreatOrderer,'order',threat_order),patch.object(search,'_set_result_provenance',provenance):yield self
        finally:
            if prior is sentinel:del search._endpoint_observer
            else:search._endpoint_observer=prior
    def result(self,decision):
        retained=self.accepted if decision.result_source=='main_iteration' else None
        return {'query':self.query_id,'counts':{str(attempt):{kind:v for (a,kind),v in self.counts.items() if a==attempt} for attempt in sorted({a for a,k in self.counts})},'roots':self.roots,'witnesses':self.witnesses,'dropped':self.dropped,'errors':self.errors,'retained_root_attempt':retained,'result_source':decision.result_source,'completed_depth':decision.completed_depth,'provenance':self.actual_provenance,'retained_changed_entries':self.counts[(retained,'changed_rank_child_entry')] if retained is not None else None,'proof_candidates':self.proof_candidates,'capture_status':'COMPLETE_FOR_SCALAR_COUNTS_BOUNDED_WITNESSES' if not self.errors and not self.dropped else 'UNKNOWN_TRUNCATED_OR_ERROR','scope':'direct actual entry after budget,not causal quality/history/TT dependency proof;prior accepted attempts may affect later throughTT/history UNKNOWN','instrumentation':self.instrumentation}
