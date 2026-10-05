#!/usr/bin/env python3
"""Call the 12 Jev MCP tools (jev_screen ... jev_gate) over stdio and persist args+result receipts.

Usage: jev_mcp_call.py TOOL ARGS.json OUT.json   (ARGS.json is the tool's argument object)
The credential is read by the child from ~/.config/jgrep/env; it is never printed or stored.
"""
import json, os, subprocess, sys, shlex

def call(tool, args, timeout=180):
    cmd = ['sh', '-c', 'set -a; . "$HOME/.config/jgrep/env"; exec npx -y @jkudish/jev-mcp']
    env = dict(os.environ, JEV_MCP_MODEL='typesafe/jev-1.13', JEV_PROVIDER='openrouter')
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env)
    def send(m): p.stdin.write(json.dumps(m) + '\n'); p.stdin.flush()
    def recv(i):
        while True:
            line = p.stdout.readline()
            if not line: raise RuntimeError('jev-mcp closed')
            m = json.loads(line)
            if m.get('id') == i: return m
    try:
        send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'carmodels','version':'1'}}})
        recv(1)
        send({'jsonrpc':'2.0','method':'notifications/initialized'})
        if tool == '--list':
            send({'jsonrpc':'2.0','id':2,'method':'tools/list'}); return recv(2)
        send({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':tool,'arguments':args}})
        return recv(2)
    finally:
        p.stdin.close(); p.terminate()

if __name__ == '__main__':
    tool = sys.argv[1]
    args = json.load(open(sys.argv[2])) if len(sys.argv) > 2 and sys.argv[2] != '-' else {}
    r = call(tool, args)
    res = r.get('result', r)
    if tool != '--list' and 'content' in res:
        try: res = json.loads(res['content'][0]['text'])
        except Exception: res = res
    out = {'args': args, 'result': res}
    if len(sys.argv) > 3: json.dump(out, open(sys.argv[3], 'w'), indent=2)
    print(json.dumps(res, indent=1)[:6000])
