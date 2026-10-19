"""DEV_AUX102 (AUX_CLAUDE): SAME task2565 Generic TD/audit/eval code on NEW generated rules.

Only change: task2565.train.compiled() also loads task2586/rules-<gs>.json for the NEW
generator seeds, installed BEFORE importing the audited modules (they bind it at import).
Usage: python -m results.dev_aux.task2586.run {train|audit|unpruned|evaluate|deployment} DIR
"""
from pathlib import Path
import json,sys
D=Path('results/dev_aux/task2586')
def install():
 import results.dev_aux.task2565.train as T
 if getattr(T.compiled,'_task2586',False):return T
 original=T.compiled
 def compiled(gs):
  path=D/f'rules-{gs}.json'
  if not path.exists():return original(gs)
  from generic_chess.rules.schema import ruleset_from_dict
  from generic_chess.rules.compiler import compile_ruleset
  return compile_ruleset(ruleset_from_dict(json.loads(path.read_text())))
 compiled._task2586=True;T.compiled=compiled;return T
def main(step,directory):
 T=install()
 if step=='train':T.run(directory)
 elif step=='audit':
  import results.dev_aux.task2565.audit as A;A.run(directory)
 elif step=='unpruned':
  import results.dev_aux.task2565.verify as V;V.unpruned(directory)
 elif step=='evaluate':
  import results.dev_aux.task2565.evaluate as E;E.run(directory)
 elif step=='deployment':
  import results.dev_aux.task2565.verify as V;V.deployment(directory)
 else:raise SystemExit('unknown step '+step)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
