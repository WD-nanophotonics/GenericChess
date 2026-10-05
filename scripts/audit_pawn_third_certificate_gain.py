"""Pure signed-feature diagnostic and exposed-state reconciliation; no events."""
from itertools import combinations,product
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.native_chess_contact_intervals import native_contact_intervals
from scripts.third_native_contact_intervals import third_native_contact_intervals,third_contact_choice
from scripts.material_interval_choice import certified_ongoing_material_choice
from scripts.research_record import write_record
from scripts.research_state_replay import read_game_state
from scripts.public_goal_intervals import PublicGame
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
OUT=ROOT/'docs/research/data/pawn_third_certificate_gain_20261005.json'
SOURCES=('scripts/audit_pawn_third_certificate_gain.py','scripts/third_native_contact_intervals.py',
 'docs/research/PAWN_THIRD_CERTIFICATE_GAIN_PROTOCOL.md','docs/research/data/chess_pawn_third_prefix_20261005.json',
 'docs/research/data/chess_knight_interposition_20261005.selections.json','scripts/native_chess_contact_intervals.py',
 'scripts/material_interval_choice.py','scripts/research_state_replay.py','scripts/research_record.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen pure diagnostic never rerun')
    start=monotonic();r=dict(complete=False,rows=[],table_evaluations=0,physical_events=0,goal_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec pure diagnostic cap')
    try:
        laws=('geometric_half','linear_mixture');bounds={law:{'old':native_contact_intervals(law),'new':third_native_contact_intervals(law)} for law in laws}
        for pc in (-2,-1,1,2):
            for size in range(3):
                for others in combinations('NBRQ',size):
                    for values in product((-2,-1,1,2),repeat=size):
                        check();vector=dict(zip(('P',)+others,(pc,)+values))
                        table={'a':{('board',t):v for t,v in vector.items() if v>0},'b':{('board',t):-v for t,v in vector.items() if v<0}}
                        row=dict(vector=vector,by_law={});r['rows'].append(row)
                        for law in laws:
                            choices={}
                            for name,boxes in bounds[law].items():
                                r['table_evaluations']+=1
                                if r['table_evaluations']>5000:raise ValueError('5000 table cap')
                                choices[name]=certified_ongoing_material_choice(table,boxes,owner=0,complete=True)['selected']
                            if choices['old'] is not None and choices['old']!=choices['new']:raise ValueError('nested refinement lost old choice')
                            row['by_law'][law]=choices
                        for name in ('old','new'):
                            picks={row['by_law'][law][name] for law in laws}
                            row[name+'_union']=next(iter(picks)) if len(picks)==1 and None not in picks else None
        r['by_law_gain']={law:sum(row['by_law'][law]['old'] is None and row['by_law'][law]['new'] is not None for row in r['rows']) for law in laws}
        r['union_gain']=sum(row['old_union'] is None and row['new_union'] is not None for row in r['rows'])
        r['old_union_certified']=sum(row['old_union'] is not None for row in r['rows']);r['new_union_certified']=sum(row['new_union'] is not None for row in r['rows'])
        pre=json.loads((ROOT/SOURCES[4]).read_text());children={k:read_game_state(v) for k,v in pre['children'].items()}
        game=PublicGame(compile_ruleset_for_execution(build_western_chess_ruleset()))
        r['exposed_falsifier_reconciliation']=third_contact_choice(children,game,owner=0,duration='both',complete=True)
        r['exposed_old_contact']=pre['selections_before_labels']['contact']['selected']
        r['unchanged_exposed_mate_risk']=r['exposed_falsifier_reconciliation']['selected']==r['exposed_old_contact']
        r['complete']=len(r['rows'])==452
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());write_record(OUT,r)
    print(json.dumps({k:v for k,v in r.items() if k not in ('rows','exposed_falsifier_reconciliation','source_sha256')}))
