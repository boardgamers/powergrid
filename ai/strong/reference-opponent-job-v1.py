"""Run one frozen diagnostic root, with explicit path relocation and no training."""
import argparse
import importlib.util
import os
from pathlib import Path
import time

from huggingface_hub import hf_hub_download
from strategic_collection import ROOT, read, write, digest
from policy_iteration_evidence_archive import upload_evidence

spec = importlib.util.spec_from_file_location('reference_probe', ROOT/'ai/strong/probe-reference-opponents-v1.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def main(args):
    assert args.worlds in (4,8,16,32,64) and args.begin>=0 and args.begin%args.worlds==0
    assert args.begin+args.worlds<=64
    original = read(probe.OUT/'protocol.json')
    pin = read(ROOT/'ai/strong/population-hybrid-development-protocol-v1.json')['model_pin']
    assert original['model_sha256'] == pin['files']['inference64.onnx']
    runtime = str(Path(args.runtime).resolve()) if args.runtime else str(ROOT)
    model_path = str(Path(args.model).resolve()) if args.model else hf_hub_download(
        pin['repo'], pin['prefix']+'/inference64.onnx', revision=pin['revision'])
    p = {**original, 'runtime': runtime, 'model_path': model_path}
    # Only filesystem locations change; model, all policies, inputs and budgets stay pinned.
    assert {k:v for k,v in p.items() if k not in ('runtime','model_path')} == {
        k:v for k,v in original.items() if k not in ('runtime','model_path')}
    probe.validate(p)
    assert not os.environ.get('NODE_OPTIONS')
    os.environ['PG_REFERENCE_RUNTIME'] = runtime
    model = probe.Model(model_path, threads=1)
    assert probe.model_revision(model) == p['feature_revision']
    node = probe.Node(str(probe.WORKER))
    try:
        root = p['roots'][args.root]
        prepared = node.call({**root['request'], 'featureRevision':p['feature_revision'], 'op':'prepare'})
        assert probe.public_seed(prepared) == root['original_decision']['search']['seed']
        assert probe.predict_batch(model, [prepared['observation']])[0] == root['options'][0]
    finally:
        node.close()
    if args.check_layout:
        print({'layout_verified':True, 'root':args.root, 'model_sha256':model.sha256,
               'frozen_runtime_files':len(p['runtime_hashes']), 'new_rollouts':0}, flush=True)
        return
    case=f'reference-opponent-full-v1-root-{args.root}-worlds-{args.begin}-{args.begin+args.worlds}'
    out = Path(args.output).resolve() if args.output else ROOT/'ai/runs'/case
    out.mkdir(parents=True, exist_ok=False)
    status = {'root':args.root, 'begin':args.begin,'worlds':args.worlds,'case':case,
              'stage':'running', 'original_protocol_sha256':digest(probe.OUT/'protocol.json'),
              'model_sha256':model.sha256, 'runtime_binding':runtime, 'model_binding':model_path,
              'job_runner_sha256':digest(__file__), 'source_revision':os.environ.get('SOURCE_REVISION'),
              'source_sha256':os.environ.get('SOURCE_SHA256'),
              'evidence_revision':os.environ.get('EVIDENCE_REVISION'),
              'evidence_sha256':os.environ.get('EVIDENCE_SHA256'),
              'qualification_eligible':False, 'reserved_final_seeds_used':False}
    started = time.perf_counter()
    try:
        probe.run_root(p, model, args.root, 'reference_opponent_v1', args.begin,args.worlds,out/'result.json')
        result = read(out/'result.json')
        check_prefix=args.begin==0 and args.root in p['pilot_roots']
        if check_prefix:
            pilot = read(probe.OUT/f'pilot-{args.root}.json')
            assert result['rows'][:4] == pilot['rows'], 'Original pilot worlds changed'
        status.update(stage='complete', rollouts=args.worlds*2, caps=0,pilot_prefix_exact=check_prefix)
    except BaseException as error:
        status.update(stage='failed', error=type(error).__name__+': '+str(error))
        raise
    finally:
        status['seconds'] = time.perf_counter()-started
        write(out/'status.json',status)
        write(out/'manifest.json',{str(f.relative_to(out)):digest(f) for f in sorted(out.rglob('*')) if f.is_file()})
        if args.upload:
            evidence = upload_evidence(out)
            print({'status':status, 'evidence':evidence}, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('root', type=int, choices=range(7))
    parser.add_argument('--begin',type=int,default=0)
    parser.add_argument('--worlds',type=int,default=64)
    parser.add_argument('--runtime')
    parser.add_argument('--model')
    parser.add_argument('--output')
    parser.add_argument('--check-layout',action='store_true')
    parser.add_argument('--upload',action='store_true')
    main(parser.parse_args())
