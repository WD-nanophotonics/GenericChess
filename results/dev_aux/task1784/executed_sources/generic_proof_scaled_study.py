"""Mechanically sized KRN learning control; same proof/price/tail policy."""
import json,random
from pathlib import Path
from scripts.generic_proof_native_study import sha,run
from scripts.generic_proof_rnb_bridge import orbit
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_native_driver import SizedNativeDriver


def freeze(folder,*,width,seed,train_count=32,dev_count=32):
    out=Path(folder);out.mkdir(exist_ok=False);model=RoyalActor(width);rng=random.Random(seed);excluded=set();sources=[]
    for path in sorted(Path('results/dev_aux').glob('task*/plan.json')):
        if path.stat().st_size>5000000:continue
        p=json.loads(path.read_text(encoding='utf-8-sig'));families=p.get('families',[]) if isinstance(p,dict) else [];n=0
        if not isinstance(families,list):continue
        for family in families:
            if not isinstance(family,dict):continue
            for raw in family.get('roots',[]):
                if isinstance(raw,list) and len(raw)==width*width+1 and set(raw[:-1])<=set('.KRNBkrnb'):
                    excluded.update(orbit(tuple(raw)));n+=1
        if n:sources.append(dict(path=path.as_posix(),sha256=sha(path),roots=n))
    fs=[];attempts=0
    while len(fs)<train_count+dev_count and attempts<100000:
        attempts+=1;board=['.']*(width*width)
        for square,piece in zip(rng.sample(range(len(board)),6),'KkRNrn'):board[square]=piece
        s=tuple(board)+(0,)
        if not model.valid(s) or model.attacked(s,model.king(s,0),1) or orbit(s)&excluded:continue
        legal=model.moves(s)
        if len(legal)<4:continue
        targets=[s[ord(u[2])-97+width*(int(u[3])-1)] for u,_ in legal]
        if not any(t!='.' for t in targets) or not any(t=='.' for t in targets):continue
        if any(not model.moves(child) for _,child in legal):continue
        flipped=tuple(p.swapcase() for p in s[:-1])+(1,)
        fs.append(dict(family=len(fs),phase='TRAIN' if len(fs)<train_count else 'DEV',roots=[s,flipped]));excluded.update(orbit(s))
    assert len(fs)==train_count+dev_count
    prices=[[r,720,720,720] for r in (360,720,1440)];names={str(tuple(p)):'aux55_'+str(width)+'_'+'_'.join(map(str,p)) for p in prices}
    ini=f'[aux55base:chess]\nmaxFile = {width}\nmaxRank = {width}\ncastling = false\ndoubleStep = false\npromotionRank = {width}\npromotionPieceTypes = rnb\nnMoveRule = 0\nnFoldRule = 0\nstartFen = '+f'k{width-1}/'+'/'.join([str(width)]*(width-2))+f'/{width-1}K w - - 0 1\n'
    for p in prices:
        ini+='\n['+names[str(tuple(p))]+':aux55base]\n'+''.join(f'pieceValue{x} = p:{p[3]} n:{p[1]} b:{p[2]} r:{p[0]} q:1664\n' for x in ('Mg','Eg'))
    (out/'variant.ini').write_text(ini,encoding='utf-8')
    wrapper=f'from scripts.generic_royal_actor import RoyalActor\nactor=RoyalActor({width})\nW=H={width}\nvalid=actor.valid\nmoves=actor.moves\nfen=actor.fen\nattacked=actor.attacked\nking=actor.king\n'
    (out/'rules.py').write_text(wrapper,encoding='utf-8')
    plan=dict(status='FROZEN_NEW_SIZED_RULE_CONTROL_BEFORE_GAMES',width=width,seed=seed,attempts=attempts,families=fs,exclusion_sources=sources,study_kind='LEARN',baseline_index=1,prices=prices,variant_names=names,model=(out/'rules.py').as_posix(),model_sha256=sha(out/'rules.py'),actor_source='scripts/generic_royal_actor.py',actor_sha256=sha('scripts/generic_royal_actor.py'),driver_sha256=sha('scripts/generic_proof_native_driver.py'),scaled_study_sha256=sha(__file__),
              binary='.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',binary_sha256=sha('.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe'),variant_ini=(out/'variant.ini').as_posix(),variant_sha256=sha(out/'variant.ini'),
              candidate_nodes=4096,opponents=[dict(id='UNIT64',nodes=64),dict(id='UNIT4096',nodes=4096)],H=16,certified_tail=True,tail_max_rank=64,seconds_cap=1200,max_go=75000,step_seconds=.25,
              solver_sha256=sha('scripts/generic_win_proof.py'),pn_sha256=sha('scripts/generic_win_proof_pn.py'),player_sha256=sha('scripts/generic_proof_player.py'),study_sha256=sha('scripts/generic_proof_native_study.py'),tail_sha256=sha('scripts/generic_proof_tail.py'),proof_algorithm='PN',active_coordinates=[0],initial_prices=prices,
              primary_selector='All3price TRAIN actual W-L, lex tie; strict adjacent paths share same real grid. No DEV or human price fitting.',
              outcome='Actual Core terminal only, UNKNOWN explicit. H16 plus only ALREADY verified rank<=64 physical strategy tail; no new proof after H16. Same policy both colors/prices.',
              rootlaw='Mechanically sized closed KkRNrn; uncheck,>=4choices,capture+quiet,no immediately terminal successor; no price/WDL selection. FullD4+color exclusion.',
              incremental_cost_decision='Board4x4 may limit a relative R/N inference; change ONLY declared board/root domain with same player budgets and real terminal objective. Two independent cohorts test selection stability; no claim the domain should match human8x8 values.',
              expected_max_games=12*train_count+16*dev_count,expected_max_moves=80*(12*train_count+16*dev_count),advance_rule='Keep all caps and failures, no continuation or sample enlargement on exposed outcomes. Cost and scope reported separately from WDL; no automatic main/default change.')
    (out/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print('SIZED_FROZEN',width,seed,len(fs))


def execute(folder):
    p=json.loads((Path(folder)/'plan.json').read_text())
    assert p['scaled_study_sha256']==sha(__file__) and p['driver_sha256']==sha('scripts/generic_proof_native_driver.py')
    run(folder,driver_class=SizedNativeDriver)


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['freeze','run']);ap.add_argument('folder');ap.add_argument('--width',type=int,default=5);ap.add_argument('--seed',type=int,default=20261015555);a=ap.parse_args()
    freeze(a.folder,width=a.width,seed=a.seed) if a.mode=='freeze' else execute(a.folder)
