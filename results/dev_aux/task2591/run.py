"""DEV_AUX107 (AUX_CLAUDE) runner: rule hook pointed at task2591 (byte-identical copy of task2590 rule 363001).
Usage: python -m results.dev_aux.task2591.run {train|audit|unpruned|evaluate|deployment} DIR"""
from pathlib import Path
import sys
import results.dev_aux.task2586.run as R
R.D=Path('results/dev_aux/task2591')
if __name__=='__main__':R.main(sys.argv[1],sys.argv[2])
