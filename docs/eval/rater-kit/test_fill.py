"""fill.py 검사 (표준 라이브러리 unittest). 파일은 임시 폴더에만 써요."""
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fill  # noqa: E402

REAL = pathlib.Path(fill.HERE)


class FillTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.old = fill.HERE
        fill.HERE = self.tmp / "kit"
        shutil.copytree(REAL / "templates", fill.HERE / "templates")
        self.addCleanup(setattr, fill, "HERE", self.old)
        keys = set()
        for t in (fill.HERE / "templates").glob("*.md"):
            keys |= {m.strip() for m in fill.TOKEN.findall(t.read_text(encoding="utf-8"))}
        self.good = {k: "가나다 1" for k in keys}
        self.good["평가자_코드"] = "R-ab12"

    def run_fill(self, values):
        f = self.tmp / "v.json"
        f.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
        return fill.main(["fill.py", str(f)])

    def outs(self):
        return list(self.tmp.rglob("*.md")) and [p for p in self.tmp.rglob("*") if "out" in p.parts]

    def test_good(self):
        self.assertEqual(self.run_fill(self.good), 0)
        out = fill.HERE / "out" / "R-ab12"
        self.assertEqual(len(list(out.glob("*.md"))), 3)
        for p in out.glob("*.md"):
            self.assertNotIn("{{", p.read_text(encoding="utf-8"))

    def test_bad_codes(self):
        for code in ["../escape", "R-../x", "R-ab/cd", "C:\evil", "/abs/path", "R-a",
                     "R-123456789", "R-__", "r-ab12", "", None, "R-ab12\n", "R-한글"]:
            v = dict(self.good, 평가자_코드=code)
            self.assertEqual(self.run_fill(v), 1, repr(code))
        self.assertFalse((fill.HERE / "out").exists())
        self.assertFalse((self.tmp / "escape").exists())

    def test_missing_code(self):
        v = dict(self.good)
        del v["평가자_코드"]
        self.assertEqual(self.run_fill(v), 1)

    def test_empty_values(self):
        key = next(k for k in self.good if k != "평가자_코드")
        bad = ["", "  ", "\u3000", "\u200b", "\u200b \u3000", "___", "R-__", "__", "-", "...",
               "해당 없음", "해당없음", "없음", "미정", "TBD", "N/A", "0원", "0", "0 원",
               None, [], {}, 0, False, "{{unresolved}}", "값 {{x}}"]
        for b in bad:
            v = dict(self.good)
            v[key] = b
            self.assertEqual(self.run_fill(v), 1, repr(b))
        v = dict(self.good)
        del v[key]
        self.assertEqual(self.run_fill(v), 1)

    def test_normal_values_ok(self):
        key = next(k for k in self.good if k != "평가자_코드")
        for ok in ["10,000원", "2026-10-20", "운영자(성우 김디도)", "010-0000-0000"]:
            v = dict(self.good)
            v[key] = ok
            self.assertEqual(self.run_fill(v), 0, ok)


if __name__ == "__main__":
    unittest.main()
