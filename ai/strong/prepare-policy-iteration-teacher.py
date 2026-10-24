"""Archive the fixed selection and define a balanced first teacher pilot."""
from collections import defaultdict
import hashlib, json
from huggingface_hub import HfApi
from strategic_collection import ROOT, read, write, digest


def main():
    report = read(ROOT/'ai/strong/policy-iteration-selection-results-v2.json')
    source = read(ROOT/'ai/strong/policy-iteration-collection-source-v2.json')
    assert report['complete'] and report['source'] == source
    assert report['cross_split_duplicate_inputs'] == report['cross_split_duplicate_public_states'] == 0
    out = ROOT/'ai/runs/policy-iteration-selected-v2'
    for file, sha in report['artifacts'].items(): assert digest(out/file) == sha
    rows = read(out/'selected-index.json'); assert len(rows) == report['selected_roots']
    groups = defaultdict(list)
    for r in rows:
        groups[r['players'], r['behavior'], r['mode'], r['variant'], r['sealed'], r['decision']].append(r)
    assert len(groups) == 360
    fields = ['rootId', 'players', 'behavior', 'mode', 'variant', 'sealed', 'decision', 'deal', 'split', 'round', 'public_root_sha256']
    pilot = []
    for key, items in sorted(groups.items()):
        r = min(items, key=lambda r: hashlib.sha256(('policy-iteration-teacher-pilot-v2:' + r['rootId']).encode()).hexdigest())
        pilot.append({k: r[k] for k in fields})
    descriptor = ROOT/'ai/strong/policy-iteration-selected-roots-v2.json'
    protocol = ROOT/'ai/strong/policy-iteration-teacher-protocol-v2.json'
    assert not descriptor.exists() and not protocol.exists(), 'Inspect an existing freeze; never overwrite pins'
    prefix = 'runs/policy-iteration-selected-v2'
    commit = HfApi().upload_folder(repo_id='coyotte508/powergrid-ai-germany-v1', folder_path=out, path_in_repo=prefix,
                                  commit_message='Freeze balanced outcome-blind policy-visited roots with whole-deal validation and no duplicate public/model inputs')
    pin = {'repo': 'coyotte508/powergrid-ai-germany-v1', 'revision': commit.oid, 'prefix': prefix,
           'files': {f.name: digest(f) for f in out.iterdir() if f.is_file()},
           'count': len(rows), 'split_counts': report['split_counts'],
           'selection_protocol_sha256': report['protocol_sha256'], 'qualification_eligible': False}
    write(descriptor, pin)
    old = read(ROOT/'ai/strong/strategic-teacher-training-protocol-v1.json')
    p = {'version': 2, 'purpose': 'Broader paired strategic teacher pilot after regressions on the smaller off-policy data set.',
         'repo': pin['repo'], 'base_source': {k: source[k] for k in ['archive', 'revision', 'sha256']},
         'roots': {**pin, 'file': 'ai/strong/data/policy-iteration-roots-v2.jsonl.gz', 'sha256': pin['files']['roots.jsonl.gz']},
         'model': old['model'], 'ort_threads': 1, 'workers': 24, 'players': [2, 3, 4, 5, 6],
         'behaviors': ['parent', '11101', '11102'], 'opponents': ['economic', 'snapshot0'],
         'modes': ['neural', 'neural_economic'], 'variants': ['original', 'recharged'],
         'decisions': ['nomination', 'bid', 'building'], 'samples': {'probe': 2, 'pilot': 96},
         'batches': ['a', 'b'], 'max_steps': 2400, 'pilot_roots': pilot, 'planned_jobs_per_stage': 60,
         'selection': 'One fixed SHA-ranked selected root per count/behavior/opponent/edition/auction/decision cell. No outcome, policy-disagreement or teacher filtering. Full selected dataset and whole-deal splits remain unchanged.',
         'options': 'Same six-proposal geographic/economic shortlist plus exact frozen parent proposal. Compatible with existing4.3 scope; no unsupported out-of-shortlist targets.',
         'beliefs': 'Use checked public policy-consistent committed sealed bids, with legal passes and the same policy as each continuation mode. No true hidden bids, future deck or real seed.',
         'targets': 'Keep every paired sample and negative or uncertain advantage over parent. Equal continuation-mode mixture, first average matched worlds across modes, then concatenate independent A/B batches into192 world pairs.',
         'admission': 'First run2-sample full-horizon probes at every exact pilot position/mode. Require all60 verified cases before pilot. Sum measured search times, multiply96/2 and2x margin, add300s setup; must fit4h or explicitly version smaller shards. Never shorten horizons.',
         'verification': 'Frozen source, legal proposals, public roots, reencoded parent/bid-policy choices, independent96-world belief traces, full terminal coverage and paired arithmetic. Pilot must reproduce the exact first2 probe trajectories despite larger inference batches/worker offsets.',
         'next': 'Assess pilot label reliability and measured throughput, then separately admit full-data labels and an HF-only training design. This protocol does not train or qualify a candidate.',
         'trained': False, 'qualification_eligible': False, 'final_seeds_used': False}
    write(protocol, p)
    print({'roots': len(rows), 'pilot_roots': len(pilot), 'revision': commit.oid, 'protocol_sha256': digest(protocol)})


if __name__ == '__main__': main()
