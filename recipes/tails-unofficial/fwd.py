#!/usr/bin/python3
"""kbtails: loopback-to-gateway TCP forwarder (runs as the session user inside the desktop container).
The desktop container sits on an internal Docker network with no route out; the only reachable peer that leads anywhere is the Tor
egress gateway (172.28.0.2). This maps the Tails loopback Tor ports (9050/9062/9063/9150 SOCKS, 9051 filtered control) onto the gateway's identical SOCKS ports."""
import asyncio, sys
GW = sys.argv[1] if len(sys.argv) > 1 else "172.28.0.2"
# listen port on the desktop loopback -> gateway port. Tails' Tor Browser wrapper hard-wires SOCKS 9050 and control 951 (it overrides the environment), the Tails apps use 9051/9150
PORTS = {9050: 9050, 9062: 9062, 9063: 9063, 9150: 9150, 9051: 9051, 951: 9051}
async def pipe(r, w):
    try:
        while (d := await r.read(65536)): w.write(d); await w.drain()
    except Exception: pass
    finally:
        try: w.close()
        except Exception: pass
async def handle(port, cr, cw):
    port = PORTS[port]
    try: sr, sw = await asyncio.wait_for(asyncio.open_connection(GW, port), 15)
    except Exception: cw.close(); return
    await asyncio.gather(pipe(cr, sw), pipe(sr, cw))
async def main():
    servers = [await asyncio.start_server(lambda r, w, p=p: handle(p, r, w), "127.0.0.1", p) for p in PORTS]
    await asyncio.gather(*(s.serve_forever() for s in servers))
asyncio.run(main())
