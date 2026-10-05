"""Changed explicit F24F adjudication scope; same frozen requests, no new transitions."""
import hashlib,json,re,shutil,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.conditional_dtm_bridge import dtm_horizon_interval,PREMISES
PRE=ROOT/'docs/research/data/chess_double_check_20261005.selections.json'
OUT=ROOT/'docs/research/data/chess_double_check_source_scope_20261005.json'
SOURCES=('scripts/audit_chess_double_check_source_scope.py','docs/research/CHESS_DOUBLE_CHECK_ADJUDICATION_SCOPE.md','docs/research/data/chess_double_check_source_20261005.json','docs/research/data/chess_double_check_20261005.selections.json',
 'docs/research/CHESS_DOUBLE_CHECK_SOURCE_PROTOCOL.md','scripts/conditional_dtm_bridge.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('source producer never rerun')
    started=monotonic();pre=json.loads(PRE.read_text());failed=json.loads((ROOT/'docs/research/data/chess_double_check_source_20261005.json').read_text());report=dict(complete=False,rows=[],outer_probe_calls=0,
      public_transitions=pre['public_transitions'],enumerated=pre['enumerated'],
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-started+pre['seconds']+failed['seconds']>=15:raise TimeoutError('15sec cumulative active computation cap')
    try:
        if failed['complete'] or failed['outer_probe_calls']!=0:raise ValueError('zero-probe preserved conversion failure required')
        if not pre['complete'] or pre['source_queries']!=0:raise ValueError('complete prelabel opportunity required')
        for p,h in pre['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h:raise ValueError('prelabel input drift')
        source=ROOT/'.local_agent/certificate_source';manifest=source/'manifest-source-correction.json'
        if hashlib.sha256(manifest.read_bytes()).hexdigest()!='1a2e45d5eb54ff451a0b7cfb8dad5e31f208d63c0654b6f8eac9581d39886a72':raise ValueError('source manifest drift')
        m=json.loads(manifest.read_text());report['installed_source_manifest']=m
        for group,folder in (('tables','tables'),('source_files','python-chess')):
            for item in m[group]:
                check();p=source/folder/item['name']
                if p.stat().st_size!=item['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('source bytes drift')
        work=source/'double-check-scope-working-tables'
        if work.exists():raise FileExistsError('new source working copy required; no rerun')
        work.mkdir()
        for item in m['tables']:shutil.copyfile(source/'tables'/item['name'],work/item['name'])
        sys.path.insert(0,str(source/'python-chess'));import chess;import chess.gaviota
        if chess.__version__!='1.11.2' or Path(chess.__file__).resolve()!=source/'python-chess/chess/__init__.py':raise ValueError('isolated pinned parser required')
        with chess.gaviota.PythonTablebase() as tb:
            tb.add_directory(str(work))
            for row in pre['rows']:
                r=dict(owner=row['owner'],weight=row['weight'],children={},canonical_margins={},tie_margins={});report['rows'].append(r)
                for key,child in row['children'].items():
                    check();q=child['request'];state=q['local_state'];external=chess.Board(q['fen'])
                    if not external.is_valid() or (external.is_checkmate() or external.is_stalemate()):raise ValueError('ongoing conversion premise fails')
                    local=set()
                    for action in child['all_actions']:
                        match=re.search(r':([a-h][1-8])-([a-h][1-8])$',action)
                        if not match:raise ValueError('unsupported projected action')
                        local.add(''.join(match.groups()))
                    if local!={move.uci() for move in external.legal_moves}:raise ValueError('complete child action mismatch')
                    if report['outer_probe_calls']+2>20:raise ValueError('20 outer probe cap')
                    report['outer_probe_calls']+=1;dtm=tb.probe_dtm(external);check()
                    report['outer_probe_calls']+=1;wdl=tb.probe_wdl(external);check()
                    bridge=dtm_horizon_interval(side=state['position']['side_to_move'],ply=q['absolute_ply'],max_ply=1000,
                      repetition_limit=100000,max_repetition_count=q['max_repetition_count'],signed_dtm=dtm,wdl_stm=wdl,
                      premises={p:True for p in PREMISES})
                    r['children'][key]=dict(request_sha256=q['state_sha256'],fen=q['fen'],signed_dtm=dtm,wdl_stm=wdl,
                      interval=bridge['interval'],bridge=bridge,projected_legal_count=len(local),source_verified=False,
                      external_insufficient_material=external.is_insufficient_material(),scope='conditional semantic/horizon bridge; no rule-independent external certificate')
                values={k:v['interval'][0] for k,v in r['children'].items()}
                if any(v['interval'][0]!=v['interval'][1] for v in r['children'].values()):raise ValueError('unknown conditional label')
                picks=row['selections_before_labels'];candidate=values[picks['contact_family']['selected']];sign=1 if row['owner']==0 else -1
                for name in ('unit','zero'):
                    r['canonical_margins'][name]=sign*(candidate-values[picks[name]['selected']])
                    margins=[sign*(candidate-values[k]) for k in picks[name]['tie_set']]
                    r['tie_margins'][name]=[min(margins),max(margins)]
        report['canonical_mean']={name:sum(r['canonical_margins'][name] for r in report['rows'])/2 for name in ('unit','zero')}
        report['tie_mean_interval']={name:[sum(r['tie_margins'][name][end] for r in report['rows'])/2 for end in (0,1)] for name in ('unit','zero')}
        report['complete']=len(report['rows'])==2
    except Exception as e:report['error']=f'{type(e).__name__}: {e}'
    report['seconds']=monotonic()-started;report['cumulative_seconds']=pre['seconds']+failed['seconds']+report['seconds']
    report['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in report['source_sha256'].items())
    OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','source_sha256','installed_source_manifest')}))
