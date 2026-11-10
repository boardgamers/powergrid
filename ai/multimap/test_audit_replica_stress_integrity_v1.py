"""OFFLINE synthetic tests, never checkpoint/game/job evaluation evidence.

Run: python3 -B -m unittest discover -s ai/multimap -p test_audit_replica_stress_integrity_v1.py
Private FunctionType bindings isolate fakes; no global monkeypatches, Torch,
network, downloads, real model loads, engine execution or serving imports.
"""
import ast
import copy
from contextlib import nullcontext
import builtins
import os
import shutil
import shlex
import stat
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest

import audit_replica_stress_integrity_v1 as a
import audit_replica_stress_v1 as audit
import audit_neural as neural
from test_audit_replica_stress_v1 import outcome, fixture_snapshot, fixture_provenance, manifest


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(a.canonical(value) + '\n')


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


class FakeRemote:
    def __init__(self, files, prefix=None, *, lfs=False):
        self.files = files
        self.prefix = prefix or 'runs/' + a.GROUP + '-strong/'
        self.api = self
        self.evidence, self.calls = [], []
        self.entries = {}
        for name, raw in files.items():
            pointer = (f'version https://git-lfs.github.com/spec/v1\noid sha256:{a.sha(raw)}\nsize {len(raw)}\n').encode()
            self.entries[name] = NS(path=self.prefix + name, size=len(raw),
                blob_id=git_blob(pointer if lfs else raw), lfs=NS(size=len(raw), sha256=a.sha(raw)) if lfs else None)

    def list_repo_tree(self, *args, **kwargs):
        self.calls.append(('tree', None))
        return list(self.entries.values())

    def describe(self, pin):
        name = pin['path'][len(self.prefix):]
        self.calls.append(('describe', name))
        return self.entries[name]

    def get(self, pin, metadata=None, cached=None):
        name = pin['path'][len(self.prefix):]
        self.calls.append(('get', name))
        if cached is None:
            raise AssertionError('Synthetic tests must supply already retained files')
        raw = Path(cached).read_bytes()
        assert raw == self.files[name]
        assert metadata.size == len(raw)
        assert pin.get('sha256', a.sha(raw)) == a.sha(raw)
        self.evidence.append(dict(path=pin['path'], sha256=a.sha(raw), bytes=len(raw)))
        return Path(cached)


def small_snapshot(root, count=1):
    files = {name: b'{"synthetic":true}\n' for name in
             ('protocol.json', 'status.json', 'environment.json', 'recovery.json', 'study/plan.json')}
    files.update({f'study/batch-{i:03}.json': b'{"synthetic":true}\n' for i in range(count)})
    manifest = {name: a.sha(raw) for name, raw in files.items()}
    files['artifacts.json'] = (a.canonical(manifest) + '\n').encode()
    for name, raw in files.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw)
    return files


def synthetic_log(panel='strong', inherited=0, complete_uploads=2, terminal=True):
    events, uploads = [], []
    def upload(label):
        revision = f'{len(uploads)+1:040x}'
        uploads.append(dict(stage=label, revision=revision))
        events.append(dict(stage='uploaded', label=label, revision=revision))
    upload('runtime-ready')
    groups = audit.expected_batches(panel)
    for i in range(inherited, 640):
        if (i+1) % 16 == 0:
            upload('batches-' + str(i+1))
        events.append(dict(stage='replica-stress-batch', panel=panel, batches=i+1,
                           totalBatches=640, games=sum(len(b) for b in groups[:i+1])))
    for _ in range(complete_uploads):
        upload('complete')
    run = a.GROUP + ('-recovery-' if inherited else '-') + panel
    if terminal:
        events.append(dict(stage='complete', run=run, panel=panel, games=7680, qualified=False))
    status = dict(stage='complete', run=run, receipts=uploads[:-1])
    if inherited:
        status['resume'] = dict(transaction=dict(committedBatches=inherited))
    return events, status, uploads[-1]['revision']


def log_text(events):
    return '\n'.join(a.canonical(e) for e in events) + '\n'


class SafetyTests(unittest.TestCase):
    def test_import_is_standard_library_and_no_side_effect_imports(self):
        code = "import sys; import audit_replica_stress_integrity_v1; assert not any(n in sys.modules for n in ('torch','huggingface_hub','replica_stress_rollout_v1','launch_replica_stress_v1'))"
        subprocess.run([sys.executable, '-B', '-c', code], cwd=a.HERE, check=True)

    def test_helpers_are_authenticated_without_serving_import(self):
        code = "import sys; import audit_replica_stress_integrity_v1 as a; assert set(a.helpers()) == {'audit_replica_stress_v1','audit_neural','audit_gap'}; assert 'torch' not in sys.modules"
        subprocess.run([sys.executable, '-B', '-c', code], cwd=a.HERE, check=True)

    def test_source_and_preflight_frozen_git_bytes(self):
        for name in (*a.SOURCE_NAMES, 'replica-stress-preflight-v1.json'):
            self.assertEqual((a.HERE/name).read_bytes(), a.git_bytes('ai/multimap/' + name, a.SOURCE))

    def test_private_binding_preserves_old_globals_and_default(self):
        old = dict(neural.verify_source.__globals__)
        f = a.source_verifier(neural, {'sourceFiles': {'x': 'a'*64}})
        self.assertIsNot(f.__globals__, neural.verify_source.__globals__)
        self.assertEqual(neural.LIMIT, 128*1024**2)
        self.assertEqual(f.__globals__['LIMIT'], 256*1024**2-1)
        self.assertEqual(f.__globals__['SOURCE'], a.SOURCE)
        self.assertEqual(old, neural.verify_source.__globals__)
        self.assertEqual(f.__globals__['git_bytes']('ai/multimap/audit_neural.py'), a.git_bytes('ai/multimap/audit_neural.py', a.SOURCE))

    def test_source_expanded_boundary_and_old_limit_unchanged(self):
        f = a.source_verifier(neural, {'sourceFiles': {}})
        cap = f.__globals__['LIMIT']
        self.assertTrue(137556136 <= cap)
        self.assertFalse(256*1024**2 <= cap)
        self.assertGreater(137556136, neural.LIMIT)

    def test_private_expansion_guard_executes_old_code_with_only_new_bound(self):
        class FakeTar:
            def __init__(self,size):self.size=size
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def getmembers(self):return [NS(name='source-manifest.json',size=self.size,isfile=lambda:True,isdir=lambda:False)]
            def extractfile(self,*args):raise RuntimeError('past-expanded-budget')
        def fake_tar(size):return NS(open=lambda *args:FakeTar(size))
        private=a.bind(a.source_verifier(neural,{'sourceFiles':{}}),tarfile=fake_tar(137556136))
        with self.assertRaisesRegex(RuntimeError,'past-expanded-budget'):private('synthetic',{})
        old=a.bind(neural.verify_source,tarfile=fake_tar(137556136))
        with self.assertRaisesRegex(ValueError,'expanded byte budget'):old('synthetic',{})
        too_large=a.bind(private,tarfile=fake_tar(256*1024**2))
        with self.assertRaisesRegex(ValueError,'expanded byte budget'):too_large('synthetic',{})
        self.assertEqual(neural.LIMIT,128*1024**2)

    def test_fresh_runtime_import_guard_only_authenticates_without_importing(self):
        code = "import sys; import audit_replica_stress_integrity_v1 as a; a.runtime_import_guard(); assert 'torch' not in sys.modules; assert 'replica_stress_study_v1' not in sys.modules"
        subprocess.run([sys.executable, '-B', '-c', code], cwd=a.HERE, check=True)
        blocked=a.bind(a.runtime_import_guard,sys=NS(modules={'data':object()}))
        with self.assertRaisesRegex(ValueError,'preloaded serving module'):blocked()

    def test_preflight_download_gate(self):
        with self.assertRaisesRegex(ValueError,'allow-download'):a.fetch_preflight('/must-not-exist')

    def test_exact_nonserving_exceptions_only(self):
        for name in ('README.md', 'runs.json', 'replica-stress-v1-design.md'):
            self.assertTrue(a.local_source_difference('ai/multimap/'+name, 'a', 'b'))
        for name in ('launch.py', 'expert-replicas-v1-design.md', 'replica_stress_study_v1.py'):
            with self.assertRaises(ValueError):
                a.local_source_difference('ai/multimap/'+name, 'a', 'b')

    def test_fetch_gate_precedes_helpers_network_and_writes(self):
        with self.assertRaisesRegex(ValueError, 'allow-download'):
            a.fetch_panel('strong', 'a'*40, '/must-not-exist')

    def test_replay_gate_precedes_session_models_games(self):
        with self.assertRaisesRegex(ValueError, 'allow-games'):
            a.replay_panel(None, 'strong')

    def test_finalizer_cannot_accept_json_attestation(self):
        with self.assertRaisesRegex(ValueError, 'Live verified session'):
            a.finalize_receipts({'checks': dict.fromkeys(audit.EXTERNAL_CHECKS, True)})

    def test_both_panels_required_before_network(self):
        with self.assertRaisesRegex(ValueError, 'Both panels'):
            a.verify_integrity({'strong': '.'}, {'strong': 'a'*40}, '.')

    def test_canonical_ledger_default_and_explicit_original_only(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);original=root/'ai/runs'/a.GROUP;original.mkdir(parents=True)
            fixed=a.bind(a.canonical_ledger,ROOT=root)
            self.assertEqual(fixed(),original)
            self.assertEqual(fixed(original),original)
            for other in (root/'copy',original/'nested',original.parent):
                with self.subTest(path=other),self.assertRaisesRegex(ValueError,'Canonical original paid-job ledger'):
                    fixed(other)
            link=root/'alias';link.symlink_to(original,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Symlink'):fixed(link)
            with self.assertRaisesRegex(ValueError,'Parent traversal'):fixed(original/'..'/a.GROUP)

    def test_all_proof_entrypoints_reject_relocated_ledger_before_side_effects(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);relocated=root/'ledger';output=root/'reports'
            roots={p:root/p for p in a.PANELS};revisions=dict.fromkeys(a.PANELS,'a'*40)
            for action in (
                    lambda:a.verify_integrity(roots,revisions,output,ledger=relocated),
                    lambda:a.verify_owner(None,None,relocated,None,None),
                    lambda:a.verify_jobs(None,relocated,roots,{},None,None,None,None,output,None)):
                with self.assertRaisesRegex(ValueError,'Canonical original paid-job ledger'):action()
                self.assertFalse(output.exists())
                self.assertFalse(relocated.exists())

    def test_no_global_monkeypatch_or_expected_projection_assignment(self):
        tree = ast.parse(Path(a.__file__).read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertFalse(any(isinstance(c.func, ast.Attribute) and c.func.attr in ('run_job', 'create_commit', 'snapshot_download') for c in calls))
        self.assertFalse(any(isinstance(n, ast.Global) for n in ast.walk(tree)))
        for n in ast.walk(tree):
            if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant):
                self.assertNotEqual(n.slice.value, 'expectedModelProjection')

    def test_duplicate_nonfinite_json_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":1e999}'):
            with self.assertRaises(ValueError):
                a.decode_json(raw)

    def test_safe_names(self):
        for name in ('../x', '/x', 'x//y', 'x/./y', 'x\\y', '.'):
            with self.assertRaises(ValueError):
                a.safe_name(name)

    def test_parent_aliases_rejected_for_output_ledger_reference_cache_and_inputs(self):
        runs=a.ROOT/'ai/runs';strong=runs/(a.GROUP+'-strong')
        aliases=[strong/'..'/a.GROUP/'audit-review-probe',
                 strong/'..'/'multimap-reference-preflight-v1/artifact/audit-review-probe',
                 strong/'..'/(a.GROUP+'-integrity-attempts-v1')/'probe']
        for path in aliases:
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'Parent traversal'):
                a.protect_output(path)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'child').mkdir();write(root/'payload.json',{'synthetic':True})
            alias=root/'child/../payload.json'
            for action in (lambda:a.read(alias),lambda:a.write_new(alias,{}),
                           lambda:a.cache_file(alias),lambda:a.cache_file(root/'payload.json',root/'child/..'),
                           lambda:a.ledger_attempts(root/'child/..'),lambda:a.protect_output(root/'out',alias)):
                with self.assertRaisesRegex(ValueError,'Parent traversal'):action()
            for kw in ({'ledger':root/'child/..'},{'preflight_root':root/'child/..'},
                       {'local_checkpoints':{'expert24':alias}},{'original_roots':{'strong':root/'child/..'}}):
                with self.assertRaisesRegex(ValueError,'Parent traversal'):
                    a.verify_integrity({p:root/p for p in a.PANELS},dict.fromkeys(a.PANELS,'a'*40),root/'out',**kw)
                self.assertFalse((root/'out').exists())
            with self.assertRaisesRegex(ValueError,'Parent traversal'):
                a.verify_integrity({'strong':root/'child/../strong','mixed':root/'mixed'},
                                   dict.fromkeys(a.PANELS,'a'*40),root/'out')

    def test_durable_exclusive_file_and_directory_fsync(self):
        with tempfile.TemporaryDirectory() as t:
            calls=[]
            def fsync(fd):calls.append(fd);os.fsync(fd)
            private=a.bind(a.durable_new,os=NS(**dict(vars(os),fsync=fsync)))
            path=Path(t)/'attempts/strong.intent.json'
            checksum=private(path,{'syntheticOnly':True})
            self.assertEqual(len(calls),3)  # file, attempt directory, directory parent
            self.assertEqual(checksum,a.digest(path))
            with self.assertRaises(FileExistsError):private(path,{'syntheticOnly':True})
            self.assertEqual(len(calls),3)

    def test_fixed_attempt_authority_cannot_overlap_report(self):
        for output in (a.ATTEMPT_ROOT,a.ATTEMPT_ROOT/'report',a.ATTEMPT_ROOT.parent):
            with self.assertRaisesRegex(ValueError,'overlap'):a.protect_output(output)

    def test_symlink_ancestor_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root/'real').mkdir(); (root/'link').symlink_to(root/'real', target_is_directory=True)
            with self.assertRaises(ValueError):
                a.no_links(root/'link/x')

    def test_legitimate_hf_cache_link_and_escape(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); (root/'snapshots/r').mkdir(parents=True); (root/'blobs').mkdir()
            (root/'blobs/b').write_text('payload'); (root/'snapshots/r/a').symlink_to(root/'blobs/b')
            self.assertEqual(a.cache_file(root/'snapshots/r/a', root), root/'blobs/b')
            with self.assertRaises(ValueError): a.cache_file(root/'snapshots/r/a')
            (root/'snapshots/r/a').unlink(); (root/'outside').write_text('no')
            (root/'snapshots/r/a').symlink_to(root/'outside')
            with self.assertRaises(ValueError): a.cache_file(root/'snapshots/r/a', root)

    def test_authenticated_source_rejects_valid_header_tampered_bytecode(self):
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'module.py';raw=b'answer = 42\n';source.write_bytes(raw)
            cache=Path(a.importlib.util.cache_from_source(str(source)));cache.parent.mkdir()
            header=a.importlib.util.MAGIC_NUMBER+(0).to_bytes(4,'little')+int(source.stat().st_mtime).to_bytes(4,'little')+len(raw).to_bytes(4,'little')
            cache.write_bytes(header+a.marshal.dumps(compile(raw,str(source),'exec')))
            a.authenticate_bytecode(source,raw)
            cache.write_bytes(header+a.marshal.dumps(compile('answer = 41',str(source),'exec')))
            with self.assertRaisesRegex(ValueError,'bytecode differs'):a.authenticate_bytecode(source,raw)

    def test_private_helpers_bypass_preloaded_module_namespaces(self):
        h=a.helpers()
        self.assertIsNot(h['audit_replica_stress_v1'],audit)
        self.assertIsNot(h['audit_neural'],neural)
        self.assertIsNot(h['audit_neural'].verify_source.__globals__,neural.verify_source.__globals__)

    def test_output_cannot_contaminate_retained_reference_or_ledger(self):
        for path in (a.ROOT/'ai/runs/multimap-reference-preflight-v1/artifact/new-audit',
                     a.ROOT/'ai/.venv', a.ROOT/'ai/runs'/a.GROUP/'audit',
                     a.ROOT/'ai/runs'/(a.GROUP+'-preflight')):
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'Output must not overlap'):
                a.protect_output(path)

    def test_write_new_retains_failure_evidence(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)/'evidence.json'; digest = a.write_new(p, {'failed': True})
            self.assertEqual(a.write_new(p, {'failed': True}), digest)
            with self.assertRaises(ValueError): a.write_new(p, {'failed': False})

    def test_public_records_pin_historical_and_decoder(self):
        records, hashes = a.public_records()
        self.assertEqual(records['peer']['git'], a.PEER_GIT)
        self.assertIn('ai/multimap/expert-replicas-results-v1.json', hashes)
        self.assertEqual(a.sha(a.authenticate_file('reconcile_replica_stress_jobs_v1.py', a.DECODER_GIT)), a.DECODER_SHA)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)/'panel'
        self.files = small_snapshot(self.root); self.remote = FakeRemote(self.files)
    def tearDown(self): self.temp.cleanup()
    def auth(self): return a.authenticate_snapshot('strong', 'a'*40, self.root, self.remote)

    def test_metadata_first_all_members(self):
        result = self.auth()
        self.assertFalse(result['complete'])
        first_get = next(i for i,c in enumerate(self.remote.calls) if c[0] == 'get')
        self.assertEqual(sum(c[0] == 'describe' for c in self.remote.calls[:first_get]), len(self.files))
        self.assertEqual(result['files']['artifacts.json'], a.digest(self.root/'artifacts.json'))

    def test_full_snapshot_member_count(self):
        manifest = {n:'a'*64 for n in ('protocol.json','status.json','environment.json','recovery.json','study/plan.json','study/summary.json')}
        manifest.update({f'study/batch-{i:03}.json':'a'*64 for i in range(640)})
        self.assertEqual(len(a.manifest_names(manifest)), 640)
        self.assertEqual(len(manifest)+1, 647)

    def test_lfs_metadata_content_pointer_verified(self):
        self.remote = FakeRemote(self.files, lfs=True)
        self.assertEqual(self.auth()['batches'], 1)

    def test_bad_lfs_pointer_before_get(self):
        self.remote = FakeRemote(self.files, lfs=True)
        self.remote.entries['status.json'].blob_id = 'a'*40
        with self.assertRaises(ValueError): self.auth()
        self.assertFalse(any(c[0] == 'get' for c in self.remote.calls))

    def test_remote_aggregate_before_get(self):
        for e in self.remote.entries.values(): e.size = a.FILE_LIMIT
        with self.assertRaises(ValueError): self.auth()
        self.assertFalse(any(c[0] == 'get' for c in self.remote.calls))

    def test_manifest_cap_before_get(self):
        self.remote.entries['artifacts.json'].size = a.MANIFEST_LIMIT+1
        with self.assertRaises(ValueError): self.auth()
        self.assertFalse(any(c[0] == 'get' for c in self.remote.calls))

    def test_noninteger_size(self):
        self.remote.entries['status.json'].size = True
        with self.assertRaises(ValueError): self.auth()

    def test_prefix_escape(self):
        self.remote.entries['status.json'].path = 'outside/status.json'
        with self.assertRaises(ValueError): self.auth()

    def test_unknown_remote_member(self):
        self.remote.entries['evil'] = NS(path=self.remote.prefix+'evil', size=1, blob_id='a'*40, lfs=None)
        with self.assertRaisesRegex(ValueError, 'Exact remote inventory'): self.auth()

    def test_duplicate_remote_member(self):
        self.remote.entries['evil'] = self.remote.entries['status.json']
        with self.assertRaisesRegex(ValueError, 'duplicate'): self.auth()

    def test_local_tmp_rejected(self):
        (self.root/'study/batch-001.json.tmp').write_text('{}')
        with self.assertRaises(ValueError): self.auth()

    def test_local_link_rejected(self):
        (self.root/'status.json').unlink(); (self.root/'status.json').symlink_to(self.root/'protocol.json')
        with self.assertRaises(ValueError): self.auth()

    def test_no_missing_local_download_fallback(self):
        (self.root/'status.json').unlink()
        with self.assertRaisesRegex(ValueError, 'explicit fetch'): self.auth()

    def test_noncontiguous_manifest(self):
        m = a.read(self.root/'artifacts.json'); m['study/batch-002.json'] = m.pop('study/batch-000.json')
        with self.assertRaisesRegex(ValueError, 'Noncontiguous'): a.manifest_names(m)

    def test_premature_summary(self):
        m = a.read(self.root/'artifacts.json'); m['study/summary.json'] = 'a'*64
        with self.assertRaises(ValueError): a.manifest_names(m)


class ProjectionTests(unittest.TestCase):
    def saved(self, name='replica1'):
        expert = name in a.EXPERTS
        config = fixture_provenance()[name]['checkpointConfig' if name == 'ppo0' else 'config']
        saved = dict(schema='multimap-expert-ppo-v2' if expert else 'multimap-residual-ppo-v1', width=64,
                     bound=16 if expert else 8, update=audit.MODEL_PINS[name]['update'], config=config, state_dict={'synthetic': 1})
        if expert: saved.update(stage='train', priorAsActionFeature=True)
        return saved, config

    def test_projection_from_actual_decoded_fields(self):
        for role in a.MODELS:
            saved, config = self.saved(role)
            result = a.checkpoint_projection(saved, audit.MODEL_PINS[role], config, expert=role in a.EXPERTS)
            self.assertEqual(result['configSha256'], a.object_sha(saved['config']))
            self.assertEqual(result['update'], saved['update'])
            self.assertNotIn('state_dict', result)

    def test_ppo0_historical_saved_hash_not_current(self):
        saved, config = self.saved('ppo0'); provenance = fixture_provenance()
        result = a.checkpoint_projection(saved, audit.MODEL_PINS['ppo0'], config, expert=False)
        self.assertNotEqual(result['configSha256'], a.object_sha(provenance['ppo0']['config']))
        a.verify_historical(audit, provenance)

    def test_historical_exception_cannot_change_protocol(self):
        p = fixture_provenance(); p['ppo0']['checkpointConfig']['protocol']['changed'] = True
        with self.assertRaises(ValueError): a.verify_historical(audit, p)

    def test_historical_sources_cannot_change_third_file(self):
        p = fixture_provenance(); p['ppo0']['config']['sourceFiles']['data.py'] = 'a'*64
        with self.assertRaises(ValueError): a.verify_historical(audit, p)

    def test_architecture_update_flags_types_and_extra_keys(self):
        for key, value in [('width',True), ('bound',8), ('update',32), ('stage','warmup'),
                           ('priorAsActionFeature',1), ('optimizer',{})]:
            saved, config = self.saved(); saved[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                a.checkpoint_projection(saved, audit.MODEL_PINS['replica1'], config, expert=True)

    def test_full_saved_config_not_subset(self):
        saved, config = self.saved(); saved['config'] = dict(config, extra='forbidden')
        with self.assertRaises(ValueError): a.checkpoint_projection(saved, audit.MODEL_PINS['replica1'], config, expert=True)

    def test_all_six_metadata_precede_model_payloads(self):
        calls = []
        remote = NS(describe=lambda pin: (calls.append(pin['name']) or NS(size=a.FILE_LIMIT+1)),
                    get=lambda *args, **kwargs: self.fail('payload before all metadata bounds'))
        with tempfile.TemporaryDirectory() as directory:
            paths = {name: Path(directory) / (name + '.pt') for name in a.EXPERTS}
            for path in paths.values():
                path.write_bytes(b'offline placeholder; never decoded')
            before = set(sys.modules)
            with self.assertRaisesRegex(ValueError, 'Six-model metadata byte limits'):
                a.decode_models(remote, audit, fixture_provenance(), local_checkpoints=paths)
            self.assertEqual(calls, list(a.MODELS))
            self.assertEqual(set(sys.modules) - before, set(), 'No new imports before all six metadata bounds')

    def test_local_ppo_override_forbidden_before_network(self):
        with self.assertRaises(ValueError): a.decode_models(None, audit, {}, {'ppo0':'no'})


class JobsLogsRecoveryTests(unittest.TestCase):
    def test_allowlisted_chronology_omits_secrets(self):
        value = a.chronology(dict(createdAt='2026-11-09T22:51:54Z', startedAt='2026-11-09T22:51:59Z', finishedAt=None, secrets={'token':'NEVER'}))
        self.assertEqual(set(value), {'createdAt','startedAt','finishedAt'})
        self.assertNotIn('NEVER', a.canonical(value))

    def test_chronology_rejects_naive_missing_and_inverted(self):
        for raw in ({}, {'createdAt':'2026-01-01T00:00:00'},
                    dict(createdAt='2026-01-02T00:00:00Z',startedAt='2026-01-01T00:00:00Z')):
            with self.assertRaises(ValueError): a.chronology(raw)

    def test_unknown_intent_consumes_hours(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            for slot in a.HOURS: write(root/'intents'/f'{slot}.json', {'slot':slot})
            report, _, _ = a.ledger_attempts(root)
            self.assertEqual(report['requestedHours'],12)
            self.assertEqual(report['unknownSlots'], list(a.HOURS))

    def test_unknown_extra_slot_and_receipt_without_intent(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); write(root/'receipts/strong.json', {})
            with self.assertRaises(ValueError): a.ledger_attempts(root)
            (root/'receipts/strong.json').unlink(); write(root/'intents/extra.json', {})
            with self.assertRaises(ValueError): a.ledger_attempts(root)

    def test_source_proves_no_startup_tests(self):
        proof = a.startup_source_proof()
        self.assertIs(proof['startupTestsInvoked'], False)

    def test_normal_two_complete_uploads_and_lag(self):
        events, status, rev = synthetic_log()
        report = a.verify_log(log_text(events), 'strong', status, rev, 'COMPLETED', audit)
        self.assertEqual(report['generatedBatches'],640)
        self.assertEqual(sum(u['stage']=='complete' for u in report['uploads']),2)
        self.assertFalse(report['terminalFailure'])

    def test_resume_log_starts_after_inherited_prefix(self):
        events, status, rev = synthetic_log(inherited=32)
        result = a.verify_log(log_text(events), 'strong', status, rev, 'COMPLETED', audit)
        self.assertEqual(result['generatedBatches'],608)

    def test_complete_output_after_error_first_upload_honest(self):
        events, status, rev = synthetic_log(complete_uploads=1,terminal=False)
        report = a.verify_log(log_text(events), 'strong', status, rev, 'ERROR', audit)
        self.assertTrue(report['terminalFailure'])
        with self.assertRaises(ValueError): a.verify_log(log_text(events), 'strong', status, rev, 'COMPLETED', audit)

    def test_nonterminal_cannot_pass(self):
        events, status, rev = synthetic_log()
        with self.assertRaises(ValueError): a.verify_log(log_text(events), 'strong', status, rev, 'RUNNING', audit)

    def test_fake_python_boundary_rejected_for_new_worker(self):
        events, status, rev = synthetic_log()
        with self.assertRaises(ValueError):
            a.verify_log('Ran 45 tests in 1s\n\nOK\n'+log_text(events),'strong',status,rev,'COMPLETED',audit)

    def test_generic_legacy_boundary_requires_both_successful_suites(self):
        fake = '{"stage":"uploaded","label":"runtime-ready","revision":"'+ 'b'*40 +'"}\n'
        with self.assertRaises(ValueError): a.production_events(fake, startup_suite={'python':2,'node':3})
        boundary = '# tests 3\n# pass 3\n# fail 0\nRan 2 tests in 1.0s\n\nOK\n'
        self.assertEqual(len(a.production_events(fake+boundary+fake,startup_suite={'python':2,'node':3})),1)

    def test_wrong_counts_order_duplicate_runtime_and_optimization(self):
        for edit in ('games','order','ready','training'):
            events,status,rev=synthetic_log()
            if edit=='games': events[1]['games']+=1
            if edit=='order': events[1],events[2]=events[2],events[1]
            if edit=='ready': events.insert(1,copy.deepcopy(events[0]))
            if edit=='training': events.insert(1,dict(stage='expert-ppo',update=1))
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                a.verify_log(log_text(events),'strong',status,rev,'COMPLETED',audit)

    def test_status_cannot_contain_own_current_upload_revision(self):
        events,status,rev=synthetic_log(); status['receipts'].append(dict(stage='complete',revision=rev))
        with self.assertRaises(ValueError): a.verify_log(log_text(events),'strong',status,rev,'COMPLETED',audit)

    def jobs(self):
        initial={p:dict(stage='ERROR',message='Job timeout',finishedAt='2026-11-10T02:00:00Z') for p in a.PANELS}
        audits={p:dict(transaction=dict(complete=False)) for p in a.PANELS}
        return initial,audits

    def test_fixed_strong_priority(self):
        jobs,audits=self.jobs()
        self.assertEqual(a.recovery_choice(jobs,audits,'2026-11-10T03:00:00Z'),('strong',['mixed']))

    def test_complete_error_never_replayed(self):
        jobs,audits=self.jobs();audits['strong']['transaction']['complete']=True
        self.assertEqual(a.recovery_choice(jobs,audits,'2026-11-10T03:00:00Z'),('mixed',[]))
        audits['mixed']['transaction']['complete']=True
        with self.assertRaises(ValueError): a.recovery_choice(jobs,audits,'2026-11-10T03:00:00Z')

    def test_recovery_before_both_terminal_rejected(self):
        jobs,audits=self.jobs();jobs['mixed']['stage']='RUNNING'
        with self.assertRaises(ValueError): a.recovery_choice(jobs,audits,'2026-11-10T03:00:00Z')
        jobs['mixed']['stage']='ERROR';jobs['mixed']['finishedAt']='2026-11-10T04:00:00Z'
        with self.assertRaises(ValueError): a.recovery_choice(jobs,audits,'2026-11-10T03:00:00Z')

    def test_non_timeout_incomplete_rejected(self):
        jobs,audits=self.jobs();jobs['mixed']['message']='different'
        with self.assertRaises(ValueError): a.recovery_choice(jobs,audits,'2026-11-10T03:00:00Z')

    def test_inherited_raw_timing_changes_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            old,final=Path(t)/'old',Path(t)/'final';small_snapshot(old);small_snapshot(final)
            m=a.read(old/'artifacts.json');transaction=dict(committedBatches=1,complete=False,planSha256=m['study/plan.json'])
            self.assertEqual(len(a.verify_inherited(old,final,m,m,transaction)),2)
            (final/'study/batch-000.json').write_text('{"seconds":2}')
            with self.assertRaisesRegex(ValueError,'RAW bytes'): a.verify_inherited(old,final,m,m,transaction)


def source_functions(filename, names, namespace, constants=()):
    """Execute selected AUTHENTICATED pure source guards, no serving imports."""
    tree=ast.parse(a.authenticate_file(filename))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or
           isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets)]
    namespace=dict(namespace)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<authenticated-offline-guards:'+filename+'>','exec'),namespace)
    return NS(**namespace)


def source_launcher():
    peer=a.decode_json(a.authenticate_file('replica-stress-peer-v1.json',a.PEER_GIT))
    ns=dict(vars(a),MODEL=a.REPO,NAMESPACE='coyotte508',STAGE='replica-stress-v1',SCHEMA='multimap-replica-stress-launch-v1',
        IMAGE=peer['records']['strong']['image'],BUDGET=audit.protocol()['jobBudget'],shlex=shlex,
        THREAD_ENV=('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'),
        immutable_revision=a.immutable,LAUNCHER_NAME='ai/multimap/launch_replica_stress_v1.py')
    return source_functions('launch_replica_stress_v1.py',
        {'coordinator','reservation_for','inventory','validate_inventory','validate_job','slot','labels_for',
         'env_for','intent_for','original_command','command_for'},ns)


class ProofIntegrationTests(unittest.TestCase):
    """Full new job/owner proofs with canonical temporary fixtures + fake transport.

    No assertion about the real running jobs: these terminal metadata/logs are
    SYNTHETIC. Frozen inventory/6+3+shared3 validation is executed, not stubbed.
    """
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.directory=self.base/'ai/runs'/a.GROUP
        self.directory.mkdir(parents=True);self.launch=source_launcher()
        # Only tracked immutable records are fixture inputs. A fresh checkout has
        # no private/ignored paid-job ledger; never read or alter the live one.
        peer=a.decode_json(a.authenticate_file('replica-stress-peer-v1.json',a.PEER_GIT))
        self.source=peer['source'];self.receipts=peer['records']
        write(self.directory/'source.json',self.source)
        intent={k:self.source[k] for k in ('schema','group','sourcePath','reservationOwner',
            'reservationPath','sourceParentRevision','preflightSha256')}
        intent.update(coordinator=self.launch.coordinator(self.directory),jobBudget=self.launch.BUDGET)
        write(self.directory/'intent.json',intent)
        write(self.directory/'reservation.json',self.launch.reservation_for(self.source))
        for panel,receipt in self.receipts.items():
            write(self.directory/'receipts'/f'{panel}.json',receipt)
            self.assertEqual(a.digest(self.directory/'receipts'/f'{panel}.json'),peer['durableReceiptSha256'][panel])
            write(self.directory/'intents'/f'{panel}.json',{k:v for k,v in receipt.items() if k not in ('jobId','url')})
        self.roots={p:self.base/p for p in a.PANELS};self.snapshots={};self.logs={};self.raw={}
        command=self.launch.original_command(a.SOURCE)[0]
        for p,r in self.receipts.items():
            for filename,kind in (('intent.json','intents'),('launch.json','receipts')):
                dst=self.base/'ai/runs'/r['run']/filename;dst.parent.mkdir(parents=True,exist_ok=True)
                dst.write_bytes((self.directory/kind/(p+'.json')).read_bytes())
            events,status,revision=synthetic_log(p)
            status.update(panel=p,slot=p,**{k:self.source[k] for k in
                ('sourceRepo','sourceRevision','sourcePath','sourceCommit','sourceSha256')})
            write(self.roots[p]/'status.json',status)
            self.snapshots[p]=dict(segment=1,revision=revision)
            self.logs[r['jobId']]=log_text(events).splitlines()
            created='2026-11-09T22:52:00Z' if p=='strong' else '2026-11-09T23:18:00Z'
            self.raw[r['jobId']]=dict(id=r['jobId'],environment=r['env'],dockerImage=r['image'],flavor=r['flavor'],
                command=command,arguments=[],volumes=[],spaceId=None,timeout=a.HOURS[p]*3600,
                expose={'ports':[]},ssh={'enabled':False},labels=dict(self.launch.labels_for(a.GROUP,p,1,p),name=r['run']),
                status=dict(stage='COMPLETED',message=None),createdAt=created,startedAt=created,finishedAt='2026-11-10T06:00:00Z')
        self.private=True;self.parent_paths=[]
        self.api=NS(repo_info=lambda *args,**kw:NS(private=self.private,sha='f'*40),
            get_paths_info=lambda *args,**kw:self.parent_paths,
            list_repo_commits=lambda repo,revision,**kw:[NS(commit_id=revision,created_at='2026-11-09T22:50:00Z')],
            list_jobs=lambda **kw:[NS(id=jid) for jid in self.raw],
            fetch_job_logs=lambda job_id,**kw:self.logs[job_id])
        self.remotes=[]
        def remote_factory():
            remote=FakeRemote({'reservation.json':(self.directory/'reservation.json').read_bytes()},prefix='multimap/'+a.GROUP+'/')
            self.remotes.append(remote);return remote
        self.remote_factory=remote_factory
        self.decoder=isolated_decoder()
        def inspect(api,jid,decoder):return decoder.decode_actual(self.raw[jid]),a.chronology(self.raw[jid])
        git=NS(check_output=lambda command,**kw:subprocess.check_output(command,**dict(kw,cwd=a.ROOT)))
        # A private original ROOT, not an override accepting arbitrary ledgers.
        self.canonical_ledger=a.bind(a.canonical_ledger,ROOT=self.base)
        self.verify_owner=a.bind(a.verify_owner,canonical_ledger=self.canonical_ledger)
        self.verify=a.bind(a.verify_jobs,ROOT=self.base,canonical_ledger=self.canonical_ledger,
                           verify_owner=self.verify_owner,inspect_with_chronology=inspect,subprocess=git)

    def run_proof(self):
        return self.verify(self.api,self.directory,self.roots,self.snapshots,self.source,self.launch,self.decoder,audit,
                           self.base/'reports',self.remote_factory)

    def test_full_verify_jobs_pinned_records_owner_and_six_plus_three(self):
        report=self.run_proof()
        self.assertEqual(report['actualRequestedHours'],9)
        self.assertEqual(report['attempts']['requestedHours'],9)
        self.assertEqual(report['attempts']['unknownSlots'],[])
        self.assertEqual(report['groupInventoryIds'],sorted(a.INITIAL_IDS.values()))
        self.assertFalse(report['recovery']['exercised'])
        self.assertEqual(report['owner']['reservation']['owner'],self.source['reservationOwner'])
        self.assertEqual(set(report['publicRecords']),{'launch','reconciliation','peer'})
        self.assertTrue(all(r['generatedBatches']==640 for r in report['logs'].values()))
        self.assertFalse((self.base/'reports/external-integrity.json').exists())

    def test_full_verify_jobs_retains_unknown_shared_slot_before_attestation(self):
        write(self.directory/'intents/recovery.json',{'syntheticUnknown':True})
        with self.assertRaisesRegex(ValueError,'Unknown attempts'):self.run_proof()
        attempted=a.read(self.base/'reports/attempted-slots.json')
        self.assertEqual(attempted['requestedHours'],12)
        self.assertEqual(attempted['unknownSlots'],['recovery'])
        self.assertTrue((self.base/'reports/observed-inventory.json').is_file())

    def test_copied_rebound_ledger_cannot_hide_unknown_recovery_with_empty_remote_slot(self):
        # Only this tracked-record TEMPORARY fixture is copied; never ai/runs.
        write(self.directory/'intents/recovery.json',{'syntheticUnknown':True})
        with self.assertRaisesRegex(ValueError,'Unknown attempts'):self.run_proof()
        original=a.read(self.base/'reports/attempted-slots.json')
        self.assertEqual((original['requestedHours'],original['unknownSlots']),(12,['recovery']))
        self.assertEqual(sorted(self.raw),sorted(a.INITIAL_IDS.values()))  # no recovery job visible
        copied=self.base/'copied-ledger'
        shutil.copytree(self.directory,copied,ignore=lambda root,names:['recovery.json'])
        intent=a.read(copied/'intent.json')
        intent['coordinator']=self.launch.coordinator(copied);write(copied/'intent.json',intent)
        self.assertEqual(a.read(copied/'intent.json')['coordinator'],self.launch.coordinator(copied))
        self.assertNotEqual(intent['coordinator'],self.launch.coordinator(self.directory))
        omitted=a.ledger_attempts(copied)[0]
        self.assertEqual((omitted['requestedHours'],omitted['unknownSlots']),(9,[]))
        # The old frozen validator accepts the copied 9h view, so the new guard
        # must reject the path, independently of coordinator and remote inventory.
        jobs=[self.decoder.decode_actual(raw) for raw in self.raw.values()]
        self.launch.validate_inventory(jobs,copied,self.source,self.launch.original_command(a.SOURCE)[0])
        self.verify_owner(self.api,self.remote_factory(),self.directory,self.source,self.launch)
        with self.assertRaisesRegex(ValueError,'Canonical original paid-job ledger'):
            self.verify_owner(self.api,self.remote_factory(),copied,self.source,self.launch)
        with self.assertRaisesRegex(ValueError,'Canonical original paid-job ledger'):
            self.verify(self.api,copied,self.roots,self.snapshots,self.source,self.launch,self.decoder,audit,
                        self.base/'copied-reports',self.remote_factory)
        self.assertFalse((self.base/'copied-reports').exists())
        with self.assertRaisesRegex(ValueError,'Unknown attempts'):self.run_proof()

    def test_actual_wrong_hours_and_extra_inventory_do_not_pass_receipt_claims(self):
        self.raw[a.INITIAL_IDS['strong']]['timeout']=10800
        with self.assertRaisesRegex(ValueError,'config/hours'):self.run_proof()

    def test_real_frozen_validator_counts_six_plus_three_plus_one_shared_three(self):
        run=a.GROUP+'-recovery-strong'
        intent=self.launch.intent_for(self.source,'strong',2,run,resumeRevision='a'*40)
        receipt=dict(intent,jobId='synthetic-recovery',url='https://huggingface.co/jobs/coyotte508/synthetic-recovery')
        write(self.directory/'intents/recovery.json',intent);write(self.directory/'receipts/recovery.json',receipt)
        raw=copy.deepcopy(self.raw[a.INITIAL_IDS['mixed']])
        raw.update(id=receipt['jobId'],environment=receipt['env'],
                   labels=dict(self.launch.labels_for(a.GROUP,'strong',2,'recovery'),name=run))
        jobs=[self.decoder.decode_actual(value) for value in (*self.raw.values(),raw)]
        command=self.launch.original_command(a.SOURCE)[0]
        self.launch.validate_inventory(jobs,self.directory,self.source,command)
        self.assertEqual(sum(j.timeout_seconds for j in jobs),12*3600)
        jobs[-1].timeout_seconds=4*3600
        with self.assertRaisesRegex(ValueError,'config/hours'):
            self.launch.validate_inventory(jobs,self.directory,self.source,command)

    def test_pinned_receipt_bytes_cannot_be_reserialized(self):
        path=self.directory/'receipts/mixed.json';value=a.read(path);path.write_text(json.dumps(value,indent=4)+'\n')
        self.assertEqual(value,self.receipts['mixed'])
        with self.assertRaisesRegex(ValueError,'receipt byte hash'):self.run_proof()

    def test_unrecorded_inventory_job_is_not_ignored(self):
        raw=copy.deepcopy(self.raw[a.INITIAL_IDS['mixed']]);raw['id']='extra'
        self.raw['extra']=raw
        with self.assertRaisesRegex(ValueError,'Duplicate remote budget slot'):self.run_proof()

    def test_verify_owner_direct_cas_pins_and_remote_absence(self):
        report=self.verify_owner(self.api,self.remote_factory(),self.directory,self.source,self.launch)
        self.assertTrue(report['parentPathsAbsent'])
        self.assertEqual(len(report['remoteEvidence']),2)
        self.parent_paths=[NS(path=self.source['sourcePath'])]
        with self.assertRaisesRegex(ValueError,'absent at original CAS parent'):
            self.verify_owner(self.api,self.remote_factory(),self.directory,self.source,self.launch)

    def test_verify_owner_direct_copied_coordinator_and_owner_tamper(self):
        path=self.directory/'intent.json';value=a.read(path);value['coordinator']['inode']+=1;write(path,value)
        with self.assertRaisesRegex(ValueError,'coordinator identity'):
            self.verify_owner(self.api,self.remote_factory(),self.directory,self.source,self.launch)
        value['coordinator']=self.launch.coordinator(self.directory);value['reservationOwner']='b'*32;write(path,value)
        with self.assertRaisesRegex(ValueError,'reservation coordinator'):
            self.verify_owner(self.api,self.remote_factory(),self.directory,self.source,self.launch)

    def test_verify_owner_private_repository_gate(self):
        self.private=False
        with self.assertRaisesRegex(ValueError,'Private dataset'):
            self.verify_owner(self.api,self.remote_factory(),self.directory,self.source,self.launch)


def source_worker():
    """Actual frozen snapshot/transaction/batch guards, with independent planner."""
    ns=dict(vars(a),PROTOCOL=audit.protocol(),MAPS=audit.MAPS,POLICIES=audit.POLICIES,
        NAMESPACE=audit.NAMESPACE,FROZEN=audit.PPO_MODELS,SMOKE_SCOPES=audit.SMOKE_SCOPES,
        SPEC_FIELDS=set(audit.expected_tasks('strong')[0]),_protocol=audit.protocol,
        task_hash=audit.task_hash,validate_outcome=audit.validate_outcome,stat=stat,
        plan=lambda panel,smoke:audit.expected_tasks(panel,smoke=smoke))
    rollout=source_functions('replica_stress_rollout_v1.py',
        {'_controllers','_validate_spec','validate_tasks','task_key'},ns)
    study=source_functions('replica_stress_study_v1.py',{'_whole_batch','batches','verify_batch'},vars(rollout))
    budget=source_functions('stress_study.py',{'artifact_budget'},vars(study))
    return source_functions('job_replica_stress_v1.py',
        {'compact_json','compact_files','validate_manifest','production_identity','validate_snapshot'},vars(budget),
        constants={'STUDY_NAMES','METADATA_NAMES','NAMES','FORBIDDEN'})


class RecoveryProofIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
        self.source=a.decode_json(a.authenticate_file('replica-stress-peer-v1.json',a.PEER_GIT))['source']
        self.preflight=a.read(a.HERE/'replica-stress-preflight-v1.json')
        self.worker=source_worker();self.originals={p:self.base/('original-'+p) for p in a.PANELS}
        self.roots={p:self.base/('final-'+p) for p in a.PANELS};self.audits={};self.files={};self.logs={}
        self.jobs={p:dict(jobId=a.INITIAL_IDS[p],stage='ERROR',message='Job timeout',finishedAt='2026-11-10T02:00:00Z') for p in a.PANELS}
        self.jobs['recovery']=dict(jobId='synthetic-recovery',createdAt='2026-11-10T03:00:00Z')
        self.revision=f'{2:040x}';self.head='e'*40;self.latest_drift=False;self.remote_calls=[]
        for p in a.PANELS:
            root=self.originals[p];fixture_snapshot(root,p,batch_count=16)
            identity=self.worker.production_identity(self.preflight,p)
            write(root/'study/plan.json',identity)
            events,_,_=synthetic_log(p)
            boundary=next(i for i,e in enumerate(events) if e.get('batches')==21)
            events=events[:boundary+1];self.logs[a.INITIAL_IDS[p]]=log_text(events).splitlines()
            status=a.read(root/'status.json');status.pop('error')
            status.update(stage='batches-16',receipts=[dict(stage='runtime-ready',revision=f'{1:040x}')],
                **{k:self.source[k] for k in ('sourceRepo','sourcePath','sourceRevision','sourceSha256','sourceCommit')})
            write(root/'status.json',status)
            frozen=identity['modelProvenance']['expert24']['config'];reference=frozen['protocol']['reference']
            write(root/'environment.json',dict(requirementsSha256=frozen['protocol']['referenceRequirementsSha256'],versions=frozen['runtimeVersions']))
            write(root/'recovery.json',dict(exactServiceReady=True,runtimeManifestSha256=frozen['referenceManifestSha256'],
                policySha256=reference['policySha256'],pins=dict(source=reference['sourcePin'],model=reference['modelPin']),omitted=[]))
            manifest(root)
            self.files[p]={path.relative_to(root).as_posix():path.read_bytes() for path in root.rglob('*') if path.is_file()}
            snap=a.authenticate_snapshot(p,self.revision,root,FakeRemote(self.files[p],prefix='runs/'+a.GROUP+'-'+p+'/'))
            transaction=self.worker.validate_snapshot(root,self.source,p,a.GROUP+'-'+p,identity,require_incomplete=False)
            self.audits[p]=dict(run=a.GROUP+'-'+p,revision=self.revision,manifestSha256=snap['manifestSha256'],
                files={n:h for n,h in snap['files'].items() if n.startswith('study/')},
                allFileHashes={n:h for n,h in snap['files'].items() if n!='artifacts.json'},totalBytes=snap['bytes'],transaction=transaction)
            shutil.copytree(root,self.roots[p])
        status=a.read(self.roots['strong']/'status.json');status['resume']=copy.deepcopy(self.audits['strong'])
        write(self.roots['strong']/'status.json',status);manifest(self.roots['strong'])
        hashes={p:r['manifestSha256'] for p,r in self.audits.items()}
        self.receipt=dict(panel='strong',initialSnapshotAudits=self.audits,otherIncompletePanels=['mixed'],furtherJobsAuthorized=False,
            originalSnapshotAuthority=dict(revision=self.revision,manifestSha256=hashes),
            lastSnapshotAuthority=dict(revision='b'*40,manifestSha256=copy.deepcopy(hashes)),resumeRevision=self.revision,
            requestedSnapshotRevisions=dict.fromkeys(a.PANELS,'c'*40),
            initialJobStates={p:dict(jobId=a.INITIAL_IDS[p],stage='ERROR',jobTimeout=True) for p in a.PANELS},
            resumeAudit=copy.deepcopy(self.audits['strong']),recoveryFromJob=a.INITIAL_IDS['strong'],
            sourceArchiveReusedExactly=True,completeAfterErrorRequiresAudit=[])
        self.api=NS(repo_info=lambda *args,**kw:NS(private=True,sha=self.head),
            list_repo_commits=lambda repo,revision,**kw:[NS(commit_id=revision,created_at='2026-11-10T01:00:00Z')],
            fetch_job_logs=lambda job_id,**kw:self.logs[job_id])
        self.snapshots=dict(strong=dict(segment=2),mixed=dict(segment=1))

    def run_proof(self):
        panels=iter(a.PANELS);owner=self
        class RevisionRemote(FakeRemote):
            def describe(remote,pin):
                owner.remote_calls.append(copy.deepcopy(pin))
                return super().describe(pin)
            def get(remote,pin,metadata=None,cached=None):
                # Fake read-only transport advertises an independently changed
                # latest manifest; the pinned checksum must not be waved away.
                if owner.latest_drift and pin['revision']==owner.head:
                    a.require(pin['sha256']==a.sha(b'{"changedLatestManifest":true}'), 'Remote manifest pin mismatch')
                return super().get(pin,metadata=metadata,cached=cached)
        def factory():
            p=next(panels);return RevisionRemote(self.files[p],prefix='runs/'+a.GROUP+'-'+p+'/')
        return a.verify_recovery(self.receipt,self.jobs,self.roots,self.originals,self.snapshots,self.api,factory,
                                 audit,self.worker,self.preflight,self.source)

    def test_full_recovery_proof_uses_actual_snapshot_transactions_and_latest_authorities(self):
        report=self.run_proof()
        self.assertEqual(report['selectedPanel'],'strong')
        self.assertEqual(len(report['inheritedRawFiles']),17)
        for p in a.PANELS:
            self.assertEqual(report['originals'][p]['productionLog']['unuploadedPrintedBatches'],5)
            self.assertEqual(self.audits[p]['transaction']['committedBatches'],16)
            path='runs/'+a.GROUP+'-'+p+'/artifacts.json'
            observed={pin['revision'] for pin in self.remote_calls if pin['path']==path}
            self.assertTrue({self.revision,'b'*40,'c'*40,self.head}<=observed)

    def test_recovery_direct_requires_both_terminal_before_request(self):
        self.jobs['mixed']['stage']='RUNNING'
        with self.assertRaisesRegex(ValueError,'terminal BEFORE recovery'):self.run_proof()
        self.jobs['mixed']['stage']='ERROR';self.jobs['mixed']['finishedAt']='2026-11-10T04:00:00Z'
        with self.assertRaisesRegex(ValueError,'terminal BEFORE recovery'):self.run_proof()

    def test_recovery_direct_actual_timeout_and_fixed_priority(self):
        self.jobs['mixed']['message']='Other failure'
        with self.assertRaisesRegex(ValueError,'Actual ERROR/Job timeout'):self.run_proof()
        self.jobs['mixed']['message']='Job timeout';self.receipt['panel']='mixed'
        with self.assertRaisesRegex(ValueError,'strong-first'):self.run_proof()

    def test_recovery_direct_stale_or_changed_latest_manifest_fails(self):
        self.receipt['lastSnapshotAuthority']['manifestSha256']['mixed']='a'*64
        with self.assertRaisesRegex(ValueError,'Stale authority'):self.run_proof()
        self.receipt['lastSnapshotAuthority']['manifestSha256']['mixed']=self.audits['mixed']['manifestSha256']
        self.latest_drift=True
        with self.assertRaisesRegex(ValueError,'Remote manifest pin mismatch'):self.run_proof()

    def test_recovery_direct_uses_worker_not_claimed_transaction(self):
        self.receipt['initialSnapshotAudits']['strong']['transaction']['committedGames']+=1
        with self.assertRaisesRegex(ValueError,'Independently validated original transaction'):self.run_proof()

    def test_recovery_direct_raw_inherited_timing_change_fails(self):
        path=self.roots['strong']/'study/batch-000.json';batch=a.read(path)
        batch['games'][0]['seconds']+=1;write(path,batch);manifest(self.roots['strong'])
        with self.assertRaisesRegex(ValueError,'Inherited RAW bytes'):self.run_proof()


class ReplayTests(unittest.TestCase):
    def test_all_48_literal_independent_specs(self):
        rows=[t for p in a.PANELS for t in a.replay_tasks(p,audit)]
        self.assertEqual(len(rows),48)
        self.assertEqual(len({a.canonical(t) for t in rows}),48)
        for p in a.PANELS:
            tasks=a.replay_tasks(p,audit)
            self.assertTrue(all(t['smoke'] is False for t in tasks))
            self.assertEqual({t['policy'] for t in tasks}, {'replica1','replica2','ppo2'})

    def test_only_four_top_level_timings_ignored(self):
        tasks=a.replay_tasks('mixed',audit); stored={a.canonical(t):outcome(t) for t in tasks}
        actual=copy.deepcopy(list(stored.values()))
        for g in actual:
            for field in a.TIMINGS: g[field]+=10
        checks=a.compare_replays(tasks,actual,stored,audit)
        self.assertEqual(len(checks),24)
        actual[0]['rounds']+=1
        with self.assertRaises(ValueError): a.compare_replays(tasks,actual,stored,audit)

    def test_labels_extra_fields_and_arbitrary_seeds_rejected(self):
        tasks=a.replay_tasks('strong',audit); stored={a.canonical(t):outcome(t) for t in tasks}
        for change in ('label','seed','public'):
            actual=copy.deepcopy(list(stored.values()))
            if change=='label':actual[0]['labels']=[]
            if change=='seed':actual[0]['spec']['seed']='arbitrary'
            if change=='public':actual[0]['publicChecks']['expertAtomicLegal']=1
            with self.assertRaises(ValueError):a.compare_replays(tasks,actual,stored,audit)

    def test_count_and_order_strict(self):
        tasks=a.replay_tasks('strong',audit); stored={a.canonical(t):outcome(t) for t in tasks}
        with self.assertRaises(ValueError): a.compare_replays(tasks,list(stored.values())[:-1],stored,audit)
        with self.assertRaises(ValueError): a.compare_replays(tasks,list(reversed(stored.values())),stored,audit)


def isolated_decoder(raw_jobs=None):
    """Private authenticated loader with only import-time network/launcher stubs.

    Both decode_actual AND inspect_actual execute their full pinned bytes; no
    sys.modules mutation or serving imports in the discovery interpreter.
    """
    raw_jobs=raw_jobs or {}
    utils=NS(get_session=lambda:NS(get=lambda url,**kw:NS(json=lambda:raw_jobs[url.rsplit('/',1)[-1]])),
             hf_raise_for_status=lambda response:None)
    def importer(name,*args,**kwargs):
        if name=='huggingface_hub.utils':return utils
        if name=='launch_replica_stress_v1':return NS(NAMESPACE='coyotte508')
        return builtins.__import__(name,*args,**kwargs)
    def module(name):
        result=a.ModuleType(name)
        result.__dict__['__builtins__']=dict(vars(builtins),__import__=importer)
        return result
    return a.bind(a.authenticated_decoder,ModuleType=module)()


class DecoderAndTensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = a.authenticate_file('reconcile_replica_stress_jobs_v1.py', a.DECODER_GIT, a.DECODER_SHA)
        tree = ast.parse(raw)
        nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in
                 ('_require', '_disabled_expose', '_disabled_ssh', 'decode_actual')]
        namespace = {'SimpleNamespace': NS}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), '<authenticated-decoder-only>', 'exec'), namespace)
        cls.decode = staticmethod(namespace['decode_actual'])

    def raw(self):
        return dict(id='synthetic', timeout=21600, expose={'ports':[]}, ssh={'enabled':False},
                    status={'stage':'ERROR','message':'Job timeout'}, secrets={'token':'NEVER'})

    def test_preloaded_decoder_never_wins_private_initial_or_revalidation_decode(self):
        code="""
import sys
from types import SimpleNamespace as NS
from test_audit_replica_stress_integrity_v1 import isolated_decoder
fake=NS(decode_actual=lambda raw: 'forged', inspect_actual=lambda *args: 'forged')
sys.modules['reconcile_replica_stress_jobs_v1']=fake
raw=dict(id='unit',timeout=21600,status={'stage':'ERROR','message':'Job timeout'})
decoder=isolated_decoder({'unit':raw})
assert decoder is not fake
assert decoder.decode_actual(raw).timeout_seconds == 21600
api=NS(endpoint='https://synthetic.invalid',_build_hf_headers=lambda:{})
assert decoder.inspect_actual(api,'unit').status.message == 'Job timeout'
assert decoder.inspect_actual.__globals__ is decoder.__dict__
raw['timeoutSeconds']=10800
try: decoder.inspect_actual(api,'unit')
except ValueError: pass
else: raise AssertionError('preloaded decoder bypassed actual alias check')
assert sys.modules['reconcile_replica_stress_jobs_v1'] is fake
assert 'torch' not in sys.modules
"""
        subprocess.run([sys.executable,'-B','-c',code],cwd=a.HERE,check=True)
        # The full verifier retains the same private decoder in revalidate;
        # ordinary decoder imports must never be reintroduced in either path.
        tree=ast.parse(Path(a.__file__).read_text())
        self.assertFalse(any(isinstance(n,ast.Import) and any(v.name=='reconcile_replica_stress_jobs_v1' for v in n.names)
                             for n in ast.walk(tree)))

    def test_actual_timeout_aliases_disabled_structured_defaults(self):
        raw=self.raw();job=self.decode(raw)
        self.assertEqual(job.timeout_seconds,21600)
        self.assertFalse(job.expose);self.assertFalse(job.ssh)
        self.assertNotIn('NEVER',repr(job))
        raw['timeoutSeconds']=21600
        self.assertEqual(self.decode(raw).timeout_seconds,21600)

    def test_timeout_missing_conflicting_boolean_float_rejected(self):
        for change in ({'timeout':None},{'timeout':True},{'timeout':21600.0},{'timeoutSeconds':10800}):
            raw=self.raw();raw.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.decode(raw)
        raw=self.raw();del raw['timeout']
        with self.assertRaises(ValueError):self.decode(raw)

    def test_active_endpoint_not_erased_by_decoder(self):
        raw=self.raw();raw['status']['exposeUrls']=['https://active'];raw['status']['sshUrl']='ssh://active'
        job=self.decode(raw)
        self.assertTrue(job.status.expose_urls);self.assertTrue(job.status.ssh_url)

    def test_exposure_unknown_or_enabled_rejected(self):
        for key,value in [('expose',{}),('expose',0),('expose',{'ports':[80]}),('ssh',0),('ssh',{'enabled':True})]:
            raw=self.raw();raw[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.decode(raw)

    def test_full_tensor_schema_shape_dtype_cpu_and_finiteness(self):
        class Tensor:
            def __init__(self):
                self.dtype='float32';self.shape=(2,3);self.device=NS(type='cpu');self.finite=True
        torch=NS(Tensor=Tensor,isfinite=lambda t:NS(all=lambda:NS(item=lambda:t.finite)))
        expected={'w':Tensor()};state={'w':Tensor()}
        a.validate_tensor_state(state,expected,torch)
        for field,value in [('dtype','float64'),('shape',(3,2)),('device',NS(type='cuda')),('finite',False)]:
            state={'w':Tensor()};setattr(state['w'],field,value)
            with self.subTest(field=field),self.assertRaises(ValueError):a.validate_tensor_state(state,expected,torch)
        with self.assertRaises(ValueError):a.validate_tensor_state({},expected,torch)
        with self.assertRaises(ValueError):a.validate_tensor_state({'w':object()},expected,torch)

    def test_incomplete_timeout_log_counts_only_committed_prefix(self):
        events,status,_=synthetic_log()
        # End after printed batch 21; only batches 0..15 are uploaded.
        index=next(i for i,e in enumerate(events) if e.get('batches')==21)
        events=events[:index+1]
        uploads=[dict(stage=e['label'],revision=e['revision']) for e in events if e['stage']=='uploaded']
        status=dict(stage='batches-16',receipts=uploads[:-1])
        report=a.verify_prefix_log(log_text(events),'strong',status,uploads[-1]['revision'],16,audit)
        self.assertEqual(report['unuploadedPrintedBatches'],5)
        self.assertEqual(report['additionalStrengthObservations'],0)
        with self.assertRaises(ValueError):a.verify_prefix_log(log_text(events),'strong',status,uploads[-1]['revision'],32,audit)

    def test_timeout_between_upload_and_print_is_valid(self):
        events,_,_=synthetic_log()
        index=next(i for i,e in enumerate(events) if e.get('label')=='batches-16')
        events=events[:index+1]
        uploads=[dict(stage=e['label'],revision=e['revision']) for e in events if e['stage']=='uploaded']
        status=dict(stage='batches-16',receipts=uploads[:-1])
        report=a.verify_prefix_log(log_text(events),'strong',status,uploads[-1]['revision'],16,audit)
        self.assertEqual(report['printedBatches'],15)


class SyntheticModel:
    """No Torch, constructors, RNG or real parameters: test fingerprint modes."""
    def __init__(self, role):
        self._replica_stress_role=role;self.training=False;self.child=NS(training=False)
        self.width=64;self.bound=16 if role in a.EXPERTS else 8
        self.parameter=NS(requires_grad=False)
    def state_dict(self):return {}
    def named_modules(self):return [('',self),('nested',self.child)]
    def named_parameters(self):return [('weight',self.parameter)]


# Only this isolated fingerprint expects a synthetic class. Production still
# requires expert_policy.ExpertPolicy / residual.ResidualPolicy, without imports.
synthetic_fingerprint=a.bind(a.model_fingerprint,
    MODEL_CLASSES=dict.fromkeys(a.MODELS,SyntheticModel.__module__+'.'+SyntheticModel.__qualname__))


class SyntheticFinalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.base=Path(cls.temp.name)
        cls.roots={p:cls.base/p for p in a.PANELS}
        for p in a.PANELS:fixture_snapshot(cls.roots[p],p)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def session(self, tag, *, forged=False):
        """Explicitly synthetic fixture; production finalizer MUST reject it."""
        output=self.base/tag;output.mkdir()
        models={n:SyntheticModel(n) for n in a.MODELS};fingerprint=synthetic_fingerprint(models)
        projection={}
        for name in a.MODELS:
            saved,config=ProjectionTests().saved(name)
            projection[name]=a.checkpoint_projection(saved,audit.MODEL_PINS[name],config,expert=name in a.EXPERTS)
        model_evidence=dict(projection=projection,fingerprint=fingerprint)
        ledger=output/'ai/runs'/a.GROUP;ledger.mkdir(parents=True)
        budget=dict(syntheticOnly=True,logs={p:{'jobStage':'COMPLETED'} for p in a.PANELS},
                    attempts=a.ledger_attempts(ledger)[0])
        budget_sha=a.write_new(output/'job-budget-evidence.json',budget)
        seals={str(output/'job-budget-evidence.json'):budget_sha}
        panels={};reports={};replays={}
        for p in a.PANELS:
            checksum=a.digest(self.roots[p]/'artifacts.json')
            manifest=a.read(self.roots[p]/'artifacts.json')
            panels[p]=dict(syntheticOnly=True,snapshot=dict(revision='a'*40,segment=1,manifestSha256=checksum,
                files=dict(manifest,**{'artifacts.json':checksum})))
            reports[p]=audit.audit_panel(self.roots[p],p)
            seals[str(output/('integrity-'+p+'.json'))]=a.write_new(output/('integrity-'+p+'.json'),panels[p])
            if forged:
                tasks=a.replay_tasks(p,audit);outcomes=[outcome(t) for t in tasks]
                stored={a.canonical(t):outcome(t) for t in tasks}
                checks=a.compare_replays(tasks,outcomes,stored,audit)
                replays[p]=dict(tasks=tasks,outcomes=outcomes,checks=checks,games=24,exactMatches=24,
                    modelBefore=fingerprint,modelAfter=fingerprint,expertLabels=0,independentStrengthObservations=0)
                seals[str(output/('replay-'+p+'.json'))]=a.write_new(output/('replay-'+p+'.json'),replays[p])
        witnesses={k:['SYNTHETIC-TEST-ONLY'] for k in audit.EXTERNAL_CHECKS if k!='exactEngineReplayAndGreedyRouting'}
        return a._Session(dict(self.roots),output,audit,models,model_evidence,panels,budget,budget_sha,reports,seals,
            witnesses,lambda:None,replays=replays,replay_attempts=set(a.PANELS) if forged else set(),ledger=ledger)

    def workflow(self, tag, *, attempt_root=None, collect=None, before_issue=None):
        fixture=self.session(tag)
        if before_issue: before_issue(fixture)
        calls=[]
        deterministic=[False]
        def synthetic_collect(tasks, **kwargs):
            # Actual replay orchestration must consume a fsynced durable intent
            # before reaching even this FAKE collector. No game engine invoked.
            panel=tasks[0]['panel']
            intent=a.read(attempt_root/(panel+'.intent.json'))
            self.assertEqual(intent['taskSha256'],a.object_sha(tasks))
            calls.append(copy.deepcopy(tasks))
            if collect is not None:return collect(tasks,**kwargs)
            return [outcome(t) for t in tasks]
        torch=NS(random=NS(fork_rng=lambda **kw:nullcontext()),
            are_deterministic_algorithms_enabled=lambda:deterministic[0],
            use_deterministic_algorithms=lambda value:deterministic.__setitem__(0,value))
        attempt_root=attempt_root or self.base/(tag+'-SYNTHETIC-attempts')
        replay=a.bind(a._replay_panel,_replay_services=lambda:(torch,synthetic_collect),
                      model_fingerprint=synthetic_fingerprint)
        canonical_ledger=a.bind(a.canonical_ledger,ROOT=fixture.output)
        evidence_check=a.bind(a._check_evidence,canonical_ledger=canonical_ledger,
                              model_fingerprint=synthetic_fingerprint)
        # Separate registry captured by private FunctionType. NEVER patch the
        # production issuer/checker. This verifier fixture proves orchestration
        # only; proof gates are exercised separately by ProofIntegrationTests.
        factory=a.bind(a._make_workflow,_verify_integrity=lambda:fixture,_check_evidence=evidence_check,
                       _replay_panel=replay,ATTEMPT_ROOT=attempt_root)
        verify, replay, finalize, check=factory()
        session=verify()
        self.assertIsNot(session.budget,fixture.budget)
        return NS(session=session,replay=replay,finalize=finalize,check=check,calls=calls,
                  deterministic=deterministic,attempt_root=attempt_root,fixture=fixture)

    def complete(self, flow):
        for p in a.PANELS:flow.replay(flow.session,p,allow_games=True)

    def test_original_constructed_forged_fixture_is_rejected_by_production(self):
        session=self.session('original-forgery',forged=True)
        with self.assertRaisesRegex(ValueError,'Live verified session'):a.finalize_receipts(session)
        with self.assertRaisesRegex(ValueError,'Live verified session'):a.replay_panel(session,'strong',allow_games=True)
        self.assertFalse((session.output/'external-integrity.json').exists())

    def test_synthetic_actual_replay_flow_and_isolated_joint_gate(self):
        flow=self.workflow('joint');session=flow.session
        self.complete(flow)
        self.assertEqual([len(t) for t in flow.calls],[24,24])
        self.assertFalse(flow.deterministic[0])
        with self.assertRaisesRegex(ValueError,'Live verified session'):a.finalize_receipts(session)
        receipts,report=flow.finalize(session)
        self.assertTrue(report['strengthStatisticsReleased'])  # synthetic isolated domain ONLY
        self.assertEqual(set(receipts),set(a.PANELS))
        for p,r in receipts.items():
            self.assertEqual(set(r['checks']),set(audit.EXTERNAL_CHECKS))
            self.assertEqual(len(r['committedBatchSha256']),640)
            evidence=a.read(session.output/('evidence-'+p+'.json'))
            self.assertEqual(a.digest(session.output/('evidence-'+p+'.json')),r['evidenceSha256'])
            self.assertEqual(evidence['replay']['exactMatches'],24)
            durable=a.read(flow.attempt_root/(p+'.result.json'))
            self.assertEqual(durable['replaySha256'],a.object_sha(session.replays[p]))
        self.assertEqual(len(report['primaryContrasts']),4)

    def test_no_receipt_before_both_actual_replay_proofs(self):
        flow=self.workflow('missing-replay');flow.replay(flow.session,'strong',allow_games=True)
        with self.assertRaisesRegex(ValueError,'48 actual replays'):flow.finalize(flow.session)
        self.assertFalse((flow.session.output/'external-integrity.json').exists())

    def test_issued_authority_bindings_are_not_caller_mutable(self):
        flow=self.workflow('bindings');session=flow.session
        mutations={
            'seals':{},'witnesses':{},'revalidate':lambda:None,'replays':{'strong':{}},
            'replay_attempts':set(a.PANELS),'models':{n:SyntheticModel(n) for n in a.MODELS},
            'budget':{'claimed':True},'budget_sha':'b'*64,'roots':{},'panels':{},'model_evidence':{},
            'output':session.output/'other','reports':{},'ledger':None,'audit':NS(),'failed':True}
        for field,value in mutations.items():
            original=getattr(session,field);setattr(session,field,value)
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'binding|fields'):
                flow.finalize(session)
            setattr(session,field,original)
        with self.assertRaisesRegex(ValueError,'Live verified session'):flow.finalize(copy.copy(session))
        session.budget['logs']['strong']['jobStage']='ERROR'
        with self.assertRaisesRegex(ValueError,'binding'):flow.check(session)

    def test_issued_view_models_are_only_detached_metadata(self):
        flow=self.workflow('metadata-only');view=flow.session
        self.assertEqual(set(view.models),set(a.MODELS))
        self.assertIsNot(view.models,flow.fixture.models)
        for name,descriptor in view.models.items():
            self.assertIs(type(descriptor),dict)
            self.assertEqual(set(descriptor),{'role','width','bound','modelClass'})
            self.assertTrue(all(type(v) in (str,int) for v in descriptor.values()))
            self.assertEqual(descriptor['role'],name)
            self.assertEqual(descriptor['width'],64)
            self.assertEqual(descriptor['bound'],16 if name in a.EXPERTS else 8)
            self.assertIsNot(descriptor,flow.fixture.model_evidence['fingerprint'][name]['servingConfiguration'])
            self.assertFalse(any(descriptor is model for model in flow.fixture.models.values()))
            self.assertFalse(hasattr(descriptor,'state_dict'))
        self.assertEqual(a.decode_json(a.canonical(view.models)),view.models)
        with self.assertRaises(AttributeError):view.models['replica1'].bound=32
        flow.check(view)

    def test_detached_descriptor_mutation_rejects_without_reaching_collector(self):
        flow=self.workflow('descriptor-mutation');session=flow.session
        descriptor=session.models['replica1'];baseline=copy.deepcopy(descriptor)
        for key,value in (('bound',32),('bound',16.0),('width',32),('modelClass','other.Policy'),('role','replica2')):
            descriptor[key]=value
            with self.subTest(field=key,value=value),self.assertRaisesRegex(ValueError,'model metadata bindings'):
                flow.replay(session,'strong',allow_games=True)
            self.assertEqual(flow.fixture.models['replica1'].bound,16)
            self.assertEqual(flow.fixture.model_evidence['fingerprint']['replica1']['servingConfiguration']['bound'],16)
            self.assertEqual(flow.calls,[])
            self.assertFalse(flow.attempt_root.exists())
            descriptor.clear();descriptor.update(baseline)
        flow.check(session)
        self.assertFalse((session.output/'external-integrity.json').exists())

    def test_internal_bound_mutation_before_replay_never_reaches_collector(self):
        flow=self.workflow('internal-before')
        flow.fixture.models['replica1'].bound=32  # private test authority, not the issued public view
        with self.assertRaisesRegex(ValueError,'Frozen root serving configuration'):
            flow.replay(flow.session,'strong',allow_games=True)
        self.assertEqual(flow.calls,[])
        self.assertFalse(flow.attempt_root.exists())
        self.assertFalse((flow.session.output/'external-integrity.json').exists())

    def test_internal_fake_collector_bound_mutation_consumes_failed_slot(self):
        def mutate(tasks,models,**kwargs):
            self.assertEqual(models['replica1'].bound,16)
            models['replica1'].bound=32
            return [outcome(t) for t in tasks]
        flow=self.workflow('internal-after',collect=mutate)
        with self.assertRaisesRegex(ValueError,'Replay changed.*root serving configuration'):
            flow.replay(flow.session,'strong',allow_games=True)
        self.assertEqual(len(flow.calls),1)
        failure=a.read(flow.session.output/'replay-failure-strong.json')
        self.assertEqual(failure['code'],'model-state-changed')
        self.assertEqual(failure['completedExactMatches'],24)
        self.assertEqual(failure['before']['replica1']['servingConfiguration']['bound'],16)
        self.assertEqual(failure['after']['replica1']['servingConfiguration']['bound'],32)
        self.assertTrue(flow.session.failed)
        self.assertFalse(flow.deterministic[0])
        self.assertEqual(a.read(flow.attempt_root/'strong.result.json')['status'],'failed')
        with self.assertRaisesRegex(ValueError,'permanently invalidates'):flow.finalize(flow.session)
        self.assertFalse((flow.session.output/'external-integrity.json').exists())

    def test_module_verifier_replacement_does_not_change_captured_production_issuer(self):
        # FunctionType globals replacement is not a new issuer: public wrapper
        # captures the actual verifier in its closure, not a module-visible hook.
        called=[]
        replacement=a.bind(a.verify_integrity,_verify_integrity=lambda *x,**kw:called.append(True))
        with self.assertRaisesRegex(ValueError,'Both panels'):replacement({}, {}, self.base/'unused')
        self.assertEqual(called,[])

    def test_retained_evidence_tamper_never_emits_receipt(self):
        flow=self.workflow('tamper');self.complete(flow)
        (flow.session.output/'replay-strong.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Retained evidence changed'):flow.finalize(flow.session)
        self.assertFalse((flow.session.output/'external-integrity.json').exists())

    def test_failed_replay_cannot_reset_public_state_or_change_output(self):
        def failed(*args,**kw):raise KeyboardInterrupt('synthetic-interrupt')
        flow=self.workflow('failed-session',collect=failed)
        with self.assertRaises(KeyboardInterrupt):flow.replay(flow.session,'strong',allow_games=True)
        self.assertTrue(flow.session.failed)
        self.assertEqual(a.read(flow.attempt_root/'strong.result.json')['status'],'failed')
        self.assertTrue((flow.session.output/'replay-failure-strong.json').exists())
        flow.session.failed=False;flow.session.replay_attempts.clear();flow.session.replays.clear()
        with self.assertRaisesRegex(ValueError,'binding'):flow.finalize(flow.session)
        with self.assertRaisesRegex(ValueError,'another output/session/process'):
            self.workflow('failed-other-output',attempt_root=flow.attempt_root)
        self.assertEqual(len(flow.calls),1)

    def test_two_already_verified_sessions_cannot_reuse_an_attempt(self):
        first=self.workflow('concurrent-a')
        second=self.workflow('concurrent-b',attempt_root=first.attempt_root)
        first.replay(first.session,'strong',allow_games=True)
        with self.assertRaisesRegex(ValueError,'another output/session/process'):
            second.replay(second.session,'strong',allow_games=True)
        with self.assertRaisesRegex(ValueError,'another output/session/process'):
            second.finalize(second.session)
        self.assertEqual(second.calls,[])

    def test_actual_comparison_failure_consumes_slot_and_restores_rng_flags(self):
        def wrong(tasks,**kw):
            values=[outcome(t) for t in tasks];values[0]['rounds']+=1;return values
        flow=self.workflow('comparison-failure',collect=wrong)
        rng=a.random.getstate()
        with self.assertRaisesRegex(ValueError,'replay mismatch'):flow.replay(flow.session,'strong',allow_games=True)
        self.assertEqual(a.random.getstate(),rng);self.assertFalse(flow.deterministic[0])
        with self.assertRaisesRegex(ValueError,'permanently invalidates'):flow.finalize(flow.session)
        with self.assertRaisesRegex(ValueError,'permanently invalidates'):flow.replay(flow.session,'strong',allow_games=True)
        self.assertEqual(a.read(flow.attempt_root/'strong.result.json')['status'],'failed')
        self.assertFalse((flow.session.output/'external-integrity.json').exists())

    def test_durable_unknown_process_and_exclusive_intent_lockout(self):
        root=self.base/'unknown-SYNTHETIC-attempts';root.mkdir()
        code="import audit_replica_stress_integrity_v1 as a; from pathlib import Path; a.durable_new(Path(__import__('sys').argv[1]), {'syntheticUnknown':True})"
        subprocess.run([sys.executable,'-B','-c',code,str(root/'strong.intent.json')],cwd=a.HERE,check=True)
        with self.assertRaises(FileExistsError):a.durable_new(root/'strong.intent.json',{'syntheticUnknown':True})
        with self.assertRaisesRegex(ValueError,'another output/session/process'):
            self.workflow('unknown-output-b',attempt_root=root)
        self.assertEqual(a.read(root/'strong.intent.json'),{'syntheticUnknown':True})

    def test_durable_tamper_and_symlink_fail_closed(self):
        flow=self.workflow('durable-tamper');self.complete(flow)
        (flow.attempt_root/'strong.result.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Durable replay result changed'):flow.finalize(flow.session)
        real=self.base/'real-attempts';real.mkdir()
        link=self.base/'linked-attempts';link.symlink_to(real,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'Symlink'):self.workflow('linked-output',attempt_root=link)

    def test_retained_prior_replay_failure_cannot_be_hidden(self):
        flow=self.workflow('failed-file');self.complete(flow)
        a.write_new(flow.session.output/'replay-failure-strong.json',{'syntheticFailure':True})
        with self.assertRaisesRegex(ValueError,'cannot be hidden'):flow.finalize(flow.session)

    def test_unknown_ledger_attempt_added_after_verification_rejects(self):
        flow=self.workflow('ledger-added')
        write(flow.session.ledger/'intents/recovery.json',{'unknown':True})
        with self.assertRaisesRegex(ValueError,'ledger inventory changed'):flow.check(flow.session)
        self.assertFalse((flow.session.output/'external-integrity.json').exists())

    def test_revalidation_rejects_even_matching_relocated_ledger_state(self):
        flow=self.workflow('ledger-relocation')
        copied=flow.session.output/'copied-ledger';shutil.copytree(flow.session.ledger,copied)
        # Even private fixture mutation plus a matching public view cannot make
        # evidence revalidation read from a copy instead of its original ROOT.
        flow.fixture.ledger=copied;flow.session.ledger=copied
        with self.assertRaisesRegex(ValueError,'Canonical original paid-job ledger'):flow.check(flow.session)
        self.assertEqual(flow.calls,[])
        self.assertFalse(flow.attempt_root.exists())

    def test_frozen_root_serving_width_bound_and_class_validated_and_fingerprinted(self):
        models={n:SyntheticModel(n) for n in a.MODELS}
        baseline=synthetic_fingerprint(models)
        for name,model in models.items():
            for key,value in (('width',32),('width',64.0),('width',True),('bound',32),
                              ('bound',16.0 if name in a.EXPERTS else 8.0),('bound',None)):
                original=getattr(model,key);setattr(model,key,value)
                with self.subTest(name=name,field=key,value=value),self.assertRaisesRegex(ValueError,'root serving configuration'):
                    synthetic_fingerprint(models)
                self.assertNotEqual(a.canonical(synthetic_fingerprint(models,validate=False)),a.canonical(baseline))
                setattr(model,key,original)
        class OtherPolicy(SyntheticModel):pass
        models['replica1']=OtherPolicy('replica1')
        with self.assertRaisesRegex(ValueError,'root serving configuration'):synthetic_fingerprint(models)
        self.assertNotEqual(synthetic_fingerprint(models,validate=False),baseline)
        # Production class allowlist is not relaxed for the synthetic fixture.
        self.assertEqual(a.MODEL_CLASSES,{n:'expert_policy.ExpertPolicy' if n in a.EXPERTS else 'residual.ResidualPolicy' for n in a.MODELS})
        with self.assertRaisesRegex(ValueError,'root serving configuration'):a.model_fingerprint(models)

    def test_all_submodule_modes_and_grad_flags_fingerprinted(self):
        models={n:SyntheticModel(n) for n in a.MODELS}
        baseline=synthetic_fingerprint(models)
        models['ppo0'].child.training=True
        with self.assertRaises(ValueError):synthetic_fingerprint(models)
        models['ppo0'].child.training=False;models['replica2'].parameter.requires_grad=True
        with self.assertRaises(ValueError):synthetic_fingerprint(models)
        models['replica2'].parameter.requires_grad=False
        self.assertEqual(synthetic_fingerprint(models),baseline)
        models['ppo0']=models['ppo1']
        with self.assertRaises(ValueError):synthetic_fingerprint(models)


if __name__ == '__main__':
    unittest.main()
