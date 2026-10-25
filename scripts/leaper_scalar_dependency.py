"""Read-only bounded return-dependency observer; no evaluator/order/tree change.

Only scalar projections/action IDs and chosen return dependencies persist. Locals
are inspected transiently at actual return sites, never serialized or retained.
TT returns and incoming bounds remain explicitly opaque rather than invented PVs.
"""
import ast,inspect,textwrap
from collections import Counter
from scripts import leaper_design as L
from generic_chess.ai.alphabeta import search as S


def instrument(source,kind):
    t=ast.parse(textwrap.dedent(source));before=ast.dump(t,include_attributes=False);sites={}
    class Wrap(ast.NodeTransformer):
        def visit_FunctionDef(self,n):
            return self.generic_visit(n)if n is t.body[0]else n
        def visit_Return(self,n):
            sites[str(n.lineno)]=ast.unparse(n.value)
            n.value=ast.Call(ast.Name('_scalar_return',ast.Load()),[ast.Constant(kind),ast.Constant(n.lineno),n.value,ast.Call(ast.Name('locals',ast.Load()),[],[])],[])
            return n
    Wrap().visit(t);ast.fix_missing_locations(t)
    check=ast.parse(ast.unparse(t))
    class Strip(ast.NodeTransformer):
        def visit_FunctionDef(self,n):
            return self.generic_visit(n)if n is check.body[0]else n
        def visit_Return(self,n):
            assert n.value.func.id=='_scalar_return';n.value=n.value.args[2];return n
    Strip().visit(check);assert ast.dump(check,include_attributes=False)==before
    t.body[0].name='_scalar_'+kind+'_impl'
    return t,sites


class ScalarDependencies:
    def __init__(self,depths=(5,6),max_classifications=24,max_root_children=64):
        self.depths=set(depths);self.max_classifications=max_classifications;self.max_root_children=max_root_children
        self.stack=[];self.actions=[];self.action_ids={};self.records=[];self.counts=Counter();self.iteration=0;self.active=False;self.saved={};self.context=None
    def aid(self,a):
        if a is None:return None
        if a not in self.action_ids:self.action_ids[a]=len(self.actions);self.actions.append(L.record_value(a))
        return self.action_ids[a]
    def returned(self,kind,site,value,env):
        if not self.active:return value
        f=self.stack[-1];assert f['kind']==kind
        ctx=env['ctx'];runtime=ctx.runtime
        score=value.score if kind=='m' else value
        f.update(site=site,returned_score=score,final_alpha=env['alpha'],final_beta=env['beta'],remaining=ctx.compiled.max_ply-runtime.ply_count,absolute_ply=runtime.ply_count,actor=runtime.position.side_to_move,terminal=str(runtime.terminal_status.status.value)if hasattr(runtime.terminal_status.status,'value')else str(runtime.terminal_status.status))
        if kind=='m':
            f['best_action']=self.aid(value.best_action);f['result_pv']=[self.aid(a)for a in value.pv]
            entry=env.get('entry');f['tt_entry']=None if entry is None else dict(depth=entry.depth,bound=entry.bound.name,stored_score=entry.score)
        else:
            f['in_check']=env.get('in_check');f['stand_pat']=env.get('stand_pat');f['ordinary_qdepth']=S._ordinary_qdepth_limit(ctx);f['hard_qdepth']=ctx.qhard_depth_limit
        self.counts[(self.iteration,kind,site)]+=1
        return value
    def call(self,kind,args,kw):
        if kind=='m'and args[4]==0:self.iteration=args[1];self.active=self.iteration in self.depths
        if not self.active:return self.impl[kind](*args,**kw)
        if kind=='m':depth,alpha,beta,ply,ctx=args[1:6];qd=None;edge=self.aid(kw.get('prev_action'))
        else:alpha,beta,ply,qd,ctx=args;depth=None;edge=None
        self.context=ctx;parent=self.stack[-1]if self.stack else None
        if kind=='q'and parent and parent['kind']=='q':edge=parent.get('pending_action')
        path=(parent['path']+[edge])if parent and edge is not None else(list(parent['path'])if parent else[])
        f=dict(kind=kind,depth=depth,qdepth=qd,ply=ply,entry_alpha=alpha,entry_beta=beta,path=path,edge=edge,children=[],classifications=[])
        self.stack.append(f)
        try:r=self.impl[kind](*args,**kw)
        except S.SearchAborted:
            self.counts[(self.iteration,kind,'ABORT')]+=1;raise
        finally:self.stack.pop()
        assert 'returned_score'in f
        candidates=f.pop('children');dependency=None;why='OPAQUE_OR_BOUND'
        if kind=='m':
            selected=[x for x in candidates if x['trace']['kind']=='m'and x['edge']==f['best_action']and -x['score']==f['returned_score']]
            if selected:dependency=selected[0]['trace'];why='CHOSEN_MAIN_CHILD'
            elif any(x['trace']['kind']=='q'and x['score']==f['returned_score']for x in candidates):dependency=next(x['trace']for x in candidates if x['trace']['kind']=='q'and x['score']==f['returned_score']);why='Q_RETURN'
        else:
            best=max(candidates,key=lambda x:-x['score'])if candidates else None
            if best and -best['score']==f['returned_score']and f['returned_score']>f['entry_alpha']and(f['stand_pat']is None or f['returned_score']>f['stand_pat']):dependency=best['trace'];why='Q_CHILD'
            elif f['stand_pat']==f['returned_score']:why='STAND_PAT_VALUE'
            elif f['returned_score']==f['entry_alpha']:why='INCOMING_ALPHA_BOUND'
            else:why='RETURN_SITE'
        f['dependency_reason']=why;f['dependency']=dependency;f['bound_vs_entry']='UPPER'if f['returned_score']<=alpha else'LOWER'if f['returned_score']>=beta else'EXACT'
        if kind=='m'and ply==0:
            f['root_children']=candidates[:self.max_root_children];f['root_children_truncated']=len(candidates)>self.max_root_children
            self.records.append(dict(iteration=self.iteration,trace=f))
        if parent:parent['children'].append(dict(edge=edge,score=f['returned_score'],trace=f))
        return r
    def edge(self,action,*args):
        if not self.active:return S._quiescence_runtime(*args)
        parent=self.stack[-1];old=parent.get('pending_action');parent['pending_action']=self.aid(action)
        try:return S._quiescence_runtime(*args)
        finally:parent['pending_action']=old
    def classify(self,action,*args,**kw):
        result=self.saved['noisy_child'](action,*args,**kw)
        if self.active and self.stack and self.stack[-1]['kind']=='q':
            f=self.stack[-1];self.counts[(self.iteration,'classified',bool(result))]+=1
            if len(f['classifications'])<self.max_classifications:f['classifications'].append(dict(action=self.aid(action),noisy=bool(result)))
            else:f['classifications_truncated']=True
        return result
    def __enter__(self):
        self.saved={n:getattr(S,n)for n in ['negamax','_quiescence_runtime','noisy_child']};self.impl={};self.sites={}
        S._scalar_return=self.returned;S._scalar_edge=self.edge
        for kind,name in [('m','negamax'),('q','_quiescence_runtime')]:
            tree,sites=instrument(inspect.getsource(self.saved[name]),kind);self.sites[kind]=sites
            if kind=='q':
                class Edges(ast.NodeTransformer):
                    def visit_Call(self,n):
                        if isinstance(n.func,ast.Name)and n.func.id=='_quiescence_runtime':n.func.id='_scalar_edge';n.args.insert(0,ast.Name('action',ast.Load()))
                        return self.generic_visit(n)
                Edges().visit(tree);ast.fix_missing_locations(tree)
            exec(compile(tree,'<scalar-dependency-'+kind+'>','exec'),S.__dict__);self.impl[kind]=getattr(S,'_scalar_'+kind+'_impl')
        S.negamax=lambda *a,**k:self.call('m',a,k);S._quiescence_runtime=lambda *a,**k:self.call('q',a,k);S.noisy_child=self.classify
        return self
    def __exit__(self,*args):
        for n,value in self.saved.items():setattr(S,n,value)
        for n in ['_scalar_return','_scalar_edge','_scalar_m_impl','_scalar_q_impl']:
            if hasattr(S,n):delattr(S,n)
        assert not self.stack
        if self.context is not None:self.context.runtime.assert_balanced()
        self.context=None
    def export(self):
        return dict(actions=self.actions,records=self.records,counts=[dict(key=list(k),count=v)for k,v in self.counts.items()],return_sites=self.sites,scope='Chosen scalar dependency chains only, not all-defense proof. Untraced TT/incoming bounds and missing/truncated classifications remain UNKNOWN. Full input record plus action-ID path supplies history; no runtime object retained.')
