"""Frozen PPO opponents, with admission independent of model selection when requested."""
import copy


class SnapshotLeague:
    def __init__(self, net, admission="best", interval=10):
        if admission not in {"best", "periodic_anchor"}:
            raise ValueError("Unknown snapshot admission policy")
        if interval < 1:
            raise ValueError("Snapshot interval must be positive")
        self.admission = admission
        self.interval = interval
        self.actors = [self._freeze(net)]
        self.updates = [-1]

    @staticmethod
    def _freeze(net):
        actor = copy.deepcopy(net).eval()
        actor.requires_grad_(False)
        return actor

    def admit(self, net, update, improved=False):
        due = improved if self.admission == "best" else (update + 1) % self.interval == 0
        if not due or update in self.updates:
            return False
        self.actors.append(self._freeze(net))
        self.updates.append(update)
        if len(self.actors) > 3:
            indices = [-3, -2, -1] if self.admission == "best" else [0, -2, -1]
            self.actors = [self.actors[i] for i in indices]
            self.updates = [self.updates[i] for i in indices]
        return True
