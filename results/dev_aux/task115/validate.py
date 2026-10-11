"""Relevant finite orchestration and saved-record verification; never launches UCI."""
import ast,hashlib,importlib.util,json,sys,tempfile
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT));import pilot16
checks=[]
def check(name,truth):
    assert truth,name
    checks.append(name)
# Reuse only the already reviewed mock class declaration; do not run old audit.
source=ROOT/'results/dev_aux/task110/test_adapter.py';text=source.read_text(encoding='utf-8')
node=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='MockEngine')
namespace={'chess':chess,'Path':Path};exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
Mock=namespace['MockEngine']
with tempfile.TemporaryDirectory(dir=ROOT/'.local_agent') as tmp:
    base=Path(tmp);engines=[]
    def factory(deadline):
        engine=Mock();engines.append(engine);return engine
    r=pilot16.execute(factory,base/'ordinary',lambda:None,clock=lambda:0,scope='MOCK_ORCHESTRATION_ONLY')
    check('four mock games completed',r['status']=='FOUR_GAME_PILOT_COMPLETE' and r['accepted_games']==r['physical_completed_games']==4)
    check('no automatic training',r['mature_training_calls']==r['learned_updates']==0 and r['automatic_expansion'] is False)
    check('all owned mock engines closed',len(engines)==4 and all(e.closed for e in engines))
    rows=json.loads((base/'ordinary/pilot.json').read_bytes())['rows']
    for i,row in enumerate(rows):
        game=row['result'];check('16ply exact mock cap'+str(i),len(game['actions'])==16)
        check('8 mock searches'+str(i),len(game['search_records'])==8)
        check('mock backend explicit'+str(i),all(x['backend']=='MOCK_UCI_ORCHESTRATION_ONLY' for x in game['search_records']))
        check('profile leaf readback'+str(i),len(game['candidate_leaf_probes'])==5)
        check('profile config values'+str(i),engines[i].config_weights=={k:v for k,v in row['weights'].items() if k!='K'})
        board=chess.Board();index=0
        for m in game['opening']:board.push_uci(m)
        for ply,uci in enumerate(game['actions']):
            if board.turn==row['context']['agent_color']:
                check(f'complete history{i}/{ply}',game['search_records'][index]['full_history']==[m.uci() for m in board.move_stack]);index+=1
            check(f'legal mock replay{i}/{ply}',chess.Move.from_uci(uci) in board.legal_moves);board.push_uci(uci)
        check('mock final FEN'+str(i),board.fen()==game['final_fen'])
        check('16ply score metadata'+str(i),game['score']['cap']==16 and game['score']==pilot16.GAME.score(board,row['context']['agent_color'],16,16))
    check('identical paired trajectories distinguish no behavior signal',r['signal_classification']=='NO_OBSERVED_BEHAVIOR_SIGNAL' and not r['paired_behavior_signal'])
    check('paired color-only gate',len(r['pairs'])==2 and r['paired_reward_signal'] is False)
    try:pilot16.execute(factory,base/'ordinary',lambda:None,clock=lambda:0,scope='MOCK');raise AssertionError('output overwrite')
    except FileExistsError:checks.append('fresh output required')
    bad=[]
    def fail(deadline):engine=Mock('eof');bad.append(engine);return engine
    r=pilot16.execute(fail,base/'eof',lambda:None,clock=lambda:0,scope='MOCK')
    check('EOF preserves partial and no accepted game',r['status']=='INTERRUPTED' and r['accepted_games']==r['physical_completed_games']==0 and all(e.closed for e in bad))
    ticks=[0];late=[]
    def slowclose(deadline):
        engine=Mock();late.append(engine)
        def close():engine.closed=True;ticks[0]=121
        engine.close=close;return engine
    r=pilot16.execute(slowclose,base/'late',lambda:None,clock=lambda:ticks[0],scope='MOCK')
    check('late completed not accepted',r['status']=='INTERRUPTED' and r['physical_completed_games']==1 and r['accepted_games']==0)
    check('late physical game journal retained',any(json.loads(s)['kind']=='game_complete' for s in (base/'late/events.jsonl').read_text().splitlines()))
    entered=[]
    def stopped():raise pilot16.adapter.PersistentStop('mock stop')
    r=pilot16.execute(lambda d:entered.append(d),base/'stop',stopped,clock=lambda:0,scope='MOCK')
    check('stop before factory',r['status']=='INTERRUPTED' and not entered)
    # Verify production CLI failed qualification without touching any executable.
    old_argv=sys.argv;old_UCI=pilot16.adapter.UCI;old_validated=pilot16.adapter.validated_entry
    def forbidden(*a,**k):raise AssertionError('UCI must not be constructed')
    def rejected(*a,**k):raise RuntimeError('synthetic missing qualification')
    try:
        pilot16.adapter.UCI=forbidden;pilot16.adapter.validated_entry=rejected
        sys.argv=['pilot16','--binary','not-a-binary','--qualification','not-a-qualification','--output',str(ROOT/'results/dev_aux'/('temporary-'+base.name))]
        path=Path(sys.argv[-1]);check('qualification blocks transport',pilot16.main()==3)
        check('failure never learning failure',json.loads((path/'status.json').read_bytes())['learning_failure'] is False)
    finally:
        sys.argv=old_argv;pilot16.adapter.UCI=old_UCI;pilot16.adapter.validated_entry=old_validated
        if 'path' in locals() and path.exists():
            (path/'status.json').unlink();path.rmdir()
# Replay the saved cheap discriminator, independently of action-selection code.
data=json.loads((ROOT/'results/dev_aux/task114/result.json').read_bytes());roots={(r['seed'],r['opening_length']):r for r in data['roots']};replayed=0
for game in data['games']:
    board=chess.Board();root=roots[game['root_seed'],game['opening_length']]
    for uci in root['prefix']+game['actions']:
        m=chess.Move.from_uci(uci);assert m in board.legal_moves;board.push(m)
    assert board.fen()==game['end_fen']
    assert pilot16.GAME.score(board,game['agent_color'],len(game['actions']),16)==game['score']
    assert len(game['actions'])<=16
    replayed+=1
check('all96 saved trajectories and exact decomposed rewards',replayed==96)
result={'complete':True,'checks':checks,'check_count':len(checks),'saved_cheap_game_replays':replayed,'mock_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'pilot16_sha256':hashlib.sha256((OUT/'pilot16.py').read_bytes()).hexdigest(),'mature_games_executed':0,'scope':'Finite mock cap/history/config/interruption/qualification controls and96 saved non-mature replays; no real engine, training or human-ratio claim.'}
(OUT/'validation.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({k:result[k] for k in ['check_count','saved_cheap_game_replays','mature_games_executed','scope']}))