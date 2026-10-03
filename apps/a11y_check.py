"""모든 웹앱의 접근성 자동 점검(axe-core, WCAG 2.1 A·AA). 라이트·다크 둘 다 본다.

준비: npm install axe-core@4   (또는 AXE 환경변수로 axe.min.js 위치 지정)
      따뜻함 채점기: apps/warmth-scorer 에서 python -m http.server 8765
      페르소나 실험실: apps/voice-persona 에서 streamlit run app.py --server.port 8502
실행: python apps/a11y_check.py   (Playwright 필요. Chromium 위치는 CHROMIUM 환경변수)
2026-10-03: 우리 코드 위반 0. 페르소나 실험실의 #MainMenu aria-expanded 1건은 Streamlit 자체 메뉴라 남음.
"""
from playwright.sync_api import sync_playwright
import json,sys
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
AXE = os.environ.get("AXE", "node_modules/axe-core/axe.min.js")
pages=[("시작 화면",(ROOT/"apps/index.html").as_uri(),None),
       ("녹음 부스",(ROOT/"apps/voice-studio/index.html").as_uri(),None),
       ("낭독 코치",(ROOT/"apps/reading-coach/index.html").as_uri(),None),
       ("따뜻함 채점기","http://127.0.0.1:8765/index.html","example"),
       ("페르소나 실험실","http://127.0.0.1:8502","persona")]
with sync_playwright() as p:
    b=p.chromium.launch(**({'executable_path': os.environ['CHROMIUM']} if os.environ.get('CHROMIUM') else {}))
    for name,url,mode in pages:
        for scheme in ("light","dark"):
            if mode=="persona" and scheme=="dark": continue
            pg=b.new_page(viewport={'width':1280,'height':900},color_scheme=scheme)
            try: pg.goto(url); pg.wait_for_timeout(3000 if mode=="persona" else 800)
            except Exception as e: print(name,"열기 실패",e); continue
            if mode=="example":
                try: pg.click("#load-example"); pg.wait_for_timeout(300)
                except Exception: pass
            pg.add_script_tag(path=AXE)
            r=pg.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,n:v.nodes.length,help:v.help,t:v.nodes.slice(0,3).map(n=>n.target.join(' ')+' | '+(n.failureSummary||'').split('\\n').slice(1,2).join(''))}))}")
            print(f"== {name} ({scheme}): 위반 {len(r)}종")
            for v in r: print(f"  [{v['impact']}] {v['id']} x{v['n']}: {v['help']}"); [print('     ',t[:200]) for t in v['t']]
            pg.close()
    b.close()
