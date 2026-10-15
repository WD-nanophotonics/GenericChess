from pathlib import Path
import json,ast
R=Path.cwd();p=R/'results/dev_aux/task1701/root_strata.py';s=p.read_text(encoding='utf-8-sig').replace('else4','else 4').replace("task1704'","task1705'");(p.parent/'root_strata_fixed.py').write_text(s,encoding='utf8');ast.parse(s);d=R/'results/dev_aux/task1704';d.mkdir(exist_ok=True);(d/'failure.json').write_text(json.dumps({'status':'PREEXECUTION_SYNTAX_FAILURE_PRESERVED','cause':'Missingwhitespaceelse4 in analysispreparedsource; noqueries, correctedseparatesource root_strata_fixed.py/new1705','actual_go':0},indent=2))
