"""Finite explicit diagnostic atlas, NOT the stopped eight-family quality panel.
No Player or WDL solver. One engineered rule; every free knight placement has
one fixed slot, invalid starts retained, no replacements or outcome tuning.
"""
import json,copy,time
from pathlib import Path
from scripts.research_record import write_record,record_value
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.leaper_threat_ordering import ThreatOrderer
from generic_chess.rules.schema import compute_fingerprint,ruleset_from_dict
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.cache import EvaluationProfileCache
from generic_chess.rules.validation import RuleValidationError

def run(out):
    out=Path(out);assert not out.exists();out.mkdir();source=json.loads(Path('.local_agent/threat-751b9f58/mechanism-witness/input-before-Core.json').read_text())['row'];write_record(out/'frozen.json',{'source':source,'slots':'knight at each row-major index0..63;occupied originalnonknight cells INVALID;Core-invalid starts INVALID;no replacements','cap_seconds':120,'max_Core_reply_checks':4096,'question':'Does the frozen threat score contain one-reply mate-risk information absent from default static preference in this engineered rule?','scope':'one highly engineered movement rule,not qualitypanel/heldoutfamily/strength.0Player,0solver,0games;no fitting or retuning'})
    tick=time.perf_counter();checks=0;results=[];contrasts=[];halt=None
    for index in range(64):
        obs={'slot':index,'status':'NOT_RUN'}
        if halt:obs['reason']=halt;results.append(obs);continue
        rule=copy.deepcopy(source['RuleSet']);rule['initial_position'][3][1]=None
        if rule['initial_position'][index//8][index%8] is not None:obs.update(status='INVALID_OCCUPIED');results.append(obs);continue
        rule['initial_position'][index//8][index%8]=dict(owner=1,base_type_id='N',current_type_id='N',promoted=False);fp=compute_fingerprint(ruleset_from_dict(rule));row=dict(source,RuleSet=rule,fingerprint=fp,record=dict(source['record'],ruleset_fingerprint=fp))
        try:c,s=make_session(row)
        except RuleValidationError as e:obs.update(status='INVALID_RULE_START',error=str(e));results.append(obs);write_record(out/'slots.json',results);continue
        if s.state.terminal_status.is_terminal:obs.update(status='TERMINAL_START');results.append(obs);continue
        evcfg=EvaluationConfig();prof,_=EvaluationProfileCache(use_disk=False).get_or_build(c,evcfg);ev=Evaluator(c,prof,evcfg);actions=[a for a in s.legal_actions() if s.state.position.board[a.to_square.rank*8+a.to_square.file] is None];features=ThreatOrderer(c).feature(s.state,actions);arm=[]
        for a in actions:
            if time.perf_counter()-tick>115 or checks>=4096:halt='frozen_cap';break
            child=type(s).replay(c,s.to_record());child.submit(a);x={'action':record_value(a),'hint':features['scores'][a],'static_from_parent':-ev.evaluate(child.state),'immediate_opponent_wins':0,'opponent_replies':0}
            for reply in child.legal_actions():
                if time.perf_counter()-tick>115 or checks>=4096:halt='frozen_cap';break
                g=type(s).replay(c,child.to_record());g.submit(reply);checks+=1;x['opponent_replies']+=1
                if g.state.terminal_status.is_terminal and g.state.terminal_status.winner==1:x['immediate_opponent_wins']+=1
            arm.append(x)
            if halt:break
        obs.update(status='CENSORED' if halt else 'COMPLETE',arms=arm);results.append(obs);write_record(out/'slots.json',results)
        if not halt and len(arm)>=2:
            staticbest=max(x['static_from_parent'] for x in arm);beststatic=[x for x in arm if x['static_from_parent']==staticbest];hintbest=max(x['hint'] for x in arm);besthint=[x for x in arm if x['hint']==hintbest]
            equal_static_riskdiff=any(x['static_from_parent']==y['static_from_parent'] and x['immediate_opponent_wins']!=y['immediate_opponent_wins'] for x in arm for y in arm)
            contrasts.append({'slot':index,'static_best_risks':[x['immediate_opponent_wins'] for x in beststatic],'hint_best_risks':[x['immediate_opponent_wins'] for x in besthint],'equal_static_different_risks':equal_static_riskdiff})
    write_record(out/'slots.json',results)
    write_record(out/'contrasts.json',contrasts);summary={'statuses':{s:sum(r['status']==s for r in results) for s in {x['status'] for x in results}},'Core_reply_checks':checks,'equal_static_riskcontrast_slots':[x['slot'] for x in contrasts if x['equal_static_different_risks']],'hintstrictly_improves_beststatic_risk_slots':[x['slot'] for x in contrasts if max(x['hint_best_risks'])<min(x['static_best_risks'])],'hintcan_be_worse_than_beststatic_slots':[x['slot'] for x in contrasts if max(x['hint_best_risks'])>min(x['static_best_risks'])],'seconds':time.perf_counter()-tick,'halt':halt,'scope':'Diagnostic conditionalone-rule atlas,notWDL or measuredsearchquality;staticmax omitsrootterminal/capture/TT semantics'};write_record(out/'summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':run('.local_agent/threat-751b9f58/tactical-atlas')
