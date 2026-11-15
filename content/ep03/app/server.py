"""EP.03 촬영용 숫자 읽기 변환기 서버.

화면(index.html)에서 입력한 문장을 실제 korean_numbers.normalize()로 바꿔 돌려줍니다.
영상에 나오는 결과는 모두 이 함수가 그 자리에서 낸 값입니다.

    python content/ep03/app/server.py 8731
"""
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from korean_numbers import normalize  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HERE), **kw)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path != "/api/normalize":
            return super().do_GET()
        text = parse_qs(url.query).get("text", [""])[0]
        body = json.dumps({"input": text, "output": normalize(text)}, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8731
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
