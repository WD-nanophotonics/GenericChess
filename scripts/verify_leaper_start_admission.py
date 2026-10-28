"""Independent Core replay of the complete pool, including compiler rejects."""
import argparse,hashlib,json,time
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.validation import RuleValidationError
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
from scripts.research_record import write_record,record_value
from tools.local_agent import session

def rejection_codes(error):
    assert isinstance(error,RuleValidationError)
    codes={issue.code for issue in error.issues}
    # Compiler collects both check and no-legal errors, independently. Both
    # are covered by the prospectively excluded checked/non-ongoing setup.
    assert 'INITIAL_ANCHOR_ATTACKED' in codes
    assert codes <= {'INITIAL_ANCHOR_ATTACKED','INITIAL_NO_LEGAL_MOVE'}
    return [issue.code for issue in error.issues]

def verify(prepared,audit,output):
    begin=datetime.now(timezone.utc).isoformat();tick=time.perf_counter()
    raw=(prepared/'inputs.json').read_bytes();roots=json.loads(raw)['rows'];spec=json.loads((prepared/'specification.json').read_bytes());lock=json.loads((prepared/'input-lock.json').read_bytes());observed=json.loads((audit/'rows.json').read_bytes());summary=json.loads((audit/'summary.json').read_bytes())
    assert len(roots)==len(observed)==64 and hashlib.sha256(raw).hexdigest()==lock['input_sha256']==summary['input_sha256']
    assert len({r['fingerprint'] for r in roots})==64
    rejected=transitions=anchors=eligible=0;selected=[];issues=Counter()
    for root,row in zip(roots,observed):
        assert root['id']==row['case_id'] and root['record']['actions']==[] and root['prefix_length']==0
        board=root['RuleSet']['initial_position'];assert len(board)==7 and all(len(rank)==7 for rank in board)
        pieces=[p for rank in board for p in rank if p is not None]
        assert Counter(p['owner'] for p in pieces)=={0:root['density'],1:root['density']}
        assert Counter(p['owner'] for p in pieces if p['current_type_id']=='K')=={0:1,1:1}
        for y,rank in enumerate(board):
            for x,piece in enumerate(rank):
                other=board[6-y][6-x]
                if piece is None:assert other is None
                else:assert other==dict(piece,owner=1-piece['owner'])
        rules=ruleset_from_dict(root['RuleSet']);assert compute_fingerprint(rules)==root['fingerprint']
        assert root['RuleSet']['max_ply']==96 and root['RuleSet']['repetition_limit']==4
        try:c=compile_legacy_ruleset_for_semantic_execution(rules)
        except Exception as e:
            assert row['status']=='REJECTED_COMPILER'
            issues.update(rejection_codes(e))
            assert str(e)==row['error'] and not row['eligible'];rejected+=1;continue
        assert row['status']=='AUDITED'
        assert _plain_leaper_hash_patterns(c) is not None
        s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])));before=s.to_record();engine=semantic_engine_for(c)
        legal=tuple(s.legal_actions());aa=[];wins=[];terms=[]
        for a in legal:
            if getattr(a,'actor_type_id',None)=='K':aa.append(record_value(a))
            child=GameSession.replay(c,before);child.submit(a);transitions+=1
            t=child.state.terminal_status
            if t.is_terminal:terms.append(dict(action=record_value(a),terminal=record_value(t)))
            if t.is_terminal and t.winner==s.state.position.side_to_move:wins.append(record_value(a))
        checks=[engine.in_check(s.state.position,p) for p in (0,1)]
        ok=not s.state.terminal_status.is_terminal and not any(checks) and len(aa)>=2 and not wins
        assert row['eligible']==ok and row['checks']==checks and row['anchor_actions']==aa and row['one_ply_wins']==wins and row['one_ply_terminals']==terms and row['legal_count']==len(legal) and row['anchor_freedom']==len(aa)
        assert s.to_record()==before;anchors+=len(aa);eligible+=ok
    for f in range(8):selected.extend([r['case_id'] for r in observed if r['family']==f and r['eligible']][:2])
    assert selected==summary['selected'] and rejected==summary['statuses']['REJECTED_COMPILER'] and eligible==summary['eligible']
    result=dict(status='PASS',roots=64,rejected=rejected,rejection_issue_counts=dict(issues),valid=64-rejected,eligible=eligible,selected=selected,Core_transitions=transitions,anchor_actions=anchors,whole_pool_preserved=True,Player_calls=0,solver_calls=0,games=0,input_sha256=lock['input_sha256'],started_at=begin,ended_at=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-tick)
    write_record(output,result);session.record_work(begin,result['ended_at'],'validation',str(output));print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.prepared,a.audit,a.output)
