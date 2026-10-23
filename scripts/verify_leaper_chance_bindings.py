"""Bind each strict alternative certificate to its original played prefix."""
from collections import Counter
from fractions import Fraction as F
import json,time
from scripts import leaper_design as L
from generic_chess.core.actions import action_from_dict,action_to_dict


def verify(compiled,docs,choices,certificates):
    tick=time.perf_counter();source={(r['receipt'],r['ply']):r for r in choices['rows']};seen=set();counts=Counter()
    if len(certificates['policies'])!=len(certificates['bindings']):raise ValueError('strict proof binding count differs')
    for binding in certificates['bindings']:
        key=binding['receipt'],binding['ply']
        if key in seen or key not in source:raise ValueError('duplicate or foreign played context binding')
        seen.add(key);row=source[key];game=json.loads(docs['forward/'+binding['receipt']])
        if row['quality']!='STRICT_ORACLE_CONTINUATION_INFERIOR'or binding['policy']!=game['policy']or binding['seed']!=game['seed']:raise ValueError('strict report group differs')
        record=game['final_record']|{'actions':game['final_record']['actions'][:row['ply']]}
        s=L.GameSession.replay(compiled,L.deserialize_game_record(json.dumps(record)))
        if L.state_sha(s.state)!=binding['state_sha']or binding['state_sha']!=row['state_sha']:raise ValueError('strict original full prefix differs')
        selected=row['actions'][row['selected']];alternative=row['actions'][row['best_lower_action']]
        if selected!=binding['selected']or alternative!=binding['alternative']:raise ValueError('strict selected/alternative metadata differs')
        original=game['queries'][row['ply']]
        if action_to_dict(L.match_action(s,original['action']))!=selected['action']:raise ValueError('claimed played action differs from actual source')
        s.submit(action_from_dict(alternative['action']));policy=certificates['policies'][binding['certificate_index']]
        if L.record_value(s.to_record())!=policy['record']or L.state_sha(s.state)!=policy['root_state_sha']:raise ValueError('lower proof not bound to literal alternative')
        if F(policy['lower'])!=F(alternative['lower'])or F(policy['lower'])<=F(selected['upper']):raise ValueError('alternative does not establish strict gap')
        counts[game['policy']]+=1
    required={(r['receipt'],r['ply'])for r in choices['rows']if r['quality']=='STRICT_ORACLE_CONTINUATION_INFERIOR'}
    if seen!=required:raise ValueError('strict claims missing literal alternative bindings')
    return dict(verified=True,strict_counts=dict(counts),seconds=time.perf_counter()-tick,scope='Eachselectedactioncomesfromtheoriginalplayedquery;eachpositivecontrollerrootisthatSAMEfullprefixplusonelegitimatealternative. Posthoccounterfactualsarenotnewtrainingstarts, performancegamesorPlayerqueries.')
