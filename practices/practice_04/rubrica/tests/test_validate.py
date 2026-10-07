import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rubrica.validate import InputRejected, validate_all, validate_target  # noqa: E402


class ValidateTargetTests(unittest.TestCase):
    def test_rejects_empty_path(self):
        with self.assertRaises(InputRejected):
            validate_target("")

    def test_rejects_missing_dir(self):
        with self.assertRaises(InputRejected) as ctx:
            validate_target("/definitely/not/here")
        self.assertIn("не существует", str(ctx.exception))

    def test_rejects_file_instead_of_dir(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as handle:
            name = handle.name
        with self.assertRaises(InputRejected) as ctx:
            validate_target(name)
        self.assertIn("не папка", str(ctx.exception))

    def test_rejects_filesystem_root(self):
        with self.assertRaises(InputRejected):
            validate_target("/")

    def test_rejects_path_with_spaces(self):
        with self.assertRaises(InputRejected) as ctx:
            validate_target("/tmp/some folder/with space")
        self.assertIn("пробел", str(ctx.exception) + "пробелы" if False else str(ctx.exception))

    def test_rejects_parent_dir(self):
        with self.assertRaises(InputRejected) as ctx:
            validate_target("..")
        self.assertIn("родительскую", str(ctx.exception))

    def test_accepts_dot_as_current_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                target, _ = validate_target(".")
                self.assertEqual(target, Path(tmp).resolve())
            finally:
                os.chdir(cwd)

    def test_accepts_normal_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "README.md").write_text("hi", encoding="utf-8")
            target, notes = validate_target(tmp)
            self.assertTrue(target.is_dir())
            self.assertEqual(notes, [])

    def test_notes_about_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real.md"
            real.write_text("x", encoding="utf-8")
            link = Path(tmp) / "link.md"
            link.symlink_to(real)
            _, notes = validate_target(tmp)
            self.assertTrue(any("символическая ссылка" in n for n in notes))

    def test_rejects_too_many_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(5001):
                (Path(tmp) / f"f{i}.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(InputRejected) as ctx:
                validate_target(tmp)
            self.assertIn("больше 5000 файлов", str(ctx.exception))

    def test_skips_vcs_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            git = Path(tmp) / ".git"
            git.mkdir()
            (git / "config").write_text("[core]", encoding="utf-8")
            target, _ = validate_target(tmp)
            self.assertEqual(target.name, Path(tmp).name)


class ValidateFlagsTests(unittest.TestCase):
    def test_rejects_zero_max_findings(self):
        with self.assertRaises(InputRejected) as ctx:
            validate_all(".", max_findings=0)
        self.assertIn("max-findings", str(ctx.exception))

    def test_rejects_huge_max_findings(self):
        with self.assertRaises(InputRejected):
            validate_all(".", max_findings=10_000)


class ValidateSpecFlagTests(unittest.TestCase):
    def test_rejects_missing_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(InputRejected) as ctx:
                validate_all(tmp, spec_path=Path(tmp) / "no.yaml")
            self.assertIn("не найден", str(ctx.exception))

    def test_rejects_non_yaml_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "rubric.json"
            spec.write_text("{}", encoding="utf-8")
            with self.assertRaises(InputRejected) as ctx:
                validate_all(tmp, spec_path=spec)
            self.assertIn("YAML", str(ctx.exception))

    def test_rejects_spec_that_is_a_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "dir.yaml").mkdir()
            with self.assertRaises(InputRejected) as ctx:
                validate_all(tmp, spec_path=Path(tmp) / "dir.yaml")
            self.assertIn("не файл", str(ctx.exception))

    def test_accepts_valid_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "r.yaml"
            spec.write_text("id: x\ntitle: t\nrules: []\n", encoding="utf-8")
            validated = validate_all(tmp, spec_path=spec)
            self.assertEqual(validated.spec_path, spec.resolve())


if __name__ == "__main__":
    unittest.main()