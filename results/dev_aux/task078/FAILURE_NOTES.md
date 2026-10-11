# Setup failures

Initial generator tried hashing a __pycache__ directory after writing declared candidate, causing PermissionError. Generated probe also had invalid nested quote syntax before execution. Both are setup failures, no search evidence. Exact failed probe retained; source replacement now uses repr and substitutes noisy call before inner side expression.
