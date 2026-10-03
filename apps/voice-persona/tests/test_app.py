import sys,unittest
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

    def test_ab_table_shows_measured_values_and_missing_speech(self):
        sys.path.insert(0,str(ROOT/'tests'))
        from test_core import riff,tone_pause_tone,wav_bytes
        self.app.button(key='prepare').click().run()
        fp=self.app.session_state['result'].fingerprint
        self.app.session_state['audio_by_result'][fp]={'A':riff(tone_pause_tone(.6),16),'B':wav_bytes(silent=True)}
        self.app.run()
        self.assertFalse(self.app.exception)
        headers=[c for t in self.app.table for c in t.value.columns]
        self.assertEqual(headers,['항목','A','B','B 설계값(참고)'])
        text=str(self.app.table[0].value)
        self.assertIn('0.60초',text);self.assertIn('말소리를 찾지 못했습니다',text)

    def test_new_work_drops_previous_recordings_and_says_so(self):
        sys.path.insert(0,str(ROOT/'tests'))
        from test_core import wav_bytes
        self.app.button(key='prepare').click().run()
        first=self.app.session_state['result'].fingerprint
        self.app.session_state['audio_by_result'][first]={'A':wav_bytes(),'B':wav_bytes(seconds=1)}
        self.app.run()
        self.app.text_area(key='source_input').set_value('다른 안내입니다.').run()
        self.app.button(key='prepare').click().run()
        self.assertFalse(self.app.exception)
        second=self.app.session_state['result'].fingerprint
        self.assertNotEqual(first,second)
        self.assertEqual(list(self.app.session_state['audio_by_result']),[second])
        self.assertTrue(any('이전 작업의 녹음 2개' in i.value for i in self.app.info))

    def test_same_work_keeps_recordings(self):
        sys.path.insert(0,str(ROOT/'tests'))
        from test_core import wav_bytes
        self.app.button(key='prepare').click().run()
        fp=self.app.session_state['result'].fingerprint
        self.app.session_state['audio_by_result'][fp]={'A':wav_bytes()}
        self.app.button(key='prepare').click().run()
        self.assertEqual(list(self.app.session_state['audio_by_result'][fp]),['A'])
        self.assertFalse(self.app.exception)

if __name__=='__main__':unittest.main(verbosity=2)
