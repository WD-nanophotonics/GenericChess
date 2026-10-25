"""Frozen2x2 leaf-feature diagnostic; no Player search or fitted values."""
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone
from collections import Counter,defaultdict
import json,time,hashlib,traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.leaper_ordinary_qorder_study import player
from scripts.pure_leaper_search_study import append
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.search import _bounded_static_score,terminal_score
from tools.local_agent.common import write_json
from tools.local_agent import session


def stamp():return datetime.now(timezone.utc).isoformat()


def run(d):
    p=L.load(d/'plan.json');data=L.load(d/'inputs.json')
    assert hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest()==p['inputs_sha256']
    assert session.status()['id']==p['session_id']
    assert not(d/'rows.jsonl').exists()and not(d/'receipt.json').exists()
    start=stamp();tick=time.perf_counter();children=0;evaluations=0;status='FAILED';mismatches=[]
    try:
        for case in data['cases']:
            assert not session.stopped()and time.perf_counter()-tick<p['limits']['batch_seconds']
            c=L.compile_rule(L.ruleset_from_dict(case['rule']));root=replay(c,case['record']);actor=root.state.position.side_to_move
            base=player(c,'baseline');cfg=base._config;profile=base.evaluation_profile
            configs=dict(actual_DEFAULT=cfg,mobility_zero=replace(cfg,dynamic_mobility_weight=0),anchor_zero=replace(cfg,anchor_escape_weight=0),both_zero=replace(cfg,dynamic_mobility_weight=0,anchor_escape_weight=0))
            evaluators={name:Evaluator(c,profile,conf)for name,conf in configs.items()}
            labels={json.dumps(x['action'],sort_keys=True):x['own_WDL']for x in case['action_labels']}
            actions=sorted(root.legal_actions(),key=str)
            assert set(labels)=={json.dumps(L.record_value(a),sort_keys=True)for a in actions}
            records=[];began=stamp()
            for a in actions:
                assert not session.stopped()and time.perf_counter()-tick<p['limits']['batch_seconds']
                children+=1;assert children<=p['limits']['max_children']
                child=replay(c,case['record']);child.submit(a);values={};raw_values={}
                terminal=child.result.status.value!='ongoing'
                source_value=labels[json.dumps(L.record_value(a),sort_keys=True)]
                if terminal:
                    assert child.result.status.value!='no_contest'
                    actual_WDL=0 if child.result.winner is None else 1 if child.result.winner==actor else -1
                    if actual_WDL!=source_value:mismatches.append(dict(case=case['key'],action=L.record_value(a),source=source_value,Core=actual_WDL,result=L.record_value(child.result)))
                    values={name:terminal_score(child.state.terminal_status,actor,1)for name in evaluators}
                else:
                    for name,evaluator in evaluators.items():
                        v=evaluator.evaluate(child.state);evaluations+=1;assert evaluations<=p['limits']['max_manual_evaluations']
                        raw_values[name]=v;v=_bounded_static_score(v)
                        values[name]=v if child.state.position.side_to_move==actor else -v
                records.append(dict(action=L.record_value(a),action_text=str(a),source_own_WDL=source_value,terminal=terminal,Core_result=L.record_value(child.result),child_record=L.record_value(child.to_record()),values=values,raw_evaluate=raw_values))
            summary={}
            for name in evaluators:
                best=max(r['values'][name]for r in records);maxima=[r for r in records if r['values'][name]==best];chosen=maxima[0]
                summary[name]=dict(score=best,maximizers=len(maxima),maximizer_WDLs=sorted({r['source_own_WDL']for r in maxima}),all_ties_source_optimal=all(r['source_own_WDL']==case['root_own_WDL']for r in maxima),some_tie_source_optimal=any(r['source_own_WDL']==case['root_own_WDL']for r in maxima),canonical_action=chosen['action'],canonical_chosen_WDL=chosen['source_own_WDL'])
            ended=stamp();append(d/'rows.jsonl',dict(case=case['key'],source_group='exposed6x6control'if case['key'].startswith('next-role')else'fixed17source_metadata',root_record=case['record'],root_actor=actor,root_own_WDL=case['root_own_WDL'],label_tier=case['label_tier'],actual_profile=L.record_value(profile),actual_configs={name:L.record_value(conf)for name,conf in configs.items()},records=records,summary=summary,started_at=began,ended_at=ended))
            if ended>began:session.record_work(began,ended,'validation',f'{d.as_posix()}/rows.jsonl actual one-ply2x2feature diagnostic {case["key"]}; manual evaluations notPlayerqueries,labelsnotusedforranking')
            print('LEAF-FACTORIAL',case['key'],len(records),{name:s['canonical_chosen_WDL']for name,s in summary.items()},flush=True)
        status='CLOSED'
    except BaseException:
        write_json(d/'failure.json',dict(at=stamp(),children=children,evaluations=evaluations,error=traceback.format_exc()));raise
    finally:
        write_json(d/'receipt.json',dict(status=status,started_at=start,ended_at=stamp(),seconds=time.perf_counter()-tick,Core_children=children,manual_evaluations=evaluations,Player_choose_queries=0,terminal_source_mismatches=mismatches,plan_sha256=hashlib.sha256((d/'plan.json').read_bytes()).hexdigest()))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
