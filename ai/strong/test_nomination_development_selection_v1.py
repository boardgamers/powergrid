"""A bounded launch must never fall through into the rest of the frozen screen."""
import unittest
from manage_nomination_development_v1 import selected_rows


class SelectionTests(unittest.TestCase):
    def test_only_requested_existing_rows_are_selected(self):
        p = {'rows': [{'name': 'old'}, {'name': 'wanted'}, {'name': 'unsubmitted'}]}
        self.assertEqual(selected_rows(p, ['wanted']), [{'name': 'wanted'}])

    def test_unknown_duplicate_and_empty_selection_rejected(self):
        p = {'rows': [{'name': 'known'}]}
        for names in ([], ['unknown'], ['known', 'known']):
            with self.subTest(names=names), self.assertRaises(AssertionError): selected_rows(p, names)

    def test_default_preserves_original_schedule(self):
        p = {'rows': [{'name': 'second'}, {'name': 'first'}]}
        self.assertEqual(selected_rows(p), p['rows'])


if __name__ == '__main__': unittest.main()
