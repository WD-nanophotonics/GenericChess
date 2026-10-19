"""Run the frozen task2568 trainer with only the TDLeaf episode swapped."""
import sys
from pathlib import Path
import chess
from results.dev_aux.task2593.episode import OutcomeGatedTDLeafEpisode
from results.dev_aux.task2568 import train as frozen_runner
if sys.version_info[:3]!=(3,12,14) or chess.__version__!="1.11.2":
    raise RuntimeError("runtime differs from registered environment")
frozen_runner.TDLeafEpisode=OutcomeGatedTDLeafEpisode
frozen_runner.run(Path(sys.argv[1]))
