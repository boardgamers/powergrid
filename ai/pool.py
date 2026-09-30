"""Concurrent isolated JS engines with one batched GPU policy call per step."""

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor


class EnginePool:
    def __init__(self, workers=1, seed="rollout-v1"):
        self.executor = ThreadPoolExecutor(workers)
        self.processes = [
            subprocess.Popen(
                ["node", "ai/bridge.cjs"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                bufsize=1,
                env={**os.environ, "SEED": f"{seed}-worker-{i}"},
            )
            for i in range(workers)
        ]
        self.sizes = []

    @staticmethod
    def _call(pair):
        process, request = pair
        process.stdin.write(json.dumps(request) + "\n")
        process.stdin.flush()
        line = process.stdout.readline()
        if not line:
            raise RuntimeError("Engine worker exited")
        return json.loads(line)

    def call(self, request):
        workers = len(self.processes)
        if request["op"] == "reset":
            n = request["n"]
            if n < workers:
                raise ValueError("Need at least one environment per worker")
            self.sizes = [n // workers + (i < n % workers) for i in range(workers)]
            requests = [{"op": "reset", "n": n} for n in self.sizes]
        else:
            requests = []
            offset = 0
            for n in self.sizes:
                requests.append(
                    {"op": "step", "actions": request["actions"][offset : offset + n]}
                )
                offset += n
            if offset != len(request["actions"]):
                raise ValueError("Incorrect action count")
        results = self.executor.map(self._call, zip(self.processes, requests))
        observations, ended, offset = [], [], 0
        for result, n in zip(results, self.sizes):
            observations.extend(result["observations"])
            ended.extend({**e, "env": e["env"] + offset} for e in result["ended"])
            offset += n
        return {"observations": observations, "ended": ended}

    def close(self):
        for process in self.processes:
            process.terminate()
            process.wait(timeout=5)
            process.stdin.close()
            process.stdout.close()
        self.executor.shutdown()
