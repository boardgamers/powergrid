"""Re-execute only recovered request 5:21 with the original immutable policy.

This is a failure reproduction, not a replacement pilot or a strength game.
Preserve the full exception stack and any failing encoded observation.
"""
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / 'ai/runs/conservative-auction-runtime-prepared-v1/source/artifact'
OUTPUT = ROOT / 'ai/runs/conservative-auction-failure-diagnosis-v1'
sys.path.insert(0, str(ARTIFACT / 'ai/strong'))
from public_policy_runtime_v1 import PublicPolicyService, digest, load_artifact


def write(name, value):
    with (OUTPUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    replay = json.loads((OUTPUT / 'prefix-replay.json').read_text())
    assert len(replay['prefix_matches']) == 20
    assert digest(OUTPUT / 'request-5-21.json') == replay['reconstructed_request_sha256']
    request = json.loads((OUTPUT / 'request-5-21.json').read_text())
    assert request['requestId'] == '5:21'
    service = PublicPolicyService(lambda: load_artifact(ARTIFACT, 'policies/conservative_dual.json'))
    report = {'original_job': replay['original_job'], 'requestId': '5:21',
              'request_sha256': replay['reconstructed_request_sha256'],
              'frozen_policy_sha256': replay['policy_sha256'],
              'new_strength_games': 0, 'new_hf_jobs': 0, 'gradient_updates': 0,
              'reserved_final_seeds_used': False, 'qualification_eligible': False}
    try:
        response = service.decide(request, diagnostics=True)
        write('reproduced-response.json', response)
        report.update(reproduced_failure=False, response_sha256=digest(OUTPUT / 'reproduced-response.json'))
    except Exception as error:
        stack = traceback.format_exc()
        (OUTPUT / 'original-policy-stack.txt').write_text(stack)
        frames = []
        tb = error.__traceback__
        while tb is not None:
            frame = tb.tb_frame
            row = {'file': str(Path(frame.f_code.co_filename).resolve().relative_to(ROOT)),
                   'line': tb.tb_lineno, 'function': frame.f_code.co_name}
            if 'observation' in frame.f_locals and isinstance(frame.f_locals['observation'], dict):
                observation = frame.f_locals['observation']
                if {'state', 'actions', 'moves'}.issubset(observation):
                    name = f'failing-observation-{len(frames)}.json'
                    write(name, observation)
                    row.update(observation_file=name, observation_sha256=digest(OUTPUT / name))
            frames.append(row)
            tb = tb.tb_next
        report.update(reproduced_failure=True, error_type=type(error).__name__,
                      error_message=str(error), frames=frames,
                      stack_sha256=digest(OUTPUT / 'original-policy-stack.txt'))
        print(stack, flush=True)
    finally:
        service.close()
    write('original-policy-reproduction.json', report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
