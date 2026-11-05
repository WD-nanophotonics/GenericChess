"""Read committed Q-policy DATA for the existing learner; no Player or fitting."""
from __future__ import annotations
import argparse,collections,gzip,hashlib,json,math,time
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.aux_count_pair_analysis_20261105 import physical_features
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,SessionChoice
PIN='549b159a0129e2f96062935ce3786ddf3efb08a1'
def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def choose(env,raw):
    options=[a for a in env.actions() if a.kind=='ACTION' and L.record_value(a.action)==raw]
    assert len(options)==1
    return options[0]
def analyze(base,output):
    began=time.perf_counter();manifest=read(base/'manifest.json')
    loaded={}
    # Only materialized project DATA. Archived source never imported.
    for item in manifest['files']:
        p=base/item['path']
        if p.exists():
            b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==item['sha256']
            decoded=gzip.decompress(b);assert hashlib.sha256(decoded).hexdigest()==item['original_sha256']
            loaded[item['path']]=item['sha256']
    inputs=read(base/'inputs.json.gz')['rows'];compiled={}
    for item in inputs:compiled[item['family']]=L.compile_rule(L.ruleset_from_dict(item['RuleSet']))
    games=[read(p) for p in sorted(base.glob('game-*.json.gz'))]
    assert len(games)==12
    facts=[];gfacts=[];counts=collections.Counter();groups=collections.defaultdict(list)
    pv_edges=0;orphans=set(p.name[:-3] for p in base.glob('return-*.json.gz'));witnesses={}
    for g in games:
        f=g['slot']['family'];world=inputs[f]
        env=FixedScaleSessionEnv(restore(compiled[f],world['record']),unit_type='A',feature_mode='count_pairs')
        assert L.record_value(env.session.to_record())==g['initial_record']
        assert len(env.names)==27
        model=Model([1,1,1]+[0]*24,fixed=0,scale=10)
        local=[]
        for ply,name in enumerate(g['returns']):
            orphans.remove(name);r=read(base/(name+'.gz'));d=r['decision'];actor=env.player()
            assert r['ply']==ply and r['game']==g['game'] and r['actor']==actor
            assert r['record_before']==L.record_value(env.session.to_record()) and env.terminal() is None
            rootphi=env.features();assert rootphi==physical_features(env.session.state.position,env.base_names)
            leaf=FixedScaleSessionEnv(env.session,unit_type='A',feature_mode='count_pairs')
            assert not d['principal_variation'] or d['principal_variation'][0]==d['action']
            for a in d['principal_variation']:leaf.push(choose(leaf,a));pv_edges+=1
            phi=leaf.features();assert phi==physical_features(leaf.session.state.position,leaf.base_names)
            actual=leaf.terminal();signed=d['score']*(1 if actor==0 else -1)
            length=len(d['principal_variation']);equal=length==d['completed_depth']
            # Diagnostic equality only: Q4/DEFAULT evaluator does not become q0/Model.
            raw=model.raw(phi);scorematch=math.isclose(signed,raw,abs_tol=1e-10,rel_tol=1e-12)
            terminalmatch=actual is not None and ((actual==0 and signed==0) or (actual!=0 and signed*actual>=900_000_000))
            row=dict(game=g['game'],family=f,ply=ply,return_path=name,actor=actor,on=r['on'],timing_eligible=r['timing_eligible'],
                source=d['result_source'],reason=d['termination_reason'],depth=d['completed_depth'],pv_length=length,
                pv_length_equal_depth=equal,pv_terminal=actual,signed_score=signed,root_phi=list(rootphi),pv_phi=list(phi),
                root_CC=rootphi[17],pv_CC=phi[17],unit_leaf_raw=raw,score_equals_unit_leaf=scorematch,
                terminal_score_match=terminalmatch,seconds=r['wall_seconds'],
                root_free_gradient_nonzero=any(model.gradient(rootphi)),
                leaf_free_gradient_nonzero=actual is None and any(model.gradient(phi)),
                mechanical_q0_checks_pass=terminalmatch or (actual is None and scorematch and equal and bool(d['principal_variation'])))
            facts.append(row);local.append(row)
            groups[f,tuple(rootphi)].append(row)
            for key,yes in [('root_nonzero_CC',rootphi[17]!=0),('pv_nonzero_CC',phi[17]!=0),
                ('root_free_gradient_nonzero',row['root_free_gradient_nonzero']),('pv_free_gradient_nonzero',row['leaf_free_gradient_nonzero']),
                ('pv_terminal',actual is not None),('empty_PV',not d['principal_variation']),('PV_length_equal_depth',equal),('score_equals_unit_leaf',scorematch),
                ('mechanical_q0_checks_pass',row['mechanical_q0_checks_pass']),
                ('timing_failure',not r['timing_eligible']),('cancelled',d['termination_reason']=='cancelled'),
                ('root_zero_phi_nonzero_teacher',not any(rootphi) and signed!=0),
                ('pv_zero_phi_nonzero_teacher',actual is None and not any(phi) and signed!=0)]:
                counts[key]+=int(yes)
                if yes and key not in witnesses:witnesses[key]=row
            env.push(choose(env,d['action']))
        assert L.record_value(env.session.to_record())==g['final_record'] and L.record_value(env.session.result)==g['literal_result']
        assert env.terminal()==0 and g['actual_terminal'] and g['ONvalue']==0
        assert g['eligible']==all(r['timing_eligible'] for r in local)
        gfacts.append(dict(game=g['game'],family=f,ONseat=g['slot']['ONseat'],queries=len(local),eligible=g['eligible'],
            literal_outcome=env.terminal(),status=g['literal_result']['status'],
            root_gradient_rows=sum(x['root_free_gradient_nonzero'] for x in local),
            leaf_gradient_rows=sum(x['leaf_free_gradient_nonzero'] for x in local),
            CC_rows=sum(x['root_CC']!=0 or x['pv_CC']!=0 for x in local),
            terminal_pv_rows=sum(x['pv_terminal'] is not None for x in local),
            mainline_cancelled=sum(x['reason']=='cancelled' for x in local)))
    assert len(facts)==724 and not orphans and pv_edges==4496
    aliases=[]
    for (f,phi),rs in groups.items():
        labels=sorted(set(x['signed_score'] for x in rs))
        if len(labels)>1:
            first=rs[0];other=next(x for x in rs if x['signed_score']!=first['signed_score'])
            aliases.append(dict(family=f,phi=list(phi),rows=len(rs),labels=labels,
                first=dict(return_path=first['return_path'],game=first['game'],ply=first['ply'],signed_score=first['signed_score']),
                other=dict(return_path=other['return_path'],game=other['game'],ply=other['ply'],signed_score=other['signed_score'])))
    result=dict(source=PIN,scope='saved-only existing learner consumer, not a new policy/teacher/fit',new_Player=0,new_training=0,
        loaded_members=len(loaded),compressed_hashes=loaded,games=gfacts,counts=dict(counts),queries=len(facts),PV_edges=pv_edges,
        literal_draws=12,qualified_games=sum(g['eligible'] for g in gfacts),qualified_pair_families=[f for f in range(6) if all(g['eligible'] for g in gfacts if g['family']==f)],
        own_same_feature_conflicts=aliases,first_witnesses=witnesses,rows=facts,wall_seconds=time.perf_counter()-began,
        interpretations=[
            'All724 retain a completed main iteration;cancelled means next iteration stopped,not necessarily unusable last score.',
            'Q4 PV omits q continuations;require_full_pv=False permits TT-prefix truncation. Legal PV does not supply exact evaluated leaf gradient.',
            'All DEFAULT scores are root-side oriented. Multiply by actor sign before any player0 learner interpretation.',
            'Mechanical q0 checks are descriptive coincidences only; DEFAULT evaluator,Q4,persistent TT,missing q PV and model epoch do not match current TDLeaf consumer.',
            'Literal draws are actual history outcomes;five timing-invalid policy slots stay UNKNOWN in the frozen quality endpoint,not fabricated DRAW labels.',
            'All sources have one C per owner,no creation. This experience cannot fix absent C/Csupport even if deeper DEFAULT search is called stronger.',
            'Same-root-feature teacher conflicts are exposed target nonrepresentability evidence,not incorrect teacher,actionWDL,fit failure or oracle truth.',
            'No direct receipt adoption,trajectory selection,extra Player,teacherfit,policy promotion or PRIMARY timing observer follows.'])
    output.write_text(json.dumps(result,separators=(',',':'),allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','compressed_hashes','first_witnesses','own_same_feature_conflicts')},indent=2))
    print('conflicting_feature_groups',len(aliases),'first',aliases[:1])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);p.add_argument('output',type=Path);a=p.parse_args();analyze(a.base,a.output)
