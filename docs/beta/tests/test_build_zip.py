"""베타 빌드 허용 필드(R20-6)와 zip 방어(R20-5·R20-11) 검사. 실행: python -m unittest docs/beta/tests/test_build_zip.py -v"""
import copy
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[3]


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


build = load("beta_build", "docs/beta/build.py")
mz = load("make_beta_zip", "tools/make_beta_zip.py")
RUBRIC = json.loads((ROOT / "apps/warmth-scorer/rubric.json").read_text(encoding="utf-8"))
PACK = json.loads((ROOT / "docs/eval/packs/calibration-v0.json").read_text(encoding="utf-8"))


class BuildWhitelist(unittest.TestCase):
    def test_answer_extra_field_is_rejected(self):  # R20-6 재현: 답변에 scores를 넣어도 통과하던 문제
        p = copy.deepcopy(PACK)
        p["items"][0]["answers"][0]["scores"] = {"notice": 2}
        with self.assertRaises(SystemExit):
            build.build_data(RUBRIC, p)

    def test_item_extra_field_is_rejected(self):
        for key in ("kind", "intended_total", "rationale", "why_chosen"):
            p = copy.deepcopy(PACK)
            p["items"][0][key] = "x"
            with self.assertRaises(SystemExit, msg=key):
                build.build_data(RUBRIC, p)

    def test_output_only_allowed_fields(self):
        d = build.build_data(RUBRIC, PACK)
        build.check_data(d)
        for it in d["pack"]["items"]:
            self.assertLessEqual(set(it), set(build.ITEM_OUT_KEYS))
            self.assertTrue(all(set(a) == {"text"} for a in it["answers"]))

    def test_check_data_catches_injected_fields(self):
        d = build.build_data(RUBRIC, PACK)
        d["pack"]["items"][0]["answers"][0]["kind"] = "low"
        with self.assertRaises(AssertionError):
            build.check_data(d)

    def test_index_html_is_current(self):
        self.assertEqual((ROOT / "docs/beta/index.html").read_text(encoding="utf-8"), build.build())


class ZipGuard(unittest.TestCase):
    def test_walk_skips_virtualenv_keys_and_recordings(self):  # R20-11
        with tempfile.TemporaryDirectory() as t:
            base = pathlib.Path(t) / "apps"
            for rel in ("a/index.html", "a/.venv/pyvenv.cfg", "a/.venv/lib/x.py", "a/venv/y.py", "a/.venv314/z.py", "a/x.key.json",
                        "a/rec.wav", "a/tests/t.js", "a/__pycache__/m.pyc", "a/GPT_PROMPT.md", "a/.env", "a/.streamlit/config.toml", "a/ok.js"):
                f = base / rel
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("x", encoding="utf-8")
            got = sorted(p.relative_to(base).as_posix() for p in mz.walk(base))
            self.assertEqual(got, ["a/.streamlit/config.toml", "a/index.html", "a/ok.js"])

    def test_real_candidates_have_no_venv_or_key(self):
        names = [n for _, n in mz.files()]
        self.assertFalse([n for n in names if mz.FORBIDDEN_RE.search(n)])
        self.assertFalse([n for n in names if ".venv" in n])

    def test_key_file_candidate_aborts_before_any_zip(self):  # R20-5 재현: 열쇠가 후보에 끼면 압축을 만들기 전에 멈춤
        key = ROOT / "docs/eval/packs/calibration-v0.key.json"
        orig = mz.files
        mz.files = lambda: iter([(key, f"{mz.TOP}/작업실/calibration-v0.key.json")])
        try:
            with tempfile.TemporaryDirectory() as t:
                with self.assertRaises(AssertionError):
                    mz.main(["x", t])
                self.assertEqual(list(pathlib.Path(t).iterdir()), [])
        finally:
            mz.files = orig

    def test_page_with_extra_answer_field_aborts(self):
        html = (ROOT / "docs/beta/index.html").read_text(encoding="utf-8")
        bad = html.replace('{"text":', '{"scores": 1, "text":', 1)
        self.assertNotEqual(html, bad)
        with self.assertRaises(AssertionError):
            mz.check_candidates([], bad, ROOT / "docs/eval/packs/calibration-v0.json")

    def test_real_zip_listing(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(mz.main(["x", t]), 0)
            files = list(pathlib.Path(t).iterdir())
            self.assertEqual([f.suffix for f in files], [".zip"])
            names = zipfile.ZipFile(files[0]).namelist()
            self.assertFalse([n for n in names if mz.FORBIDDEN_RE.search(n) or ".venv" in n or "docs/gpt" in n or "key" in n.lower()])
            self.assertTrue(any(n.endswith("베타-채점.html") for n in names))


if __name__ == "__main__":
    unittest.main()
