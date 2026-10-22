"""Read the technical observations; never run fitness producers or train a model."""
import argparse,gzip,hashlib,json,random,sys,time
from collections import Counter
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.evaluation.config import EvaluationConfig,MATE_SCORE
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.core.actions import action_is_drop
from generic_chess.core.transition import legal_successors
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value


def digest(value):
    return hashlib.sha256(json.dumps(record_value(value),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


def floor_choice(session,rng):
    actions=[];actor=session.state.position.side_to_move
    for action,child in legal_successors(session.state,session.compiled):
        actions.append(action)
        if child.terminal_status.winner==actor:
            return action,len(actions),True
    return actions[rng.randrange(len(actions))],len(actions),False


def terminal_value(state,actor,ply):
    result=state.terminal_status
    return 0 if result.winner is None else (MATE_SCORE-ply)*(1 if result.winner==actor else -1)


def verify(directory):
    started=time.perf_counter();manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'));blob=(directory/'observations.json.gz').read_bytes()
    assert hashlib.sha256(blob).hexdigest()==manifest['sha256'] and len(blob)==manifest['bytes']
    raw=gzip.decompress(blob);assert len(raw)==manifest['uncompressed_bytes'];data=json.loads(raw);assert data['schema']==1
    compiled={fp:compile_rule(ruleset_from_dict(row['rule']))for fp,row in data['rules'].items()}
    assert all(c.ruleset_fingerprint==fp for fp,c in compiled.items())
    for name,source in data['source_files'].items():
        assert hashlib.sha256(source['text'].encode()).hexdigest()==source['sha256']==manifest['source_files'][name]
    counters=Counter();per_batch=Counter();choices=Counter();density={(x['source_slot'],x['ply']):x for x in data['natural_density']['rows']};evaluators={};attractor={x['case']:x for x in data['attractor_cases']};root_contexts={};density_counts=Counter()
    for game in data['games']:
        batch=game['batch'];c=compiled[game['ruleset_fingerprint']];s=GameSession.replay(c,deserialize_game_record(json.dumps(game['initial_record'])));assert digest(s.state)==game['initial_state_sha256'];n=len(s.history);record=deserialize_game_record(json.dumps(game['final_record']));assert tuple(s.to_record().actions)==record.actions[:n];assert len(record.actions)-n==len(game['queries']);counters['prefix_plies_replayed']+=n
        rng={int(a):random.Random(seed)for a,seed in (game['rng_seeds']or{}).items()}
        if batch=='attractor':
            case=attractor[game['case']];assert record_value(s.state)==case['full_state']
            for a,state in case['rng_states'].items():
                rng[int(a)]=random.Random();rng[int(a)].setstate((state[0],tuple(state[1]),state[2]))
        if batch=='small_ladder'and game['world']not in evaluators:
            base=AlphaBetaPlayer(c,use_disk_cache=False).evaluation_profile;profiles=data['finite_profiles'][str(game['world'])];evaluators[game['world']]={name:Evaluator(c,replace(base,board_value_by_type=p['board_value_by_type'],hand_value_by_base_type=p['hand_value_by_base_type'],promotion_gain_by_type=p['promotion_gain_by_type']),EvaluationConfig())for name,p in profiles.items()}
        for q,action in zip(game['queries'],record.actions[n:]):
            actor=s.state.position.side_to_move;assert q['actor']==actor and q['root_ply']==s.state.ply_count;policy=q.get('policy','Player');dec=q.get('decision');assert record_value(action)==(dec['action']if dec else q['action']);choices[batch,policy]+=1
            if policy=='RNG':
                legal=s.legal_actions();assert legal[rng[actor].randrange(len(legal))]==action
            elif policy=='FLOOR':
                chosen,count,winning=floor_choice(s,rng[actor]);assert chosen==action and count==q['floor']['enumerated_children']and winning==q['floor']['winning_action_found'];counters['FLOOR_children']+=count
            if dec:
                assert dec['runtime_depth_balanced'];limit=int(policy[1:])if policy.startswith('N')else 65536 if batch=='attractor'else 2048
                assert dec['nodes']+dec['qnodes']<=limit
                if batch!='check_only'or not q.get('candidate'):assert dec['qnodes']==0
                pv=s.state
                for entry in dec['principal_variation']:
                    _,pv=next((a,ch)for a,ch in legal_successors(pv,c)if record_value(a)==entry);counters['PV_edges']+=1
                    if batch!='baseline_A':counters['new_PV_edges']+=1
                if dec['result_source']=='root_immediate_win':assert pv.terminal_status.winner==actor
                counters['Player_returns']+=1
                if batch!='baseline_A':counters['new_Player_returns']+=1
            if batch=='small_ladder':
                row=density[game['slot'],s.state.ply_count];children=list(legal_successors(s.state,c));assert len(children)==len(row['branches'])
                for (a,ch),br in zip(children,row['branches']):
                    assert record_value(a)==br['action'];actual={name:terminal_value(ch,actor,1)if ch.terminal_status.is_terminal else ev.evaluate(ch)*(1 if ch.position.side_to_move==actor else-1)for name,ev in evaluators[game['world']].items()};assert actual==br['scores'];counters['density_children']+=1
                scores={name:max(b['scores'][name]for b in row['branches'])for name in row['support_indices']};supports={name:[i for i,b in enumerate(row['branches'])if b['scores'][name]==scores[name]]for name in scores};assert supports==row['support_indices'];sensitive=any(v!=supports['Static']for v in supports.values());assert sensitive==row['price_sensitive'];density_counts['sensitive']+=sensitive;density_counts['invariant']+=not sensitive
                coeffs={tuple(b['material_difference'])if b['material_difference']is not None else(0,0,0)for b in row['branches']};assert not sensitive or len(coeffs)>1;density_counts['potential']+=len(coeffs)>1;counters['density_roots']+=1
            s.submit(action);counters['history_plies']+=1
            if batch!='baseline_A':counters['new_history_plies']+=1
        assert digest(s.state)==game['final_state_sha256'] and record_value(s.result)==game['terminal'];result=s.result;value=None if not game['eligible']or result.status.value in('ongoing','no_contest')else 0 if result.winner is None else 1 if result.winner==game['role']else -1;assert game['utility']==([value,value]if value is not None else[-1,1]);per_batch[batch]+=1
    assert dict(per_batch)==manifest['retained_games_by_batch'];assert density_counts=={'sensitive':300,'invariant':12091,'potential':2699}
    # Scalar negamax per price, independent of the producer's shared-vector min/max.
    cases=data['finite_inputs']['cases'];parent_fp={g['world']:g['ruleset_fingerprint']for g in data['games']if g['batch']=='small_ladder'}
    for row in data['finite_results']['rows']:
        if row['status']!='complete':continue
        case=cases[row['case']];c=compiled[parent_fp[row['world']]];s=GameSession.replay(c,deserialize_game_record(json.dumps(case['record'])));assert record_value(s.state)==case['full_state'];actor=s.state.position.side_to_move
        for name,ev in evaluators[row['world']].items():
            def negamax(st,depth,ply):
                if st.terminal_status.is_terminal:return terminal_value(st,st.position.side_to_move,ply)
                if depth==0:return ev.evaluate(st)
                values=[]
                for a,ch in legal_successors(st,c):counters['finite_scalar_edges']+=1;values.append(-negamax(ch,depth-1,ply+1))
                assert values;return max(values)
            values=[]
            for a,ch in legal_successors(s.state,c):counters['finite_scalar_edges']+=1;values.append((record_value(a),-negamax(ch,row['depth']-1,1)))
            assert [v for a,v in values]==[b['values'][name]for b in row['partial_root_actions']];best=max(v for a,v in values);assert best==row['best'][name]and[a for a,v in values if v==best]==row['supports'][name]
        counters['finite_completed_rows']+=1
    # Retained cold resource probes, including actual hands and legal drops.
    resource_cases={c['world']:c for c in data['resource_preflight_inputs']['cases']}
    for q in data['resource_preflight_results']['queries']:
        case=resource_cases[q['world']];mode=q['mode'];c=compile_rule(ruleset_from_dict(case[mode+'_rule']));s=GameSession.replay(c,deserialize_game_record(json.dumps(case[mode+'_record'])));assert record_value(s.state)==case[mode+'_full_state'];dec=q['decision'];assert dec['nodes']+dec['qnodes']<=2048 and dec['qnodes']==0 and dec['runtime_depth_balanced'];pv=s.state
        for entry in dec['principal_variation']:_,pv=next((a,ch)for a,ch in legal_successors(pv,c)if record_value(a)==entry);counters['cold_PV_edges']+=1
        if dec['result_source']=='root_immediate_win':assert pv.terminal_status.winner==s.state.position.side_to_move
        if mode=='variant':assert sum(action_is_drop(a)for a in s.legal_actions())==case['variant_drop_count']
        counters['cold_Player_returns']+=1
    # Balanced self-source utilities cancel exactly even when the single tail is UNKNOWN.
    baseline=[g for g in data['games']if g['batch']=='baseline_A'];assert len(baseline)==12 and all(g['eligible']for g in baseline)
    games=[g for g in data['games']if g['batch']=='check_only'];effect=[str(sum(Fraction(g['utility'][side])for g in games)/24)for side in(0,1)];assert effect==data['analyses']['check_only']['effects']['checkonly-pureq0']
    direct=[g for g in data['games']if g['batch']=='resource_direct'];assert len(direct)==16;assert[str(sum(Fraction(g['utility'][side])for g in direct)/16)for side in(0,1)]==data['analyses']['resource_direct']['effects']['N2048_versus_D1']
    return {'all_passed':True,'scope':'SharedCore full-history/PV, actualEvaluator density, independent scalar finite references; not a second engine or WDL oracle. No fitness/training executed.','counters':dict(counters),'retained_games':dict(per_batch),'choices_by_batch_policy':{str(k):v for k,v in choices.items()},'seconds':time.perf_counter()-started,'observation_sha256':manifest['sha256']}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=Path(__file__).resolve().parent);parser.add_argument('--output',type=Path);args=parser.parse_args();result=verify(args.data)
    if args.output:args.output.write_bytes((json.dumps(result,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result,indent=2))
