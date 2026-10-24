"""Use the unchanged atomic arena runner with an explicit resource-policy factory.

This process-local binding changes no frozen files or running jobs. Every learner
decision still goes through the original single-action engine step and receipt.
"""
import importlib.util
from pathlib import Path
from resource_replanning_policy_v1 import ResourceReplanningPolicy,RESOURCE_ARMS


def arena_module():
    path=Path(__file__).with_name('evaluate-population-policy.py')
    spec=importlib.util.spec_from_file_location('resource_atomic_arena',path)
    arena=importlib.util.module_from_spec(spec);spec.loader.exec_module(arena)
    arena.PopulationPolicy=ResourceReplanningPolicy
    arena.ARMS=(*arena.ARMS,*RESOURCE_ARMS)
    return arena


def play(config,episode):return arena_module().play(config,episode)


if __name__=='__main__':
    arena=arena_module()
    # The importable top-level wrapper is the process-pool task; the dynamically
    # loaded frozen function stays inside each child and need not be pickled.
    arena.play=play
    arena.main()
