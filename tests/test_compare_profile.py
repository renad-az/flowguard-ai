import unittest
from copy import deepcopy

from src.compare_profile import compare_profiles


class CompareProfileTests(unittest.TestCase):

    def setUp(self):
        self.baseline = {
            "version": 1,
            "sheets": [
                {
                    "name": "Sales",
                    "columns": [
                        {
                            "name": "Amount",
                            "position": 1,
                            "observed_types": ["number"],
                        }
                    ],
                }
            ],
        }

        self.profile = {
            "sheets": [
                {
                    "name": "Sales",
                    "data_rows": 3,
                    "columns": [
                        {
                            "name": "Amount",
                            "position": 1,
                            "missing_count": 0,
                            "types": {"number": 3},
                        }
                    ],
                }
            ]
        }

    def test_matching_structure_passes(self):
        errors, warnings = compare_profiles(
            self.profile,
            self.baseline,
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_column_is_blocked(self):
        profile = deepcopy(self.profile)
        profile["sheets"][0]["columns"] = []

        errors, warnings = compare_profiles(
            profile,
            self.baseline,
        )

        self.assertTrue(
            any("Missing column 'Amount'" in error for error in errors)
        )

    def test_new_value_type_is_blocked(self):
        profile = deepcopy(self.profile)

        profile["sheets"][0]["columns"][0]["types"] = {
            "number": 2,
            "text": 1,
        }

        errors, warnings = compare_profiles(
            profile,
            self.baseline,
        )

        self.assertTrue(
            any("New value types: text" in error for error in errors)
        )

    def test_more_rows_are_allowed(self):
        profile = deepcopy(self.profile)

        profile["sheets"][0]["data_rows"] = 100
        profile["sheets"][0]["columns"][0]["types"] = {
            "number": 100
        }

        errors, warnings = compare_profiles(
            profile,
            self.baseline,
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()