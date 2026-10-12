from pathlib import Path
import json,subprocess,time,hashlib
R=Path.cwd();S=R/'.local_agent/yaneura25/source';O=R/'results/dev_aux/task362';O.mkdir(exist_ok=True)
# Preserve the qualified build. Align SEE's actual attacker values/order, without claiming full shogi exchange exactness.
old=S.parent/'yaneura-material1-aux.exe';backup=S.parent/'yaneura-material1-original-see.exe';backup.write_bytes(old.read_bytes())
p=S/'position.cpp';t=p.read_text(encoding='utf-8-sig');start=t.index('        // 歩で取れるなら、まず歩で取る。',t.index('bool Position::see_ge'));end=t.index('#if !STOCKFISH\n        /*',start)
replacement=r'''        // DEV_AUX: candidate board-price LVA; retain upstream board-only SEE approximation.
        bb = Bitboard(ZERO);
        PieceType selected = NO_PIECE_TYPE;
        int cheapest = 100000000;
        for (int pt = 1; pt <= 14; ++pt) {
            if (pt == int(KING)) continue;
            auto candidates = stmAttackers & pieces(PieceType(pt));
            if (candidates && PieceValue[pt] < cheapest) {
                cheapest = PieceValue[pt]; selected = PieceType(pt); bb = candidates;
            }
        }
        if (!bb) return (attackers & ~pieces(stm)) ? res ^ 1 : res;
        if ((swap = PieceValue[selected] - swap) < res) break;
        if (selected == KNIGHT) {
            occupied ^= bb.pop();
            continue;
        }

'''
t=t[:start]+replacement+t[end:];p.write_text(t,encoding='utf-8')
p=S/'usi.cpp';t=p.read_text(encoding='utf-8');needle='else if (token == "auxstate")';assert t.count(needle)==1;t=t.replace(needle,'else if (token == "auxsee") { std::string u; int threshold; is >> u >> threshold; auto& pos=engine.get_position(); auto m=USIEngine::to_move(pos,u); if(!m.is_ok()) sync_cout << "info string auxsee invalid" << sync_endl; else sync_cout << "info string auxsee " << pos.see_ge(m,Value(threshold)) << sync_endl; }\n    '+needle);p.write_text(t,encoding='utf-8')
b=json.loads((R/'results/dev_aux/task358/build.json').read_text(encoding='utf-8'));steps=[];t0=time.monotonic()
for index in [5,6]:
 args=b['steps'][index]['args'];r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append({'args':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});print(index,r.returncode,r.stderr[-2000:],flush=True)
 if r.returncode:break
else:
 args=b['steps'][-1]['link_args'];r=subprocess.run(args,cwd=S,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);steps.append({'args':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr});print('link',r.returncode,r.stderr[-2000:],flush=True)
(O/'build.json').write_text(json.dumps({'seconds':time.monotonic()-t0,'steps':steps,'original_see_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),'candidate_see_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'scope':'Candidate board-price SEE/LVA; upstream SEE omits demoted hand gain and recapture promotions; fixed search margins/USI P90 unchanged. Do not call fullyaligned exchange oracle.'},indent=2),encoding='utf-8')
(O/'see_replacement.txt').write_text(replacement,encoding='utf-8')