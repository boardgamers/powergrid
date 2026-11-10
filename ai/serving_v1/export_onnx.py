"""Offline-only export/parity tool; production inference is Node, never Python.

Both role-specific checkpoint paths must be provided explicitly. ReplicaPolicy
checks unchanged checkpoint bytes, configuration, frozen source files, and the
pinned CPU runtime before loading the full frozen ExpertPolicy in eval mode.
There is no training, model download, policy selection, or checkpoint rewriting.

See requirements-export.txt for isolated /tmp dependency installation. Example:

    PYTHONPATH="$DEPS" ai/.venv/bin/python -B -m ai.serving_v1.export_onnx \
      --replica1-checkpoint /explicit/replica1/best.pt \
      --replica2-checkpoint /explicit/replica2/best.pt \
      --output ai/runs/serving-prototype-v1/onnx

The output directory MUST NOT exist: every artifact is created exclusively.
Existing exports, checkpoints, and evidence are never overwritten. Re-export
into a fresh directory after any source manifest byte changes.

Optional engineering parity (also works without --output):
    --reference-fixtures fixtures.json --reference-output reference.json
Fixtures may be a JSON array of {"id": "unique-id", "observation": {...}}, or
{schema: "pg-serving-engineering-fixtures-v1", namespace: "pg-serving-prototype-v1",
 fixtures: [{id, map, players, variant, fastBid, kind, observation}, ...]}.
Only public multimap-graph-v1 observations enter the model; envelope metadata is
validated and discarded. Results retain each fixture id alongside logits (flat
list), value (scalar), and first-argmax index for BOTH replicas. Values are
uncalibrated engineering outputs, not labels, game results, or policy scores.
CLI references bind the exact fixture-file bytes with fixturesInputSha256 and
fixturesInputHashMode="raw-file-bytes". Programmatic reference_results uses
"python-canonical-normalized-json-v1" instead: Python canonical JSON of the
validated {id, observation} list, which is NOT cross-language canonical JSON
(e.g. JS float spelling can differ). Cross-language parity must use the CLI raw
file binding, not reserialize observations to compare the Python-only digest.
"""
import argparse
import io
import json
import os
from pathlib import Path
import sys

try:
    from . import worker as w
except ImportError:
    import worker as w

OPSET = 17
ONNX_VERSION = '1.17.0'
PROTOBUF_VERSION = '5.29.5'
ROLES = ('replica1', 'replica2')
INPUT_NAMES = ('global', 'players', 'nodes', 'relations', 'actions', 'actionCity',
               'prior', 'nodeMask', 'playerMask', 'actionMask')
OUTPUT_NAMES = ('logits', 'value')
# ONNX tensor enum values; importing this module does not require Torch/ONNX.
CONTRACT = {
    'global': (1, (1, 273)),
    'players': (1, (1, 'P', 80)),
    'nodes': (1, (1, 'N', 36)),
    'relations': (1, (1, 4, 'N', 'N')),
    'actions': (1, (1, 'A', 34)),
    'actionCity': (7, (1, 'A')),
    'prior': (1, (1, 'A')),
    'nodeMask': (9, (1, 'N')),
    'playerMask': (9, (1, 'P')),
    'actionMask': (9, (1, 'A')),
    'logits': (1, (1, 'A')),
    'value': (1, (1,)),
}
DYNAMIC_AXES = {name: {i: dim for i, dim in enumerate(shape) if isinstance(dim, str)}
                for name, (_, shape) in CONTRACT.items() if any(isinstance(d, str) for d in shape)}
MAX_MODEL_BYTES = 16 * 1024**2
MAX_FIXTURE_BYTES = 32 * 1024**2


def export_dependencies():
    import onnx
    import google.protobuf
    w.require(onnx.__version__ == ONNX_VERSION and google.protobuf.__version__ == PROTOBUF_VERSION)
    return onnx


def sample_observation():
    """Public-shaped trace inputs only; dynamic axes are not frozen to this size."""
    players, nodes, actions = 2, 3, 5
    return dict(schema='multimap-graph-v1', **{'global': [0.0] * 273},
                players=[[0.0] * 80 for _ in range(players)],
                nodes=[[0.0] * 36 for _ in range(nodes)],
                relations=[[[float(i == j) for j in range(nodes)] for i in range(nodes)] for _ in range(4)],
                actions=[[0.0] * 34 for _ in range(actions)],
                actionCity=[-1, 0, 1, 2, -1], prior=[0.0, -1.0, -2.0, -3.0, -20.0])


def tensor_inputs(policy, observation):
    w.validate_observation(observation)
    tensors = policy._expert.batch([policy._expert.row(observation)])
    return {name: tensors[name] for name in INPUT_NAMES}


def check_policy(policy):
    policy.assert_unchanged()
    torch = policy._torch
    w.require(policy.replica in ROLES and policy.checkpoint_sha256 == w.REPLICAS[policy.replica]['sha256'])
    w.require(type(policy.model) is policy._expert.ExpertPolicy)
    w.require(torch.get_default_dtype() == torch.float32 and torch.get_default_device().type == 'cpu'
              and torch.get_num_threads() == 1)
    w.require(all(not module.training for module in policy.model.modules()))
    w.require(all(not p.requires_grad and p.grad is None and p.dtype == torch.float32
                  and p.device.type == 'cpu' and bool(torch.isfinite(p).all())
                  for p in policy.model.parameters()))


def _messages(message):
    """Visit nested protobufs, including subgraphs and tensor-valued attributes."""
    yield message
    for field, value in message.ListFields():
        if field.message_type is not None:
            if field.label == field.LABEL_REPEATED:
                for item in value:
                    yield from _messages(item)
            else:
                yield from _messages(value)


def validate_onnx(raw):
    """Check bytes without resolving any external tensor data or custom operators."""
    onnx = export_dependencies()
    w.require(type(raw) is bytes and 0 < len(raw) <= MAX_MODEL_BYTES)
    model = onnx.load_model_from_string(raw)
    w.require([(op.domain, op.version) for op in model.opset_import] == [('', OPSET)])
    w.require(not model.functions and not model.training_info)
    for item in _messages(model):
        if isinstance(item, onnx.TensorProto):
            w.require(item.data_location != onnx.TensorProto.EXTERNAL and not item.external_data)
            w.require(item.data_type in (onnx.TensorProto.FLOAT, onnx.TensorProto.INT64,
                                        onnx.TensorProto.INT32, onnx.TensorProto.BOOL))
        elif isinstance(item, onnx.NodeProto):
            w.require(item.domain == '')
            # Verify standard-domain operator identity against the fixed opset.
            onnx.defs.get_schema(item.op_type, OPSET, '')
    w.require(tuple(v.name for v in model.graph.input) == INPUT_NAMES)
    w.require(tuple(v.name for v in model.graph.output) == OUTPUT_NAMES)
    for value in (*model.graph.input, *model.graph.output):
        dtype, shape = CONTRACT[value.name]
        tensor = value.type.tensor_type
        actual = tuple(d.dim_value if d.HasField('dim_value') else d.dim_param for d in tensor.shape.dim)
        w.require(tensor.elem_type == dtype and actual == shape)
    w.require(all(t.data_type == onnx.TensorProto.FLOAT for t in model.graph.initializer))
    onnx.checker.check_model(model, full_check=True)
    return model


def export_policy(policy):
    """Trace the unchanged full ExpertPolicy, including prior feature/residual."""
    export_dependencies()
    check_policy(policy)
    torch = policy._torch

    class TensorContract(torch.nn.Module):
        def __init__(self, expert):
            super().__init__()
            self.expert = expert

        def forward(self, *args):
            return self.expert(dict(zip(INPUT_NAMES, args)))

    buffer = io.BytesIO()
    with torch.inference_mode():
        inputs = tensor_inputs(policy, sample_observation())
        torch.onnx.export(
            TensorContract(policy.model).eval(), tuple(inputs.values()), buffer,
            input_names=list(INPUT_NAMES), output_names=list(OUTPUT_NAMES),
            opset_version=OPSET, dynamo=False, external_data=False,
            dynamic_axes={name: dict(axes) for name, axes in DYNAMIC_AXES.items()},
            training=torch.onnx.TrainingMode.EVAL,
            operator_export_type=torch.onnx.OperatorExportTypes.ONNX,
            export_params=True, keep_initializers_as_inputs=False,
            do_constant_folding=True, export_modules_as_functions=False,
        )
    check_policy(policy)
    raw = buffer.getvalue()
    validate_onnx(raw)
    return raw


def load_policies(replica1_checkpoint, replica2_checkpoint):
    policies = {'replica1': w.ReplicaPolicy('replica1', replica1_checkpoint),
                'replica2': w.ReplicaPolicy('replica2', replica2_checkpoint)}
    verify_manifest_identity(policies)
    return policies


def verify_manifest_identity(policies):
    w.require(type(policies) is dict and tuple(policies) == ROLES)
    manifest, checksum = w.load_manifest()
    w.verify_sources(manifest)
    for role, policy in policies.items():
        w.require(policy.replica == role and policy.manifest_sha256 == checksum)
        check_policy(policy)
    return checksum


def bundle(policies):
    """Build/check both independent models in memory before creating output files."""
    source_sha256 = verify_manifest_identity(policies)
    models = {f'{role}.onnx': export_policy(policies[role]) for role in ROLES}
    manifest = dict(
        schema='pg-replica-onnx-export-v1', sourceManifestSha256=source_sha256,
        replicas={role: dict(file=f'{role}.onnx', sha256=w.sha256(models[f'{role}.onnx']),
                             bytes=len(models[f'{role}.onnx']),
                             checkpointSha256=policies[role].checkpoint_sha256) for role in ROLES},
        runtimes={name: w.RUNTIMES[name] for name in ('python', 'torch', 'numpy')},
        exporter=dict(name='torch.onnx.export', torch=w.RUNTIMES['torch'], onnx=ONNX_VERSION,
                      protobuf=PROTOBUF_VERSION, dynamo=False, opset=OPSET,
                      externalData=False, dtype='float32', mode='eval'),
    )
    w.require(verify_manifest_identity(policies) == source_sha256)
    return dict(models, **{'export-manifest.json': json_bytes(manifest)})


def json_bytes(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf-8')


def _parent_directory(path):
    """Create/open ancestors without following symlinks; caller closes the fd."""
    path = Path(path)
    w.require('..' not in path.parts and path.name not in ('', '.', '..'))
    path = path.absolute()
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            try:
                os.mkdir(part, mode=0o700, dir_fd=directory)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        return path.name, directory
    except BaseException:
        os.close(directory)
        raise


def _write_exclusive(directory, name, raw):
    descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def write_bundle(output, artifacts):
    w.require(set(artifacts) == {'replica1.onnx', 'replica2.onnx', 'export-manifest.json'})
    name, parent = _parent_directory(output)
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent)  # Existing directory is always an error.
        directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            # Manifest is the completion marker and must be written LAST. Failed
            # writes leave an incomplete directory; never delete unknown files.
            for file in ('replica1.onnx', 'replica2.onnx', 'export-manifest.json'):
                _write_exclusive(directory, file, artifacts[file])
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.close(parent)


def _normalize_fixture_payload(payload):
    wrapped = type(payload) is dict
    if wrapped:
        w.require(set(payload) == {'schema', 'namespace', 'fixtures'})
        w.require(payload['schema'] == 'pg-serving-engineering-fixtures-v1'
                  and payload['namespace'] == 'pg-serving-prototype-v1')
        fixtures = payload['fixtures']
    else:
        fixtures = payload
    return validate_fixtures(fixtures, wrapped=wrapped)


def validate_fixtures(fixtures, *, wrapped=False):
    """Validate/normalize public rows; direct reference calls disallow envelopes."""
    w.require(type(fixtures) is list and 1 <= len(fixtures) <= 256)
    fields = {'id', 'observation'}
    if wrapped:
        fields |= {'map', 'players', 'variant', 'fastBid', 'kind'}
    seen, normalized = set(), []
    for fixture in fixtures:
        w.require(type(fixture) is dict and set(fixture) == fields)
        identity = fixture['id']
        w.require(type(identity) is str and 0 < len(identity) <= 256 and identity not in seen)
        seen.add(identity)
        w.validate_observation(fixture['observation'])
        if wrapped:
            w.require(type(fixture['map']) is str and 0 < len(fixture['map']) <= 128)
            w.require(type(fixture['players']) is int
                      and fixture['players'] == len(fixture['observation']['players']))
            w.require(fixture['variant'] in ('original', 'recharged') and type(fixture['fastBid']) is bool)
            w.require(fixture['kind'] in ('nomination', 'bid', 'Resources', 'Building', 'Bureaucracy'))
        normalized.append(dict(id=identity, observation=fixture['observation']))
    return normalized


def _read_fixture_input(path):
    # Hash and parse the SAME bounded file read; never reopen it for the digest.
    raw = w.safe_read(path, MAX_FIXTURE_BYTES)
    return _normalize_fixture_payload(w.strict_json(raw)), w.sha256(raw)


def read_fixtures(path):
    """Return normalized {id, observation} rows from an array or public envelope."""
    return _read_fixture_input(path)[0]


def reference_results(policies, fixtures):
    """Frozen outputs bound to validated rows by a Python-only canonical digest.

    The CLI replaces this digest/mode with the exact original file-byte binding.
    No ONNX dependency or model/fixture mutation is required for this operation.
    """
    fixtures = validate_fixtures(fixtures)
    fixtures_sha256 = w.sha256(w.canonical(fixtures))
    source_sha256 = verify_manifest_identity(policies)
    results = []
    for fixture in fixtures:
        count = w.validate_observation(fixture['observation'])
        replicas = {}
        for role, policy in policies.items():
            torch = policy._torch
            with torch.inference_mode():
                logits, value = policy.model(tensor_inputs(policy, fixture['observation']))
                w.require(logits.dtype == value.dtype == torch.float32
                          and tuple(logits.shape) == (1, count) and tuple(value.shape) == (1,)
                          and bool(torch.isfinite(logits).all()) and bool(torch.isfinite(value).all()))
                replicas[role] = dict(logits=logits[0].tolist(), value=float(value[0]),
                                      index=int(logits[0].argmax().item()))
        results.append(dict(id=fixture['id'], actionCount=count, replicas=replicas))
    w.require(verify_manifest_identity(policies) == source_sha256)
    return dict(schema='pg-replica-pytorch-reference-v1', sourceManifestSha256=source_sha256,
                fixturesInputSha256=fixtures_sha256,
                fixturesInputHashMode='python-canonical-normalized-json-v1',
                runtimes={name: w.RUNTIMES[name] for name in ('python', 'torch', 'numpy')},
                replicas={role: dict(checkpointSha256=p.checkpoint_sha256) for role, p in policies.items()},
                fixtures=results)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--replica1-checkpoint', required=True)
    parser.add_argument('--replica2-checkpoint', required=True)
    parser.add_argument('--output', help='New directory for both models and export-manifest.json')
    parser.add_argument('--reference-fixtures', help='Offline {id, observation} array or versioned JS fixture envelope')
    parser.add_argument('--reference-output', help='New file for both replicas direct PyTorch outputs')
    args = parser.parse_args(argv)
    if bool(args.reference_fixtures) != bool(args.reference_output):
        parser.error('--reference-fixtures and --reference-output must be used together')
    if not args.output and not args.reference_fixtures:
        parser.error('provide --output and/or both reference options')
    try:
        # Fail cheaply for an existing output, including dangling symlinks.
        for path in (args.output, args.reference_output):
            if path and os.path.lexists(path):
                raise FileExistsError('Output already exists; use a fresh destination')
        fixtures, fixtures_input_sha256 = (_read_fixture_input(args.reference_fixtures)
                                           if args.reference_fixtures else (None, None))
        policies = load_policies(args.replica1_checkpoint, args.replica2_checkpoint)
        artifacts = bundle(policies) if args.output else None
        reference = None
        if fixtures is not None:
            result = reference_results(policies, fixtures)
            result['fixturesInputSha256'] = fixtures_input_sha256
            result['fixturesInputHashMode'] = 'raw-file-bytes'
            reference = json_bytes(result)
        if artifacts is not None:
            write_bundle(args.output, artifacts)
        if reference is not None:
            name, parent = _parent_directory(args.reference_output)
            try:
                _write_exclusive(parent, name, reference)
            finally:
                os.close(parent)
    except (Exception, KeyboardInterrupt) as error:
        print(f'Offline export/reference failed ({type(error).__name__}); no existing output was overwritten.',
              file=sys.stderr)
        return 1
    print('Offline export/reference complete; both explicit replica identities preserved.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
