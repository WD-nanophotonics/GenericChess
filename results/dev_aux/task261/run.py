import json,hashlib,time,sys,dataclasses,random,importlib.util
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R));O=R/'results/dev_aux/task261';assert not (O/'profile.json').exists()
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.ai.evaluation.config import EvaluationConfig,config_hash
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from scripts.research_record import record_value
start=time.monotonic();c=compile_semantic_ruleset(build_western_chess_ruleset());cfg=EvaluationConfig();profile,scope=build_semantic_opportunity_profile(c,cfg)
raw=dict(profile.board_value_by_type);assert set(raw)==set('PNBRQK') and raw['K']==0
# FixedP208 applied equally to allcandidate ratios; rawgenerator untouched.
w={k:0 if k=='K' else max(1,round(v*208/raw['P'])) for k,v in raw.items()}
source_paths=['generic_chess/ai/evaluation/semantic.py','generic_chess/ai/evaluation/profile.py','generic_chess/ai/evaluation/config.py','generic_chess/rules/western_chess.py']
out=dict(complete=True,task_id='261',question='Whatactualsemantic opportunity prices/scope does ownpinnedproductionAPI generate, withoutinventinghumanprices?',source_base='1de362ef6c7ef9b5de3ec5ef236333469f1428f7',raw_prices=raw,normalized_P208=w,normalization='round(raw*208/rawP), allnonanchor>=1; king0fixed. Generator raw kept. No humanprior/fitting.',generator_config=dataclasses.asdict(cfg),generator_config_hash=config_hash(cfg),profile=record_value(profile),scope=scope,source_hashes={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in source_paths},seconds=time.monotonic()-start,authority='Independentfeasibilityreview ofDotsupplement1791802864; attributedanotheruserconversationnotimportedasauthority. No takeoverprimaryUI/searchtask. Defaultsemanticcandidateignoresfuturepromotion/king-safety/compoundeffects; notfullgamevalueproof.')
(O/'profile.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ('complete','raw_prices','normalized_P208','generator_config_hash','seconds')},indent=2));print({k:dict(included=v['included'],excluded=v['excluded'],raw=v['raw']) for k,v in scope['types'].items()})
