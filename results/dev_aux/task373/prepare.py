import sys,json,random,hashlib
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G
O=R/'results/dev_aux/task373';O.mkdir(exist_ok=True);initial='ln1ks1rnl/1+B1sg4/3p2p1b/p1p2p1pp/1P1P5/PpR1p1PPP/2N1PP1S1/4G3L/L1SKG2N1 b GP 65';mate='G*7b';b=A.shogi.Board(initial);assert A.shogi.Move.from_usi(mate) in b.legal_moves;b.push_usi(mate);assert b.is_check() and not list(b.legal_moves);proof={'initial_sfen':initial,'history':[mate],'terminal_sfen':b.sfen(),'source':'ownfixedinheritedgeneric_chess/learning/shogi_certification.py curatedcheckmate; entirepre-SFENhistory unavailable'};roots=[];paths=[]
for idx,seed in enumerate(range(2026102572,2026102580)):
 rng=random.Random(seed);b=A.shogi.Board(initial);keys=[G.key(b)];checks=[b.is_check()];movers=[];h=[];term=None
 for ply in range(6):
  term=G.terminal(b,keys,checks,movers)
  if term:break
  moves=sorted(m.usi() for m in b.legal_moves);u=rng.choice(moves);movers.append(b.turn);b.push_usi(u);h.append(u);keys.append(G.key(b));checks.append(b.is_check())
 term=G.terminal(b,keys,checks,movers);useh=list(h);status='sixlegalstepsfromknownmatepredecessor'
 if term:
  distance=rng.choice([1,2,4]);useh=h[:max(0,len(h)-distance)];status='legalhistoryrollbackfromactualrandomterminal'
 q=A.replay(initial,useh);f={'phase':'near_seed_diagnostic','family':'curated_seed_family0','index':idx,'seed':seed,'initial_sfen':initial,'history':useh,'expected_sfen':q.sfen(),'generation':status};bb,k,c,m=G.full_root(f);assert G.terminal(bb,k,c,m) is None;G.quantity(bb,0);roots.append(f);paths.append({'seed':seed,'all_random_history':h,'random_terminal':term,'selected_prefix_length':len(useh)})
d={'known_true_mate_seed':proof,'roots':roots,'generation_paths':paths,'selection':'fixed8seeds/alllegaluniform6steps, no price/human/tactical screening; ifterminal rollbackpredeterminedrandom1/2/4 preservingactuallegalhistory, no replacement','scope':'single seed familyallkeptdiagnostic; no siblingtrain/validation split, no independentholdout/standard-startreachabilityclaim; unknownpre-SFENrepetitionexcluded','execution':'all original2profiles+allfrozen370endpoints unique prices, bothcolors, fixedunit cold1024 cap24/goal364; runonlyafter370ends toavoidextra searchworkers; no training/reselectonthis panel','hypothesis':'highertrue-terminalrate atlowerper-outcome cost may still havezero price discrimination ifall prices solve same easy seeds'};(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print('PREPARED',len(roots),[p['random_terminal'] for p in paths])