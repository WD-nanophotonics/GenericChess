"""Clock-only teacher information experiment on saved, outcome-blind slots."""
from pathlib import Path
from dataclasses import replace
import gzip,json,time
from collections import Counter
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict,ruleset_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.research_record import record_value,write_record
from scripts.leaper_neural_teacher import solve_session


def run(base,output,seconds=360):
    base=Path(base);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    if (out/'results.jsonl').exists():raise FileExistsError('completed/partial clock slots are not refilled')
    old=json.loads(gzip.decompress((base/'dataset.json.gz').read_bytes()))
    selected=[r for r in old['rows'] if r.get('status')=='EXACT' and (r['size']==4 and r['slot']<256 or r['size']==5 and r['slot']<128)]
    write_record(out/'plan.json',dict(question='Does only extending the authoritative clock4→8/16 improve exact decisive teacher support?',
        inputs='first2564x4+1285x5saved slots, fixed before results; identical initial boards and legal action histories',
        clocks=[8,16],nodes=1500,batch_seconds=seconds,model='unchanged/no training in this experiment',
        labels='Core/existing solver; UNKNOWN distinct; one proven winning action certifies rootWIN even if other root actions unresolved',
        expected_seconds=180,maximum_calls=len(selected)*2,no_refill=True))
    tick=time.perf_counter();rows=[];stop=None
    for clock in (8,16):
        for i,oldrow in enumerate(selected):
            if time.perf_counter()-tick>=seconds:stop='batch_cap';break
            rules=replace(ruleset_from_dict(oldrow['rules']),max_ply=clock);c=compile_ruleset(rules)
            record=dict(oldrow['record'],ruleset_fingerprint=c.ruleset_fingerprint)
            s=GameSession.replay(c,deserialize_game_record(json.dumps(record)));start=time.perf_counter();teacher=solve_session(rules,s,1500)
            row=dict(size=oldrow['size'],slot=oldrow['slot'],family=oldrow['family'],clock=clock,split=oldrow['split'],original_label=oldrow['label'],
                rules=ruleset_to_dict(rules),record=record_value(s.to_record()),teacher=teacher,seconds=time.perf_counter()-start)
            rows.append(row)
            with (out/'results.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,separators=(',',':'))+'\n')
            if i%64==0:print(json.dumps(dict(clock=clock,done=i+1,seconds=time.perf_counter()-tick,labels=dict(Counter(r['teacher']['label'] or 'UNKNOWN' for r in rows if r['clock']==clock)))),flush=True)
        if stop:break
    summary=dict(seconds=time.perf_counter()-tick,stop=stop,calls=len(rows),not_run=len(selected)*2-len(rows),
        conditions=[dict(size=size,clock=clock,labels=dict(Counter(r['teacher']['label'] or 'UNKNOWN' for r in rows if r['size']==size and r['clock']==clock)),
            all_root_solved=sum(r['teacher']['all_root_actions_solved'] for r in rows if r['size']==size and r['clock']==clock),
            winning_action_only=sum(r['teacher']['basis']=='proven_winning_action' for r in rows if r['size']==size and r['clock']==clock)) for size in (4,5) for clock in (8,16)],
        newNNtraining=0,scope='same fixed boards/history; only clock changes; budget censoring disclosed; not full-game strength or transfer')
    write_record(out/'summary.json',summary);print(json.dumps(summary),flush=True)


if __name__=='__main__':
    import sys;run(sys.argv[1],sys.argv[2])
