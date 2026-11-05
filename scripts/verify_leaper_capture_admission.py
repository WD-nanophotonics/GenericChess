"""Independent saved-data inputgate reader; no Core/Player or source execution."""
from pathlib import Path
from collections import Counter
import hashlib,json
from scripts.research_record import write_record


def verify(base,output):
    b=Path(base);f=json.loads((b/'frozen.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((b/'inputs.json').read_bytes()).hexdigest()==f['inputs_sha256']
    for name,sha in f['sources'].items():
        assert hashlib.sha256((b/'tested-source'/name).read_bytes()).hexdigest()==sha
    rows=json.loads((b/'inputs.json').read_text(encoding='utf-8'))['rows']
    admission=json.loads((b/'Core-admission.json').read_text(encoding='utf-8'))
    stop=json.loads((b/'admission-stop.json').read_text(encoding='utf-8'))
    assert len(rows)==len(admission)==16 and not list(b.glob('return-*.json'))
    assert stop['player_calls']==0 and stop['NOT_RUN']==list(range(32))
    witnesses=[];rejected=[]
    for i,(row,status) in enumerate(zip(rows,admission)):
        assert row['id']==status['id'] and row['record']['actions']==[]
        rule=row['RuleSet'];board=rule['initial_position'];types={t['type_id']:t for t in rule['piece_types']};n=rule['board_size']
        assert n==6 and len(board)==n and all(len(line)==n for line in board)
        kings=[(x,y,p) for y,line in enumerate(board) for x,p in enumerate(line) if p is not None and types[p['current_type_id']]['is_anchor']]
        assert Counter(p['owner'] for x,y,p in kings)=={0:1,1:1}
        actual=[]
        for kx,ky,king in kings:
            for y,line in enumerate(board):
                for x,p in enumerate(line):
                    if p is None or p['owner']==king['owner']:continue
                    sign=1 if p['owner']==0 else -1
                    for atom in types[p['current_type_id']]['movement_atoms']:
                        assert atom['kind']=='leap'
                        dx,dy=atom['offset']
                        if (x+sign*dx,y+sign*dy)==(kx,ky):
                            actual.append(dict(royal_owner=king['owner'],royal=[kx,ky],attacker=[x,y],owner=p['owner'],type=p['current_type_id'],offset=[dx,dy]))
        if actual:
            assert status['status']=='REJECTED' and 'INITIAL_ANCHOR_ATTACKED' in status['error']
            rejected.append(i);witnesses.append(dict(root=i,witnesses=actual))
        else:assert status['status']=='ADMITTED'
    assert rejected==stop['rejected_roots']==[9,12,15]
    result=dict(status='PASS_SAVED_ADMISSION_STOP',inputs=16,admitted=13,rejected=rejected,attack_witnesses=witnesses,fitnessPlayerCalls=0,NOT_RUN=32,source_fitness_executed=False,newCore=0,newPlayer=0,limits='direct literal leap arithmetic confirms rejected initialanchors only;acceptedrows are producerCoreattribution;no cost/quality result or replacement authority')
    write_record(output,result);return result

if __name__=='__main__':
    import sys
    print(json.dumps(verify(sys.argv[1],sys.argv[2])))
