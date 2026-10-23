"""Zero-query decomposition of the sealed singleton-Leaper cost screen.

Reads data-only JSON, never executes producer capsules or refills old queries.
Rates describe paid algorithm events, not unique states, WDL or latent solve cost.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
from tools.local_agent.common import write_json


def rank_correlation(x, y):
    def ranks(v):
        counts=Counter(v); offset=0; table={}
        for z in sorted(counts):
            table[z]=offset+(counts[z]+1)/2; offset+=counts[z]
        return [table[z] for z in v]
    if not x or len(x)!=len(y):
        raise ValueError('equal nonempty vectors required')
    a=ranks(x); b=ranks(y); am=statistics.mean(a); bm=statistics.mean(b)
    den=math.sqrt(sum((z-am)**2 for z in a)*sum((z-bm)**2 for z in b))
    return sum((u-am)*(v-bm) for u,v in zip(a,b,strict=True))/den if den else None


def derive_row(row, meta, budget):
    d=row['decision']; nodes=d['nodes']; qnodes=d['qnodes']; total=nodes+qnodes
    if any(type(z) is not int or z<0 for z in (nodes,qnodes)) or total<=0:
        raise ValueError('nonnegative integer event counts and positive paid work required')
    elapsed=row['query_seconds']
    if not math.isfinite(elapsed) or elapsed<=0:
        raise ValueError('positive finite query time required')
    if d['termination_reason'] not in ('root_immediate_win','time_limit','node_limit'):
        raise ValueError('this sealed screen has only three stopping strata')
    if d['elapsed_seconds']>elapsed+1e-6:
        raise ValueError('decision clock exceeds enclosing query clock')
    # These are scoped observed identities, not a generic product invariant.
    if qnodes!=0 or d['position_keys_computed']!=d['successors_searched']+d['tt_probes']:
        raise ValueError('sealed Q0/runtime counter contract mismatch')
    if not d['runtime_depth_balanced'] or d['runtime_pushes']!=d['runtime_pops']:
        raise ValueError('unbalanced runtime')
    if d['native_legality_fallbacks'] or d['native_legality_operational_failures']:
        raise ValueError('native-only screen route changed')
    r={k:meta[k] for k in ('seed','n','mask','placement','support_rank','forward2_width','root_branch','graph_components','graph_mean_degree')}
    r.update(budget=budget,reason=d['termination_reason'],completed_depth=d['completed_depth'],
             nodes=nodes,qnodes=qnodes,total_work=total,query_seconds=elapsed,
             player_setup_seconds=row['player_setup_seconds'],decision_seconds=d['elapsed_seconds'],
             query_minus_decision_seconds=elapsed-d['elapsed_seconds'],
             work_per_query_second=total/elapsed,
             instrumented_phase_seconds=sum(d[k] for k in ('legal_generation_seconds','evaluation_seconds','ordering_seconds')))
    # In THIS runtime/Q0/nonstaged route these three search wrappers are not
    # nested with each other. They omit transitions, check/availability, keys,
    # terminal/history, TT, control checks, recursion, setup and recorder work.
    r['query_outside_three_wrappers_seconds']=elapsed-r['instrumented_phase_seconds']
    if r['query_outside_three_wrappers_seconds'] < -1e-6:
        raise ValueError('three-wrapper time cannot exceed query in this route')
    for k in ('legal_generation_calls','legal_actions_generated','evaluation_calls','ordering_calls','ordered_moves',
              'position_keys_computed','position_key_cache_hits','tt_probes','tt_hits','root_scan_nodes',
              'successors_searched','runtime_pushes','native_legality_calls'):
        r[k]=d[k]; r[k+'_per_work']=d[k]/total
    for k in ('legal_generation_seconds','evaluation_seconds','ordering_seconds'):
        r[k]=d[k];r[k+'_per_work']=d[k]/total
    r['actions_per_generation']=d['legal_actions_generated']/d['legal_generation_calls'] if d['legal_generation_calls'] else None
    r['native_success_per_explicit_generation']=d['native_legality_calls']/d['legal_generation_calls'] if d['legal_generation_calls'] else None
    return r


def summarize(rows):
    groups=defaultdict(list)
    for r in rows: groups[r['n'],r['budget'],r['reason']].append(r)
    summaries=[]; correlations=[]
    sums=('total_work','query_seconds','player_setup_seconds','decision_seconds','query_minus_decision_seconds',
          'legal_generation_seconds','evaluation_seconds','ordering_seconds','instrumented_phase_seconds',
          'query_outside_three_wrappers_seconds','legal_generation_calls','legal_actions_generated',
          'evaluation_calls','position_keys_computed','tt_probes','runtime_pushes','native_legality_calls')
    for (n,budget,reason), rs in sorted(groups.items()):
        s=dict(n=n,budget=budget,reason=reason,queries=len(rs),sum={k:sum(r[k] for r in rs) for k in sums})
        s['median_completed_depth']=statistics.median(r['completed_depth'] for r in rs)
        s['median_per_query']={k:statistics.median(r[k] for r in rs) for k in ('work_per_query_second','actions_per_generation','legal_generation_calls_per_work','legal_actions_generated_per_work','evaluation_calls_per_work','position_keys_computed_per_work')}
        s['pooled_work_per_second']=s['sum']['total_work']/s['sum']['query_seconds']
        s['three_wrapper_fraction']=s['sum']['instrumented_phase_seconds']/s['sum']['query_seconds']
        summaries.append(s)
    # Keep root and equally-weighted rule means separate; conditional strata
    # have unequal root counts per rule and are exploratory, not a new headline.
    features=('forward2_width','root_branch','graph_components','graph_mean_degree','legal_actions_generated_per_work','evaluation_calls_per_work','position_keys_computed_per_work')
    for n in sorted({r['n'] for r in rows}):
        for budget in sorted({r['budget'] for r in rows}):
            for stratum in ('ALL','time_limit','node_limit','root_immediate_win'):
                rs=[r for r in rows if r['n']==n and r['budget']==budget and (stratum=='ALL' or r['reason']==stratum)]
                if len(rs)<2: continue
                byrule=defaultdict(list)
                for r in rs:byrule[r['mask']].append(r)
                means=[{k:statistics.mean(r[k] for r in rr) for k in features+('work_per_query_second','total_work','completed_depth')} for rr in byrule.values()]
                for target in ('total_work','work_per_query_second','completed_depth'):
                    correlations.append(dict(n=n,budget=budget,stratum=stratum,target=target,roots=len(rs),rules=len(means),
                       root={f:rank_correlation([r[f] for r in rs],[r[target] for r in rs]) for f in features},
                       rule_mean={f:rank_correlation([r[f] for r in means],[r[target] for r in means]) for f in features}))
    return summaries,correlations


def analyze_documents(docs):
    plan=docs['plan.json']; meta={r['seed']:r for r in docs['metadata.json']['rows']}; rows=[]; batch=[]
    for budget in plan['budgets']:
        data=docs[f'N{budget}.json']; seen=set()
        if data['missing_slots'] or data['failures']:raise ValueError('retain/review missing and failed slots explicitly')
        for row in data['rows']:
            seed=row['seed']
            if seed in seen or seed not in meta:raise ValueError('duplicate or unregistered seed')
            seen.add(seed);rows.append(derive_row(row,meta[seed],budget))
        if seen!=set(meta):raise ValueError('incomplete sealed batch')
        query=sum(r['query_seconds'] for r in data['rows']);setup=sum(r['player_setup_seconds'] for r in data['rows']);rule=sum(w['rule_setup_seconds'] for w in data['worlds'])
        batch.append(dict(budget=budget,wall_seconds=data['wall_seconds'],query_seconds=query,player_setup_seconds=setup,rule_setup_seconds=rule,
                          unassigned_outer_residual_seconds=data['wall_seconds']-query-setup-rule))
    summaries,correlations=summarize(rows)
    return dict(schema='genericchess.leaper_cost_decomposition.v1',new_Player_calls=0,rows=rows,strata=summaries,associations=correlations,batches=batch,
                limitations=['Exploratory reuse of correlated roots/shared rules; no independent replication or causal fit.',
                  'nodes+qnodes counts budget events; not distinct states. This screen has qnodes=0 and check-only qsearch OFF.',
                  'position_keys_computed is a mixed bookkeeping counter, not SHA calls; true runtime key/timing detail was not exported.',
                  'Three wrappers do not cover transition/check/availability/history/TT costs; outer residual is not measured serialization time.',
                  'Two caps mostly nonbinding under a three-second limit; no requested-depth64 completion cost or quality claim.'])


def load_screen(path):
    manifest=json.loads((path.parent/'screen-manifest.json').read_text(encoding='utf-8'))
    raw=path.read_bytes();body=gzip.decompress(raw)
    if hashlib.sha256(raw).hexdigest()!=manifest['compressed_sha256'] or hashlib.sha256(body).hexdigest()!=manifest['decoded_sha256']:
        raise ValueError('sealed screen bytes changed')
    p=json.loads(body);docs={}
    for name,text in p['documents_utf8'].items():
        if hashlib.sha256(text.encode('utf-8')).hexdigest()!=manifest['original_sha256'][name]:raise ValueError('original byte mismatch')
        if name.endswith('.json'):docs[name]=json.loads(text)
    return docs



def analyze_policy_returns(plan, inputs, metadata, old, panels, *, qualify_pvs=False):
    """Compare new q policies to OLD references without turning cost into truth.

    Panels may be incomplete; retain missing slots and paired coverage explicitly.
    qualify_pvs uses the existing Core replay boundary, not a separate engine.
    """
    if plan['planned_new_calls']!=2*len(inputs['worlds']):raise ValueError('registered panel count mismatch')
    worlds={w['seed']:w for w in inputs['worlds']};meta={r['seed']:r for r in metadata['rows']}
    if set(worlds)!=set(meta):raise ValueError('input/metadata seed mismatch')
    allowed={a['label']:a for a in plan['new_arms']};reference={r['seed']:r for r in old['rows']}
    if set(reference)!=set(worlds):raise ValueError('incomplete OLD reference')
    rows=[];coverage=[];comparisons=[];compiled={};pv_count=0;root_win_checks=0
    conditions={'staticQ0':{'qdepth':0,'check_only_qsearch':False},**allowed}
    if set(panels)-set(allowed):raise ValueError('unregistered policy arm')
    allpanels={'staticQ0':old,**panels};indexed={}
    for label,data in allpanels.items():
        spec=conditions[label];protocol=data['protocol'];lim=protocol['query_limits']
        if protocol['planned_queries']!=len(worlds):raise ValueError('registered slot count mismatch')
        if label!='staticQ0' and protocol['source_sha256']!=plan['source_sha256']['scripts/semantic_probe_cost.py']:raise ValueError('new producer source differs')
        if (protocol['evaluation_backend']!='unit' or protocol['variants']!=['all'] or
            lim['max_depth']!=64 or lim['max_nodes']!=32768 or lim['max_time_seconds']!=3 or
            lim['quiescence_max_depth']!=spec['qdepth'] or
            bool(protocol.get('check_only_qsearch',False))!=spec['check_only_qsearch']):
            raise ValueError('policy/limit contract changed')
        if protocol['input_sha256']!=plan['input_sha256']:raise ValueError('input identity changed')
        seen={};returned_worlds={w['seed']:w for w in data['worlds']}
        for raw in data['rows']:
            seed=raw['seed']
            if seed not in worlds or seed in seen or raw['prefix']!=0 or raw['rep']!=0 or raw['variant']!='all':raise ValueError('wrong/duplicate query slot')
            w=worlds[seed];wr=returned_worlds[seed]
            if wr['rule']!=w['rule'] or wr['roots'][0]['record']!=w['roots'][0]['record']:raise ValueError('complete rule/history mismatch')
            d=raw['decision'];total=d['nodes']+d['qnodes']
            if any(type(d[k]) is not int or d[k]<0 for k in ('nodes','qnodes')) or total<=0 or not math.isfinite(raw['query_seconds']) or raw['query_seconds']<=0:raise ValueError('invalid count/time')
            if label=='staticQ0' and d['qnodes']!=0:raise ValueError('OLD static Q0 changed')
            if d['runtime_depth_balanced'] is not True or d['runtime_pushes']!=d['runtime_pops']:raise ValueError('unbalanced runtime')
            if not raw['provider_available'] or d['native_legality_fallbacks'] or d['native_legality_operational_failures']:raise ValueError('Native route differs')
            # A result retained from an earlier iteration has its own provenance;
            # a hard-depth abort is not a completed full-depth leaf model.
            r={k:meta[seed][k] for k in ('seed','n','mask','placement','support_rank','forward2_width','root_branch','graph_components','graph_mean_degree')}
            r.update(label=label,new_execution=label!='staticQ0',query_seconds=raw['query_seconds'],nodes=d['nodes'],qnodes=d['qnodes'],total_work=total,q_fraction=d['qnodes']/total,
                     work_per_query_second=total/raw['query_seconds'],completed_depth=d['completed_depth'],reason=d['termination_reason'],result_source=d['result_source'],
                     in_check_qnodes=d['in_check_qnodes'],hard_q_aborts=d['qsearch_check_hard_limit_aborts'],legal_generation_calls=d['legal_generation_calls'],
                     legal_actions_generated=d['legal_actions_generated'],evaluation_calls=d['evaluation_calls'],score=d['score'],action=d['action'],
                     runtime_pushes=d['runtime_pushes'],runtime_pushes_per_query_second=d['runtime_pushes']/raw['query_seconds'])
            if qualify_pvs and label!='staticQ0':
                from scripts import leaper_design as L
                c=compiled.get(seed)
                if c is None:c=compiled.setdefault(seed,L.compile_rule(L.ruleset_from_dict(w['rule'])))
                ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(w['roots'][0]['record'])))
                chosen=L.match_action(ss,d['action'])
                if d['principal_variation'] and d['principal_variation'][0]!=d['action']:raise ValueError('PV is not bound to chosen root action')
                if d['termination_reason']=='root_immediate_win':
                    win=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(w['roots'][0]['record'])));win.submit(chosen)
                    if win.state.terminal_status.winner!=0:raise ValueError('rootshortcut is not literal Core win')
                    root_win_checks+=1
                for action in d['principal_variation']:ss.submit(L.match_action(ss,action));pv_count+=1
                r['literal_PV_plies']=len(d['principal_variation'])
            rows.append(r);seen[seed]=r
        missing=set(worlds)-set(seen)
        slots=data['missing_slots'];declared={s[0] for s in slots}
        if len(declared)!=len(slots) or any(s[1:]!=[0,0,'all'] for s in slots) or missing!=declared:raise ValueError('missing-slot declaration mismatch')
        coverage.append({'label':label,'new_execution':label!='staticQ0','observed':len(seen),'missing':len(missing),'missing_seeds':sorted(missing),'reason_histogram':dict(Counter(r['reason'] for r in seen.values())),'batch_wall_seconds':data['wall_seconds'],'failures':data['failures']})
        indexed[label]=seen
    for label in allowed:
        if label not in panels:
            coverage.append({'label':label,'new_execution':True,'observed':0,'missing':len(worlds),'missing_seeds':sorted(worlds),'reason_histogram':{},'batch_wall_seconds':None,'failures':[],'status':'UNPROVIDED_NOT_QUALIFIED'})
    aggregates=[];associations=[]
    for label in allpanels:
        for n in sorted({r['n'] for r in rows}):
            full=[r for r in indexed[label].values() if r['n']==n]
            if not full:continue
            for scope,rs in [('ALL',full)]+[(reason,[r for r in full if r['reason']==reason]) for reason in sorted({r['reason'] for r in full})]:
                aggregates.append({'label':label,'n':n,'stratum':scope,'queries':len(rs),'sum_nodes':sum(r['nodes'] for r in rs),'sum_qnodes':sum(r['qnodes'] for r in rs),'sum_runtime_pushes':sum(r['runtime_pushes'] for r in rs),'sum_query_seconds':sum(r['query_seconds'] for r in rs),'median_completed_depth':statistics.median(r['completed_depth'] for r in rs),'mean_q_fraction':statistics.mean(r['q_fraction'] for r in rs)})
                if len(rs)<2:continue
                rm=defaultdict(list)
                for r in rs:rm[r['mask']].append(r)
                features=('forward2_width','root_branch','graph_components','graph_mean_degree')
                means=[{k:statistics.mean(r[k] for r in rr) for k in features+('total_work','work_per_query_second','completed_depth','runtime_pushes_per_query_second')} for rr in rm.values()]
                for target in ('total_work','work_per_query_second','completed_depth','runtime_pushes_per_query_second'):
                    associations.append({'label':label,'n':n,'stratum':scope,'target':target,'post_registration_diagnostic':target=='runtime_pushes_per_query_second','root_count':len(rs),'rule_count':len(means),
                       'root':{f:rank_correlation([r[f] for r in rs],[r[target] for r in rs]) for f in features},
                       'rule_mean':{f:rank_correlation([r[f] for r in means],[r[target] for r in means]) for f in features}})
    for label in panels:
        for n in sorted({r['n'] for r in rows}):
            seeds=sorted(s for s in indexed[label] if meta[s]['n']==n);paired=[(indexed['staticQ0'][s],indexed[label][s]) for s in seeds]
            comparisons.append({'label':label,'n':n,'matched_full_inputs':len(paired),'planned_full_inputs':sum(m['n']==n for m in meta.values()),
              'root_shortcut_membership_mismatches':[a['seed'] for a,b in paired if (a['reason']=='root_immediate_win')!=(b['reason']=='root_immediate_win')],
              'changed_literal_actions':sum(a['action']!=b['action'] for a,b in paired),'changed_scores':sum(a['score']!=b['score'] for a,b in paired),
              'completed_depth_greater_equal_less':[sum((b['completed_depth']>a['completed_depth'],b['completed_depth']==a['completed_depth'],b['completed_depth']<a['completed_depth'])[i] for a,b in paired) for i in range(3)],
              'scope':'Same full root/rule, different leaf models and algorithm-event mix; differences are not utility/WDL or uniform-depth proof.'})
    return {'schema':'genericchess.leaper_policy_cost.v1','coverage':coverage,'aggregates':aggregates,'associations':associations,'paired_comparisons':comparisons,'rows':rows,
       'new_PV_Core_plies':pv_count,'new_root_shortcut_Core_checks':root_win_checks,'Core_qualification_enabled':qualify_pvs,'scope':'Old reference is reused once; new actual policy executions on exposed common inputs. All stop reasons/missing retained. q nodes are algorithm events, not equal-cost operations. No strength/latent complexity/default claim.'}


def verify_packet(packet, old_screen):
    """Read published originals as data and independently replay current Core APIs."""
    manifest=json.loads((packet.parent/'manifest.json').read_text(encoding='utf-8'))
    raw=packet.read_bytes();body=gzip.decompress(raw)
    if hashlib.sha256(raw).hexdigest()!=manifest['compressed_sha256'] or hashlib.sha256(body).hexdigest()!=manifest['decoded_sha256']:raise ValueError('packet byte mismatch')
    p=json.loads(body)
    if p['schema']!='genericchess.policy_cost_quantity.evidence.v1':raise ValueError('packet schema')
    texts=p['documents_utf8']
    if set(texts)!=set(manifest['documents_sha256']):raise ValueError('document manifest differs')
    for name,text in texts.items():
        if hashlib.sha256(text.encode('utf-8')).hexdigest()!=manifest['documents_sha256'][name]:raise ValueError('document byte mismatch')
    docs={name:json.loads(text) for name,text in texts.items() if name.endswith('.json')}
    old=load_screen(old_screen);plan=docs['policy/plan.json']
    if docs['policy/execution-public.json']['status'] not in ('CLOSED','FAILED'):raise ValueError('only closed producer evidence may be qualified')
    old_texts=json.loads(gzip.decompress(old_screen.read_bytes()))['documents_utf8']
    if hashlib.sha256(old_screen.read_bytes()).hexdigest()!=manifest['old_screen_sha256']:raise ValueError('wrong fixed OLD reference')
    for name,key in (('inputs.json','input_sha256'),('metadata.json','metadata_sha256')):
        if hashlib.sha256(old_texts[name].encode('utf-8')).hexdigest()!=plan[key]:raise ValueError('old complete input/metadata bytes differ')
    for path,sha in plan['source_sha256'].items():
        if hashlib.sha256(texts['source/'+path+'.txt'].encode('utf-8')).hexdigest()!=sha:raise ValueError('executed source capsule differs')
    panels={arm['label']:docs['policy/'+arm['label']+'.json'] for arm in plan['new_arms'] if 'policy/'+arm['label']+'.json' in docs}
    result=analyze_policy_returns(plan,old['inputs.json'],old['metadata.json'],old['N32768.json'],panels,qualify_pvs=True)
    expected=docs['policy/analysis.json']
    for field in ('coverage','aggregates','associations','paired_comparisons'):
        if result[field]!=expected[field]:raise ValueError('derived policy analysis differs: '+field)
    # One matched-node diagnostic, preserving repeats/order/profile flags.
    from scripts import leaper_design as L
    from scripts.leaper_rule_coordinates import (template,multi_actor_forward2_polynomial,evaluate_orbit_polynomial,minimum_static_ordinary_count,static_quantity_witness)
    from dataclasses import replace
    for path,expected_sha in docs['pair/sources.json'].items():
        if hashlib.sha256(texts['pair/source/'+path+'.txt'].encode('utf-8')).hexdigest()!=expected_sha:raise ValueError('matched executed source capsule differs')
    for prefix,source_name in (('quantity','executed-source-recovered.txt'),('static','executed-source.txt')):
        if hashlib.sha256(texts[prefix+'/'+source_name].encode('utf-8')).hexdigest()!=docs[prefix+'/plan.json']['source_sha256']:raise ValueError('mathematical executed source differs')
    pairplan=docs['pair/plan.json'];pairinputs=docs['pair/inputs.json']
    if hashlib.sha256(texts['pair/inputs.json'].encode('utf-8')).hexdigest()!=pairplan['input_sha256']:raise ValueError('pair inputs differ')
    worlds={w['seed']:w for w in pairinputs['worlds']};pairrows=docs['pair/returns.json']['rows'];pair_pv=0
    if len(pairrows)!=len(pairplan['sequence']):raise ValueError('matched diagnostic missing')
    for row,slot in zip(pairrows,pairplan['sequence'],strict=True):
        if row['seed']!=slot['seed'] or row['profile']!=slot['profile']:raise ValueError('pair sequence differs')
        d=row['decision'];w=worlds[row['seed']];c=L.compile_rule(L.ruleset_from_dict(w['rule']));ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(w['roots'][0]['record'])))
        if L.state_sha(ss.state)!=row['input_state_sha256'] or d['nodes']+d['qnodes']!=8192 or d['termination_reason']!='node_limit':raise ValueError('matched event contract failed')
        L.match_action(ss,d['action'])
        for a in d['principal_variation']:ss.submit(L.match_action(ss,a));pair_pv+=1
    # New three-actor degree-four boundary: complete two-action Core paths.
    q=docs['quantity/result.json'];qr=docs['quantity/Core-returns.json']['rows'];poly=multi_actor_forward2_polynomial(0,(6,7,11),24,5)
    if poly!=q['polynomials']['3'] or multi_actor_forward2_polynomial(0,(7,11),24,5)!=q['polynomials']['2']:raise ValueError('quantity polynomial differs')
    if len(qr)!=31 or {r['mask'] for r in qr}!=set(range(1,32)):raise ValueError('quantity coverage differs')
    width_edges=0
    for row in qr:
        c=L.compile_rule(L.ruleset_from_dict(row['full_rule']));ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(row['initial_record'])))
        b=[None]*25
        for sq,owner,tid in [(0,0,'K'),(24,1,'K'),(6,0,'A'),(7,0,'A'),(11,0,'A')]:b[sq]=L.Piece(owner,tid,tid)
        expected_rule=replace(template(row['mask'],5,(0,6,24)),initial_position=tuple(tuple(b[5*y:5*y+5]) for y in range(5)))
        if L.ruleset_to_dict(expected_rule,include_metadata=True)!=row['full_rule'] or L.state_sha(ss.state)!=row['initial_state_sha256']:raise ValueError('three-actor context differs')
        front=[]
        for action,child in L.legal_successors(ss.state,c):
            grandchildren=[] if child.terminal_status.is_terminal else L.legal_successors(child,c)
            front.append({'action':L.record_value(action),'child_state_sha256':L.state_sha(child),'terminal':L.record_value(child.terminal_status),
              'replies':[{'action':L.record_value(a),'state_sha256':L.state_sha(ch),'terminal':L.record_value(ch.terminal_status)} for a,ch in grandchildren]})
        width=sum(len(z['replies']) for z in front)
        if front!=row['frontier'] or width!=row['width'] or width!=evaluate_orbit_polynomial(poly,row['mask']):raise ValueError('Core quantity frontier differs')
        width_edges+=width
    # Static configurations explicitly reconstruct synthetic Position/history;
    # they are not replayed or represented as reachable opening records.
    from generic_chess.core.semantic_executor import semantic_engine_for
    from generic_chess.core.identity import repetition_identity_key
    from generic_chess.core.position import HistoryRecord
    static=docs['static/returns.json'];positive=0;negative=0;seen=set()
    def check_static(obs,n,mask,k,actors,v):
        r=L.ruleset_from_dict(obs['full_rule']);c=L.compile_rule(r);board=[None]*(n*n)
        for sq,owner,tid in [(k,0,'K'),(v,1,'K')]+[(a,0,'A') for a in actors]:board[sq]=L.Piece(owner,tid,tid)
        base=template(mask,n,(0,1,n*n-1));initial=[[None]*n for _ in range(n)];initial[0][0]=L.Piece(0,'K','K');initial[-1][-1]=L.Piece(1,'K','K');base=replace(base,initial_position=tuple(map(tuple,initial)))
        if L.ruleset_to_dict(base,include_metadata=True)!=obs['full_rule']:raise ValueError('static rule changed')
        pos=replace(c.initial_position,board=tuple(board),side_to_move=1);key=repetition_identity_key(pos,c);hist=(HistoryRecord(key,-1,'',False),);e=semantic_engine_for(c)
        actual={'synthetic_position':L.record_value(pos),'synthetic_history':L.record_value(hist),'check':e.in_check(pos,1),'legal_actions':L.record_value(e.legal_actions(pos)),
                'terminal':L.record_value(e.terminal_result(pos,0,((key,1),),hist))}
        if any(actual[k]!=obs[k] for k in actual):raise ValueError('static synthetic position/history/terminal differs')
        return actual
    for row in static['rows']:
        n,mask=row['n'],row['mask'];key=n,mask
        if key in seen:raise ValueError('duplicate static context')
        seen.add(key);w=static_quantity_witness(mask,n)
        if w!=row['witness'] or minimum_static_ordinary_count(mask,n)!=row['minimum_ordinary_count']:raise ValueError('static coordinate differs')
        flat=lambda p:p[0]+n*p[1];a=check_static(row['observation'],n,mask,flat(w['king0']),tuple(map(flat,w['ordinary'])),flat(w['king1']))
        if not a['check'] or a['legal_actions'] or a['terminal']!={'status':'checkmate','winner':0}:raise ValueError('static positive failed')
        positive+=1
    if seen!={(n,m) for n in (3,4,5,6) for m in range(1,32) if not(n==3 and m==16)}:raise ValueError('static positive coverage differs')
    seennegative=set()
    for row in static['negative_maximal_configurations']:
        k,v=row['king0'],row['king1'];actors=tuple(i for i in range(9) if i not in (k,v))
        if (k,v) in seennegative or list(actors)!=row['ordinary']:raise ValueError('negative occupancy changed')
        seennegative.add((k,v));a=check_static(row['observation'],3,16,k,actors,v)
        if a['terminal']['winner'] is not None:raise ValueError('static negative failed')
        negative+=1
    from scripts.leaper_parity_scope import adjacent,xy
    if seennegative!={(k,v) for k in range(9) for v in range(9) if k!=v and not adjacent(xy(k,3),xy(v,3))}:raise ValueError('negative coverage differs')
    # Four selected common-main-depth queries, distinct from the panel/pilots.
    depthplan=docs['depth/plan.json'];depth_pv=0;depth_queries=0
    for case in depthplan['cases']:
        text=texts['depth/input-'+str(case['seed'])+'.json']
        if hashlib.sha256(text.encode('utf-8')).hexdigest()!=case['input_sha256']:raise ValueError('depth input differs')
        world=json.loads(text)['worlds'][0]
        for label in ('staticQ0','checkQ0'):
            data=docs['depth/'+str(case['seed'])+'-'+label+'.json'];protocol=data['protocol'];lim=protocol['query_limits']
            if protocol['source_sha256']!=depthplan['source_sha256'] or protocol['input_sha256']!=case['input_sha256'] or lim['max_depth']!=case['requested_main_depth'] or lim['max_nodes']!=32768 or lim['max_time_seconds']!=10 or lim['quiescence_max_depth']!=0 or protocol.get('check_only_qsearch',False)!=(label=='checkQ0'):raise ValueError('depth diagnostic policy differs')
            if len(data['rows'])!=1 or data['missing_slots'] or data['failures']:raise ValueError('depth diagnostic incomplete')
            d=data['rows'][0]['decision']
            if d['completed_depth']!=case['requested_main_depth'] or d['termination_reason']!='completed_depth':raise ValueError('common main depth not completed')
            c=L.compile_rule(L.ruleset_from_dict(world['rule']));ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(world['roots'][0]['record'])))
            L.match_action(ss,d['action'])
            for a in d['principal_variation']:ss.submit(L.match_action(ss,a));depth_pv+=1
            depth_queries+=1
    # The next scientific step is real complete-input preparation, zero fitness.
    prepared=docs['next/inputs.json'];next_fingerprints=set();next_counts=[]
    if hashlib.sha256(texts['next/inputs.json'].encode('utf-8')).hexdigest()!=docs['next/plan.json']['input_sha256']:raise ValueError('next inputs differ')
    for path,expected_sha in docs['next/plan.json']['source_sha256'].items():
        if hashlib.sha256(texts['source/'+path+'.txt'].encode('utf-8')).hexdigest()!=expected_sha:raise ValueError('next preparation source differs')
    for world in prepared['worlds']:
        c=L.compile_rule(L.ruleset_from_dict(world['rule']));ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(world['roots'][0]['record'])))
        if L.state_sha(ss.state)!=world['initial_state_sha256'] or L.record_value(ss.state)!=world['initial_state'] or L.record_value(ss.legal_actions())!=world['initial_actions']:raise ValueError('next full input does not replay')
        colors=[(i%5+i//5)%2 for i,a in enumerate(ss.state.position.board) if a is not None and a.owner==0 and a.current_type_id=='A']
        if colors!=world['component_allocation']:raise ValueError('next component allocation differs')
        next_fingerprints.add(c.ruleset_fingerprint);next_counts.append(len(ss.legal_actions()))
    if len(prepared['worlds'])!=2 or len(next_fingerprints)!=1 or next_counts!=[3,6]:raise ValueError('next same-rule setup contract differs')
    prefix=docs['next/preflight-inputs.json'];prefix_result=docs['next/prefix-result.json'];prefix_moves=0
    if hashlib.sha256(texts['next/preflight-inputs.json'].encode('utf-8')).hexdigest()!=prefix_result['input_sha256'] or hashlib.sha256(texts['next/inputs.json'].encode('utf-8')).hexdigest()!=docs['next/prefix-plan.json']['input_sha256']:raise ValueError('prefix byte provenance differs')
    for world in prefix['worlds']:
        c=L.compile_rule(L.ruleset_from_dict(world['rule']))
        for frame in world['saved_prefixes']:
            ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(frame['record'])))
            if L.state_sha(ss.state)!=frame['state_sha256'] or L.record_value(ss.state.terminal_status)!=frame['terminal']:raise ValueError('saved full prefix differs')
        for root in world['roots']:
            ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(root['record'])))
            if ss.state.ply_count!=root['target']:raise ValueError('prefix absolute clock differs')
        prefix_moves+=len(world['saved_prefixes'])
    if prefix_moves!=prefix_result['actual_Core_transitions'] or prefix_result['actual_Player_calls']!=0:raise ValueError('next preparation execution differs')
    return {'status':'PASS','policy_analysis':result,'matched_node_queries':len(pairrows),'matched_node_PV_plies':pair_pv,'common_depth_queries':depth_queries,'common_depth_PV_plies':depth_pv,'next_inputs_replayed':len(prepared['worlds']),'next_prefix_moves_replayed':prefix_moves,'new_quantity_Core_roots':len(qr),'new_quantity_Core_second_edges':width_edges,
            'static_positive_configurations':positive,'static_maximal_negative_configurations':negative,'document_byte_hashes':len(texts),'source_capsules_executed':0,
            'scope':'Data-only packet. Current shared Core verifies supplied paths/static configurations; not independent engine, reachability of synthetic positions or general WDL/quality.'}

def main():
    ap=argparse.ArgumentParser(description=__doc__);group=ap.add_mutually_exclusive_group(required=True);group.add_argument('--screen',type=Path);group.add_argument('--packet',type=Path);ap.add_argument('--old-screen',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    if args.output.exists():raise FileExistsError('fresh analysis output required')
    if not args.output.resolve().is_relative_to(Path.cwd().resolve()/'.local_agent'):raise ValueError('analysis must use ignored local output')
    if args.packet:
        if not args.old_screen:ap.error('--packet requires the fixed --old-screen reference')
        result=verify_packet(args.packet,args.old_screen)
    else:result=analyze_documents(load_screen(args.screen))
    write_json(args.output,result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('policy_analysis','rows','strata','associations','batches','limitations')}))


if __name__=='__main__':main()
