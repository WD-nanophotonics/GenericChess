from pathlib import Path
import json,random,importlib.util,hashlib,collections
R=Path.cwd();O=R/'results/dev_aux/task1498';O.mkdir(exist_ok=False)
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1490/tiny_rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
P=R/'results/dev_aux/task1495';states=list(map(tuple,json.loads((P/'states.json').read_bytes())));index={s:i for i,s in enumerate(states)};data=json.loads((P/'values.json').read_bytes());v=data['value'];rank=data['rank'];edges=[json.loads(x)['moves'] for x in (P/'edges.jsonl').read_text().splitlines()]
def twin(s):return tuple(8-s[i] if s[i]!=9 else 9 for i in [3,4,5,0,1,2])+(1-s[6],)
for i,s in enumerate(states):assert twin(twin(s))==s and v[index[twin(s)]]==v[i]
eligible=[]
for i,s in enumerate(states):
 if 9 in s[:6] or len(edges[i])<2:continue
 if len({-v[j] for u,j in edges[i]})<2:continue
 if any(v[j]==-1 and rank[j]==0 for u,j in edges[i]):continue
 j=index[twin(s)]
 if i<j:eligible.append([i,j])
rng=random.Random(2026610000);rng.shuffle(eligible);assert len(eligible)>=192
families=[]
for n,pair in enumerate(eligible[:192]):families.append({'family':n,'phase':'TRAIN' if n<128 else 'DEV','state_ids':pair,'fens':[T.fen(states[i]) for i in pair]})
plan={'question':'Can material-only mature search learn R/N from exact true-WDL on tiny3x3 game?','source_graph':'results/dev_aux/task1495','rules':'results/dev_aux/task1490/tiny_rules.py','variant_ini':'results/dev_aux/task1497/variant.ini','TRAIN_families':128,'DEV_families':64,'family_basis':'180degree rotation plus colorswap, pair retained across split; shuffled before prices with seed2026610000','mu':'Full KR NvKR N stock, at least2legal and exactchildWDL conflict, no immediate winningmate. Label-based selection is declared distribution; never candidate/humanprice based.','R_grid':[360,720,1440,1728],'N_fixed':720,'nodes':[16,64,256],'nativePNBR':720,'Q_fixed':1664,'objective':'Mean exact -WDL(child selected by mature engine); perfect-play continuation. This is proved finite-game WDL afteronechoice, not selfplay empirical winrate or humanChessvalue.','selection':'Independent TRAIN-only global lowesttie at each of3declared budgets; strict adjacent paths reported. DEV fixed union three selectedR plus720 dedup then allthreebudgets; primary eachbudgetownminus720, simultaneous across3; noDEVfit/extension.','max_seconds_train':300,'max_seconds_dev':300,'binary':'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe','binary_sha256':'0263e8d6e9677b82e179c0d1a61ea5080df3275aba3464569e040eb222a20fe9','families':families,'eligible_families':len(eligible),'input_hashes':{x:hashlib.sha256((P/x).read_bytes()).hexdigest() for x in ['states.json','values.json','edges.jsonl']}}
(O/'study.json').write_text(json.dumps(plan,indent=2));print('eligible',len(eligible),'TRAIN128/DEV64 symmetryfamilies','nodebudget16/64/256 frozen before choices')
