import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rubrica.spec import SpecError, load_spec, parse_spec  # noqa: E402


def _spec_dict(rules):
    return {"id": "demo", "title": "Demo", "rules": rules}


class ParseSpecTests(unittest.TestCase):
    def test_accepts_minimal_valid_spec(self):
        spec = parse_spec(_spec_dict([{"id": "has_readme", "kind": "file_exists", "path": "README.md"}]))
        self.assertEqual(spec.id, "demo")
        self.assertEqual(len(spec.rules), 1)
        self.assertEqual(spec.rules[0].severity, "major")
        self.assertEqual(spec.rules[0].weight, 1)

    def test_rejects_non_mapping(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(["not", "a", "mapping"])
        self.assertIn("отображением", str(ctx.exception))

    def test_rejects_missing_id(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec({"title": "x", "rules": [{"id": "a_b", "kind": "file_exists", "path": "x"}]})
        self.assertIn("id:", str(ctx.exception))

    def test_rejects_empty_rules(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict([]))
        self.assertIn("пуст", str(ctx.exception))

    def test_rejects_unknown_kind(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict([{"id": "weird_rule", "kind": "teleport"}]))
        self.assertIn("kind:", str(ctx.exception))

    def test_rejects_bad_rule_id(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict([{"id": "Bad-ID", "kind": "file_exists", "path": "x"}]))
        self.assertIn("rules[0].id", str(ctx.exception))

    def test_rejects_duplicate_ids(self):
        rules = [
            {"id": "same_name", "kind": "file_exists", "path": "a"},
            {"id": "same_name", "kind": "file_exists", "path": "b"},
        ]
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict(rules))
        self.assertIn("дубликат", str(ctx.exception))

    def test_rejects_bad_severity(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict([{"id": "sev_rule", "kind": "file_exists", "path": "a", "severity": "fatal"}]))
        self.assertIn("severity:", str(ctx.exception))

    def test_rejects_out_of_range_weight(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict([{"id": "weighty_thing", "kind": "file_exists", "path": "a", "weight": 99}]))
        self.assertIn("weight:", str(ctx.exception))

    def test_requires_path_for_file_exists(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict([{"id": "pathless_thing", "kind": "file_exists"}]))
        self.assertIn("path: обязателен", str(ctx.exception))

    def test_requires_pattern_for_file_contains(self):
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict([{"id": "contains_it", "kind": "file_contains", "path": "a"}]))
        self.assertIn("pattern: обязателен", str(ctx.exception))

    def test_rejects_uncompilable_pattern(self):
        rules = [{"id": "bad_regex_ok", "kind": "file_contains", "path": "a", "pattern": "([unclosed"}]
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict(rules))
        self.assertIn("не компилируется", str(ctx.exception))

    def test_rejects_min_count_zero_for_dir_count(self):
        rules = [{"id": "any_files_here", "kind": "dir_count", "glob": "*.md", "min_count": 0}]
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict(rules))
        self.assertIn("min_count", str(ctx.exception))

    def test_reports_all_problems_at_once(self):
        rules = [
            {"id": "BAD", "kind": "nope"},
            {"id": "also_bad", "kind": "file_exists"},
        ]
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict(rules))
        self.assertGreaterEqual(len(ctx.exception.problems), 3)

    def test_rejects_too_many_rules(self):
        rules = [{"id": f"rule_number_{i}", "kind": "file_exists", "path": "a"} for i in range(201)]
        with self.assertRaises(SpecError) as ctx:
            parse_spec(_spec_dict(rules))
        self.assertIn("не больше 200", str(ctx.exception))


class LoadSpecTests(unittest.TestCase):
    def test_missing_file(self):
        with self.assertRaises(SpecError) as ctx:
            load_spec(Path("/nonexistent/rubric.yaml"))
        self.assertIn("не найден", str(ctx.exception))

    def test_empty_file(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write("")
            name = handle.name
        with self.assertRaises(SpecError) as ctx:
            load_spec(Path(name))
        self.assertIn("пуста", str(ctx.exception))

    def test_broken_yaml(self):
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
            handle.write("id: [unclosed\n")
            name = handle.name
        with self.assertRaises(SpecError) as ctx:
            load_spec(Path(name))
        self.assertIn("YAML", str(ctx.exception))

    def test_shipped_rubric_is_valid(self):
        rubric = Path(__file__).resolve().parents[1] / "rubrics" / "practice_04.yaml"
        spec = load_spec(rubric)
        self.assertEqual(spec.id, "practice_04")
        self.assertGreaterEqual(len(spec.rules), 10)


if __name__ == "__main__":
    unittest.main()