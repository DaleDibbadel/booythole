#!/usr/bin/python3
"""kbtails: loopback-to-gateway TCP forwarder (runs as the session user inside the desktop container).  v0.9
The desktop container sits on an internal Docker network with no route out; the only reachable peer that leads anywhere is the Tor
egress gateway (172.28.0.2). This maps the Tails loopback Tor ports (9050/9062/9063/9150 SOCKS, 9051/951 filtered control) onto the gateway's identical ports.

SOCKS ports: plain byte pipes (a gateway restart ends those connections; the browser reconnects on the next load).
Control ports (9051 and Tails' hard-wired 951): a control-protocol-aware relay that keeps the *client's* connection open across a gateway/Tor restart:
  * it reconnects upstream by itself, replays the null AUTHENTICATE and the last accepted SETEVENTS, and never fabricates any other state;
  * a command in flight when the gateway goes away, or one that arrives while it is away, gets a prompt "551" error reply (so a synchronous client such as Onion
    Circuits' stem calls can never wait forever), and no later answer can ever be matched to the wrong command;
  * circuits/streams the client had seen are reported closed ("650 CIRC/STREAM ... CLOSED") when the gateway goes away, because they really are gone.
It adds no privilege: it only relays to the same filtered port the desktop could always reach."""
import asyncio, collections, re, sys, time
GW = sys.argv[1] if len(sys.argv) > 1 else "172.28.0.2"
SOCKS = {9050: 9050, 9062: 9062, 9063: 9063, 9150: 9150}
CTRL = {9051: 9051, 951: 9051}            # Tails' Tor Browser wrapper hard-wires control 951; the Tails apps use 9051
CMD_TIMEOUT = 4          # s: no answer from the gateway -> 551 to the client (the late answer is discarded)
DOWN_WAIT = 2            # s: a command arriving while the gateway is away waits this long for the reconnect before failing
FINAL = re.compile(r"^\d{3} ")
def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

async def pipe(r, w):
    try:
        while (d := await r.read(65536)): w.write(d); await w.drain()
    except Exception: pass
    finally:
        try: w.close()
        except Exception: pass

async def handle_socks(port, cr, cw):
    try: sr, sw = await asyncio.wait_for(asyncio.open_connection(GW, SOCKS[port]), 15)
    except Exception: cw.close(); return
    await asyncio.gather(pipe(cr, sw), pipe(sr, cw))

async def read_reply(r):
    """Read one full reply (data blocks included); return the list of lines, or None on EOF."""
    out = []; data = False
    while True:
        raw = await r.readline()
        if not raw: return None
        t = raw.decode("latin1").rstrip("\r\n"); out.append(t)
        if data:
            if t == ".": data = False
            continue
        if re.match(r"^\d{3}\+", t): data = True; continue
        if FINAL.match(t) and not t.startswith("650"): return out

class Session:
    def __init__(self, cr, cw, port):
        self.cr, self.cw = cr, cw
        self.up = None                      # (reader, writer) while connected
        self.upv = 0                        # connection generation
        self.pending = collections.deque()  # (time, command line) awaiting a final reply, oldest first
        self.abandoned = 0                  # late replies to discard
        self.events = ""                    # last SETEVENTS argument the gateway accepted
        self.circs = set(); self.streams = {}
        self.closing = False
        self.reconn = None

    def to_client(self, line):
        try: self.cw.write(line.encode("latin1", "replace") + b"\r\n")
        except Exception: pass

    async def connect_up(self):
        r, w = await asyncio.wait_for(asyncio.open_connection(GW, 9051), 3)
        try:
            w.write(b"AUTHENTICATE\r\n"); await w.drain()
            a = await asyncio.wait_for(read_reply(r), 5)
            if not a or not a[-1].startswith("250"): raise IOError("auth refused")
            if self.events:
                w.write(("SETEVENTS " + self.events + "\r\n").encode()); await w.drain()
                a = await asyncio.wait_for(read_reply(r), 5)
                if not a or not a[-1].startswith("250"): raise IOError("events refused")
        except Exception:
            w.close(); raise
        self.up = (r, w); self.upv += 1
        asyncio.get_event_loop().create_task(self.pump(r, self.upv))

    async def reconnect_loop(self):
        n = 0
        while not self.closing and self.up is None:
            try:
                await self.connect_up()
                log("control session re-established" + (f" (events {self.events})" if self.events else "")); break
            except Exception:
                n += 1; await asyncio.sleep(1)
        self.reconn = None

    def lost(self, ver):
        if ver != self.upv or self.up is None: return
        try: self.up[1].close()
        except Exception: pass
        self.up = None
        if self.closing: return                      # the client itself ended the session (QUIT/EOF): nothing to report or reconnect
        for _ in range(len(self.pending)): self.to_client("551 Tor gateway connection lost")
        self.pending.clear(); self.abandoned = 0
        ev = set(self.events.split())
        if "CIRC" in ev:
            for c in sorted(self.circs): self.to_client(f"650 CIRC {c} CLOSED REASON=FINISHED")
        if "STREAM" in ev:
            for sid, (circ, tgt) in sorted(self.streams.items()): self.to_client(f"650 STREAM {sid} CLOSED {circ} {tgt} REASON=END")
        self.circs.clear(); self.streams.clear()
        log("control gateway connection lost; reconnecting without closing the client's connection")
        if not self.closing and self.reconn is None:
            self.reconn = asyncio.get_event_loop().create_task(self.reconnect_loop())

    def track(self, line):
        m = re.match(r"^650 CIRC (\S+) (\S+)", line)
        if m:
            (self.circs.discard if m[2] in ("CLOSED", "FAILED") else self.circs.add)(m[1]); return
        m = re.match(r"^650 STREAM (\S+) (\S+) (\S+) (\S+)", line)
        if m:
            if m[2] in ("CLOSED", "FAILED"): self.streams.pop(m[1], None)
            else: self.streams[m[1]] = (m[3], m[4])

    async def pump(self, r, ver):
        """gateway -> client; matches final replies to the oldest pending command."""
        cur = []; data = False
        try:
            while True:
                raw = await r.readline()
                if not raw: break
                t = raw.decode("latin1").rstrip("\r\n")
                if data:
                    cur.append(t)
                    if t == ".": data = False
                    continue
                if t.startswith("650"):
                    self.track(t); self.to_client(t); continue
                cur.append(t)
                if re.match(r"^\d{3}\+", t): data = True; continue
                if not FINAL.match(t): continue
                reply, cur = cur, []
                if self.abandoned > 0:
                    self.abandoned -= 1; continue
                if not self.pending: continue          # unsolicited (should not happen)
                _, cmd = self.pending.popleft()
                verb, _, arg = cmd.partition(" ")
                ok = reply[-1].startswith("250")
                if ok and verb.upper() == "SETEVENTS": self.events = arg.strip().upper()
                if ok and verb.upper() == "GETINFO" and arg.strip() in ("circuit-status", "stream-status"):
                    for ln in reply:
                        ln = ln.partition("=")[2] if ln[:4] in ("250+", "250-") else ln
                        f = ln.split(" ")
                        if arg.strip() == "circuit-status" and len(f) > 1 and f[0].isdigit() and f[1] in ("BUILT", "EXTENDED", "LAUNCHED", "GUARD_WAIT"): self.circs.add(f[0])
                        if arg.strip() == "stream-status" and len(f) > 3 and f[0].isdigit(): self.streams[f[0]] = (f[2], f[3])
                for ln in reply: self.to_client(ln)
                try: await self.cw.drain()
                except Exception: pass
        except Exception: pass
        self.lost(ver)

    async def watchdog(self):
        while not self.closing:
            await asyncio.sleep(0.5)
            if self.up is not None and self.pending and time.time() - self.pending[0][0] > CMD_TIMEOUT:
                self.pending.popleft(); self.abandoned += 1
                self.to_client("551 Tor gateway did not answer in time")
                log("command timeout answered locally; late reply will be discarded")

    async def run(self):
        wd = asyncio.get_event_loop().create_task(self.watchdog())
        try:
            try: await self.connect_up()
            except Exception: self.reconn = asyncio.get_event_loop().create_task(self.reconnect_loop())
            while True:
                raw = await self.cr.readline()
                if not raw: break
                line = raw.decode("latin1").strip()
                if not line: continue
                if line.upper().startswith("QUIT") :
                    self.to_client("250 closing connection"); await self.cw.drain(); break
                t0 = time.time()
                while self.up is None and time.time() - t0 < DOWN_WAIT: await asyncio.sleep(0.1)
                if self.up is None:
                    self.to_client("551 Tor gateway unavailable (reconnecting)")
                else:
                    self.pending.append((time.time(), line))
                    try: self.up[1].write(line.encode("latin1", "replace") + b"\r\n")
                    except Exception: pass
                try: await self.cw.drain()
                except Exception: break
        except Exception: pass
        finally:
            self.closing = True; wd.cancel()
            for w in ((self.up[1],) if self.up else ()) + (self.cw,):
                try: w.close()
                except Exception: pass

async def handle_ctl(port, cr, cw):
    await Session(cr, cw, port).run()

async def main():
    servers = [await asyncio.start_server(lambda r, w, p=p: handle_socks(p, r, w), "127.0.0.1", p) for p in SOCKS]
    servers += [await asyncio.start_server(lambda r, w, p=p: handle_ctl(p, r, w), "127.0.0.1", p) for p in CTRL]
    await asyncio.gather(*(s.serve_forever() for s in servers))
asyncio.run(main())
