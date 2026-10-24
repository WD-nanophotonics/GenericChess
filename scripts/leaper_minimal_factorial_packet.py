"""Literal data-only qualification for the four-actor fixed-order experiment."""
from pathlib import Path
from collections import Counter
from dataclasses import replace
import argparse,json,hashlib,time
from scripts import leaper_design as L
from scripts.leaper_two_type_packet import read_packet
from scripts.leaper_two_type_qualify import qualify_game
from scripts.semantic_probe_cost import unit_evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.core.attacks import anchor_square
from tools.local_agent.common import write_json

def metadata(world,row,reg):
    c=L.compile_rule(L.ruleset_from_dict(world['rule']));u=unit_evaluator(c);mode=reg['controller']
    assert row['controller']==row['slot']['policy']==mode and row['slot']['root']==reg['root']
    assert row['generated_default_profile']==reg['profile']==world['profile']
    assert world['profile']==L.record_value(L.AlphaBetaPlayer(c,use_disk_cache=False).evaluation_profile)
    assert row['ordering_profile']==L.record_value(u._profile) and row['ordering_config']==L.record_value(u._config)
    expected_profile=world['profile'] if mode in ('STATIC_FIXED','FULL_FIXED') else L.record_value(u._profile)
    expected_config=L.record_value(EvaluationConfig()) if mode in ('DYNAMIC_FIXED','FULL_FIXED') else L.record_value(u._config)
    assert row['actual_leaf_profile']==expected_profile and row['actual_leaf_config']==expected_config
    for q in row['queries']:assert q['controller']==(mode if q['actor']==0 else 'UNIT')

def selected_leaves(world,row):
    c=L.compile_rule(L.ruleset_from_dict(world['rule']));u=unit_evaluator(c);full=Evaluator(c,u._profile,EvaluationConfig());s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(row['initial_record'])));out=[]
    wa=world['profile']['board_value_by_type']['A'];wb=world['profile']['board_value_by_type']['B']
    for i,q in enumerate(row['queries']):
        pv=L.GameSession.replay(c,s.to_record())
        for a in q['decision']['principal_variation']:pv.submit(L.match_action(pv,a))
        if not pv.state.terminal_status.is_terminal:
            ct=Counter((x.owner,x.current_type_id)for x in pv.state.position.board if x);a=ct[0,'A']-ct[1,'A'];b=ct[0,'B']-ct[1,'B'];sgn=1 if pv.state.position.side_to_move==0 else -1
            material=u.evaluate(pv.state)*sgn;assert material==1000*(a+b)
            maps=full._attack_maps(pv.state);mob=len(maps[0])-len(maps[1]);esc=full._anchor_escape(pv.state.position,0,maps[1])-full._anchor_escape(pv.state.position,1,maps[0]);check=int(anchor_square(pv.state.position,1,c)in maps[0])-int(anchor_square(pv.state.position,0,c)in maps[1]);delta=full.evaluate(pv.state)*sgn-material;assert delta==2*mob+5*esc+50*check
            out.append(dict(query=i,actor=q['actor'],absolute_ply=pv.state.ply_count,deltaA=a,deltaB=b,unit=material,default_material=wa*a+wb*b,dynamic=delta,state_sha256=L.state_sha(pv.state)))
        s.submit(L.match_action(s,q.get('executed_action',q['action'])))
    return out

def contrast(rows):
    modes=('UNIT','STATIC_FIXED','DYNAMIC_FIXED','FULL_FIXED');by={(r['root'],r['controller']):r for r in rows};pairs=[]
    coefficients={'material_OFF':{'STATIC_FIXED':1,'UNIT':-1},'material_ON':{'FULL_FIXED':1,'DYNAMIC_FIXED':-1},'dynamic_UNIT':{'DYNAMIC_FIXED':1,'UNIT':-1},'dynamic_DEFAULT':{'FULL_FIXED':1,'STATIC_FIXED':-1},'interaction':{'FULL_FIXED':1,'DYNAMIC_FIXED':-1,'STATIC_FIXED':-1,'UNIT':1}}
    for root in range(8):
        values={m:by.get((root,m),{}).get('value') for m in modes};effects={}
        for name,co in coefficients.items():
            lo=hi=0
            for mode,k in co.items():
                value=values[mode]
                if value is None:lo-=abs(k);hi+=abs(k)
                else:lo+=k*value;hi+=k*value
            effects[name]=dict(value=lo if lo==hi else None,lower=lo,upper=hi)
        pairs.append(dict(root=root,values=values,effects=effects))
    return dict(roots=pairs,equalweight_mean_bounds={name:[sum(r['effects'][name]['lower']for r in pairs)/8,sum(r['effects'][name]['upper']for r in pairs)/8]for name in coefficients},scope='Finite equalweight8root distribution, correlated deterministic arms; no iid/population confidence claim. Missing terminal values remain[-1,1].')

def qualify_documents(docs):
    j=lambda n:json.loads(docs[n]);sha=lambda n:hashlib.sha256(docs[n].encode('utf-8')).hexdigest()
    w=j('inputs.json');reg=j('registration.json');results=j('results.json')
    assert sha('inputs.json')==reg['input_sha256'] and sha('source/factorial.py')==reg['driver_sha256'] and sha('source/game.py')==reg['game_source_sha256']
    rule=L.ruleset_from_dict(w['rule']);c=L.compile_rule(rule)
    assert w['fingerprint']==L.compute_fingerprint(rule) and len(w['roots'])==8
    for root in w['roots']:
        initial=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(root['record'])))
        assert not initial.state.terminal_status.is_terminal and initial.state.ply_count==0
        assert L.record_value(initial.state)==root['state'] and L.state_sha(initial.state)==root['state_sha256']
        assert len(initial.legal_actions())==root['legal_count']
        assert Counter((p.owner,p.current_type_id)for p in initial.state.position.board if p)==Counter({(0,'K'):1,(0,'A'):1,(1,'K'):1,(1,'B'):1})
    assert results['status']=='CLOSED' and len(reg['slots'])==32 and len({(s['root'],s['controller'])for s in reg['slots']})==32
    rows=[];counts=Counter();leaves=0;reused=0;leaf_classes=set()
    for index,actual in enumerate(results['slots']):
        slot=reg['slots'][index];assert all(actual[k]==v for k,v in slot.items())
        if actual['status']!='finished':continue
        row=j(f'game-{index:03d}.json');case=j(f'case-{index:03d}.json')
        assert case['input_sha256']==reg['input_sha256'] and case['source_sha256']==reg['game_source_sha256'] and case['root']==slot['root'] and case['controller']==slot['controller'] and case['nodes']==reg['nodes']
        assert case['q']==reg['q'] and case['services']==reg['services'] and case['tt']==reg['tt'] and not case.get('first_action_override')
        metadata(w,row,case);q=qualify_game(w,row,case);counts.update(q['counts']);selected=selected_leaves(w,row);leaves+=len(selected);leaf_classes.update((z['deltaA'],z['deltaB'],z['dynamic'])for z in selected)
        assert actual['value']==q['value'];reused+=bool(actual['reused']);rows.append(dict(index=index,root=slot['root'],controller=slot['controller'],reused=actual['reused'],**q))
        if actual['reused']:assert sha(f'game-{index:03d}.json')==actual['original_sha256']
    expected_missing=[i for i in range(32)if i>=len(results['slots'])or results['slots'][i]['status']!='finished'or results['slots'][i].get('value') is None];assert results['missing']==expected_missing
    from itertools import combinations
    pooled=Counter();wa=w['profile']['board_value_by_type']['A'];wb=w['profile']['board_value_by_type']['B']
    for a,b in combinations(sorted(leaf_classes),2):
        for mode in ('static','dynamic'):
            d=a[2]-b[2]if mode=='dynamic'else 0;u=1000*(a[0]+a[1]-b[0]-b[1])+d;v=wa*(a[0]-b[0])+wb*(a[1]-b[1])+d
            label='strict_reversal'if u*v<0 else 'unit_tie_split'if u==0 and v!=0 else 'default_tie_split'if v==0 and u!=0 else 'same_weak_order';pooled[mode+':'+label]+=1
    if 'analysis/selected-leaf-order.json'in docs:
        po=j('analysis/selected-leaf-order.json');assert po['selected_leaf_occurrences']==leaves and po['unique_quantity_dynamic_classes']==len(leaf_classes)and po['class_pair_counts']==dict(pooled)
    bands=j('analysis/bands.json');breg=j('analysis/bands-registration.json');assert breg['input_sha256']==reg['input_sha256'] and breg['source_sha256']==sha('source/bands.py');assert bands['status']=='PASS' and bands['placements']==28800 and bands['distinct_physical_placements']==28200
    for r in bands['rows']:
        h={int(k):v for k,v in r['dynamic_histograms']['0'].items()};p={int(k):v for k,v in r['dynamic_histograms']['1'].items()};assert sum(h.values())==600 and sum(p.values())==13800 and max(map(abs,(*h,*p)))<=140
        threshold=max(h)-min(p)if r['remnant']=='A0' else max(p)-min(h);assert threshold==r['strict_sufficient_threshold'] and min(r['prices'])>threshold
    return dict(status='PASS',games=len(rows),missing=expected_missing,reused_games=reused,new_formal_games=len(rows)-reused,rows=rows,counts=dict(counts),nonterminal_selected_PV_leaves=leaves,pooled_leaf_class_pairs=dict(pooled),contrast=contrast(rows),static_functional_placements=28800,new_Player_queries=0,source_capsule_executions=0,scope='Literal shared Core/PV/history/profile/source qualification; not independent engine, search rerun or fullWDL. Static-band histogram arithmetic bound checked, physical census was not independently repeated.')

def qualify(packet,manifest,output):
    tick=time.perf_counter();docs=read_packet(packet,manifest);r=qualify_documents(docs)
    from scripts.leaper_role_mate_packet import qualify_role_documents
    r['role_mate']=qualify_role_documents(docs)
    r['cold']=qualify_cold_documents(docs)
    r['next']=qualify_next_documents(docs)
    pilot=json.loads(docs['pilot/game.json']);pr=json.loads(docs['pilot/registration.json']);world=json.loads(docs['inputs.json'])
    assert pr['controller']==pilot['controller']==pilot['slot']['policy']=='DEFAULT' and pr['input_sha256']==hashlib.sha256(docs['inputs.json'].encode('utf-8')).hexdigest()
    assert pr['source_sha256']==hashlib.sha256(docs['source/game.py'].encode('utf-8')).hexdigest()
    c=L.compile_rule(L.ruleset_from_dict(world['rule']));ep=L.record_value(L.AlphaBetaPlayer(c,use_disk_cache=False).evaluation_profile);ec=L.record_value(EvaluationConfig())
    assert pr['profile']==pilot['generated_default_profile']==pilot['actual_leaf_profile']==pilot['ordering_profile']==ep
    assert pilot['actual_leaf_config']==pilot['ordering_config']==ec
    r['natural_DEFAULT_pilot']=qualify_game(world,pilot,pr)
    if 'adjacent/results.json' in docs:r['adjacent']=qualify_adjacent_documents(docs,r['rows'])
    r['seconds']=time.perf_counter()-tick;write_json(output,r);print('PASS',len(r['rows']),r['counts'],r['contrast']['equalweight_mean_bounds'],r['seconds']);return r

def qualify_adjacent_documents(docs, main_rows):
    j=lambda n:json.loads(docs[n]);sha=lambda n:hashlib.sha256(docs[n].encode('utf-8')).hexdigest()
    w=j('adjacent/inputs.json');old=j('inputs.json');reg=j('adjacent/registration.json');results=j('adjacent/results.json');r=L.ruleset_from_dict(w['rule']);r0=L.ruleset_from_dict(old['rule'])
    # The complete physical input law is preserved, but each rule owns its record.
    types=tuple(replace(pt,movement_atoms=tuple(L.LeapAtom(z)for z in L.offsets(1)))if pt.type_id=='A'else pt for pt in r0.piece_types)
    assert L.ruleset_to_dict(replace(r0,piece_types=types),include_metadata=True)==L.ruleset_to_dict(r,include_metadata=True)
    c=L.compile_rule(r);c0=L.compile_rule(r0);assert len(w['roots'])==len(old['roots'])==8
    for a,b in zip(old['roots'],w['roots']):
        s0=L.GameSession.replay(c0,L.deserialize_game_record(json.dumps(a['record'])));s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(b['record'])));assert s.state.position.board==s0.state.position.board and s.state.ply_count==s0.state.ply_count==0 and not s.state.terminal_status.is_terminal;assert L.record_value(s.state)==b['state'] and L.state_sha(s.state)==b['state_sha256']
    assert sha('adjacent/inputs.json')==reg['input_sha256'] and sha('source/factorial.py')==reg['driver_sha256'] and sha('source/game.py')==reg['game_source_sha256']
    assert results['status']=='CLOSED' and len(reg['slots'])==16 and {(s['root'],s['controller'])for s in reg['slots']}=={(i,m)for i in range(8)for m in ('UNIT','DYNAMIC_FIXED')}
    rows=[];counts=Counter();reused=0
    for i,actual in enumerate(results['slots']):
        slot=reg['slots'][i];assert all(actual[k]==v for k,v in slot.items())
        if actual['status']!='finished':continue
        g=j(f'adjacent/game-{i:03d}.json');case=j(f'adjacent/case-{i:03d}.json');assert case['input_sha256']==reg['input_sha256']and case['source_sha256']==reg['game_source_sha256'] and case['root']==slot['root']and case['controller']==slot['controller'] and case['nodes']==reg['nodes'];metadata(w,g,case);q=qualify_game(w,g,case);counts.update(q['counts']);assert actual['value']==q['value'];reused+=bool(actual['reused'])
        if actual['reused']:assert sha(f'adjacent/game-{i:03d}.json')==actual['original_sha256']
        # Actual no-P0-mate static scope is separately qualified. A contradiction
        # is retained and diagnosed; never rewrite a positive observed outcome.
        assert q['value'] is None or q['value']<=0,'observed positive payoff contradicts qualified A1/B10 no-checkmate scope'
        rows.append(dict(index=i,root=slot['root'],controller=slot['controller'],reused=actual['reused'],**q))
    missing=[i for i in range(16)if i>=len(results['slots'])or results['slots'][i]['status']!='finished'or results['slots'][i].get('value')is None];assert results['missing']==missing
    by0={(x['root'],x['controller']):x for x in main_rows};by={(x['root'],x['controller']):x for x in rows};effects=[]
    co={'geometry_UNIT':{'newU':1,'oldU':-1},'geometry_DYNAMIC':{'newD':1,'oldD':-1},'dynamic_old':{'oldD':1,'oldU':-1},'dynamic_new':{'newD':1,'newU':-1},'interaction':{'newD':1,'newU':-1,'oldD':-1,'oldU':1}}
    for root in range(8):
        values={'oldU':by0.get((root,'UNIT'),{}).get('value'),'oldD':by0.get((root,'DYNAMIC_FIXED'),{}).get('value'),'newU':by.get((root,'UNIT'),{}).get('value'),'newD':by.get((root,'DYNAMIC_FIXED'),{}).get('value')};e={}
        for name,terms in co.items():
            lo=hi=0
            for k,v in terms.items():
                value=values[k]
                if value is None:lo-=abs(v);hi+=abs(v)
                else:lo+=v*value;hi+=v*value
            e[name]=dict(value=lo if lo==hi else None,lower=lo,upper=hi)
        effects.append(dict(root=root,values=values,effects=e))
    return dict(status='PASS',games=len(rows),reused_games=reused,new_games=len(rows)-reused,missing=missing,rows=rows,counts=dict(counts),paired=effects,equalweight_mean_bounds={name:[sum(x['effects'][name]['lower']for x in effects)/8,sum(x['effects'][name]['upper']for x in effects)/8]for name in co},scope='Same8physical unfiltered starts, separate fullrules and complete histories; unit leaf/order botharms, dynamic feature geometry intentionally follows changed rule. Two exposed rules, no IID holdout/learning/WDL claim; generic missing completion bounds[-1,1] retained separately from static no-P0-checkmate fact.',new_Player_queries=0)


def qualify_cold_documents(docs):
    j=lambda n:json.loads(docs[n]);sha=lambda n:hashlib.sha256(docs[n].encode('utf-8')).hexdigest();w=j('inputs.json');reg=j('registration.json');plan=j('analysis/cold-registration.json');cold=j('analysis/cold-returns.json');vp=j('analysis/action-value-registration.json');values=j('analysis/action-value-returns.json');c=L.compile_rule(L.ruleset_from_dict(w['rule']));u=unit_evaluator(c)
    assert plan['input_sha256']==reg['input_sha256']and plan['source_sha256']==sha('source/cold.py') and vp['source_sha256']==sha('source/action_values.py') and vp['input_sha256']==plan['input_sha256']
    assert vp['record']==plan['record']and vp['state_sha256']==plan['state_sha256'];prefix=len(plan['record']['actions'])
    for mode in ('DYNAMIC_FIXED','FULL_FIXED'):
        index=next(i for i,s in enumerate(reg['slots'])if s['root']==1 and s['controller']==mode);row=j(f'game-{index:03d}.json');s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(row['initial_record'])))
        for q in row['queries'][:prefix]:s.submit(L.match_action(s,q.get('executed_action',q['action'])))
        assert L.record_value(s.to_record())==plan['record']and L.state_sha(s.state)==plan['state_sha256']and s.state.position.side_to_move==plan['actor']==0
    assert cold['status']==values['status']=='CLOSED'and cold['missing']==values['missing']==0 and len(cold['rows'])==4 and len(values['rows'])==8
    pv_edges=0
    def decision(s,d,depth):
        nonlocal pv_edges
        assert d['completed_depth']==depth and d['result_source']=='main_iteration' and d['qnodes']==0 and d['result_ordinary_qdepth']==0 and d['nodes']<=8192
        assert d['runtime_depth_balanced']and d['runtime_pushes']==d['runtime_pops'] and d['native_legality_operational_failures']==0
        assert d['action']in [L.record_value(a)for a in s.legal_actions()]
        for a in d['principal_variation']:s.submit(L.match_action(s,a));pv_edges+=1
    for row in cold['rows']:
        s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(plan['record'])));decision(s,row['decision'],6);mode=row['controller'];ep=w['profile']if mode in ('STATIC_FIXED','FULL_FIXED')else L.record_value(u._profile);ec=L.record_value(EvaluationConfig())if mode in ('DYNAMIC_FIXED','FULL_FIXED')else L.record_value(u._config);assert row['actual_leaf_profile']==ep and row['actual_leaf_config']==ec
    assert vp['actions']==[next(x['decision']['action']for x in cold['rows']if x['controller']==m)for m in ('DYNAMIC_FIXED','FULL_FIXED')]
    by={m:[]for m in plan['controllers']}
    for row in values['rows']:
        s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(plan['record'])));assert row['submitted_action']==vp['actions'][row['action_index']];s.submit(L.match_action(s,row['submitted_action']));assert L.record_value(s.to_record())==row['record'];d=row['decision'];decision(s,d,5);score=-d['score']+(1 if d['score']>0 else -1)if abs(d['score'])>=900000000 else -d['score'];assert row['root_perspective_value']==score;by[row['controller']].append((row['action_index'],score))
    pairs={m:[v for _,v in sorted(a)]for m,a in by.items()};assert all(len(v)==2 and v[0]==v[1]for v in pairs.values())
    return dict(status='PASS',queries=12,PV_plies=pv_edges,actual_requested_completed_depths=[6,5],result_sources=['main_iteration'],two_candidate_values=pairs,scope='Two candidates tie under all four actual cold fixed-depth evaluators. Not every root action evaluated, no strict argmax crossing or utility claim; shared Core replay, no search/source-capsule reexecution.',new_Player_queries=0)


def qualify_next_documents(docs):
    j=lambda n:json.loads(docs[n]);sha=lambda n:hashlib.sha256(docs[n].encode('utf-8')).hexdigest();w=j('next/inputs.json');old=j('adjacent/inputs.json');q=j('next/remnants.json');r=L.ruleset_from_dict(w['rule']);r0=L.ruleset_from_dict(old['rule'])
    assert w['status']=='PREPARED_ZERO_PLAYER_OR_TRAINING' and w['new_Player_queries']==w['learner_updates']==0
    assert w['source_sha256']==q['source_sha256']==sha('source/next_prepare.py') and q['input_sha256']==sha('next/inputs.json') and w['source_input_sha256']==sha('adjacent/inputs.json')
    types=tuple(replace(pt,movement_atoms=tuple(L.LeapAtom(o)for o in L.offsets(8)))if pt.type_id=='B'else pt for pt in r0.piece_types);assert L.ruleset_to_dict(replace(r0,piece_types=types),include_metadata=True)==L.ruleset_to_dict(r,include_metadata=True)
    c=L.compile_rule(r);c0=L.compile_rule(r0);assert w['fingerprint']==q['target_fingerprint']==L.compute_fingerprint(r) and len(w['roots'])==8
    for a,b in zip(old['roots'],w['roots']):
        s0=L.GameSession.replay(c0,L.deserialize_game_record(json.dumps(a['record'])));s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(b['record'])));assert s.state.position.board==s0.state.position.board and not s.state.terminal_status.is_terminal and s.state.ply_count==0;assert L.record_value(s.state)==b['state'] and L.state_sha(s.state)==b['state_sha256'] and len(s.legal_actions())==b['legal_count']
    from itertools import permutations
    from scripts.leaper_parity_scope import xy,adjacent,escapes
    from generic_chess.core.attacks import is_in_check
    from generic_chess.core.movegen import legal_actions_from_position
    counts={}
    for tid,owner,mask in [('A',0,1),('B',1,8)]:
        count=Counter()
        for k,a,v in permutations(range(25),3):
            if adjacent(xy(k,5),xy(v,5))or (xy(v,5)[0]-xy(a,5)[0],xy(v,5)[1]-xy(a,5)[1])not in L.offsets(mask):continue
            board=[None]*25
            for square,seat,typ in [(k,owner,'K'),(a,owner,tid),(v,1-owner,'K')]:board[square]=L.Piece(seat,typ,typ)
            p=replace(c.initial_position,board=tuple(board),side_to_move=1-owner);assert is_in_check(p,1-owner,c)and not is_in_check(p,owner,c);actions=legal_actions_from_position(p,c);actual=sorted((z.to_square.file,z.to_square.rank)for z in actions);free=sorted(escapes(xy(k,5),xy(a,5),xy(v,5),set(L.offsets(mask)),5));assert actual==free and actual;count['checked_frontiers']+=1;count['defenses']+=len(actions)
        counts[tid]=dict(count)
    assert counts==q['rosters'] and q['new_Player_queries']==q['learner_updates']==0
    return dict(status='PASS',prepared_roots=8,full_rule_fingerprint=w['fingerprint'],bare_remnant_checks=counts,scope='Prepared complete next-rule input and static absence of checkmate after any ordinary capture. No actual Player, learning or original-root WDL; no source-capsule execution.',new_Player_queries=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();qualify(a.packet,a.manifest,a.output)
