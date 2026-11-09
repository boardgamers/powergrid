"""Versioned worker wrapper; no launch API and no legacy namespace relaxation."""
import os
from pathlib import Path

# Before any transitive huggingface_hub import. Offline module imports never
# redirect the user's cache; the executable worker alone owns this cache.
if __name__ == '__main__':
    os.environ['HF_HUB_CACHE'] = os.environ.get(
        'REPLICA_MODEL_CACHE', '/tmp/multimap-expert-replicas-models')

import job_expert
from expert_replicas_v1 import Replica, bind

FORBIDDEN_JSON = job_expert.FORBIDDEN_JSON | {'response', 'state', 'move', 'rows', 'trajectory'}


def compact_json(value):
    if isinstance(value, dict):
        if FORBIDDEN_JSON & set(value):
            raise ValueError('Raw decision/optimization payload forbidden')
        for child in value.values():
            compact_json(child)
    elif isinstance(value, list):
        for child in value:
            compact_json(child)


def _compact_training_json(value):
    """Preserve the frozen trainer's aggregate ``optimization.rows`` count.

    Never change stored JSON, checkpoint bytes, metrics, or the frozen writer.
    Only the validator's private view omits this one nonnegative integer count;
    a raw rows list/dict (even at that location) is still rejected. All other
    forbidden keys retain the strict recursive compact_json guard.
    """
    def counts(child):
        if isinstance(child, dict):
            result = {}
            for key, item in child.items():
                if key == 'optimization' and isinstance(item, dict) and 'rows' in item:
                    n = item['rows']
                    if type(n) is not int or n < 0:
                        raise ValueError('Raw optimization rows forbidden')
                    item = {k: v for k, v in item.items() if k != 'rows'}
                result[key] = counts(item)
            return result
        if isinstance(child, list):
            return [counts(item) for item in child]
        return child
    compact_json(counts(value))


# Private binding only: do not mutate job_expert.compact_json/compact_files.
compact_files = bind(job_expert.compact_files, compact_json=_compact_training_json)


def _run():
    raw = os.environ.get('EXPERT_REPLICA')
    if raw not in ('1', '2'):
        raise ValueError('EXPERT_REPLICA must be 1 or 2')
    if os.environ.get('EXPERT_WORKERS', '6') != '6':
        raise ValueError('Replica worker is frozen to six workers')
    if os.environ.get('EXPERT_SMOKE', '0') != '0':
        raise ValueError('Authorized replica worker requires the full frozen recipe')
    segment = os.environ.get('REPLICA_SEGMENT')
    if segment not in ('1', '2'):
        raise ValueError('REPLICA_SEGMENT must be 1 or 2')
    run_id = job_expert.shared.safe_run(os.environ.get('RUN_ID', ''))
    suffix = '-r' + raw
    if not run_id.endswith(suffix) or len(run_id) == len(suffix):
        raise ValueError('Replica run ID must end in its replica suffix')
    previous, revision = os.environ.get('RESUME_RUN'), os.environ.get('RESUME_REVISION')
    if segment == '1':
        if previous or revision or run_id[:-len(suffix)].endswith('-continuation'):
            raise ValueError('First replica segment cannot resume')
    else:
        if not previous or not revision:
            raise ValueError('Second replica segment requires an immutable resume')
        job_expert.shared.safe_run(previous)
        job_expert.shared.immutable_revision(revision)
        if (not previous.endswith(suffix) or len(previous) == len(suffix) or
                previous[:-len(suffix)].endswith('-continuation') or
                run_id != previous[:-len(suffix)] + '-continuation' + suffix):
            raise ValueError('Continuation must resume the same replica first segment')
    # The unchanged worker uses the first four paths; include the dedicated
    # model cache before *any* restore, reference recovery, or warm download.
    paths = [Path(os.environ.get(key, default)) for key, default in (
        ('RUN_DIR', '/tmp/multimap-expert-run'),
        ('REFERENCE_CACHE', '/tmp/multimap-expert-reference'),
        ('REFERENCE_VENV', '/tmp/multimap-expert-reference-venv'),
        ('RESUME_CACHE', '/tmp/multimap-expert-resume'),
        ('REPLICA_MODEL_CACHE', '/tmp/multimap-expert-replicas-models'),
    )]
    job_expert.shared.separate_paths(*paths)
    from huggingface_hub.constants import HF_HUB_CACHE
    if Path(HF_HUB_CACHE).resolve() != paths[-1].resolve():
        raise ValueError('Replica models must use the dedicated startup cache')
    replica = Replica(int(raw))
    # The frozen test_expert*.py discovery already runs our adapter tests once.
    # Preserve its four checkpoint metadata checks before any warm download.
    return bind(job_expert.run, PROTOCOL=replica.protocol, train=replica.run,
                compact_json=compact_json, compact_files=compact_files)()


def run():
    try:
        return _run()
    except BaseException:
        # Frozen worker already records fixed-code status. Never print a raw
        # request/response or exception packet via its re-raised traceback.
        raise RuntimeError('Replica training stopped; inspect fixed-code status and committed transactions') from None


if __name__ == '__main__':
    run()
