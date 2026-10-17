"""First corrected TD-only continuation study; old smoke remains immutable."""
from pathlib import Path
import results.dev_aux.task2492.run as trainer
if __name__=='__main__':
 trainer.OUT=Path('results/dev_aux/task2495');trainer.run()
