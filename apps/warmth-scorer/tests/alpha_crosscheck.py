# 크리펜도르프 α 대조 검사: 채점기(app.js)의 krippendorffAlpha와 공개 패키지 krippendorff(서열)를
# 같은 무작위 자료 300묶음(평가자 2~5명, 답변 3~27개, 빈칸 약 15%)으로 비교한다.
# 실행: pip install krippendorff numpy 후, 저장소 맨 위에서 python apps/warmth-scorer/tests/alpha_crosscheck.py
# 모든 점수가 같아 우연 기대치가 0인 묶음은 둘 다 계산할 수 없으므로 비교에서 빼고 개수만 알린다.
import json
import random
import subprocess
import sys
from pathlib import Path

import krippendorff
import numpy as np

HERE = Path(__file__).resolve().parent
rng = random.Random(7)
sets = []
for _ in range(300):
    raters, units = rng.randint(2, 5), rng.randint(3, 27)
    data = []
    for _u in range(units):
        base = rng.randrange(3)
        row = []
        for _r in range(raters):
            if rng.random() < 0.15:
                row.append(None)
            else:
                shift = rng.choice([-1, 1]) if rng.random() < 0.3 else 0
                row.append(max(0, min(2, base + shift)))
        data.append(row)
    sets.append(data)

js = "const W=require(process.argv[1]);let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{console.log(JSON.stringify(JSON.parse(s).map(u=>W.krippendorffAlpha(u))))})"
ours = json.loads(subprocess.run(["node", "-e", js, str(HERE.parent / "app.js")], input=json.dumps(sets),
                                 capture_output=True, text=True, check=True).stdout)

compared = skipped = bad = 0
for data, a in zip(sets, ours):
    if a is None:
        skipped += 1
        continue
    m = np.array([[np.nan if v is None else v for v in row] for row in data], dtype=float).T
    ref = krippendorff.alpha(reliability_data=m, level_of_measurement="ordinal", value_domain=[0, 1, 2])
    compared += 1
    if abs(ref - a) > 1e-9:
        bad += 1
        print(f"다름: 채점기 {a} / 패키지 {ref}")
print(f"대조 {compared}묶음, 다름 {bad}, 계산 불가로 뺀 묶음 {skipped}")
sys.exit(1 if bad or compared < 250 else 0)
