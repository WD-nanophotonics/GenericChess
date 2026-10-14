from pathlib import Path
import ast,json,chess
R=Path.cwd();O=R/'results/dev_aux/task1335';O.mkdir()
src=(R/'results/dev_aux/task1293/audit.py').read_text(encoding='utf-8-sig')
tree=ast.parse(src);defs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
exec(compile(ast.Module(body=defs,type_ignores=[]),'literal','exec'),globals())
inside=lambda s:0<=s<64
legal5=lambda b:sorted(m.uci() for m in b.legal_moves)
D=json.loads((R/'results/dev_aux/task1334/result.json').read_bytes());counts=__import__('collections').Counter();rows=[]
for row in D['rows']:
 b=chess.Board(row['root']['fen8']);assert sorted(row['scores'])==sorted(row['actions'])
 for c in row['certificates']:
  assert c['first'] in literal(b) and c['value']==row['scores'][c['first']] and c['child']['value']==-c['value']
  b.push_uci(c['first']);walk(c['child'],b);b.pop();counts['verified_root_action_certificates']+=1
 counts['selected_actions']+=len(row['scores']);counts['roots']+=1
 counts['roots_with_H4differences']+=len(set(row['scores'].values()))>1
 rows.append(dict(seed=row['seed'],values=row['scores'],D2=row['D2_points']))
(O/'result.json').write_text(json.dumps(dict(status='PASS_SELECTED_UNION_H4_CERTIFICATES',counts=dict(counts),rows=rows,scope='0no forcedterminal within H4; longterm unresolved; subset not all rootactions'),indent=2))
print(dict(counts));print([{k:v for k,v in r.items() if k!='D2'} for r in rows])
