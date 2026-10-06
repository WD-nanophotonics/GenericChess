"""Saved complete Chess responses, common-coefficient static minimax only."""
from fractions import Fraction as F
from pathlib import Path
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.material_leaf_choice import inventory_features
from scripts.research_state_replay import read_game_state
from scripts.shared_parameter_order import certify_order
from scripts.multiaffine_envelope_certificate import cube_min
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/chess_multimode_static2_20261006.json'
SOURCES=('scripts/audit_chess_multimode_static2.py','docs/research/CHESS_MULTIMODE_STATIC2_PROTOCOL.md',
 'scripts/chess_exact_contact_family.py','scripts/material_leaf_choice.py','scripts/research_state_replay.py',
 'scripts/shared_parameter_order.py','scripts/multiaffine_envelope_certificate.py','scripts/research_record.py',
 'docs/research/data/chess_multimode_response_20261006.json',
 'docs/research/data/chess_multimode_source_replay_20261006.json',
 'docs/research/data/chess_zero_target_correction_20261005.json')

def main():
    if OUT.exists():raise FileExistsError('closed saved-tree algebra never rerun')
    start=monotonic();r=dict(complete=False,leaf_rows=0,vertices=0,branches={},endpoints={},proofs=[],
      public_transitions=0,runtime_pushes=0,source_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        r['vertices']+=1
        if r['vertices']>4096 or monotonic()-start>=15:raise ValueError('4096 vertices/15sec saved-tree algebra cap')
    try:
        raw=json.loads((ROOT/SOURCES[-3]).read_text());independent=json.loads((ROOT/SOURCES[-2]).read_text())
        for old in (raw,independent):
            if not old['complete'] or not old['source_hashes_unchanged']:raise ValueError('complete original/source tables required')
            for p,pin in old['source_sha256'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('original input drift')
        saved=json.loads((ROOT/SOURCES[-1]).read_text())
        means={}
        for law in ('geometric_half','linear_mixture'):
            m=(lambda t:F(1,2**t)) if law=='geometric_half' else (lambda t:F(2,(t+1)*(t+2)))
            means[law]={mode:sum((int(n)*m(int(t)) for t,n in row['histogram'].items()),F(0))/249984 for mode,row in saved['rows'].items()}
            normalized=exact_chess_contact_intervals(law)
            if any(normalized['board',mode]!=(value/means[law]['Q'],)*2 for mode,value in means[law].items()):
                raise ValueError('raw means not exact frozen normalized constructor')
        d0=31*means['linear_mixture']['Q'];d1=31*(means['geometric_half']['Q']-means['linear_mixture']['Q'])
        denominator=(d0,d1)+(F(0),)*6;endpoint_scores={name:{} for name in (*means,'unit','zero')}
        for key,branch in raw['replies'].items():
            unique=[];incidence={};scores={name:{} for name in endpoint_scores}
            if sorted(branch['all_actions'])!=sorted(row['action'] for row in branch['rows']):raise ValueError('missing actual reply')
            for leaf in branch['rows']:
                state=read_game_state(leaf['state'])
                if state.terminal_status.is_terminal or state.position.side_to_move!=0:raise ValueError('ongoing full two-ply target changed')
                features=inventory_features(state.position,{'K'})
                if any(location!='board' or mode not in means['linear_mixture'] for location,mode in features):raise ValueError('unqualified material leaf domain')
                n0=sum((n*means['linear_mixture'][mode] for (_,mode),n in features.items()),F(0))
                n1=sum((n*(means['geometric_half'][mode]-means['linear_mixture'][mode]) for (_,mode),n in features.items()),F(0))
                row=(n0,n1)+(F(0),)*6
                if row not in unique:unique.append(row)
                incidence[leaf['action']]=unique.index(row);r['leaf_rows']+=1
                if r['leaf_rows']>128:raise ValueError('128 stored leaves cap')
                for law in means:
                    scores[law][leaf['action']]=sum((n*means[law][mode]/means[law]['Q'] for (_,mode),n in features.items()),F(0))/31
                scores['unit'][leaf['action']]=F(sum(features.values()),31);scores['zero'][leaf['action']]=F(0)
            r['branches'][key]=dict(unique_rows=unique,action_to_row=incidence)
            for name,values in scores.items():
                endpoint_scores[name][key]=dict(score=min(values.values()),worst_replies=sorted(k for k,v in values.items() if v==min(values.values())))
        for name,values in endpoint_scores.items():
            best=max(v['score'] for v in values.values());ties=sorted(k for k,v in values.items() if v['score']==best)
            r['endpoints'][name]=dict(selected=ties[0],tie_set=ties,score=best,branches=values)
        candidate=raw['selections_before_labels']['geometric_half']['selected']
        r['candidate']=candidate;r['denominator']=denominator
        first=r['branches'][candidate]['unique_rows']
        for key,branch in r['branches'].items():
            if key==candidate:continue
            second=branch['unique_rows'];proofs=[]
            for row_a in first:
                margins=[cube_min(tuple(a-b for a,b in zip(row_a,row_b)),check) for row_b in second]
                witness=max(range(len(second)),key=lambda i:margins[i])
                proofs.append(tuple(F(int(j==witness)) for j in range(len(second))))
            result=certify_order(first,second,first_kind='min',second_kind='min',denominator=denominator,
                retained_id=candidate,discarded_id=key,proofs=proofs,checkpoint=check)
            if not result['canonical_action_prune_proved']:raise ValueError('common-law fixed candidate order unproved')
            r['proofs'].append(dict(baseline=key,supplied_proofs=proofs,**result))
        r['window_gain_unchanged']=all(v['window']==[0,0] for v in raw['goal_intervals'].values())
        r['complete']=len(r['proofs'])==2 and r['leaf_rows']==87
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r)
    print(json.dumps(record_value({k:v for k,v in r.items() if k not in ('source_sha256','branches','endpoints')})))
    print(json.dumps(record_value({k:{kk:vv for kk,vv in v.items() if kk!='branches'} for k,v in r['endpoints'].items()})))

if __name__=='__main__':main()
