"""Frozen eight-root fixed-order leaf factorial, with literal paid-cost reuse."""
from pathlib import Path
import argparse,json,random,time,traceback
from scripts import leaper_design as L
from scripts import leaper_default_contact as D
from scripts.leaper_two_type_forward import now
from scripts.leaper_two_type_qualify import qualify_game
from generic_chess.ai.evaluation.config import EvaluationConfig
from tools.local_agent.common import write_json
from tools.local_agent import session

def run(inp,registration,out):
    assert not out.exists();out.mkdir()
    w=L.load(inp);reg=L.load(registration)
    assert L.sha(inp)==reg['input_sha256'] and L.sha(Path(__file__))==reg['driver_sha256']
    assert L.sha(Path(D.__file__))==reg['game_source_sha256']
    assert reg['expected_total_seconds']<7200
    tick=time.perf_counter();rows=[];result=dict(status='RUNNING',started_at=now(),slots=rows)
    for index,slot in enumerate(reg['slots']):
        if session.stopped() or time.perf_counter()-tick>=reg['cap_seconds']:break
        receipt=dict(index=index,**slot,status='not_started');rows.append(receipt)
        try:
            if 'reuse_game' in slot:
                g=L.load(Path(slot['reuse_game']));r=L.load(Path(slot['reuse_registration']))
                assert r['input_sha256']==reg['input_sha256'] and r['source_sha256']==reg['game_source_sha256']
                assert r['root']==slot['root'] and r['controller']==slot['controller'] and r['nodes']==reg['nodes']
                assert r['q']==reg['q'] and r['services']==reg['services'] and r['tt']==reg['tt'] and not r.get('first_action_override')
                assert r['profile']==w['profile']
                receipt.update(reused=True,original_game=slot['reuse_game'],original_sha256=L.sha(Path(slot['reuse_game'])))
            else:
                r=dict(reg['base_game_registration'],root=slot['root'],controller=slot['controller'],cap_seconds=min(reg['case_cap_seconds'],max(0,reg['cap_seconds']-(time.perf_counter()-tick))),registered_at=reg['registered_at'])
                if slot['controller']=='STATIC_FIXED':
                    from scripts.semantic_probe_cost import unit_evaluator
                    c=L.compile_rule(L.ruleset_from_dict(w['rule']));r.update(actual_leaf_profile=w['profile'],actual_leaf_config=L.record_value(unit_evaluator(c)._config))
                elif slot['controller']=='DYNAMIC_FIXED':
                    from scripts.semantic_probe_cost import unit_evaluator
                    c=L.compile_rule(L.ruleset_from_dict(w['rule']));r.update(actual_leaf_profile=L.record_value(unit_evaluator(c)._profile),actual_leaf_config=L.record_value(EvaluationConfig()))
                elif slot['controller']=='FULL_FIXED':r.update(actual_leaf_profile=w['profile'],actual_leaf_config=L.record_value(EvaluationConfig()))
                rp=out/f'case-{index:03d}.json';write_json(rp,r)
                call_tick=time.perf_counter()
                g=D.run(inp,rp,out/f'game-{index:03d}.json')
                receipt.update(reused=False,caller_seconds=time.perf_counter()-call_tick,caller_scope='D.run including final serialization; module imports excluded')
            # Save literal return before downstream qualification. Reused original stays immutable.
            write_json(out/f'retained-{index:03d}.json',g)
            q=qualify_game(w,g,r);write_json(out/f'qualification-{index:03d}.json',q)
            receipt.update(status='finished',value=g['value'],censor=g['censor'],seconds=g['seconds'],plies=len(g['queries']))
        except Exception as e:
            receipt.update(status='failed',error=repr(e));write_json(out/f'error-{index:03d}.json',dict(error=repr(e),traceback=traceback.format_exc()))
        result.update(seconds=time.perf_counter()-tick);write_json(out/'results.json',result)
        print('CELL',index,slot['root'],slot['controller'],receipt,flush=True)
    missing=[i for i in range(len(reg['slots'])) if i>=len(rows) or rows[i]['status']!='finished' or rows[i].get('value') is None]
    result.update(status='CLOSED',ended_at=now(),seconds=time.perf_counter()-tick,missing=missing)
    write_json(out/'results.json',result);print('FACTORIAL_CLOSED',len(rows),missing,result['seconds'],flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--registration',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.input,a.registration,a.output)
