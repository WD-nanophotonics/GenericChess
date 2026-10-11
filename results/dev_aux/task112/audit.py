"""Pinned YaneuraOu source and finite material bookkeeping audit, no engine runs."""
import ast, hashlib, json, re
from pathlib import Path
ROOT=Path.cwd(); OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'.local_agent/yane-material-review'
PIN='c1b80eaa09fe13d5f12b1599d1ae4d53c224de30'
PATHS={
'evaluate.h':'source/evaluate.h',
'eval_evaluate.cpp':'source/eval/evaluate.cpp',
'eval_evaluate_bona_piece.cpp':'source/eval/evaluate_bona_piece.cpp',
'eval_material_evaluate_material.cpp':'source/eval/material/evaluate_material.cpp',
'position.cpp':'source/position.cpp', 'position.h':'source/position.h',
'engine.cpp':'source/engine.cpp', 'engine_yaneuraou-engine_yaneuraou-search.cpp':'source/engine/yaneuraou-engine/yaneuraou-search.cpp',
'usi.cpp':'source/usi.cpp','tt.cpp':'source/tt.cpp','config.h':'source/config.h','movepick.cpp':'source/movepick.cpp'}
WITNESSES={
'evaluate.h':['extern int PieceValue[PIECE_NB]','extern int PieceValueM[PIECE_NB]','extern int CapturePieceValue[PIECE_NB]','extern int ProDiffPieceValue[PIECE_NB]'],
'eval_evaluate.cpp':['v += PieceValueM[pos.piece_on(i)]','hand_count(pos.hand_of(c), pt) * PieceValue[pt]'],
'eval_material_evaluate_material.cpp':['void load_eval() {}','MATERIAL_LEVEL == 1','void add_options(OptionsMap&, ThreadPool&) {}','auto score = pos.state()->materialValue','pos.side_to_move() == BLACK ? score : -score'],
'eval_evaluate_bona_piece.cpp':['int PieceValue[PIECE_NB]','int PieceValueM[PIECE_NB]','int CapturePieceValue[PIECE_NB]','int ProDiffPieceValue[PIECE_NB]'],
'position.cpp':['st->materialValue = Eval::material(*this)','materialDiff = 0','Eval::ProDiffPieceValue[moved_pc]','PieceType pr = raw_type_of(captured)','put_hand_piece(Us, pr)','materialDiff += Eval::CapturePieceValue[captured]','st->previous->materialValue + (Us == BLACK ? materialDiff : -materialDiff)','int swap = PieceValue[piece_on(to)] - threshold'],
'engine.cpp':['states = StateListPtr(new std::deque<StateInfo>(1))','auto err = pos.set(sfen','pos.do_move(m, states->back())'],
'engine_yaneuraou-engine_yaneuraou-search.cpp':['Eval::load_eval()','pos.set(StartSFEN, &states->back())','tt.clear(threads)','return Eval::evaluate(pos)','PieceValue[pos.piece_on(move.to_sq())]'],
'usi.cpp':['options.read_engine_options("engine_options.txt")','options.read_engine_options(eval_options_path)','engine.isready()','else if (token == "e")','"eval = " << engine.evaluate()'],
'config.h':['#define USE_CLASSIC_EVAL','#define USE_PIECE_VALUE','#define EVAL_MATERIAL','#define MATERIAL_LEVEL 001'],
'movepick.cpp':['7 * int(Eval::PieceValue[capturedPiece])','m.value += PieceValue[pt] * v'],
'position.h':['Value materialValue'],
' tt.cpp'.strip():['void TranspositionTable::new_search()','++generation8','std::tuple<bool, TTData, TTWriter> TranspositionTable::probe(const Key key','tte[i].key == key_for_ttentry']}
def clean(s): return re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S)
files={}; source_checks=[]
for name,path in PATHS.items():
    b=(SOURCE/name).read_bytes(); rows=b.decode('utf-8-sig').splitlines()
    locations={}
    for fragment in WITNESSES[name]:
        found=[i+1 for i,s in enumerate(rows) if fragment in s]
        assert found,(name,fragment)
        locations[fragment]=found; source_checks.append(name+': '+fragment)
    files[name]={'sha256':hashlib.sha256(b).hexdigest(),'url':f'https://raw.githubusercontent.com/yaneurao/YaneuraOu/{PIN}/{path}','locations':locations}
constants={'VALUE_ZERO':0}
header=clean((SOURCE/'evaluate.h').read_text(encoding='utf-8-sig'))
for k,v in re.findall(r'(\w+Value)\s*=\s*(\d+)',header): constants[k]=int(v)
def expr(text):
    node=ast.parse(text.strip(),mode='eval').body
    def ev(n):
        if isinstance(n,ast.Constant) and isinstance(n.value,int): return n.value
        if isinstance(n,ast.Name): return constants[n.id]
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub): return -ev(n.operand)
        if isinstance(n,ast.BinOp):
            a,b=ev(n.left),ev(n.right)
            if isinstance(n.op,ast.Add): return a+b
            if isinstance(n.op,ast.Sub): return a-b
            if isinstance(n.op,ast.Mult): return a*b
        raise ValueError(ast.dump(n))
    return ev(node)
tabletext=clean((SOURCE/'eval_evaluate_bona_piece.cpp').read_text(encoding='utf-8-sig'))
tables={}
for name in ['PieceValue','PieceValueM','CapturePieceValue','ProDiffPieceValue']:
    body=re.search(r'int\s+'+name+r'\[PIECE_NB\]\s*=\s*\{(.*?)\}',tabletext,re.S).group(1)
    tables[name]=[expr(x) for x in body.split(',') if x.strip()]
    assert len(tables[name])==32
RAW={i:i for i in range(1,8)}|{i:i-8 for i in range(9,15)}
PROMOTE={i:i+8 for i in [1,2,3,4,5,6]}
checks=[]
for i in range(32):
    t=i%16; sign=1 if i<16 else -1; p=tables['PieceValue'][i]
    assert p==tables['PieceValue'][t]
    assert tables['PieceValueM'][i]==sign*p
    if t in RAW:
        assert tables['CapturePieceValue'][i]==p+tables['PieceValue'][RAW[t]]
    else: assert tables['CapturePieceValue'][i]==0
    base=t if t in PROMOTE else t-8 if t-8 in PROMOTE else None
    expected=tables['PieceValue'][PROMOTE[base]]-tables['PieceValue'][base] if base else 0
    assert tables['ProDiffPieceValue'][i]==expected
    checks.append({'piece_id':i,'signed':sign*p,'capture':tables['CapturePieceValue'][i],'promote':expected})
# Synthetic prices intentionally do not use human reference ratios.
old={t:100 for t in RAW}; new={t:31+17*t for t in RAW}; old[8]=new[8]=0
# Independent count representation: (owner sign, type) -> actor count.
def full(counts, prices): return sum(sign*prices[t]*n for (sign,t),n in counts.items())
def step(counts, sign, mover, target=None, promote=False):
    c=counts.copy()
    if promote:
        c[sign,mover]=c.get((sign,mover),0)-1
        c[sign,PROMOTE[mover]]=c.get((sign,PROMOTE[mover]),0)+1
    if target is not None:
        c[-sign,target]=c.get((-sign,target),0)-1
        # Captured actor changes owner and returns to unpromoted hand type.
        c[sign,RAW[target]]=c.get((sign,RAW[target]),0)+1
    return c
transitions=[]
for sign in [-1,1]:
    for mover in RAW:
        for target in [None,*RAW]:
            for promote in [False,True] if mover in PROMOTE else [False]:
                counts={(sign,mover):1}
                if target is not None: counts[-sign,target]=1
                nxt=step(counts,sign,mover,target,promote)
                delta=sign*((new[PROMOTE[mover]]-new[mover] if promote else 0)+(new[target]+new[RAW[target]] if target is not None else 0))
                assert full(nxt,new)-full(counts,new)==delta
                transitions.append({'side':sign,'mover':mover,'captured':target,'promotion':promote,'delta':delta})
# Failure witnesses are arithmetic only, no coordinates or legality claims.
counts={(1,6):1,(-1,1):1}
root_old=full(counts,old); root_new=full(counts,new)
promoted=step(counts,1,6,promote=True)
new_delta=new[14]-new[6]
warm_next=root_old+new_delta
fresh_next=full(promoted,new)
assert warm_next!=fresh_next and warm_next-fresh_next==root_old-root_new
capturecounts={(1,7):1,(-1,9):1}
captured=step(capturecounts,1,7,9)
stale_capture_delta=old[9]+old[1]
actual_capture_delta=full(captured,new)-full(capturecounts,new)
assert stale_capture_delta!=actual_capture_delta
# Updating signed board values without the base hand table corrupts a drop.
board_value=new[6]; hand_value=old[6]
assert board_value-hand_value!=0
failures=[
 {'case':'old root cache with fully refreshed tables','old_root':root_old,'new_root':root_new,'warm_child':warm_next,'fresh_child':fresh_next,'constant_cache_error':warm_next-fresh_next},
 {'case':'capture table not refreshed','cached_delta':stale_capture_delta,'full_recompute_delta':actual_capture_delta},
 {'case':'board and hand prices independently changed but source drop delta remains0','source_drop_delta':0,'required_delta':board_value-hand_value}]
result={'complete':True,'source_pin':PIN,'source_witness_count':len(source_checks),'files':files,'initializer_consistency':checks,'initializer_consistency_count':len(checks),'finite_count_transitions':transitions,'finite_count_transition_count':len(transitions),'counterexamples':failures,'mature_games_executed':0,'search_calls_executed':0,'limitations':['No compilation, launch, security change, source-to-binary attestation, or USI setter execution.','Count transitions check material algebra only; they are not legal Shogi games or an independent move generator.','Pinned MaterialLv1 exposes no material setter in its empty add_options/load_eval path. This does not claim every Yane version lacks a setter.','Changing the coherent Eval tables also changes SEE/order/pruning uses. It is a separate shared-price experiment, not the Fairy leaf-only arm.','TT generations age entries; the actual candidate contract must clear candidate-dependent TT and rebuild full root history, or use fresh owned process.']}
(OUT/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({k:result[k] for k in ['source_pin','source_witness_count','initializer_consistency_count','finite_count_transition_count','counterexamples','mature_games_executed']}))