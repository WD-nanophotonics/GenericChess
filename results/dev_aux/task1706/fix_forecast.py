from pathlib import Path
import ast,json
R=Path.cwd();p=R/'results/dev_aux/task1706/forecast.py';s=p.read_text(encoding='utf-8-sig').replace('else0','else 0').replace("task1712'","task1713'");(p.parent/'forecast_fixed.py').write_text(s,encoding='utf8');ast.parse(s);d=R/'results/dev_aux/task1712';d.mkdir(exist_ok=True);(d/'failure.json').write_text(json.dumps({'status':'PREEXECUTION_SYNTAX_FAILURE_PRESERVED','cause':'Preparedanalysiselse0 spacing syntaxerror; zeroqueries. Correctseparatesourceforecast_fixed.py/new1713.','actual_go':0},indent=2))
