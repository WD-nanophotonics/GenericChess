"""Read-only, single-call clock-horizon observer. Never changes ordering or values."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import argparse, ast, hashlib, inspect, json, textwrap, time, traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def stamp(): return datetime.now(timezone.utc).isoformat()
def canonical(x): return json.dumps(x, sort_keys=True, separators=(',', ':'))

def instrument(source):
    """Wrap original return expressions; removing wrappers recovers identical AST."""
    tree=ast.parse(textwrap.dedent(source)); original=ast.dump(tree, include_attributes=False)
    sites={}
    class Wrap(ast.NodeTransformer):
        def visit_Return(self, node):
            sites[str(node.lineno)]=ast.unparse(node.value)
            node.value=ast.Call(ast.Name('_clock_trace_return', ast.Load()),
                [ast.Constant(node.lineno), node.value]+[ast.Name(n, ast.Load()) for n in ('alpha','beta','ply','qdepth','ctx')], [])
            return node
    Wrap().visit(tree); ast.fix_missing_locations(tree)
    class Strip(ast.NodeTransformer):
        def visit_Return(self,node):
            assert isinstance(node.value, ast.Call) and node.value.func.id=='_clock_trace_return'
            node.value=node.value.args[1]; return node
    check=ast.parse(ast.unparse(tree)); Strip().visit(check)
    assert ast.dump(check,include_attributes=False)==original
    return tree, sites

def runtime_projection(runtime):
    return dict(position=L.record_value(runtime.position),ply_count=runtime.ply_count,terminal_status=L.record_value(runtime.terminal_status),history=L.record_value(runtime.history))

def run(d):
    from generic_chess.ai.alphabeta import search as S
    from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
    from generic_chess.ai.alphabeta.tuning import SearchTuning
    from generic_chess.ai.limits import SearchLimits
    plan=L.load(d/'plan.json'); inp=Path(plan['inputs']); data=L.load(inp)
    assert hashlib.sha256(inp.read_bytes()).hexdigest()==plan['inputs_sha256']
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==plan['source_sha256']
    assert not (d/'receipt.json').exists() and not (d/'query.json').exists(), 'closed/no refill'
    case=next(x for x in data['cases'] if x['key']==plan['key'])
    c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
    sess=replay(c,case['record']); assert L.state_sha(sess.state)==case['state_sha256']
    legal=sess.legal_actions(); aid={a:i for i,a in enumerate(sorted(legal,key=str))}
    actions={str(i):L.record_value(a) for a,i in aid.items()}
    original=S.negamax; oq=S._quiescence_runtime
    assert hashlib.sha256(inspect.getsource(oq).encode()).hexdigest()==plan['q_source_sha256']
    tree,sites=instrument(inspect.getsource(oq))
    before=stamp(); tick=time.perf_counter(); cpu=time.process_time()
    active={'depth':0,'branch':None}; stats={}; samples={}; children=[]; iterations=[]; roots=[]
    class Stop:
        last=0.; flag=False
        def is_cancelled(self):
            now=time.perf_counter()
            if now-self.last>.25: self.last=now; self.flag=stopped() or now-tick>plan['batch_seconds']
            return self.flag
    def returned(site,value,alpha,beta,ply,qdepth,ctx):
        st=ctx.runtime.state; rem=c.max_ply-st.ply_count
        key=(active['depth'],active['branch'],site,rem,qdepth)
        row=stats.setdefault(key,[0,value,value,0]);row[0]+=1;row[1]=min(row[1],value);row[2]=max(row[2],value);row[3]+=value
        samplekey=(active['depth'],active['branch'],site,rem)
        if active['depth'] in (6,7) and len(samples)<plan['max_samples'] and samplekey not in samples:
            samples[samplekey]=dict(key=list(key),value=value,alpha=alpha,beta=beta,ply=ply,runtime_projection=runtime_projection(ctx.runtime),projection_scope='Runtime identities and full history; not portable GameState SHA')
        return value
    def observe(*args,**kw):
        depth,alpha,beta,ply,ctx=args[1:6]
        if ply==0: active['depth']=depth
        parent=active['branch']; startn=ctx.stats.nodes; startq=ctx.stats.qnodes
        if ply==1: active['branch']=aid[kw['prev_action']]
        try: r=original(*args,**kw)
        except S.SearchAborted:
            if ply==1: children.append(dict(depth=active['depth'],branch=active['branch'],completed=False,alpha=alpha,beta=beta,nodes=ctx.stats.nodes-startn,qnodes=ctx.stats.qnodes-startq))
            raise
        else:
            if ply==0: roots[:]=[r]
            if ply==1: children.append(dict(depth=active['depth'],branch=active['branch'],completed=True,alpha=alpha,beta=beta,child_score=r.score,root_score=-r.score,classification='UPPER' if r.score<=alpha else 'LOWER' if r.score>=beta else 'EXACT',nodes=ctx.stats.nodes-startn,qnodes=ctx.stats.qnodes-startq,pv=L.record_value(r.pv)))
            return r
        finally: active['branch']=parent
    def progress(depth,nodes,qnodes):
        r=roots[0]; row=dict(depth=depth,score=r.score,action=L.record_value(r.best_action),nodes=nodes,qnodes=qnodes,elapsed=time.perf_counter()-tick)
        iterations.append(row);append(d/'iterations.jsonl',row);print('CLOCK',depth,r.score,round(row['elapsed'],3),flush=True)
    status='FAILED';attempted=0
    try:
        S._clock_trace_return=returned
        exec(compile(tree,'<read-only-q-return-observer>','exec'),S.__dict__)
        S.negamax=observe
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning())
        qstart=stamp();qt=time.perf_counter();qc=time.process_time()
        attempted=1
        dec=p.choose_action(sess,SearchLimits(**plan['limits']),cancel_token=Stop(),progress_callback=progress)
        qend=stamp();qseconds=time.perf_counter()-qt;qcpu=time.process_time()-qc
        # Save actual returned decision before qualification, never rerun to refill.
        write_json(d/'query.json',dict(started_at=qstart,ended_at=qend,seconds=qseconds,cpu_seconds=qcpu,decision=L.record_value(dec),iterations=iterations,children=children,actions=actions,return_sites=sites,groups=[dict(key=list(k),count=v[0],minimum=v[1],maximum=v[2],sum=v[3]) for k,v in stats.items()],samples=list(samples.values()),tuning=L.record_value(p.tuning) if hasattr(p,'tuning') else L.record_value(SearchTuning()),evaluation_profile=L.record_value(p.evaluation_profile)))
        assert L.state_sha(sess.state)==case['state_sha256']
        assert dec.score==iterations[-1]['score'] and L.record_value(dec.action)==iterations[-1]['action']
        pv=replay(c,case['record'])
        for a in dec.principal_variation: assert a in pv.legal_actions();pv.submit(a)
        status='CLOSED'
    except Exception:
        write_json(d/'partial-trace.json',dict(iterations=iterations,children=children,actions=actions,return_sites=sites,groups=[dict(key=list(k),count=v[0],minimum=v[1],maximum=v[2],sum=v[3]) for k,v in stats.items()],samples=list(samples.values())));write_json(d/'failure.json',dict(at=stamp(),traceback=traceback.format_exc()));raise
    finally:
        S.negamax=original;S._quiescence_runtime=oq
        if hasattr(S,'_clock_trace_return'):del S._clock_trace_return
        write_json(d/'receipt.json',dict(status=status,started_at=before,ended_at=stamp(),seconds=time.perf_counter()-tick,cpu_seconds=time.process_time()-cpu,attempted_queries=attempted,queries=int((d/'query.json').exists()),source_sha256=plan['source_sha256']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
