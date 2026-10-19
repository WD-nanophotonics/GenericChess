"""DEV_AUX108 (AUX_CLAUDE) runner: task2586 rule hook pointed at task2592 rules; P/A/X channels unchanged.
Usage: python -m results.dev_aux.task2592.run {train|audit|unpruned|evaluate|deployment} DIR"""
from pathlib import Path
import sys
import results.dev_aux.task2586.run as R
R.D=Path('results/dev_aux/task2592')
if __name__=='__main__':R.main(sys.argv[1],sys.argv[2])
