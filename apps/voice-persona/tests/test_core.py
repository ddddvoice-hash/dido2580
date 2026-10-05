import io,json,math,struct,unittest,wave,array
from dataclasses import replace
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import *
from core import _frame_size as core_frame_size
import shutil,subprocess

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

PCM_GUID=bytes.fromhex("0100000000001000800000aa00389b71")
FLOAT_GUID=bytes.fromhex("0300000000001000800000aa00389b71")

def sine(seconds,rate,amp=.4,freq=240):
    return [amp*math.sin(2*math.pi*freq*i/rate) for i in range(round(seconds*rate))]

def encode(values,bits,code):
    if code==3:return array.array('f',values).tobytes()
    top=2**(bits-1)-1
    ints=[max(-top-1,min(top,round(v*top))) for v in values]
    if bits==16:return array.array('h',ints).tobytes()
    if bits==32:return array.array('i',ints).tobytes()
    return b''.join(i.to_bytes(3,'little',signed=True) for i in ints)

def riff(values,bits=16,code=1,rate=24000,channels=1,extensible=False,declared=None,fmt_last=False,pad_chunk=False,block=None):
    """메모리에서 WAV를 만든다. declared는 data 선언 크기, fmt_last는 data 뒤에 fmt를 둔다."""
    body=encode(values,bits,code)
    block=channels*bits//8 if block is None else block
    if extensible:
        fmt=struct.pack('<HHIIHH',0xFFFE,channels,rate,rate*block,block,bits)+struct.pack('<HHI',22,bits,3)+(PCM_GUID if code==1 else FLOAT_GUID)
    else:
        fmt=struct.pack('<HHIIHH',code,channels,rate,rate*block,block,bits)
    fmt_chunk=b'fmt '+struct.pack('<I',len(fmt))+fmt
    data_chunk=b'data'+struct.pack('<I',len(body) if declared is None else declared)+body+(b'\0' if len(body)%2 else b'')
    parts=[]
    if pad_chunk:parts.append(b'LIST'+struct.pack('<I',3)+b'abc\0')
    parts+=[data_chunk,fmt_chunk] if fmt_last else [fmt_chunk,data_chunk]
    payload=b'WAVE'+b''.join(parts)
    return b'RIFF'+struct.pack('<I',len(payload))+payload

def tone_pause_tone(gap,rate=24000):
    return sine(1,rate)+[0.0]*round(gap*rate)+sine(1,rate)

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
        for raw in [b'',b'not audio',wav_bytes()[:-100],wav_bytes(seconds=0)]:
            with self.assertRaises(ValueError):analyze_wav(raw)

class FormatTests(unittest.TestCase):
    def check_ok(self,raw,duration=.5,channels=1):
        meta=analyze_wav(raw)
        self.assertAlmostEqual(meta['duration'],duration,places=3);self.assertEqual(meta['channels'],channels)
        self.assertAlmostEqual(meta['sampled_peak'],.4,places=2)
        self.assertTrue(all(0<=v<=1 for v in meta['envelope']))
        return meta
    def test_24bit_pcm_accepted(self):self.check_ok(riff(sine(.5,24000),24))
    def test_24bit_wave_module_file_accepted(self):
        # 이전에는 거부하던 wave 모듈 작성 24bit 파일(기존 사례를 통과 쪽으로 옮김)
        self.assertEqual(analyze_wav(wav_bytes(width=3))['sample_rate'],24000)
    def test_32bit_pcm_accepted(self):self.check_ok(riff(sine(.5,24000),32))
    def test_32bit_float_accepted(self):self.check_ok(riff(sine(.5,24000),32,code=3))
    def test_extensible_24bit_pcm_accepted(self):self.check_ok(riff(sine(.5,48000),24,rate=48000,extensible=True))
    def test_extensible_float_accepted(self):self.check_ok(riff(sine(.5,24000),32,code=3,extensible=True))
    def test_stereo_24bit_same_level_as_16bit(self):
        values=[v for x in sine(.5,24000) for v in (x,x)]
        a=analyze_wav(riff(values,16,channels=2));b=analyze_wav(riff(values,24,channels=2))
        self.assertEqual(b['channels'],2);self.assertAlmostEqual(a['rms_dbfs'],b['rms_dbfs'],places=1)
    def test_chunk_order_and_odd_padding(self):
        self.check_ok(riff(sine(.5,24000),24,fmt_last=True))
        self.check_ok(riff(sine(.5,24000),16,pad_chunk=True))
        self.check_ok(riff(sine(.5,24000),24,pad_chunk=True,fmt_last=True))
    def test_truncated_data_rejected(self):
        raw=riff(sine(.5,24000),24)
        with self.assertRaises(ValueError):analyze_wav(raw[:-300])
        with self.assertRaises(ValueError):analyze_wav(riff(sine(.5,24000),16,declared=999999))
    def test_non_finite_float_rejected(self):
        for bad in (float('nan'),float('inf'),float('-inf')):
            values=sine(.5,24000);values[5000]=bad
            with self.assertRaises(ValueError):analyze_wav(riff(values,32,code=3))
    def test_unsupported_formats_rejected(self):
        eight=riff([0.0]*4800,16).replace(struct.pack('<HHIIHH',1,1,24000,48000,2,16),struct.pack('<HHIIHH',1,1,24000,24000,1,8))
        bad_guid=riff(sine(.5,24000),24,extensible=True).replace(PCM_GUID[4:],b'\0'*12)
        cases=[eight,riff(sine(.5,24000),16,rate=4000),riff(sine(.5,24000),16,rate=200000),riff(sine(.5,24000),16,block=4),
               riff(sine(.5,24000),16).replace(b'RIFF',b'RIFX',1),bad_guid,riff([],16)]
        for raw in cases:
            with self.assertRaises(ValueError):analyze_wav(raw)
    def test_ten_minutes_ok_and_longer_rejected(self):
        ok=analyze_wav(riff([0.0]*(8000*600),16,rate=8000))
        self.assertEqual(ok['duration'],600)
        with self.assertRaises(ValueError):analyze_wav(riff([0.0]*(8000*601),16,rate=8000))
    def test_size_limit_covers_48k_32bit_stereo_ten_minutes(self):
        self.assertGreaterEqual(MAX_AUDIO,48000*4*2*600)
        with self.assertRaises(ValueError):analyze_wav(b'RIFF'+b'\0'*MAX_AUDIO)

class SpeechMeasureTests(unittest.TestCase):
    def test_06_second_pause_measured(self):
        m=analyze_wav(riff(tone_pause_tone(.6),16))['speech']
        self.assertTrue(m['found']);self.assertEqual(m['pause_count'],1)
        self.assertAlmostEqual(m['pause_longest'],.6,delta=.04);self.assertAlmostEqual(m['pause_median'],.6,delta=.04)
        self.assertAlmostEqual(m['speech_start'],0,delta=.04);self.assertAlmostEqual(m['speech_end'],2.6,delta=.04)
        self.assertAlmostEqual(m['spoken'],2.0,delta=.06)
    def test_measure_speech_function_on_samples(self):
        m=measure_speech(tone_pause_tone(.6),24000)
        self.assertEqual(m['pause_count'],1);self.assertAlmostEqual(m['pause_longest'],.6,delta=.04)
    def test_leading_and_trailing_silence_not_counted(self):
        m=measure_speech([0.0]*24000+tone_pause_tone(.6)+[0.0]*24000,24000)
        self.assertEqual(m['pause_count'],1);self.assertAlmostEqual(m['speech_start'],1,delta=.04);self.assertAlmostEqual(m['speech_end'],3.6,delta=.04)
    def test_short_02_second_gap_is_not_a_pause(self):
        m=measure_speech([0.0]*12000+tone_pause_tone(.2)+[0.0]*12000,24000)  # 바닥(하위 10%)을 잡으려면 앞뒤 무음이 필요하다
        self.assertTrue(m['found']);self.assertEqual(m['pause_count'],0)
        self.assertIsNone(m['pause_median']);self.assertIsNone(m['pause_longest'])
    def test_silence_only_has_no_speech(self):
        for m in (measure_speech([0.0]*24000,24000),analyze_wav(wav_bytes(silent=True))['speech']):
            self.assertFalse(m['found']);self.assertIsNone(m['speech_start']);self.assertEqual(m['pause_count'],0)
    def test_very_quiet_and_short_blip_have_no_speech(self):
        self.assertFalse(measure_speech([v*.01 for v in sine(1,24000)],24000)['found'])
        self.assertFalse(measure_speech([0.0]*24000+sine(.04,24000)+[0.0]*24000,24000)['found'])
    def test_works_on_24bit_stereo(self):
        values=[v for x in tone_pause_tone(.6,48000) for v in (x,x)]
        m=analyze_wav(riff(values,24,rate=48000,channels=2))['speech']
        self.assertEqual(m['pause_count'],1);self.assertAlmostEqual(m['pause_longest'],.6,delta=.04)

class BackupTests(unittest.TestCase):
    def test_large_recordings_rejected_with_clear_message(self):
        r=build_result(inputs());big=riff([0.0]*2,16,rate=24000,declared=24000*2*600)[:-4]+bytes(24000*2*600)
        with self.assertRaises(ValueError) as e:make_bundle(r,{'A':big,'B':big},{},'')
        self.assertIn('작업 JSON',str(e.exception))
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


class CacheTests(unittest.TestCase):
    def test_repeat_analysis_is_cached_copy(self):
        data=wav_bytes(seconds=1.2)
        first=analyze_wav(data)
        first['envelope'].clear();first['speech']['found']='changed'
        again=analyze_wav(data)
        self.assertTrue(again['envelope']);self.assertNotEqual(again['speech']['found'],'changed')
        self.assertEqual(again['sha256'],first['sha256'])
    def test_invalid_data_is_not_cached_as_valid(self):
        with self.assertRaises(ValueError):analyze_wav(b'not audio')
        with self.assertRaises(ValueError):analyze_wav(b'not audio')


class ReviewFixTests(unittest.TestCase):
    """6번 교차 리뷰 반영(2026-10-03). 기존 테스트는 그대로 두고 추가한다."""
    def pad(self,seconds=.5,rate=24000):return [0.0]*round(seconds*rate)
    def speech(self,values):return measure_speech(self.pad()+values+self.pad(),24000)

    def test_blip_60ms_rejected_and_80ms_kept_with_real_threshold(self):
        # 앞에 긴 소리가 있어 임계값 검사는 통과한다. 짧은 소리 필터만 결과를 가른다.
        def run(blip):return measure_speech(sine(1,24000)+self.pad()+sine(blip,24000)+self.pad()+self.pad(),24000)
        short,ok=run(.06),run(.08)
        self.assertTrue(short['found']);self.assertEqual(short['pause_count'],0)
        self.assertEqual(ok['pause_count'],1)  # 80ms 소리는 말소리로 남아 앞의 0.5초 쉼이 잡힌다

    def test_pause_boundary_240_not_counted_260_counted(self):
        self.assertEqual(self.speech(tone_pause_tone(.24))['pause_count'],0)
        m=self.speech(tone_pause_tone(.26))
        self.assertEqual(m['pause_count'],1);self.assertAlmostEqual(m['pause_longest'],.26,delta=.001)

    def test_frame_size_rounds_half_up_like_js(self):
        self.assertEqual(core_frame_size(8025),161);self.assertEqual(core_frame_size(8000),160)
        self.assertEqual(core_frame_size(44100),882);self.assertEqual(core_frame_size(11025),221)

    def test_riff_declared_size_checked(self):
        good=riff(sine(.5,24000),16)
        for size in (0,0xFFFFFFFF):  # 스트리밍 도구가 남기는 자리표시값은 허용
            analyze_wav(good[:4]+struct.pack('<I',size)+good[8:])
        with self.assertRaises(ValueError):analyze_wav(good[:4]+struct.pack('<I',4)+good[8:])
        with self.assertRaises(ValueError):analyze_wav(good[:4]+struct.pack('<I',30)+good[8:])
        analyze_wav(good+b'junk')  # 파일 끝에 덧붙은 바이트는 허용

    def test_data_size_must_be_whole_frames(self):
        body=encode(sine(.5,24000),16,1)
        for declared in (len(body)-1,len(body)-3):  # 16bit 모노에서 샘플(2바이트)로 나누어 떨어지지 않는 크기
            with self.assertRaises(ValueError):analyze_wav(riff(sine(.5,24000),16,declared=declared))
        stereo=encode(sine(.5,24000),16,1)  # 스테레오는 4바이트 단위: 2바이트 어긋남도 거부
        with self.assertRaises(ValueError):analyze_wav(riff(sine(.5,24000),16,channels=2,declared=len(stereo)-2))

    def test_extensible_valid_bits_and_cbsize_checked(self):
        good=riff(sine(.5,24000),32,rate=24000,extensible=True)
        analyze_wav(good)
        bad_bits=bytearray(good);bad_bits[38:40]=struct.pack('<H',33)   # 컨테이너 32bit에 유효 비트 33
        with self.assertRaises(ValueError):analyze_wav(bytes(bad_bits))
        bad_cb=bytearray(good);bad_cb[36:38]=struct.pack('<H',65535)    # fmt 청크 밖까지 선언한 확장 길이
        with self.assertRaises(ValueError):analyze_wav(bytes(bad_cb))
        ok_bits=bytearray(good);ok_bits[38:40]=struct.pack('<H',24)     # 32bit 컨테이너의 24bit 유효 비트는 정상
        analyze_wav(bytes(ok_bits))

    def test_deeply_nested_backup_is_user_error(self):
        for raw in (b'['*20000+b']'*20000,b'{"a":'*20000+b'1'+b'}'*20000):
            with self.assertRaises(ValueError) as e:load_bundle(raw)
            self.assertIn('현재 작업은 유지',str(e.exception))

    def test_decode_memory_does_not_scale_with_input(self):
        import tracemalloc
        n=48000*6*40  # 48kHz 24bit 스테레오 40초
        head=riff([0.0]*2,24,rate=48000,channels=2,declared=n)[:-6]
        data=head[:4]+struct.pack('<I',len(head)-8+n)+head[8:]+bytes(range(256))*(n//256)+bytes(n%256)
        tracemalloc.start();base=tracemalloc.get_traced_memory()[0];tracemalloc.reset_peak()
        analyze_wav(data);extra=tracemalloc.get_traced_memory()[1]-base;tracemalloc.stop()
        self.assertLess(extra,len(data))  # 이전 구현은 입력의 약 2.75배였다

    def test_session_audio_limit_and_cleanup_helpers(self):
        self.assertGreaterEqual(MAX_SESSION_AUDIO,2*MAX_AUDIO)
        store={'a':{'A':b'12','B':b'345'},'b':{'A':b'6'}}
        self.assertEqual(audio_total(store),6)
        dropped,count=drop_other_audio(store,'b')
        self.assertEqual((dropped,count),(['a'],2));self.assertEqual(list(store),['b'])


NODE=shutil.which('node');ANALYSIS_JS=Path(__file__).resolve().parents[2]/'reading-coach'/'analysis.js'
JS_RUNNER="""const A=require(process.argv[1]);const cases=JSON.parse(require('fs').readFileSync(0,'utf8'));
console.log(JSON.stringify(cases.map(c=>{const r=A.analyze(Float32Array.from(c.samples),c.rate);
return {found:r.speechEnd>0,start:r.speechStart,end:r.speechEnd,spoken:r.spoken,pauses:r.pauses.length,longest:Math.max(0,...r.pauses.map(p=>p.length))};})));"""

@unittest.skipUnless(NODE and ANALYSIS_JS.exists(),'node가 없어 JS 비교는 건너뜁니다')
class JsParityTests(unittest.TestCase):
    """apps/reading-coach/analysis.js를 node로 실제 돌려 같은 합성음에서 결과가 같은지 비교한다."""
    def js(self,cases):
        out=subprocess.run([NODE,'-e',JS_RUNNER,str(ANALYSIS_JS)],input=json.dumps([{'samples':s,'rate':r} for s,r in cases]),capture_output=True,text=True,encoding='utf-8',check=True,timeout=60)
        return json.loads(out.stdout)
    def same(self,py,js,label):
        self.assertEqual(py['found'],js['found'],label)
        if not py['found']:return
        self.assertAlmostEqual(py['speech_start'],js['start'],places=9,msg=label)
        self.assertAlmostEqual(py['speech_end'],js['end'],places=9,msg=label)
        self.assertAlmostEqual(py['spoken'],js['spoken'],places=9,msg=label)
        self.assertEqual(py['pause_count'],js['pauses'],label)
        self.assertAlmostEqual(py['pause_longest'] or 0,js['longest'],places=9,msg=label)
    def test_synthetic_cases_match_js(self):
        def lead(rate,body):return [0.0]*round(.5*rate)+body+[0.0]*round(.5*rate)
        cases=[]
        for rate in (8000,8025,11025,16000,24000,44100,48000):  # 8025Hz는 프레임이 160.5샘플
            cases.append((lead(rate,sine(1,rate)+[0.0]*round(.6*rate)+sine(1,rate)),rate))
        r=24000
        for gap in (.24,.26):cases.append((lead(r,tone_pause_tone(gap,r)),r))
        for blip in (.06,.08):cases.append((sine(1,r)+[0.0]*r+sine(blip,r)+[0.0]*r*2,r))
        for amp in (.0139,.0141,.0143):cases.append((lead(r,sine(1,r,amp=amp)+[0.0]*(r//2)+sine(1,r,amp=amp)),r))  # 0.01 경계(RMS=amp/√2)
        for (samples,rate),js in zip(cases,self.js(cases)):
            self.same(measure_speech(samples,rate),js,f'{rate}Hz n={len(samples)}')
    def test_32bit_pcm_precision_matches_js(self):
        r=24000
        for amp in (.0139,.0141,.0143,.2):
            values=[0.0]*r+sine(1,r,amp=amp)+[0.0]*(r//2)+sine(1,r,amp=amp)+[0.0]*r
            ints=array.array('i');ints.frombytes(encode(values,32,1))
            py=analyze_wav(riff(values,32,rate=r))['speech']
            self.same(py,self.js([([i/2**31 for i in ints],r)])[0],f'32bit amp={amp}')


class StepAndExampleTests(unittest.TestCase):
    def test_example_replace_rule(self):
        self.assertTrue(can_replace_with_example("",["예문"]))
        self.assertTrue(can_replace_with_example(" 예문 ",["예문"]))
        self.assertFalse(can_replace_with_example("직접 쓴 글",["예문"]))

    def test_step_states_reflect_real_checks(self):
        self.assertEqual(step_states(False,0,False,False),["now","","","",""])
        self.assertEqual(step_states(True,0,False,False),["done","avail","now","","avail"])
        self.assertEqual(step_states(True,2,False,True),["done","avail","done","now","avail"])
        self.assertEqual(step_states(True,2,True,False)[3],"now")
        self.assertEqual(step_states(True,2,True,True)[3],"done")


if __name__=='__main__':unittest.main(verbosity=2)
