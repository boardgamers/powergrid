"""One engine per game; advance ready games without a global step barrier."""

from concurrent.futures import FIRST_COMPLETED, wait
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pool import EnginePool


class AsyncEnginePool(EnginePool):
    def __init__(self, workers, seed="rollout-v1", script="ai/strong/bridge.cjs"):
        super().__init__(workers, seed, script)
        self.pending = {}
        self.ready = set()
        self.started = False

    def _submit(self, index, request):
        future = self.executor.submit(self._call, (self.processes[index], request))
        self.pending[future] = index

    def _collect(self):
        observations = [None] * len(self.processes)
        ended = []
        while self.pending:
            done, _ = wait(self.pending, return_when=FIRST_COMPLETED)
            # Also consume replies that finished during the wakeup.
            done.update(f for f in self.pending if f.done())
            for future in sorted(done, key=lambda f: self.pending[f]):
                index = self.pending.pop(future)
                result = future.result()
                if len(result["observations"]) != 1:
                    raise ValueError("Async engines must own exactly one game")
                row = result["observations"][0]
                observations[index] = row
                if row is not None:
                    self.ready.add(index)
                for e in result["ended"]:
                    if e["env"] != 0:
                        raise ValueError("Unexpected worker-local environment index")
                    ended.append({**e, "env": index})
            if self.ready:
                break
            # Completed games alone must not end the caller's loop while other
            # engines still have requests in flight.
        return {"observations": observations, "ended": ended}

    def call(self, request):
        count = len(self.processes)
        if request["op"] == "reset":
            if self.pending or self.ready:
                raise ValueError("Cannot reset while a batch is active")
            if request["n"] != count:
                raise ValueError("Async training needs one worker per environment")
            self.started = True
            offset = request.get("offset", 0)
            for index in range(count):
                self._submit(index, {**request, "n": 1, "offset": offset + index})
        elif request["op"] == "step":
            actions = request["actions"]
            if not self.started or len(actions) != count:
                raise ValueError("Incorrect action count or missing reset")
            supplied = {i for i, action in enumerate(actions) if action is not None}
            if supplied != self.ready:
                raise ValueError("Actions must match the ready environments exactly")
            for index in sorted(self.ready):
                self._submit(index, {"op": "step", "actions": [actions[index]]})
            self.ready.clear()
        else:
            raise ValueError("Unknown operation")
        return self._collect()
