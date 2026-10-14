from pathlib import Path
import ast,json,collections,chess
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1349';O.mkdir()
src=(R/'results/dev_aux/task1326/run.py').read_text(encoding='utf-8-sig');ns=dict(chess=chess)
exec(compile(ast.Module(body=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name in ['inside','legal5','term5']],type_ignores=[]),'terminal', 'exec'),ns)
gs=[json.loads(v) for v in (R/'results/dev_aux/task1329/games.jsonl').read_text().splitlines()];labels={};counts=collections.Counter()
for g in gs:
 b=chess.Board(g['root']['fen8'])
 for a in g['actions'][:12]:b.push_uci(a['move'])
 t=ns['term5'](b);label='C' if t is None else 'D' if t['winner'] is None else 'W' if t['winner']==g['color'] else 'L'
 labels[g['game']]=label;counts[g['arm']+'_'+label]+=1
out=dict(status='SAME_ACTUAL_POLICY_PREFIX_H12_TRUE_TERMINAL',counts=dict(counts),labels=labels,scope='Exposed paired horizon sensitivity from preserved trajectories; H12 labels actualterm only, C unresolved. Original H24 remains frozen and unchanged; no future perfectWDL claim/newqueries.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(dict(counts))
