"""DEV_AUX103 (AUX_CLAUDE) runner: task2586 rule hook pointed at task2587 rules; warm-start train/audit copies.
Usage: python -m results.dev_aux.task2587.run {train|audit|unpruned|evaluate|deployment} DIR
"""
from pathlib import Path
import sys
import results.dev_aux.task2586.run as R
R.D=Path('results/dev_aux/task2587')
def main(step,directory):
 T5=R.install()
 if step=='train':
  import results.dev_aux.task2587.train as T;T.compiled=T5.compiled;T.run(directory)
 elif step=='audit':
  import results.dev_aux.task2587.audit as A;A.run(directory)
 else:R.main(step,directory)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
