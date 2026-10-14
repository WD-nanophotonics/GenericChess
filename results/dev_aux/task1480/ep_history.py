from pathlib import Path
import chess,json,ast,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1481';O.mkdir(exist_ok=False);s=(R/'results/dev_aux/task1462/audit.py').read_text(encoding='utf-8-sig')
sp=importlib.util.spec_from_file_location('L',R/'results/dev_aux/task1453/literal_pawn.py');L=importlib.util.module_from_spec(sp);sp.loader.exec_module(L);literal=L.literal
exec(compile(ast.Module(body=[n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name=='history_key'],type_ignores=[]),'key','exec'))
root='k7/8/8/3pP3/8/8/8/7K w - d6 0 2';b=chess.Board(root);assert b.is_valid();cycle=['h1g1','a8a7','g1h1','a7a8'];naive=[b.board_fen()+str(b.turn)];proper=[history_key(b)];rows=[]
for i in range(12):
 u=cycle[i%4];assert u in literal(b);b.push_uci(u);naive.append(b.board_fen()+str(b.turn));proper.append(history_key(b))
 if i%4==3:
  row=dict(plies=i+1,fen=b.fen(),naive_occurrences=naive.count(naive[-1]),correct_occurrences=proper.count(proper[-1]),python_threefold=b.is_repetition(3),literal_moves=literal(b));rows.append(row);assert (row['correct_occurrences']>=3)==row['python_threefold']
assert rows[1]['naive_occurrences']==3 and rows[1]['correct_occurrences']==2 and rows[1]['python_threefold'] is False and rows[2]['python_threefold'] is True
b0=chess.Board(root);b1=chess.Board(root);b1.ep_square=None;assert b0.board_fen()==b1.board_fen() and b0.turn==b1.turn and history_key(b0)!=history_key(b1);assert 'e5d6' in literal(b0) and 'e5d6' not in literal(b1)
out=dict(status='PASS_CONCRETE_LEGAL_EP_REPETITION_IDENTITY_COUNTEREXAMPLE',root=root,cycle=cycle,rows=rows,new_go=0,scope='OwnPawnindependentaudit guard mustinclude LEGAL EP capability: boardFen+turn naive falselydeclares3foldat8plies, properneeds12. Controller alreadyusespythonfullhistory, no productbug/patch or priornoPawnresultschange. Relevantobservedfinitecounterexample afteraddingP, notgenericallhistoryproof.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
