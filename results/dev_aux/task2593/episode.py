"""Outcome-gated per-residual trace for the DEV_AUX standard-Chess probe.

For each bootstrap residual, use lambda=1 only when its *target* (the next
observed search value) is tagged as a terminal PV. Other residuals, including
the final known game outcome, use the frozen base lambda. Unknown final outcomes
remain censored. This is a local research prototype, not a production learner.
"""

from results.dev_aux.task2492.learning import transformed


class OutcomeGatedTDLeafEpisode:
    def __init__(self, eta=0.05, lam=0.95):
        if not 0 <= lam <= 1:
            raise ValueError("lambda")
        self.eta = eta
        self.lam = lam
        self.reset()

    def reset(self):
        self.rows = []
        self.snapshot = None

    def observe(self, model, receipt):
        if not receipt.complete:
            return dict(samples=0, loss=None, changed=False)
        current = tuple(model.weights)
        if self.snapshot is None:
            self.snapshot = current
        if current != self.snapshot:
            raise ValueError("episode weights changed before TD update")
        value = transformed(receipt.value, model.scale)
        grad = (tuple(0.0 for _ in model.weights) if receipt.pv_terminal
                else model.gradient(receipt.pv_phi))
        self.rows.append((value, grad, bool(receipt.pv_terminal)))
        return dict(samples=0, loss=None, changed=False)

    def finish(self, model, outcome):
        if self.snapshot is not None and tuple(model.weights) != self.snapshot:
            raise ValueError("episode weights changed")
        delta = [0.0] * len(model.weights)
        loss = 0.0
        terms = 0
        terminal_change = 0.0
        for i, (prediction, _, _) in enumerate(self.rows):
            if i + 1 < len(self.rows):
                target, _, target_is_terminal = self.rows[i + 1]
                trace_lambda = 1.0 if target_is_terminal else self.lam
            else:
                target = outcome
                trace_lambda = self.lam
            if target is None:
                break  # censored; never invent a draw or terminal TD error
            error = float(target) - prediction
            eligibility = [
                sum((trace_lambda ** (i - j)) * self.rows[j][1][k]
                    for j in range(i + 1))
                for k in range(len(model.weights))
            ]
            loss += error * error / 2.0
            terms += 1
            for k, value in enumerate(eligibility):
                delta[k] += error * value
            if i + 1 == len(self.rows):
                terminal_change = sum(abs(error * value)
                                      for value in eligibility)
        model.apply([self.eta * value for value in delta])
        stats = dict(samples=terms, loss=loss / max(1, terms),
                     changed=any(delta), terminal_credit_l1=terminal_change,
                     observed_searches=len(self.rows), censored=outcome is None)
        self.reset()
        return stats
