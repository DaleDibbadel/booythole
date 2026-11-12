#!/usr/bin/python3 -I
"""kbtails Kasm callback relay (UNOFFICIAL Tails workspace). The ONLY thing a Tails desktop may reach besides the Tor gateway.

Kasm session containers report to the Kasm API: POST /api/set_kasm_session_status?token=<session JWT> and POST /api/kasm_session_log?token=<JWT>.
Desktops sit on an isolated network and must not reach kasm_proxy (web UI/API) in general, so they send those two callbacks here instead.
This relay accepts exactly those two endpoints (POST, JSON, token-only query string, size-limited, per-source rate-limited), forwards them to the
fixed upstream https://proxy:443 (kasm_proxy on kasm_default_network; Kasm verifies the session JWT itself) and returns the upstream answer.
No other method/path/host is ever forwarded; the relay is not a generic proxy. Tokens are never logged."""
import asyncio, json, os, re, ssl, subprocess, sys, time, urllib.request, urllib.error
LISTEN = os.environ.get("KB_LISTEN", "172.28.0.10"); UPSTREAM = os.environ.get("KB_UPSTREAM", "https://proxy:443")
ALLOWED = {"/api/set_kasm_session_status", "/api/kasm_session_log"}
TOKEN_RE = re.compile(rb"^token=[A-Za-z0-9._~+/=-]{20,4096}$")
MAXBODY = 65536
rate = {}; sem = asyncio.Semaphore(20)
up_ctx = ssl.create_default_context(); up_ctx.check_hostname = False; up_ctx.verify_mode = ssl.CERT_NONE   # internal docker network hop to kasm_proxy (self-signed)
def log(*a): print(time.strftime("%H:%M:%SZ", time.gmtime()), *a, flush=True)
async def reply(w, code, body=b""):
    w.write(f"HTTP/1.1 {code} {'OK' if code == 200 else 'ERR'}\r\nContent-Length: {len(body)}\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n".encode() + body)
    try: await w.drain()
    except Exception: pass
def forward(path, query, body):
    req = urllib.request.Request(UPSTREAM + path + "?" + query, data=body, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10, context=up_ctx) as r: return r.status, r.read(MAXBODY)
    except urllib.error.HTTPError as e: return e.code, e.read(MAXBODY)
    except Exception as e: return 502, json.dumps({"error": "upstream unreachable"}).encode()
async def handle(r, w):
    peer = (w.get_extra_info("peername") or ("?", 0))[0]
    try:
        async with sem:
            now = time.time(); q = [t for t in rate.get(peer, []) if now - t < 60]; q.append(now); rate[peer] = q
            if len(q) > 60: log("429", peer); return await reply(w, 429)
            head = await asyncio.wait_for(r.readuntil(b"\r\n\r\n"), 10)
            if len(head) > 16384: return await reply(w, 431)
            lines = head.split(b"\r\n"); m = lines[0].split(b" ")
            if len(m) != 3 or m[0] != b"POST": log("405", peer, lines[0][:40]); return await reply(w, 405)
            path, _, query = m[1].partition(b"?")
            if path.decode("latin1") not in ALLOWED or not TOKEN_RE.match(query): log("403", peer, path[:60]); return await reply(w, 403)
            hdr = {l.split(b":", 1)[0].strip().lower(): l.split(b":", 1)[1].strip() for l in lines[1:] if b":" in l}
            n = int(hdr.get(b"content-length", b"0") or 0)
            if n > MAXBODY or n < 2: return await reply(w, 413)
            body = await asyncio.wait_for(r.readexactly(n), 10)
            try: j = json.loads(body)
            except Exception: return await reply(w, 400)
            p = path.decode()
            if p.endswith("status"):
                if not (isinstance(j, dict) and set(j) <= {"status", "destroyed"}): log("400 status keys", peer); return await reply(w, 400)
            else:
                if not (isinstance(j, list) and len(j) <= 50 and all(isinstance(x, dict) for x in j)): return await reply(w, 400)
            st, out = await asyncio.get_running_loop().run_in_executor(None, forward, p, query.decode(), body)
            log(st, peer, p, (json.dumps(j)[:80] if p.endswith("status") else f"{len(j)} log rows"))
            await reply(w, st, out)
    except Exception as e: log("err", peer, type(e).__name__)
    finally:
        try: w.close()
        except Exception: pass
async def main():
    d = "/tmp/kbrelay"; os.makedirs(d, exist_ok=True)
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", d + "/k.pem", "-out", d + "/c.pem", "-days", "3650", "-subj", "/CN=kbtails-kasm-relay"], check=True, capture_output=True)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(d + "/c.pem", d + "/k.pem")
    srv = await asyncio.start_server(handle, LISTEN, 443, ssl=ctx)
    log("relay listening", LISTEN, 443, "upstream", UPSTREAM); await srv.serve_forever()
asyncio.run(main())
