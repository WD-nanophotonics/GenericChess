"""DEV_AUX106 (AUX_CLAUDE) runner: task2586 rule hook pointed at task2590 rules; P/A/X channels unchanged.
Usage: python -m results.dev_aux.task2590.run {train|audit|unpruned|evaluate|deployment} DIR"""
from pathlib import Path
import sys
import results.dev_aux.task2586.run as R
R.D=Path('results/dev_aux/task2590')
if __name__=='__main__':R.main(sys.argv[1],sys.argv[2])
