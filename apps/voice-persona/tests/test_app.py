import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]

class StreamlitTests(unittest.TestCase):
    def setUp(self):self.app=AppTest.from_file(str(ROOT/'app.py'),default_timeout=15).run()
    def test_initial_and_real_upload_example(self):
        self.assertFalse(self.app.exception)
        self.app.text_area(key='source_input').set_value("파일 업로드가 실패했습니다. 파일은 삭제되지 않았습니다. '다시 업로드'를 눌러 주세요.").run()
        self.app.radio(key='mode_input').set_value('terms').run()
        self.app.button(key='prepare').click().run()
        self.assertFalse(self.app.exception)
        result=self.app.session_state['result']
        self.assertIn('파일을 올리지 못했습니다',result.text)
        self.assertNotIn('계정',result.text)
    def test_change_hides_result_and_blank_does_not_generate(self):
        self.app.button(key='prepare').click().run()
        self.app.text_area(key='source_input').set_value('다른 안내').run()
        self.assertTrue(any('입력이 바뀌었습니다' in w.value for w in self.app.warning))
        self.app.text_area(key='source_input').set_value(' ').run()
        self.app.button(key='prepare').click().run()
        self.assertTrue(self.app.error)
        self.assertFalse(self.app.exception)
    def test_persona_sets_design_only(self):
        self.app.selectbox(key='persona_input').set_value('visual').run()
        self.assertEqual(self.app.session_state['rate_input'],.95)
        self.app.button(key='prepare').click().run()
        self.assertEqual(self.app.session_state['result'].text,self.app.session_state['source_input'])
        self.assertFalse(self.app.exception)

if __name__=='__main__':unittest.main(verbosity=2)
