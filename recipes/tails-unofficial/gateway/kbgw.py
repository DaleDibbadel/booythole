#!/usr/bin/python3 -I
"""kbgw: gateway front-end for the UNOFFICIAL Tails-derived Kasm workspace (runs inside the Tor egress gateway container).

Tor itself listens only on the gateway's loopback (SOCKS 19050/19062/19063/19150, control 9052 with a cookie). Desktop containers on the
internal network can reach ONLY the two services in this file:
  * SOCKS5 front ends on the standard Tails ports (9050/9062/9063/9150). Destination policy is enforced here, on the proxy path that is
    actually used: private/non-global addresses, the owner's own public host names and WAN addresses (deny.conf) are refused before Tor
    is asked to connect; clear-net names are resolved through Tor first and the connection is made to the verified address (no
    resolve/connect race). Per-desktop stream isolation: the SOCKS user name sent to Tor is prefixed with the desktop's IP and an epoch.
  * A filtered Tor control port (9051): null authentication towards the desktop, SAFECOOKIE towards Tor. Per-desktop views of circuits
    and streams (a desktop can never see or close another desktop's circuits), read-only bootstrap status, New Identity = a new epoch +
    closing only that desktop's own circuits (never the global NEWNYM signal), no SETCONF/SAVECONF/raw access."""
import asyncio, hashlib, hmac, ipaddress, os, re, socket, struct, subprocess, sys, time

LISTEN = os.environ.get("KB_LISTEN", "172.28.0.2")
SOCKS_MAP = {9050: 19050, 9062: 19062, 9063: 19063, 9150: 19150}
CTL_PORT = 9051
UP_CTL = ("127.0.0.1", 9052)
COOKIE = "/var/lib/kbtails-tor/control_auth_cookie"
DENY_FILE = os.environ.get("KB_DENY", "/etc/kbgw/deny.conf")
TORRC_SRC = os.environ.get("KB_TORRC", "/etc/kbgw/torrc")
CGNAT = ipaddress.ip_network("100.64.0.0/10")
PFX = re.compile(r'kbc-(\d+\.\d+\.\d+\.\d+)-(\d+)-')


def log(*a):
    print(time.strftime("%b %d %H:%M:%S"), "[kbgw]", *a, flush=True)


# ---------------------------------------------------------------- policy
DENY_SUFFIX, DENY_NETS = [], []


def load_deny():
    DENY_SUFFIX.clear(); DENY_NETS.clear()
    try:
        for ln in open(DENY_FILE):
            ln = ln.split("#")[0].strip()
            if not ln:
                continue
            kind, _, val = ln.partition(" ")
            val = val.strip().lower()
            if kind == "suffix":
                DENY_SUFFIX.append(val.lstrip("."))
            elif kind == "net":
                DENY_NETS.append(ipaddress.ip_network(val, strict=False))
    except FileNotFoundError:
        pass


def bad_ip(ip):
    try:
        a = ip if hasattr(ip, "is_global") else ipaddress.ip_address(ip)
    except ValueError:
        return True
    if not a.is_global or a in CGNAT:
        return True
    return any(a in n for n in DENY_NETS)


def bad_name(n):
    n = n.lower().rstrip(".")
    try:
        return bad_ip(ipaddress.ip_address(n))
    except ValueError:
        pass
    if n.endswith(".onion"):
        return False
    if "." not in n or n.endswith((".local", ".lan", ".internal", ".home", ".home.arpa", ".localdomain", ".corp", ".intranet")):
        return True
    return any(n == s or n.endswith("." + s) for s in DENY_SUFFIX)


# ---------------------------------------------------------------- client identity / isolation
EPOCH = {}


def uname(ip, user, pw):
    h = hashlib.sha256(user + b"\0" + pw).hexdigest()[:24]
    return f"kbc-{ip}-{EPOCH.get(ip, 0)}-{h}".encode()


# ---------------------------------------------------------------- SOCKS front end
async def rd(r, n):
    return await asyncio.wait_for(r.readexactly(n), 20)


async def tor_socks(lport, user, cmd, atyp, addr, port):
    r, w = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", lport), 10)
    try:
        w.write(b"\x05\x01\x02"); await w.drain()
        if await rd(r, 2) != b"\x05\x02":
            raise IOError("socks auth method")
        w.write(b"\x01" + bytes([len(user)]) + user + b"\x01x"); await w.drain()
        if (await rd(r, 2))[1] != 0:
            raise IOError("socks auth")
        w.write(b"\x05" + bytes([cmd, 0, atyp]) + addr + struct.pack(">H", port)); await w.drain()
        h = await asyncio.wait_for(r.readexactly(4), 120)    # onion services / slow circuits can take well over 20 s to answer
        if h[3] == 1: rest = await rd(r, 4)
        elif h[3] == 4: rest = await rd(r, 16)
        elif h[3] == 3: rest = bytes([(await rd(r, 1))[0]]); rest += await rd(r, rest[0])
        else: raise IOError("socks atyp")
        rest += await rd(r, 2)
        return h, rest, r, w
    except BaseException:
        w.close(); raise


RES_CACHE = {}


async def resolve(lport, user, name):
    k = (name,)
    c = RES_CACHE.get(k)
    if c and c[0] > time.time():
        return c[1]
    nb = name.encode()
    h, rest, r, w = await tor_socks(lport, user + b"r", 0xF0, 3, bytes([len(nb)]) + nb, 0)
    w.close()
    if h[1] != 0:
        return None
    ip = socket.inet_ntoa(rest[:4]) if h[3] == 1 else socket.inet_ntop(socket.AF_INET6, rest[:16])
    RES_CACHE[k] = (time.time() + 120, ip)
    return ip


async def pipe(r, w):
    try:
        while (d := await r.read(65536)):
            w.write(d); await w.drain()
    except Exception:
        pass
    finally:
        try: w.close()
        except Exception: pass


async def socks_client(cr, cw, lport):
    ip = cw.get_extra_info("peername")[0]
    user = pw = b""
    try:
        v, n = await rd(cr, 2)
        if v != 5:
            return
        methods = await rd(cr, n)
        if 2 in methods:
            cw.write(b"\x05\x02"); await cw.drain()
            await rd(cr, 1); ul = (await rd(cr, 1))[0]; user = await rd(cr, ul); pl = (await rd(cr, 1))[0]; pw = await rd(cr, pl)
            cw.write(b"\x01\x00")
        elif 0 in methods:
            cw.write(b"\x05\x00")
        else:
            cw.write(b"\x05\xff"); return
        await cw.drain()
        v, cmd, _, atyp = await rd(cr, 4)
        if atyp == 1: raw = await rd(cr, 4); host = socket.inet_ntoa(raw); addr = raw
        elif atyp == 4: raw = await rd(cr, 16); host = socket.inet_ntop(socket.AF_INET6, raw); addr = raw
        elif atyp == 3: l = (await rd(cr, 1))[0]; nb = await rd(cr, l); host = nb.decode("latin1"); addr = bytes([l]) + nb
        else: cw.write(b"\x05\x08\x00\x01" + bytes(6)); return
        port = struct.unpack(">H", await rd(cr, 2))[0]
        un = uname(ip, user, pw)
        deny = False
        if atyp == 3:
            if bad_name(host):
                deny = True
            elif not host.lower().endswith(".onion") and cmd in (1, 0xF0):
                rip = await resolve(lport, un, host)
                if rip is None or bad_ip(rip):
                    deny = True
                elif cmd == 1:
                    atyp, addr = (1, socket.inet_aton(rip)) if ":" not in rip else (4, socket.inet_pton(socket.AF_INET6, rip))
        elif cmd in (1, 0xF0, 0xF1) and bad_ip(host):
            deny = True
        if deny or cmd not in (1, 0xF0, 0xF1):
            log(f"DENY {ip} cmd={cmd} dest-class={'name' if atyp == 3 else 'ip'}")
            cw.write(b"\x05\x02\x00\x01" + bytes(6)); await cw.drain(); return
        h, rest, ur, uw = await tor_socks(lport, un, cmd, atyp, addr, port)
        cw.write(h + rest); await cw.drain()
        if h[1] != 0 or cmd != 1:
            uw.close(); return
        await asyncio.gather(pipe(cr, uw), pipe(ur, cw))
    except Exception as e:
        try: cw.write(b"\x05\x01\x00\x01" + bytes(6))
        except Exception: pass
    finally:
        try: cw.close()
        except Exception: pass


# ---------------------------------------------------------------- upstream control (single admin connection)
class Up:
    def __init__(self):
        self.r = self.w = None
        self.lock = asyncio.Lock()
        self.waiter = None
        self.clients = set()
        self.stream_owner = {}   # stream id -> owner ip
        self.circ_owner = {}     # circuit id -> owner ip
        self.circ_closed = set()
        self.version = "0.4"

    async def connect(self):
        while True:
            try:
                self.r, self.w = await asyncio.open_connection(*UP_CTL)
                break
            except OSError:
                await asyncio.sleep(1)
        cookie = open(COOKIE, "rb").read()
        cn = os.urandom(32)
        self.w.write(b"AUTHCHALLENGE SAFECOOKIE " + cn.hex().encode() + b"\r\n"); await self.w.drain()
        line = (await self.r.readline()).decode()
        m = re.match(r"250 AUTHCHALLENGE SERVERHASH=([0-9A-F]+) SERVERNONCE=([0-9A-F]+)", line)
        if not m:
            raise RuntimeError("authchallenge failed: " + line[:60])
        sn = bytes.fromhex(m[2])
        msg = cookie + cn + sn
        sh = hmac.new(b"Tor safe cookie authentication server-to-controller hash", msg, hashlib.sha256).digest()
        if not hmac.compare_digest(sh.hex().upper().encode(), m[1].encode()):
            raise RuntimeError("tor server hash mismatch")
        ch = hmac.new(b"Tor safe cookie authentication controller-to-server hash", msg, hashlib.sha256).digest()
        self.w.write(b"AUTHENTICATE " + ch.hex().encode() + b"\r\n"); await self.w.drain()
        if not (await self.r.readline()).startswith(b"250"):
            raise RuntimeError("authenticate failed")
        asyncio.get_event_loop().create_task(self.reader())
        r = await self.cmd("SETEVENTS CIRC STREAM STATUS_CLIENT")
        log("upstream control authenticated with SAFECOOKIE; events:", r[0][:20])
        v = await self.cmd("GETINFO version")
        m = re.search(r"version=(\S+)", " ".join(v))
        if m: self.version = m[1]

    async def reader(self):
        cur = []; data = False
        while True:
            line = await self.r.readline()
            if not line:
                log("upstream control closed"); os._exit(3)
            t = line.decode("latin1").rstrip("\r\n")
            if data:
                if t == ".": data = False
                else: cur.append(t)
                continue
            if t.startswith("650"):
                self.event(t); continue
            if re.match(r"^\d{3}\+", t):
                cur.append(t); data = True; continue
            cur.append(t)
            if re.match(r"^\d{3} ", t):
                if self.waiter and not self.waiter.done():
                    self.waiter.set_result(cur)
                cur = []

    async def cmd(self, c):
        async with self.lock:
            self.waiter = asyncio.get_event_loop().create_future()
            self.w.write(c.encode() + b"\r\n"); await self.w.drain()
            return await asyncio.wait_for(self.waiter, 20)

    def owner_of(self, line):
        m = re.search(r'SOCKS_USERNAME="([^"]*)"', line)
        if m:
            m = PFX.match(m[1])
            if m:
                return m[1]
        return None

    def event(self, t):
        p = t.split(" ", 3)
        if len(p) < 3:
            return
        kind = p[1]
        if kind == "STATUS_CLIENT":
            # only the global bootstrap/readiness events; other STATUS_CLIENT events carry other desktops' destination addresses
            if re.match(r"650 STATUS_CLIENT \w+ (BOOTSTRAP|CIRCUIT_ESTABLISHED|CIRCUIT_NOT_ESTABLISHED|ENOUGH_DIR_INFO|NOT_ENOUGH_DIR_INFO)\b", t):
                for c in list(self.clients):
                    if "STATUS_CLIENT" in c.events:
                        c.send(t)
        elif kind == "STREAM":
            f = t.split(" ")
            sid, st, circ = f[2], f[3], f[4]
            o = self.owner_of(t)
            if o: self.stream_owner[sid] = o
            if circ != "0" and sid in self.stream_owner:
                self.circ_owner.setdefault(circ, self.stream_owner[sid])
            o = self.stream_owner.get(sid)
            if st in ("CLOSED", "FAILED"):
                self.stream_owner.pop(sid, None)
            if o:
                for c in list(self.clients):
                    if c.ip == o and "STREAM" in c.events:
                        c.send(t)
        elif kind == "CIRC":
            f = t.split(" ")
            cid, st = f[2], f[3]
            o = self.owner_of(t)
            if o: self.circ_owner[cid] = o
            o = self.circ_owner.get(cid)
            if st in ("CLOSED", "FAILED"):
                self.circ_owner.pop(cid, None)
                if o:
                    for c in list(self.clients):
                        if c.ip == o and "CIRC" in c.events:
                            c.send(f"650 CIRC {cid} {st}")
                return
            if o:
                for c in list(self.clients):
                    if c.ip == o and "CIRC" in c.events:
                        c.send(t)


UP = Up()


# ---------------------------------------------------------------- filtered control client
class Client:
    def __init__(self, r, w):
        self.r, self.w = r, w
        self.ip = w.get_extra_info("peername")[0]
        self.events = set()

    def send(self, line):
        try:
            self.w.write(line.encode() + b"\r\n")
        except Exception:
            pass

    async def run(self):
        UP.clients.add(self)
        try:
            while True:
                raw = await self.r.readline()
                if not raw:
                    return
                line = raw.decode("latin1").strip()
                if not line:
                    continue
                await self.handle(line)
                await self.w.drain()
                if line.upper().startswith("QUIT"):
                    return
        except Exception:
            pass
        finally:
            UP.clients.discard(self)
            try: self.w.close()
            except Exception: pass

    async def handle(self, line):
        cmd, _, arg = line.partition(" ")
        C = cmd.upper(); arg = arg.strip()
        if os.environ.get("KB_DEBUG"):
            log(f"ctl {self.ip}: {C} {arg[:60] if C not in ('AUTHENTICATE',) else ''}")
        if C == "PROTOCOLINFO":
            self.send('250-PROTOCOLINFO 1'); self.send('250-AUTH METHODS=NULL')
            self.send(f'250-VERSION Tor="{UP.version}"'); self.send("250 OK")
        elif C == "AUTHENTICATE" or C == "AUTHCHALLENGE":
            self.send("250 OK" if C == "AUTHENTICATE" else "513 AUTHCHALLENGE not needed (null auth)")
        elif C == "QUIT":
            self.send("250 closing connection")
        elif C == "GETINFO":
            for key in arg.split():
                if not await self.getinfo(key):
                    return
            self.send("250 OK")
        elif C == "SETEVENTS":
            ev = set(arg.upper().split())
            ok = {"CIRC", "STREAM", "STATUS_CLIENT", "SIGNAL", "CONF_CHANGED", "STATUS_SERVER", "STATUS_GENERAL"}
            if not ev <= ok:
                self.send("552 Unrecognized or filtered event"); return
            self.events = ev & {"CIRC", "STREAM", "STATUS_CLIENT"}
            self.send("250 OK")
        elif C == "SETCONF":
            names = [a.split("=")[0].lower() for a in arg.split()]
            if names and all(n == "__owningcontrollerprocess" for n in names):
                self.send("250 OK")
            else:
                self.send("510 Command filtered: configuration is managed by the gateway")
        elif C == "GETCONF":
            out = []
            for k in arg.split():
                kl = k.lower()
                if kl in ("bridge", "usebridges", "disablenetwork", "__owningcontrollerprocess", "sandbox"):
                    out.append(k)
                else:
                    self.send("510 Command filtered"); return
            for i, k in enumerate(out):
                self.send(("250 " if i == len(out) - 1 else "250-") + k)
            if not out: self.send("250 OK")
        elif C == "SIGNAL":
            if arg.upper() == "NEWNYM":
                EPOCH[self.ip] = EPOCH.get(self.ip, 0) + 1
                n = 0
                for cid, o in list(UP.circ_owner.items()):
                    if o == self.ip:
                        await UP.cmd(f"CLOSECIRCUIT {cid}"); n += 1
                log(f"NEWNYM for {self.ip}: epoch={EPOCH[self.ip]}, closed {n} own circuit(s)")
                self.send("250 OK")
            else:
                self.send("510 Command filtered")
        elif C == "CLOSECIRCUIT":
            cid = arg.split()[0] if arg else ""
            if UP.circ_owner.get(cid) == self.ip:
                await UP.cmd(f"CLOSECIRCUIT {cid}"); self.send("250 OK")
            else:
                self.send("552 Unknown circuit")
        elif C in ("ONION_CLIENT_AUTH_ADD", "ONION_CLIENT_AUTH_REMOVE", "ONION_CLIENT_AUTH_VIEW"):
            self.send("510 Command filtered: onion client authorization is not shared through the gateway")
        else:
            self.send("510 Unrecognized command (filtered)")

    async def getinfo(self, key):
        if key in ("version", "status/bootstrap-phase", "status/circuit-established", "status/enough-dir-info", "traffic/read", "traffic/written", "dormant"):
            r = await UP.cmd("GETINFO " + key)
            for ln in r[:-1]:
                self.send(ln)
            if not r[-1].startswith("250 OK"):
                self.send(r[-1]); return False
            return True
        if key == "net/listeners/socks":
            self.send('250-net/listeners/socks="127.0.0.1:9050" "127.0.0.1:9062" "127.0.0.1:9063" "127.0.0.1:9150"'); return True
        if key in ("circuit-status", "stream-status"):
            r = await UP.cmd("GETINFO " + key)
            lines = []
            for ln in r:
                if ln.startswith("250 ") or not ln.strip():
                    continue
                if ln[:4] in ("250-", "250+"):     # single-entry answers come as "250-key=<entry>"
                    ln = ln.partition("=")[2]
                    if not ln.strip():
                        continue
                f = ln.split(" ")
                if key == "circuit-status":
                    o = UP.owner_of(ln) or UP.circ_owner.get(f[0])
                else:
                    o = UP.stream_owner.get(f[0]) or (UP.circ_owner.get(f[2]) if len(f) > 2 else None)
                if o == self.ip:
                    lines.append(ln)
            if lines:
                self.send(f"250+{key}="); [self.send(x) for x in lines]; self.send(".")
            else:
                self.send(f"250-{key}=")
            return True
        m = re.fullmatch(r"ns/id/[0-9A-Fa-f]{40}", key) or re.fullmatch(r"ip-to-country/\d+\.\d+\.\d+\.\d+", key)
        if m:
            r = await UP.cmd("GETINFO " + key)
            for ln in r[:-1]:
                self.send(ln)
            if not r[-1].startswith("250 OK"):
                self.send(r[-1]); return False
            return True
        self.send(f"552 Unrecognized key \"{key}\" (filtered)")
        return False


# ---------------------------------------------------------------- main
async def main():
    load_deny()
    torrc = open(TORRC_SRC).read().replace("@LISTEN@", LISTEN)
    open("/tmp/torrc", "w").write(torrc)
    tor = subprocess.Popen(["/usr/sbin/tor", "-f", "/tmp/torrc"], stdout=sys.stdout, stderr=sys.stderr)
    log("tor started pid", tor.pid, "listen", LISTEN, "deny suffixes", len(DENY_SUFFIX), "deny nets", len(DENY_NETS))

    async def watch():
        while True:
            if tor.poll() is not None:
                log("tor exited", tor.returncode); os._exit(2)
            await asyncio.sleep(2)
    asyncio.get_event_loop().create_task(watch())
    await UP.connect()
    servers = []
    for pub, loc in SOCKS_MAP.items():
        servers.append(await asyncio.start_server(lambda r, w, l=loc: socks_client(r, w, l), LISTEN, pub))
    servers.append(await asyncio.start_server(lambda r, w: Client(r, w).run(), LISTEN, CTL_PORT))
    log("serving SOCKS", list(SOCKS_MAP), "and filtered control", CTL_PORT)
    await asyncio.gather(*(s.serve_forever() for s in servers))


asyncio.run(main())
