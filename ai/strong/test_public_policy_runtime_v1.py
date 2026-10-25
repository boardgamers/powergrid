import copy
import json
from pathlib import Path
import tempfile
import unittest

from public_policy_runtime_v1 import PublicPolicyService, checked_path, encode


class Backend:
    def __init__(self, fault=None):
        self.fault, self.closed = fault, False
        self.identity = {'modelSha256': 'a'*64, 'policySha256': 'b'*64,
                         'runtimeManifestSha256': 'c'*64, 'featureRevision': '4.3-strategic-correction'}

    def prepare(self, request):
        if self.fault == 'prepare':
            raise RuntimeError('engine failure')
        actor = request['player']
        order = [actor, 1-actor] if self.fault != 'ordering' else [actor, actor]
        return {'moves': [{'name': 'Pass', 'data': True}, {'name': 'Bid', 'data': 3}],
                'observation': {'playerOrder': order}}

    def choose(self, request):
        result = {'index': 1, 'move': {'name': 'Bid', 'data': 3},
                  'modelSha256': self.identity['modelSha256'],
                  'featureRevision': self.identity['featureRevision'], 'search': {'sentinel': 'unchanged'}}
        if self.fault == 'move':
            result['move']['data'] = 100
        if self.fault == 'bool':
            result.update(index=0, move={'name': 'Pass', 'data': 1})
        if self.fault == 'identity':
            result['modelSha256'] = 'd'*64
        if self.fault == 'mutation':
            request['state']['players'].append({})
        return result

    def close(self):
        self.closed = True


class PublicPolicyContracts(unittest.TestCase):
    def setUp(self):
        self.request = {'requestId': 'opaque-id', 'revision': 17,
                        'state': {'players': [{}, {}]}, 'player': 1}

    def test_same_move_and_metadata_for_cold_warm_reordered_requests(self):
        instances = []
        def factory():
            instance = Backend(); instances.append(instance); return instance
        service = PublicPolicyService(factory)
        try:
            for q in [self.request, {**self.request, 'requestId': 'second', 'revision': 18}, self.request]:
                response = service.handle_line(encode(q), diagnostics=True)
                self.assertEqual(response['requestId'], q['requestId'])
                self.assertEqual(response['revision'], q['revision'])
                self.assertEqual(response['playerOrder'], [1, 0])
                self.assertEqual(response['move'], {'name': 'Bid', 'data': 3})
                self.assertEqual(response['decision']['search'], {'sentinel': 'unchanged'})
                self.assertNotIn('winProbabilities', response)
                self.assertFalse(response['qualification_eligible'])
            self.assertEqual(len(instances), 1)
        finally:
            service.close()
        self.assertTrue(instances[0].closed)

    def test_invalid_json_and_numbers_recover_on_next_request(self):
        service = PublicPolicyService(Backend)
        try:
            for line in ['not json', '[]', '{"requestId": NaN}', '{"requestId": 1e999}']:
                response = service.handle_line(line)
                self.assertIn('error', response)
                encode(response)
                self.assertNotIn('error', service.handle_line(encode(self.request)))
        finally:
            service.close()

    def test_invalid_actor_never_reaches_backend(self):
        def factory():
            self.fail('Malformed actor reached engine')
        service = PublicPolicyService(factory)
        for actor in [True, -1, 2, 1.0, None]:
            response = service.handle_line(encode({**self.request, 'player': actor}))
            self.assertIn('error', response)
            self.assertEqual(response['requestId'], 'opaque-id')
            self.assertEqual(response['revision'], 17)

    def test_bad_backend_is_closed_and_replaced_before_next_request(self):
        for fault in ['prepare', 'ordering', 'move', 'bool', 'identity', 'mutation']:
            with self.subTest(fault=fault):
                bad, good = Backend(fault), Backend()
                instances = iter([bad, good])
                service = PublicPolicyService(lambda: next(instances))
                try:
                    response = service.handle_line(encode(copy.deepcopy(self.request)))
                    self.assertIn('error', response)
                    self.assertTrue(bad.closed)
                    self.assertNotIn('error', service.handle_line(encode(self.request)))
                finally:
                    service.close()
                self.assertTrue(good.closed)

    def test_diagnostics_are_opt_in(self):
        service = PublicPolicyService(Backend)
        try:
            self.assertNotIn('decision', service.handle_line(encode(self.request)))
        finally:
            service.close()

    def test_artifact_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); (root/'valid').write_text('ok')
            self.assertEqual(checked_path(root, 'valid'), root/'valid')
            for invalid in ['', '../valid', '/etc/passwd', 'missing']:
                with self.assertRaises(ValueError):
                    checked_path(root, invalid)
            (root/'escape').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                checked_path(root, 'escape')


if __name__ == '__main__':
    unittest.main()
