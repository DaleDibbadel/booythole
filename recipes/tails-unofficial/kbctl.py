#!/usr/bin/python3 -I
"""kbctl: tiny client for the gateway's FILTERED Tor control port (127.0.0.1:9051 -> gateway). Read-only status helper for the UNOFFICIAL Tails workspace."""
import re, socket, sys, time

def query(host="127.0.0.1", port=9051, timeout=4):
    """Returns dict(ok, progress, summary, circuit) or dict(ok=False, error)."""
    try:
        s = socket.create_connection((host, port), timeout); s.settimeout(timeout)
        f = s.makefile("rwb", buffering=0)
        def cmd(c):
            f.write(c.encode() + b"\r\n"); out = []
            while True:
                ln = f.readline().decode().rstrip("\r\n")
                if not ln: raise IOError("closed")
                out.append(ln)
                if re.match(r"^\d{3} ", ln): return out
        cmd("AUTHENTICATE")
        b = " ".join(cmd("GETINFO status/bootstrap-phase"))
        c = " ".join(cmd("GETINFO status/circuit-established"))
        n = cmd("GETINFO circuit-status")
        cmd("QUIT"); s.close()
        p = re.search(r"PROGRESS=(\d+)", b); sm = re.search(r'SUMMARY="([^"]*)"', b)
        circ = [l for l in n if re.match(r"^\d+ BUILT", l)]
        return {"ok": True, "progress": int(p[1]) if p else 0, "summary": sm[1] if sm else "", "circuit": "circuit-established=1" in c, "own_circuits": len(circ)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

if __name__ == "__main__":
    print(query())
