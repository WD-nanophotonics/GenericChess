"""Prospective finite role-budget policy check on new uniform opening histories.

Generate from saved full RuleSets, retaining every terminal prefix. No learning,
rule selection, old-slot refill or product default changes. Run with leaper_design.
"""
from __future__ import annotations
import argparse,copy,json,random,time
from pathlib import Path
from datetime import datetime,timezone
from fractions import Fraction as F
from scripts import leaper_design as L
from scripts.leaper_budget_calibration import serial,interval_sub,interval_mean


def prepare(source,registration,output):
    assert not output.exists();output.mkdir(parents=True);tick=time.perf_counter()
    old=L.load(source)['worlds'];r=copy.deepcopy(L.load(registration))
    assert len(old)==12
    plan={'frozen_at':datetime.now(timezone.utc).isoformat(),
        'question':'Does the exposed-cohort role-budget hypothesis transfer to prospectively generated full histories while saving actual search work?',
        'changed_premise':'New36game calibration gives own0 gain0, own1 gain5/12, layout1 own0 -1/3. This suggests a simple finite deployment comparison: role0 uses128, role1 uses512, reference always128. It is not the stopped rule-selection Pareto recipe, an intrinsic role claim, or an automatic default.',
        'selection':'ALL6 existing movement triples and2 fixed layouts,16 fresh uniform8 prefixes each, no outcome/price/oracle filtering. Freeze this sampler before generation; retain short terminal prefixes and immediate wins. These are fresh histories within exposed rules, not unseen-rule holdout or IID games.',
        'seed_formula':'202610231019 +10000*code_world+100*placement+prefix_index; prefix_index0..15. Fresh GameSession from exact full RuleSet; each step uniform among actual legal actions, stop only actual terminal or8 actions.',
        'source_inputs_sha256':L.sha(source),'new_worlds':192,'physical_games':576,
        'hypothesis':'Adaptive(role0L,role1H) vs alwaysH finite mean utility loss<=1/48; adaptive vs alwaysL mean gain>=1/24; derived serving total search nodes <=3/4 alwaysH. Also report each role/layout and confidence/partial-identification limits. Failure leaves this policy unadopted; no threshold/seed/root replacement.',
        'min_adaptive_minus_high':'-1/48','min_adaptive_minus_low':'1/24','max_node_ratio':'3/4',
        'cap_seconds':2400,'expected_seconds':2100,
        'cost_basis':'Current same-source36 games83.0080154s *16 prefixes *1.5 reserve =1992.1923696s, plus actual full-history384cost calls/preparation. Current whole-game empirical estimate, not guarantee; original2400cooperativecap includes prep/preflight and missing slots remain UNKNOWN. Code/analysis overhead expected<15min; whole logical experiment expected<50min, below120min.',
        'stop':'576physicalslots or2400seconds, all original missing/censored slots retained, no refill/broadening/fourth matrix cell. No AUX learning, solver or default changes.'}
    L.write_record(output/'prospective-plan-before-prefix-generation.json',plan)
    worlds=[]
    for ow in old:
        c=L.compile_rule(L.ruleset_from_dict(ow['rule']))
        for rep in range(16):
            s=L.GameSession(c);seed=202610231019+10000*ow['code_world']+100*ow['placement_index']+rep;rng=random.Random(seed)
            for _ in range(8):
                if s.state.terminal_status.is_terminal:break
                aa=s.legal_actions();s.submit(aa[rng.randrange(len(aa))])
            w=copy.deepcopy(ow);w.update(world=len(worlds),prefix_index=rep,prefix_seed=seed,source_world=ow['world'],context='prospective_uniform8',initial_record=L.record_value(s.to_record()),initial_state=L.record_value(s.state),initial_terminal=L.record_value(s.result),initial_legal_count=len(s.legal_actions()))
            actor=s.state.position.side_to_move
            w['initial_oneply_wins']=0 if s.state.terminal_status.is_terminal else sum(ch.terminal_status.is_terminal and ch.terminal_status.winner==actor for _,ch in L.legal_successors(s.state,c))
            replay=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(w['initial_record'])));assert L.record_value(replay.state)==w['initial_state'];worlds.append(w)
    L.write_record(output/'inputs.json',{'scope':L.load(source).get('scope','Full plainLeap/remove rules/history, prospective finite policy test.'),'worlds':worlds})
    r.update(frozen_at=plan['frozen_at'],question=plan['question'],changed_premise=plan['changed_premise'],selection=plan['selection'],criterion=plan['hypothesis'],stop=plan['stop'],cost_basis=plan['cost_basis'],pairs={'LL':['STATIC128','STATIC128'],'HL':['STATIC_ADAPTER','STATIC128'],'LH':['STATIC128','STATIC_ADAPTER']},roles=[0],repetitions=1,first_repeat=0,planned_games=576,nodes=512,search_variants={'STATIC128':{'base':'STATIC_ADAPTER','nodes':128}},preflight_policies=['STATIC128','STATIC_ADAPTER'],whole_cap_seconds=2400,expected_seconds=2100,empirical_loop_forecast_seconds=1992.1923696,source_sha256=L.sha(Path(L.__file__)),preparer_sha256=L.sha(Path(__file__)),input_sha256=L.sha(output/'inputs.json'))
    r['preparation_seconds']=time.perf_counter()-tick;L.write_record(output/'registration.json',r)
    L.write_record(output/'preflight-inputs.json',{'roots':[{'world':w['world'],'phase':w['context'],'rule':w['rule'],'record':w['initial_record']}for w in worlds if not w['initial_terminal']['status']!='ongoing']})
    # Terminal roots need no Player cost call. They remain in ALL fitness slots.
    L.write_record(output/'input-generation-assessment.json',{'worlds':len(worlds),'terminal_prefixes':sum(w['initial_terminal']['status']!='ongoing'for w in worlds),'initial_oneply_roots':sum(w['initial_oneply_wins']>0 for w in worlds),'literal_prefixes':len({json.dumps([w['fingerprint'],w['initial_record']],sort_keys=True)for w in worlds}),'new_Player_calls':0,'new_fitness':0,'preparation_seconds':r['preparation_seconds'],'scope':'Repeated short terminal prefixes remain weighted sampler occurrences, not independent observations. Every rule/layout has16 slots.'})
    print(L.load(output/'input-generation-assessment.json'),flush=True)


def analyze(output):
    rr=L.load(output/'results.json');ww=L.load(output/'inputs.json')['worlds'];assert rr['status']=='CLOSED';ss={(s['world'],s['pair']):s for s in rr['slots']};rows=[]
    for w in ww:
        ll,hl,lh=(ss[w['world'],p]['utility']for p in ('LL','HL','LH'))
        g0,g1=interval_sub(hl,ll),interval_sub(ll,lh)
        costs={}
        for p in ('LL','HL','LH'):
            sl=ss[w['world'],p];g=L.load(output/sl['receipt'])if sl.get('receipt') else None
            costs[p]=None if not g or sl['utility'][0]!=sl['utility'][1] else {'nodes':sum(q['decision']['nodes']+q['decision']['qnodes']for q in g['queries']),'main_nodes':sum(q['decision']['nodes']for q in g['queries']),'qnodes':sum(q['decision']['qnodes']for q in g['queries']),'seconds':g['seconds'],'candidate0_nodes':sum(q['decision']['nodes']+q['decision']['qnodes']for q in g['queries']if q['actor']==0),'candidate1_nodes':sum(q['decision']['nodes']+q['decision']['qnodes']for q in g['queries']if q['actor']==1)}
        rows.append(dict(world=w['world'],code=w['code_world'],placement=w['placement_index'],prefix=w['prefix_index'],terminal_prefix=w['initial_terminal']['status']!='ongoing',gain0=g0,gain1=g1,adaptive_minus_high=[-g0[1]/2,-g0[0]/2],adaptive_minus_low=[g1[0]/2,g1[1]/2],costs=costs))
    groups={}
    for name,z in [('ALL',rows)]+[(f'layout{p}',[x for x in rows if x['placement']==p])for p in (0,1)]+[(f'code{p}',[x for x in rows if x['code']==p])for p in range(6)]:
        groups[name]={'worlds':len(z),'means':{k:interval_mean([x[k]for x in z])for k in ('gain0','gain1','adaptive_minus_high','adaptive_minus_low')}}
    known=all(x['costs'][p]is not None for x in rows for p in ('LL','HL','LH'));cost={}
    if known:
        # Two virtual role deployments per root: adaptive uses LL(role0),LH(role1);
        # alwaysH uses HL(role0),LH(role1). Reuse is derived, not NEW executions.
        for field in ('nodes','seconds'):
            adaptive=sum(x['costs']['LL'][field]+x['costs']['LH'][field]for x in rows);high=sum(x['costs']['HL'][field]+x['costs']['LH'][field]for x in rows);cost[field]={'adaptive':adaptive,'always_high':high,'ratio':None if high==0 else adaptive/high}
    p=L.load(output/'prospective-plan-before-prefix-generation.json');u=groups['ALL']['means'];support=u['adaptive_minus_high'][0]>=F(p['min_adaptive_minus_high']) and u['adaptive_minus_low'][0]>=F(p['min_adaptive_minus_low']) and known and cost['nodes']['ratio'] is not None and cost['nodes']['ratio']<=F(p['max_node_ratio'])
    out=dict(status='CLOSED',hypothesis_supported=support,groups=groups,derived_serving_cost=cost,rows=rows,UNKNOWN=sum(s['utility'][0]!=s['utility'][1]for s in rr['slots']),scope='Prospective full-history sample within exposed six rules. Physical observations and virtual role deployment costs distinguished. Actual elapsed includes load/recording; node ratio not wall guarantee. No learning, intrinsic role/quality, population or default claim.')
    L.write_record(output/'assessment.json',serial(out));print(serial({k:out[k]for k in ('hypothesis_supported','groups','derived_serving_cost','UNKNOWN')}),flush=True)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('command',choices=['prepare','analyze']);p.add_argument('--output',type=Path,required=True);p.add_argument('--inputs',type=Path);p.add_argument('--source-registration',type=Path);a=p.parse_args()
    if a.command=='prepare':
        if a.inputs is None or a.source_registration is None:p.error('prepare requires saved source inputs and registration')
        prepare(a.inputs,a.source_registration,a.output)
    else:analyze(a.output)
if __name__=='__main__':main()
