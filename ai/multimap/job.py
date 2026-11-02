"""Bounded HF workflow. Upload data before fitting; checkpoint every five epochs.

All writes go to an isolated run prefix in private repos. Terminal failures are
archived and propagated as a nonzero process exit, never reported as completion.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import traceback

from huggingface_hub import HfApi, hf_hub_download
from data import ROOT, PROTOCOL, atomic_json, audit_splits, collect, digest, generator_digest
from train import train
from evaluate import run as evaluate


def retry(fn):
    for attempt in range(4):
        try:
            return fn()
        except Exception:
            if attempt == 3:
                raise
            time.sleep([5, 15, 45][attempt])


def run():
    run_id = os.environ["RUN_ID"]
    model_repo = os.environ["MODEL_REPO"]
    dataset_repo = os.environ["DATASET_REPO"]
    base = Path(os.environ.get("RUN_DIR", "/tmp/multimap-run"))
    base.mkdir(parents=True, exist_ok=True)
    api = HfApi()
    receipts = []
    status = dict(run=run_id, sourceRevision=os.environ["SOURCE_REVISION"],
                  sourceSha256=os.environ["SOURCE_SHA256"], protocol=PROTOCOL,
                  modelRepo=model_repo, datasetRepo=dataset_repo, qualified=False)

    def upload_model(stage):
        status.update(stage=stage, receipts=receipts)
        atomic_json(base / "status.json", status)
        artifacts = {str(p.relative_to(base)): digest(p) for p in base.rglob('*')
                     if p.is_file() and p.name != 'artifacts.json' and p.suffix not in ('.tmp','.tgz')
                     and 'data' not in p.relative_to(base).parts}
        atomic_json(base / "artifacts.json", artifacts)
        info = retry(lambda: api.upload_folder(repo_id=model_repo, folder_path=base,
                          path_in_repo=f"runs/{run_id}", ignore_patterns=["data/**", "*.tmp", "*.tgz"],
                          commit_message=f"{run_id}: {stage}"))
        receipts.append(dict(stage=stage, repo=model_repo, revision=info.oid))
        print(json.dumps(dict(stage="uploaded", label=stage, revision=info.oid)),flush=True)

    try:
        subprocess.run(["node", "--test", "ai/multimap/test.cjs"], cwd=ROOT, check=True)
        subprocess.run([sys.executable,"-B","-m","unittest","discover","-s","ai/multimap","-p","test_*.py"],cwd=ROOT,check=True)
        reuse = None
        if os.environ.get('REUSE_DATA') == '1':
            reuse = json.loads((Path(__file__).parent/'bootstrap-data-v1.json').read_text())
            if reuse['generatorDigest'] != generator_digest():
                raise RuntimeError('Archived data generator differs from current source')
        for split in ("train", "validation", "transfer"):
            if reuse:
                pin = next(p for p in reuse['archives'] if p['stage']==split)
                archive = hf_hub_download(pin['repo'],pin['path'],repo_type='dataset',revision=pin['revision'])
                if digest(archive) != pin['sha256']:
                    raise RuntimeError('Archived data hash mismatch')
                (base/'data').mkdir(exist_ok=True)
                with tarfile.open(archive) as tar:
                    tar.extractall(base/'data',filter='data')
                receipts.append({**pin,'reused':True})
                upload_model(f'restored-{split}')
                continue
            collect(base / "data" / split, split, workers=6)
            archive = base / f"{split}.tgz"
            with tarfile.open(archive, "w:gz", compresslevel=3) as tar:
                tar.add(base / "data" / split, arcname=split)
            sha = digest(archive)
            info = retry(lambda: api.upload_file(repo_id=dataset_repo, repo_type="dataset", path_or_fileobj=archive,
                           path_in_repo=f"multimap/{run_id}/data/{split}.tgz",
                           commit_message=f"{run_id}: {split} complete games"))
            receipts.append(dict(stage=split, repo=dataset_repo, revision=info.oid,
                                 path=f"multimap/{run_id}/data/{split}.tgz",sha256=sha))
            archive.unlink()
            upload_model(f"collected-{split}")
        audit = audit_splits(base / "data")
        atomic_json(base / "split-audit.json",audit)
        atomic_json(base / "excluded-train-fingerprints.json",json.loads((base/'data/excluded-train-fingerprints.json').read_text()))
        upload_model('audited-data')
        train(base / "data",base / "model",epochs=40,seed=508,device="cpu",
              checkpoint_callback=lambda epoch:upload_model(f"epoch-{epoch}"))
        upload_model("trained")
        summary = evaluate(base / "model/best.pt",base / "development",workers=6,
                           deals=PROTOCOL["developmentDealsPerCell"],
                           checkpoint_callback=lambda games:upload_model(f"development-{games}"))
        status["evaluationFailures"] = summary["failures"]
        status["macroCellDifference"] = summary["macroCellDifference"]
        upload_model("complete")
        # Completion means complete research artifacts, not a qualified policy.
        print(json.dumps(dict(stage="complete",run=run_id,receipts=receipts,
                              evaluationFailures=summary["failures"],qualified=False)),flush=True)
    except BaseException:
        status["error"] = traceback.format_exc()
        try:
            upload_model("failed")
        except Exception:
            traceback.print_exc()
        raise


if __name__ == "__main__":
    run()
