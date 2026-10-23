"""Describe complete/UNKNOWN forward price games, without new Player decisions."""
import argparse
from collections import Counter,defaultdict
from fractions import Fraction
from pathlib import Path
from scripts import leaper_design as L


def bounds(slots):
    return [str(sum(Fraction(s['utility'][i]) for s in slots)/len(slots)) for i in (0,1)]


def analyze(d):
    reg=L.load(d/'registration.json');result=L.load(d/'results.json');inputs=L.load(d/'inputs.json')
    assert result['status']=='CLOSED' and L.sha(d/'inputs.json')==reg['input_sha256']
    expected={(w['world'],pair,role,rep) for w in inputs['worlds'] for pair in reg['pairs'] for role in reg['roles'] for rep in range(reg.get('first_repeat',0),reg.get('first_repeat',0)+reg['repetitions'])}
    actual=[(s['world'],s['pair'],s['role'],s['repeat']) for s in result['slots']]
    assert len(actual)==len(set(actual))==reg['planned_games'] and set(actual)==expected,'complete planned census required'
    groups=defaultdict(list);codes=defaultdict(list);paths=[];counts=Counter();seconds=defaultdict(float);nodes=Counter();depths=defaultdict(Counter)
    for s in result['slots']:
        w=inputs['worlds'][s['world']];board=w['rule']['board_size'];groups[board,s['pair']].append(s);codes[board,w['code_world'],s['pair']].append(s)
        if s['status']!='finished':continue
        g=L.load(d/s['receipt']);assert all(g[k]==s[k] for k in ('world','pair','role','repeat','utility'))
        for q in g['queries']:
            counts[q['policy']]+=1;seconds[q['policy']]+=q['seconds'];nodes[q['policy']]+=q['decision']['nodes'];depths[q['policy']][q['decision']['completed_depth']]+=1
    for w in inputs['worlds']:
        for pair,policies in reg['pairs'].items():
            ss=[s for s in result['slots'] if s['world']==w['world'] and s['pair']==pair]
            if len(ss)!=2 or any(s['status']!='finished' for s in ss):continue
            ss=sorted(ss,key=lambda x:x['role']);games=[L.load(d/s['receipt']) for s in ss]
            first=None
            for a,b in zip(games[0]['queries'],games[1]['queries']):
                if a['action']!=b['action']:
                    first={'ply':a['root_ply'],'actor':a['actor'],'policies':[a['policy'],b['policy']],'scores':[a['decision']['score'],b['decision']['score']],'completed_depths':[a['decision']['completed_depth'],b['decision']['completed_depth']],'termination_reasons':[a['decision']['termination_reason'],b['decision']['termination_reason']]};break
            static=w['material_profiles']['Static'];candidate=w['price_profiles'][policies[1]]
            same_board_prices=static['board_value_by_type']==candidate['board_value_by_type']
            paths.append({'world':w['world'],'board_size':w['rule']['board_size'],'code_world':w['code_world'],'layout_index':w['layout_index'],'pair':pair,
                'same_board_prices':same_board_prices,'same_full_action_history':games[0]['final_record']==games[1]['final_record'],
                'same_physical_winner_or_draw':games[0]['terminal']['winner']==games[1]['terminal']['winner'],
                'first_action_difference':first,'by_role_utilities':[s['utility'] for s in ss]})
    summary=[]
    for (board,pair),ss in sorted(groups.items()):
        summary.append({'board_size':board,'pair':pair,'planned':len(ss),'retained':sum(s['status']=='finished' for s in ss),'UNKNOWN':sum(s['utility'][0]!=s['utility'][1] for s in ss),'bounds':bounds(ss),
            'by_role':{str(role):bounds([s for s in ss if s['role']==role]) for role in reg['roles']},'known_outcomes':dict(Counter(str(s['utility'][0]) for s in ss if s['utility'][0]==s['utility'][1]))})
    per_code=[{'board_size':board,'code_world':code,'pair':pair,'planned':len(ss),'bounds':bounds(ss)} for (board,code,pair),ss in sorted(codes.items())]
    out={'status':'CLOSED','planned':len(result['slots']),'retained':sum(s['status']=='finished' for s in result['slots']),'UNKNOWN':sum(s['utility'][0]!=s['utility'][1] for s in result['slots']),'summary':summary,'per_code':per_code,'role_swap_paths':paths,
         'controller_returns':dict(counts),'policy_seconds':dict(seconds),'actual_nodes':dict(nodes),'completed_depth_histograms':dict(depths),'loop_seconds':result['seconds'],'new_Player_calls':0,
         'scope':'All frozen slots include UNKNOWN; exposed generated rules/layouts, deterministic role swaps not independent seed replicates. Zero finite contrast or a zero-containing completion interval does not prove no learning space. Same physical winner is weaker than same full action history. Differentboard/profile/layout contrasts are joint, not purecausality. No fit/qualityscalar/learnergate/WDL.'}
    L.write_record(d/'price-assessment.json',out)
    # In this admitted no-hand/remove domain, unchanged board prices imply the
    # same leaf evaluator on reachable states; actual path check catches routing.
    noops=[x for x in paths if x['same_board_prices']]
    assert all(x['same_full_action_history'] for x in noops),'same-price no-op changed an actual deterministic path'
    L.write_record(d/'price-assessment-qualification.json',{'status':'PASS','census':len(actual),'same_price_noop_pairs':len(noops),'same_price_noop_paths_equal':len(noops),'scope':'Actual no-op pair paths, not an independent optimality test.'})
    print(summary,flush=True);return out

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.output)
