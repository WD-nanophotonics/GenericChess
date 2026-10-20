# attempt-3 cost scan interpretation

The raw result is preserved. All eight single-game arms ended when the game became terminal before reaching the 100,000-node arm ceiling; they produced 9,472–32,948 nodes per arm, for 187,144 combined nodes in 26.502s. Terminal labels and learned weights were censored. This confirms that fixed-foe actor routing and shared receipts execute, but this single-game-per-arm scan does not measure a full node-budget cost. Attempt-4 repeats paired games under the same per-arm and global caps until node exhaustion, terminal games, or the frozen maximum-game bound; no cap is extended.

{
  "attempt_3_result_sha256": "554beac7934a24ab54daa6e24d52180fa12727faa1dacefa9d584fbc22ba5d94",
  "arm_ends": {
    "5670": "TERMINAL_REACHED_LABEL_CENSORED",
    "181982": "TERMINAL_REACHED_LABEL_CENSORED",
    "449984": "TERMINAL_REACHED_LABEL_CENSORED",
    "714589": "TERMINAL_REACHED_LABEL_CENSORED"
  }
}
