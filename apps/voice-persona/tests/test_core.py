import io,json,math,struct,unittest,wave
from dataclasses import replace
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import *

def inputs(source="파일 업로드가 실패했습니다. 파일은 삭제되지 않았습니다. '다시 업로드'를 눌러 주세요.", **changes):
    return {"source":source,"persona":"senior","scenario":"error","mode":"original","rate":.85,"pause_ms":850,**changes}

def wav_bytes(seconds=.8,channels=1,silent=False,width=2):
    out=io.BytesIO()
    with wave.open(out,'wb') as f:
        f.setnchannels(channels);f.setsampwidth(width);f.setframerate(24000)
        if width==2:
            data=b''.join(struct.pack('<h',0 if silent else int(6000*math.sin(2*math.pi*240*i/24000))) for i in range(round(24000*seconds)) for _ in range(channels))
        else:data=b'\x00'*round(24000*seconds)*channels*width
        f.writeframes(data)
    return out.getvalue()

class ContentTests(unittest.TestCase):
    def test_all_personas_scenarios_preserve_source(self):
        for persona in PERSONAS:
            for scenario in SCENARIOS:
                r=build_result(inputs(persona=persona,scenario=scenario))
                self.assertEqual(r.text,r.source)
    def test_upload_never_becomes_account_lock(self):
        r=build_result(inputs(mode="terms",persona="visual"))
        self.assertEqual(r.text,"파일을 올리지 못했습니다. 파일은 삭제되지 않았습니다. '다시 업로드'를 눌러 주세요.")
        for forbidden in ['지문','계정','1588','즉시','오른쪽']:self.assertNotIn(forbidden,r.text)
    def test_missing_info_not_invented(self):
        s="통신 연결이 끊겼습니다."
        self.assertEqual(build_result(inputs(s,mode='terms')).text,s)
    def test_numbers_negative_conditions_and_forbidden_actions_preserved(self):
        samples=["계정이 잠기지 않았습니다.","삭제는 완료되지 않았습니다. 다시 업로드하지 마세요.",
                 "14:30까지 2.5MB 이하 파일을 첨부하세요.","오류가 감지되면 고객센터에 문의하세요. 감지되지 않으면 계속하세요.",
                 "3회 실패하여 계정이 잠겼습니다. 24시간 후 다시 시도하세요."]
        for s in samples:self.assertEqual(build_result(inputs(s,mode='terms')).text,s)
    def test_quotes_code_urls_and_labels_protected(self):
        s='"파일 업로드" 버튼을 누르세요. `에러 코드` https://example.com/파일 업로드'
        r=build_result(inputs(s,mode='terms'))
        self.assertEqual(r.text,s)
    def test_unquoted_control_names_protected(self):
        for source in ["파일 업로드 버튼을 누르십시오.","에러 코드 메뉴를 선택하세요.","파일 업로드 탭에서 확인하십시오."]:
            self.assertEqual(build_result(inputs(source,mode="terms")).text,source)
    def test_whitelisted_edits_logged_and_replayable(self):
        s="에러 코드 404: 지문 생체 인증에 3회 연속 실패했습니다. 고객센터로 문의하십시오."
        r=build_result(inputs(s,mode='terms'))
        self.assertEqual(len(r.edits),4)
        verify_edits(r.source,r.text,r.edits)
        self.assertIn('3번 연속',r.text)
    def test_unlogged_or_unknown_change_rejected(self):
        r=build_result(inputs(mode='terms'))
        with self.assertRaises(ValueError):verify_edits(r.source,r.text+' 고객센터 1588-1234',r.edits)
        with self.assertRaises(ValueError):verify_edits(r.source,r.text,(replace(r.edits[0],rule_id='unknown'),))
    def test_unicode_whitespace_and_linebreaks_preserved(self):
        s="  🙂 안내\n\n파일은 삭제되지 않았습니다.\n"
        self.assertEqual(build_result(inputs(s,mode='terms')).text,s)
    def test_input_change_invalidates_result(self):
        base=inputs();r=build_result(base)
        for changes in [{"source":"다른 안내"},{"persona":"visual"},{"scenario":"complete"},{"mode":"terms"},{"rate":.9},{"pause_ms":900}]:
            self.assertFalse(result_is_current(r,{**base,**changes}))
        self.assertTrue(result_is_current(r,base))
    def test_empty_oversize_and_invalid_types(self):
        for source in ['', '  ', 'a'*(MAX_TEXT+1)]:
            with self.assertRaises(ValueError):build_result(inputs(source))
        for changes in [{"rate":True},{"rate":float('nan')},{"pause_ms":True},{"persona":[]},{"mode":"ai"}]:
            with self.assertRaises(ValueError):build_result(inputs(**changes))
    def test_markup_is_text_not_evaluated(self):
        s='<script>alert("x")</script> **강조**'
        self.assertEqual(build_result(inputs(s,mode='terms')).text,s)

class AudioTests(unittest.TestCase):
    def test_wav_duration_and_actual_envelope(self):
        meta=analyze_wav(wav_bytes())
        self.assertEqual(meta['duration'],.8);self.assertEqual(meta['channels'],1)
        self.assertGreater(meta['sampled_peak'],.1);self.assertLessEqual(len(meta['envelope']),128)
    def test_stereo_and_silence(self):
        self.assertEqual(analyze_wav(wav_bytes(channels=2))['channels'],2)
        meta=analyze_wav(wav_bytes(silent=True));self.assertIsNone(meta['rms_dbfs']);self.assertEqual(meta['sampled_peak'],0)
    def test_invalid_truncated_and_wrong_pcm_rejected(self):
        for raw in [b'',b'not audio',wav_bytes()[:-100],wav_bytes(width=3),wav_bytes(seconds=0)]:
            with self.assertRaises(ValueError):analyze_wav(raw)

class BackupTests(unittest.TestCase):
    def test_full_backup_round_trip(self):
        r=build_result(inputs(mode='terms'));audio={'A':wav_bytes(),'B':wav_bytes(seconds=1)}
        packet=make_bundle(r,audio,{'A':True,'B':False},'B가 더 또렷하게 들렸습니다.')
        next_r,next_a,checks,notes=load_bundle(packet)
        self.assertEqual(next_r,r);self.assertEqual(next_a,audio);self.assertTrue(checks['A']);self.assertIn('B가',notes)
    def test_tampered_result_and_audio_rejected(self):
        r=build_result(inputs());packet=json.loads(make_bundle(r,{'A':wav_bytes()},{},''))
        packet['result']['text']='계정이 잠겼습니다.'
        with self.assertRaises(ValueError):load_bundle(json.dumps(packet).encode())
        packet=json.loads(make_bundle(r,{'A':wav_bytes()},{},''));packet['audio']['A']['sha256']='wrong'
        with self.assertRaises(ValueError):load_bundle(json.dumps(packet).encode())
    def test_bad_format_base64_and_checks_rejected(self):
        for raw in [b'not json',b'null',b'{"format":"other","version":1}']:
            with self.assertRaises(ValueError):load_bundle(raw)
        r=build_result(inputs());packet=json.loads(make_bundle(r,{'A':wav_bytes()},{},''))
        packet['audio']['A']['base64']='not!base64'
        with self.assertRaises(ValueError):load_bundle(json.dumps(packet).encode())
        with self.assertRaises(ValueError):make_bundle(r,{}, {'A':'yes'},'')

if __name__=='__main__':unittest.main(verbosity=2)
