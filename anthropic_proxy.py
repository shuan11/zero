import json, os, time, http.server, urllib.request, urllib.error

PORT = 8787
from api_config import API_BASE as TARGET

class H(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        L = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(L).decode()
        try:
            rd = json.loads(body)
        except Exception:
            self._r(400, {"e": "json"})
            return
        auth = self.headers.get("Authorization", "")
        k = auth.replace("Bearer ", "").strip() if "Bearer " in auth else ""
        if not k:
            k = self.headers.get("x-api-key", "").strip()
        if not k:
            from api_config import API_KEY as _DEFAULT_KEY
            k = _DEFAULT_KEY
        streaming = rd.get("stream", False)
        msgs = []
        if rd.get("system"):
            msgs.append({"role": "system", "content": rd["system"]})
        for m in rd.get("messages", []):
            c = m.get("content", "")
            if isinstance(c, list):
                c = " ".join(p.get("text", "") for p in c if p.get("type") == "text")
            msgs.append({"role": m["role"], "content": c})
        od = json.dumps({
            "model": rd.get("model", "deepseek-v4-pro"),
            "messages": msgs,
            "max_tokens": rd.get("max_tokens", 4096),
            "stream": streaming,
        }).encode()
        try:
            fwd = urllib.request.Request(TARGET + "/chat/completions", data=od, method="POST")
            fwd.add_header("Authorization", "Bearer " + k)
            fwd.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(fwd, timeout=120) as resp:
                if streaming:
                    self._anthropic_stream(resp, rd.get("model", "deepseek-v4-pro"))
                else:
                    o = json.loads(resp.read())
                    ch = o["choices"][0]
                    text = ch["message"].get("content", "") or ""
                    self._r(200, {
                        "id": "msg_" + str(int(time.time() * 1000)),
                        "type": "message", "role": "assistant",
                        "content": [{"type": "text", "text": text}],
                        "model": rd.get("model", "deepseek-v4-pro"),
                        "stop_reason": "end_turn",
                        "usage": {
                            "input_tokens": o.get("usage", {}).get("prompt_tokens", 0),
                            "output_tokens": o.get("usage", {}).get("completion_tokens", 0)
                        }
                    })
        except urllib.error.HTTPError as e:
            eb = e.read().decode(errors="replace")[:200]
            self._r(500, {"type": "error", "error": {"type": "api_error", "message": "HTTP " + str(e.code) + ": " + eb}})
        except Exception as e:
            self._r(500, {"type": "error", "error": {"type": "api_error", "message": str(e)}})

    def _anthropic_stream(self, resp, model):
        """Convert OpenAI SSE to Anthropic SSE format"""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        msg_id = "msg_" + str(int(time.time() * 1000))
        self._sse_send("message_start", {"type": "message_start", "message": {
            "id": msg_id, "type": "message", "role": "assistant",
            "content": [], "model": model, "stop_reason": None,
            "usage": {"input_tokens": 0, "output_tokens": 0}
        }})
        self._sse_send("content_block_start", {"type": "content_block_start", "index": 0,
            "content_block": {"type": "text", "text": ""}})
        for chunk in iter(lambda: resp.readline(), b""):
            line = chunk.decode(errors="replace").strip()
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                d = json.loads(data_str)
                delta = d.get("choices", [{}])[0].get("delta", {})
                if "reasoning_content" in delta:
                    continue
                text = delta.get("content", "")
                if text:
                    self._sse_send("content_block_delta", {
                        "type": "content_block_delta", "index": 0,
                        "delta": {"type": "text_delta", "text": text}
                    })
                if d.get("choices", [{}])[0].get("finish_reason") == "stop":
                    break
            except Exception:
                continue
        self._sse_send("content_block_stop", {"type": "content_block_stop", "index": 0})
        self._sse_send("message_delta", {
            "type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
            "usage": {"output_tokens": 0}
        })
        self._sse_send("message_stop", {"type": "message_stop"})
        try:
            self.wfile.write(b"\n")
            self.wfile.flush()
        except Exception:
            pass

    def _sse_send(self, event, data):
        try:
            self.wfile.write(("event: " + event + "\n").encode())
            self.wfile.write(("data: " + json.dumps(data) + "\n\n").encode())
            self.wfile.flush()
        except Exception:
            pass

    def do_GET(self):
        self._r(200, {"status": "ok"})
    def do_HEAD(self):
        self.send_response(200); self.end_headers()
    def _r(self, c, b):
        d = json.dumps(b).encode()
        self.send_response(c)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(d)))
        self.end_headers()
        try:
            self.wfile.write(d)
        except BrokenPipeError:
            pass
    def log_message(self, *a):
        if len(a) >= 3:
            print('%s %s %s' % (a[0], a[1], a[2]), flush=True)

if __name__ == "__main__":
    s = http.server.HTTPServer(("127.0.0.1", PORT), H)
    print("proxy: %d -> %s" % (PORT, TARGET), flush=True)
    s.serve_forever()
