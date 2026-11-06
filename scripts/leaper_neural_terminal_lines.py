"""Replay two certified teacher-value lines through public Core sessions.

An individual terminal line is not the all-replies proof; existing threshold
certificates establish WDL. This check verifies side/label/terminal binding.
"""
import argparse
import gzip,json
from pathlib import Path
from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_neural_teacher import solve_session
from scripts.research_record import record_value,write_record


def run(source):
    source=Path(source)
    records=[json.loads(x) for x in gzip.decompress((source/'results.jsonl.gz').read_bytes()).decode().splitlines()]
    selected=[]
    for wanted in ('WIN','LOSS'):
        selected.append(next((row,c) for row in records if row['size']==5 for c in row.get('conditions',[]) if c['mask']==23 and c['teacher']['label']==wanted))
    results=[]
    for row,condition in selected:
        rules=ruleset_from_dict(condition['rules']);s=GameSession.replay(compile_ruleset(rules),deserialize_game_record(json.dumps(condition['record'])))
        root_actor=s.state.position.side_to_move;root_label=condition['teacher']['label'];steps=[]
        for _ in range(rules.max_ply):
            if s.result.status.value!='ongoing':break
            result=solve_session(rules,s,1500)
            if result['label'] is None:
                steps.append(dict(status='UNKNOWN',ply=s.state.ply_count));break
            choices=[x for x in result['action_values'] if x['value']==result['label']]
            if not choices:raise ValueError('exactroot has no certified realizing action')
            raw=choices[0]['action'];a=next(a for a in s.legal_actions() if action_to_dict(a)==raw)
            actor=s.state.position.side_to_move;s.submit(a)
            steps.append(dict(actor=actor,teacher_label=result['label'],basis=result['basis'],action=raw,status_after=s.result.status.value))
        terminal=s.result.status.value!='ongoing'
        realized='DRAW' if s.result.winner is None else 'WIN' if s.result.winner==root_actor else 'LOSS'
        if terminal and realized!=root_label:raise ValueError('literalterminal disagrees with rootlabel')
        results.append(dict(source_slot=row['slot'],root_label=root_label,root_actor=root_actor,terminal=terminal,realized=realized if terminal else None,
                            final_status=s.result.status.value,steps=steps,rules=condition['rules'],final_record=record_value(s.to_record())))
    report=dict(lines=results,scope='Two labelled5x5rich-leap examples, at most8plies each, same1500node teacher per step. A line checks literal Core outcome, not independent proof against every reply or playing strength.')
    write_record(source/'terminal-lines.json',report)
    print(json.dumps([dict(slot=r['source_slot'],label=r['root_label'],terminal=r['terminal'],realized=r['realized'],plies=len(r['steps']),status=r['final_status']) for r in results]))

if __name__=='__main__':
    import sys;run(sys.argv[1])
