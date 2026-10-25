"""Bounded actual-assignment dependencies for shallow pure-Leaper diagnosis.
No numeric-equality causal inference, no extra semantic/evaluator invocation.
"""
import ast, inspect, textwrap
from collections import Counter
from scripts import leaper_design as L
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation import evaluator as EM

WATCH={'alpha','beta','best','best_action','best_pv','score','null_score',
       'child_result','stand_pat','cached_score','entry','actions','in_check'}


def transform(function,kind):
    tree=ast.parse(textwrap.dedent(inspect.getsource(function)))
    before=ast.dump(tree,include_attributes=False);root=tree.body[0];sites={}
    def method(name,args):
        return ast.Call(ast.Attribute(ast.Name('_leaper_dependency',ast.Load()),name,ast.Load()),args,[])
    class Add(ast.NodeTransformer):
        def visit_FunctionDef(self,n):
            return self.generic_visit(n)if n is root else n
        def visit_Call(self,n):
            original=ast.unparse(n)
            n=self.generic_visit(n)
            if isinstance(n.func,ast.Name)and n.func.id in {'child_search','quiescence'}:
                return ast.copy_location(method('invoke',[ast.Constant(original),n.func,*n.args]),n)
            if kind=='q'and isinstance(n.func,ast.Name)and n.func.id=='_quiescence_runtime':
                return ast.copy_location(method('qedge',[ast.Name('action',ast.Load()),ast.Constant(original),*n.args]),n)
            if ast.unparse(n.func)=='ctx.tt.probe':
                return ast.copy_location(method('probe',[n]),n)
            return n
        def visit_Assign(self,n):
            names=[x.id for t in n.targets for x in ast.walk(t)if isinstance(x,ast.Name)]
            watched=[x for x in names if x in WATCH]
            expr=ast.unparse(n.value);reads=sorted({x.id for x in ast.walk(n.value)if isinstance(x,ast.Name)and isinstance(x.ctx,ast.Load)})
            self.generic_visit(n)
            if not watched:return n
            note=ast.Expr(method('assigned',[ast.Constant(','.join(watched)),ast.Constant(expr),ast.Constant(','.join(reads)),ast.Call(ast.Name('locals',ast.Load()),[],[])]))
            return [n,ast.copy_location(note,n)]
        def visit_Return(self,n):
            expr=ast.unparse(n.value);sites[str(n.lineno)]=expr
            n.value=self.visit(n.value)
            n.value=method('returned',[ast.Constant(kind),ast.Constant(n.lineno),ast.Constant(expr),n.value,ast.Call(ast.Name('locals',ast.Load()),[],[])])
            return n
    Add().visit(tree);ast.fix_missing_locations(tree)
    check=ast.parse(ast.unparse(tree));checkroot=check.body[0]
    class Strip(ast.NodeTransformer):
        def visit_FunctionDef(self,n):
            return self.generic_visit(n)if n is checkroot else n
        def visit_Expr(self,n):
            if isinstance(n.value,ast.Call)and ast.unparse(n.value.func)=='_leaper_dependency.assigned':return None
            return self.generic_visit(n)
        def visit_Call(self,n):
            if isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='_leaper_dependency':
                if n.func.attr=='returned':return self.visit(n.args[3])
                if n.func.attr=='probe':return self.visit(n.args[0])
                if n.func.attr=='invoke':return ast.Call(n.args[1],[self.visit(a)for a in n.args[2:]],[])
                if n.func.attr=='qedge':return ast.Call(ast.Name('_quiescence_runtime',ast.Load()),[self.visit(a)for a in n.args[2:]],[])
            return self.generic_visit(n)
    Strip().visit(check)
    assert ast.dump(check,include_attributes=False)==before,'non-reversible observer AST'
    root.name='_leaper_dependency_'+kind+'_impl'
    return tree,sites


class AssignmentDependencies:
    def __init__(self,depths=(3,4),cap=100000):
        self.depths=set(depths);self.cap=cap;self.events=[];self.calls=[];self.actions=[]
        self.action_ids={};self.stack=[];self.eval_stack=[];self.dropped=0
        self.next_event=0;self.next_call=0;self.active=False;self.iteration=0
        self.call_cap=20000;self.dropped_calls=0
        self.impl={};self.sites={};self.classified=Counter()

    def aid(self,a):
        if a is None:return None
        if a not in self.action_ids:
            self.action_ids[a]=len(self.actions);self.actions.append(L.record_value(a))
        return self.action_ids[a]

    def emit(self,data):
        self.next_event+=1;data=dict(id=self.next_event,**data)
        if len(self.events)<self.cap:self.events.append(data)
        else:self.dropped+=1
        return dict(type='event',id=data['id'])

    def invoke(self,expr,function,*args):
        if not self.active:return function(*args)
        f=self.stack[-1];old=f.get('pending');f['pending']=dict(expression=expr,alpha_source=f['vars'].get('alpha'),beta_source=f['vars'].get('beta'))
        try:return function(*args)
        finally:f['pending']=old

    def qedge(self,action,expr,*args):
        if not self.active:return S._quiescence_runtime(*args)
        f=self.stack[-1];old=f.get('pending_action');f['pending_action']=self.aid(action)
        try:return self.invoke(expr,S._quiescence_runtime,*args)
        finally:f['pending_action']=old

    def probe(self,entry):
        if self.active:
            snap=None if entry is None else dict(depth=entry.depth,bound=entry.bound.name,score=entry.score,best_action=self.aid(entry.best_action))
            ref=self.emit(dict(kind='TT_PROBE',call_id=self.stack[-1]['id'],entry=snap,producer='UNKNOWN_NOT_CAPTURED'))
            self.stack[-1]['last_tt']=ref
        return entry

    def assigned(self,names,expr,readnames,env):
        if not self.active:return
        f=self.stack[-1]
        reads={n:f['vars'].get(n,dict(type='UNTRACKED',name=n))for n in readnames.split(',')if n}
        scalar={n:env[n]for n in ('alpha','beta','best','score','null_score','stand_pat','cached_score')if n in env}
        ref=self.emit(dict(kind='ASSIGN',call_id=f['id'],names=names,expression=expr,reads=reads,
            scalar=scalar,action=self.aid(env.get('action')),best_action=self.aid(env.get('best_action')),
            last_child=f.get('last_child'),last_eval=f.get('last_eval'),last_tt=f.get('last_tt')))
        for name in names.split(','):f['vars'][name]=ref
        if 'actions'in names.split(','):
            f['generated_actions']=[self.aid(a)for a in env['actions']]

    def returned(self,kind,site,expr,value,env):
        if not self.active:return value
        f=self.stack[-1];assert f['kind']==kind
        score=value.score if kind=='m'else value
        ref=self.emit(dict(kind='RETURN',call_id=f['id'],site=site,expression=expr,
            score=score,sources=dict(f['vars']),last_child=f.get('last_child'),last_eval=f.get('last_eval'),last_tt=f.get('last_tt'),
            final_alpha=env['alpha'],final_beta=env['beta'],original_alpha=env.get('original_alpha'),
            in_check=env.get('in_check'),stand_pat=env.get('stand_pat'),
            ordinary_qdepth=S._ordinary_qdepth_limit(env['ctx']),hard_qdepth=env['ctx'].qhard_depth_limit,
            neutral_present=env.get('neutral')is not None,
            best_action=self.aid(value.best_action)if kind=='m'else None,
            actual_pv=[self.aid(a)for a in value.pv]if kind=='m'else None))
        f['return_ref']=ref;f['score']=score;return value

    def call(self,kind,args,kwargs):
        if kind=='m'and args[4]==0:
            self.iteration=args[1];self.active=self.iteration in self.depths
        if not self.active:return self.impl[kind](*args,**kwargs)
        if kind=='m':
            depth,a,b,ply,ctx=args[1:6];qd=None;edge=self.aid(kwargs.get('prev_action'))
        else:
            a,b,ply,qd,ctx=args;depth=None;edge=self.stack[-1].get('pending_action')if self.stack else None
        parent=self.stack[-1]if self.stack else None
        self.next_call+=1;cid=self.next_call
        path=(parent['path']+[edge])if parent and edge is not None else(list(parent['path'])if parent else[])
        f=dict(id=cid,parent_id=parent['id']if parent else None,kind=kind,iteration=self.iteration,
            depth=depth,qdepth=qd,ply=ply,entry_alpha=a,entry_beta=b,path=path,edge=edge,
            callsite=parent.get('pending')if parent else None,vars={},generated_actions=None,
            completed=False,actor=ctx.runtime.position.side_to_move,absolute_ply=ctx.runtime.ply_count)
        for n,v in [('alpha',a),('beta',b)]:f['vars'][n]=dict(type='ENTRY_BOUND',call_id=cid,name=n,value=v)
        self.stack.append(f)
        try:
            value=self.impl[kind](*args,**kwargs);f['completed']=True
            assert 'return_ref'in f
            return value
        except BaseException as exc:
            f['exception_type']=type(exc).__name__;f['exception_message']=str(exc);raise
        finally:
            self.stack.pop();f.pop('pending',None);f.pop('pending_action',None)
            if len(self.calls)<self.call_cap:self.calls.append(f)
            else:self.dropped_calls+=1
            if parent:parent['last_child']=dict(type='call',id=cid)

    def classify(self,*args,**kwargs):
        value=self.saved['noisy_child'](*args,**kwargs)
        if self.active:
            self.classified[bool(value)]+=1
            self.emit(dict(kind='CLASSIFY',call_id=self.stack[-1]['id'],action=self.aid(args[0]),noisy=bool(value),scope='Actual short-circuit classification only; not all predicates.'))
        return value

    def evaluate(self,state,evaluator,ctx):
        if not self.active:return self.saved['_evaluate'](state,evaluator,ctx)
        f=self.stack[-1];details={};self.eval_stack.append(details)
        try:value=self.saved['_evaluate'](state,evaluator,ctx)
        finally:self.eval_stack.pop()
        details.pop('_actual_maps',None)
        profile=evaluator._profile;position=state.position
        material=sum((1 if p.owner==0 else -1)*profile.board_value_by_type[p.current_type_id]for p in position.board if p is not None)
        material+=sum((1 if owner==0 else -1)*count*profile.hand_value_by_base_type[tid]for owner in (0,1)for tid,count in position.hands[owner].counts)
        cfg=evaluator._config
        attacks=details.get('attack_counts',[0,0]);esc=details.get('anchor_escapes',{});hit=details.get('anchor_attacked',{})
        mobility=cfg.dynamic_mobility_weight*(attacks[0]-attacks[1])
        escape=cfg.anchor_escape_weight*(esc.get('0',0)-esc.get('1',0)-10*int(hit.get('0',False))+10*int(hit.get('1',False)))
        reconstructed=material+mobility+escape+details.get('promotion_sum',0)
        details.update(mobility_seat0=mobility,anchor_term_seat0=escape,reconstructed_raw_side_to_move=reconstructed if position.side_to_move==0 else -reconstructed)
        f['last_eval']=self.emit(dict(kind='EVALUATE',call_id=f['id'],value=value,side=position.side_to_move,material_seat0=material,**details))
        return value

    def __enter__(self):
        assert not hasattr(S,'_leaper_dependency')
        self.saved={n:getattr(S,n)for n in ['negamax','_quiescence_runtime','noisy_child','_evaluate']}
        self.saved_attack=Evaluator._attack_maps;self.saved_escape=Evaluator._anchor_escape
        self.saved_anchor=EM.anchor_square;self.saved_promotion=Evaluator._promotion_bonus
        def attacks(evaluator,state):
            actual=self.saved_attack(evaluator,state)
            if self.active and self.eval_stack:
                self.eval_stack[-1]['attack_counts']=[len(a)for a in actual]
                self.eval_stack[-1]['_actual_maps']=actual
            return actual
        def escape(evaluator,position,owner,opponent):
            value=self.saved_escape(evaluator,position,owner,opponent)
            if self.active and self.eval_stack:self.eval_stack[-1].setdefault('anchor_escapes',{})[str(owner)]=value
            return value
        def anchor(position,owner,compiled):
            square=self.saved_anchor(position,owner,compiled)
            if self.active and self.eval_stack:
                f=self.eval_stack[-1]
                if '_actual_maps'in f:
                    f.setdefault('anchor_attacked',{})[str(owner)]=square in f['_actual_maps'][1-owner]
            return square
        def promotion(evaluator,piece,index):
            value=self.saved_promotion(evaluator,piece,index)
            if self.active and self.eval_stack:
                f=self.eval_stack[-1];f['promotion_sum']=f.get('promotion_sum',0)+value
            return value
        try:
            S._leaper_dependency=self
            for kind,name in [('m','negamax'),('q','_quiescence_runtime')]:
                tree,sites=transform(self.saved[name],kind);self.sites[kind]=sites
                exec(compile(tree,'<actual-assignment-'+kind+'>','exec'),S.__dict__)
                self.impl[kind]=getattr(S,'_leaper_dependency_'+kind+'_impl')
            S.negamax=lambda *a,**k:self.call('m',a,k)
            S._quiescence_runtime=lambda *a,**k:self.call('q',a,k)
            S.noisy_child=self.classify;S._evaluate=self.evaluate
            Evaluator._attack_maps=attacks;Evaluator._anchor_escape=escape
            EM.anchor_square=anchor;Evaluator._promotion_bonus=promotion
            return self
        except BaseException:
            self.__exit__(None,None,None)
            raise

    def __exit__(self,*exc):
        for n,v in self.saved.items():setattr(S,n,v)
        Evaluator._attack_maps=self.saved_attack;Evaluator._anchor_escape=self.saved_escape
        EM.anchor_square=self.saved_anchor;Evaluator._promotion_bonus=self.saved_promotion
        for n in ['_leaper_dependency','_leaper_dependency_m_impl','_leaper_dependency_q_impl']:
            if hasattr(S,n):delattr(S,n)
        assert not self.stack and not self.eval_stack

    def export(self):
        return dict(actions=self.actions,calls=self.calls,events=self.events,dropped_events=self.dropped,
            cap=self.cap,call_cap=self.call_cap,dropped_calls=self.dropped_calls,classifications={str(k):v for k,v in self.classified.items()},return_sites=self.sites,
            scope='Actual assignment/call refs, never same-number dependency matching. TT producers NOT_CAPTURED. Entry bound sources and original/postTT windows retained. Missing refs/truncation UNKNOWN. No runtime owner objects; only root action-ID paths and scalar snapshots. Evaluation hooks observe actual maps/escape calls once, not extra semantic/evaluator queries.')
