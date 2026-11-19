#!/usr/bin/env python3
"""Start the internet tunnel that connects the Vercel proxy project to this PC.

    python scripts/pc_tunnel.py            start the tunnel (restarts itself if it drops)
    python scripts/pc_tunnel.py --check    show what is configured and whether the tunnel program is installed
    python scripts/pc_tunnel.py --test     test the public address end to end (needs the server + tunnel running)

Provider is chosen with TUNNEL_PROVIDER in .env (written by setup_internet.bat):
    ngrok              free static domain from ngrok:   ngrok http --url=NGROK_DOMAIN PORT
    cloudflared        permanent, your own domain:      cloudflared tunnel run   (CLOUDFLARE_TUNNEL_TOKEN)
    cloudflared-quick  TEST ONLY, new random address on every start
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from signalsleuth import config  # noqa: E402,F401  (loads .env)

PORT = os.environ.get("PORT", "8000")


def find_exe(name):
    exe = shutil.which(name)
    if exe:
        return exe
    candidates = [str(ROOT / "tools" / f"{name}.exe"), str(ROOT / "tools" / name)]
    pf = [os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
    for base in pf:
        candidates += [rf"{base}\{name}\{name}.exe", rf"{base}\Cloudflare\Cloudflared\{name}.exe"]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidates += [rf"{local}\Microsoft\WinGet\Links\{name}.exe", rf"{local}\Microsoft\WindowsApps\{name}.exe"]
        candidates += glob.glob(rf"{local}\Microsoft\WinGet\Packages\*{name}*\{name}.exe")
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def provider():
    return os.environ.get("TUNNEL_PROVIDER", "").strip().lower()


def public_url():
    return os.environ.get("TUNNEL_PUBLIC_URL", "").strip().rstrip("/")


def show_check():
    prov = provider()
    print(f"TUNNEL_PROVIDER      : {prov or '(not set - run setup_internet.bat)'}")
    print(f"ORIGIN_SECRET        : {'set' if config.ORIGIN_SECRET else 'NOT SET - run setup_internet.bat'}")
    print(f"TRUST_PROXY          : {os.environ.get('TRUST_PROXY', '0')}")
    print(f"SESSION_COOKIE_SECURE: {os.environ.get('SESSION_COOKIE_SECURE', '(default)')}")
    print(f"TUNNEL_PUBLIC_URL    : {public_url() or '(not set)'}")
    needed = {"ngrok": "ngrok", "cloudflared": "cloudflared", "cloudflared-quick": "cloudflared"}.get(prov)
    if needed:
        exe = find_exe(needed)
        print(f"{needed} program     : {exe or 'NOT FOUND - install it (see docs/INTERNET_ACCESS.md, step 3)'}")
    return 0


def http_get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "SignalSleuth-check", "ngrok-skip-browser-warning": "1", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(300).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(300).decode("utf-8", "replace")
    except Exception as e:  # network, DNS, tunnel down
        return 0, str(e)


def run_test():
    url = public_url()
    if not url:
        print("TUNNEL_PUBLIC_URL is not set in .env (the quick tunnel prints its address when it starts).")
        return 1
    print(f"Local server  : {http_get(f'http://127.0.0.1:{PORT}/api/health')[0]} (expect 200)")
    code, body = http_get(url + "/api/health", {"X-Origin-Secret": config.ORIGIN_SECRET})
    print(f"Tunnel + secret : {code} (expect 200)  {body[:80] if code != 200 else ''}")
    code2, _ = http_get(url + "/api/health", {"X-Forwarded-For": "203.0.113.250"})  # what a stranger looks like
    print(f"Tunnel, no secret: {code2} (expect 403 - proves strangers cannot use the tunnel directly)")
    good = code == 200 and code2 == 403

    front = os.environ.get("FRONT_URL", "").strip().rstrip("/")
    if front:
        fcode, fbody = http_get(front + "/__front/health")
        print(f"Vercel address   : {fcode} (expect 200 with \"origin\": \"up\")  {fbody[:90].replace(chr(10), ' ')}")
        good = good and fcode == 200
    else:
        print("Vercel address   : not tested (add FRONT_URL=https://your-project.vercel.app to .env after you deploy it)")
    return 0 if good else 1


def build_command():
    prov = provider()
    env = dict(os.environ)
    if prov == "ngrok":
        exe = find_exe("ngrok")
        if not exe:
            return None, env, "ngrok is not installed (see docs/INTERNET_ACCESS.md, step 3)."
        domain = os.environ.get("NGROK_DOMAIN", "").strip()
        flag = os.environ.get("NGROK_URL_FLAG", "url").strip() or "url"  # older ngrok versions use 'domain'
        cmd = [exe, "http"] + ([f"--{flag}={domain}"] if domain else []) + [PORT]
        return cmd, env, None
    if prov == "cloudflared":
        exe = find_exe("cloudflared")
        token = os.environ.get("CLOUDFLARE_TUNNEL_TOKEN", "").strip()
        if not exe:
            return None, env, "cloudflared is not installed (see docs/INTERNET_ACCESS.md, step 3)."
        if not token:
            return None, env, "CLOUDFLARE_TUNNEL_TOKEN is empty in .env. Run setup_internet.bat again."
        env["TUNNEL_TOKEN"] = token  # token via environment, not on the command line
        return [exe, "tunnel", "--no-autoupdate", "run"], env, None
    if prov == "cloudflared-quick":
        exe = find_exe("cloudflared")
        if not exe:
            return None, env, "cloudflared is not installed (see docs/INTERNET_ACCESS.md, step 3)."
        return [exe, "tunnel", "--no-autoupdate", "--url", f"http://localhost:{PORT}"], env, None
    return None, env, "TUNNEL_PROVIDER is not set. Run setup_internet.bat first."


def run_once(cmd, env):
    if provider() != "cloudflared-quick":
        return subprocess.call(cmd, env=env)
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    shown = False
    for line in proc.stdout:
        print(line, end="")
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
        if m and not shown:
            shown = True
            print("\n" + "=" * 64)
            print(f" Quick tunnel address: {m.group(0)}")
            print(" Vercel -> signalsleuth-vercel-proxy project -> Settings -> Environment Variables:")
            print(f"   ORIGIN_URL = {m.group(0)}   then Redeploy. (TEST USE: it changes every restart)")
            print("=" * 64 + "\n")
    return proc.wait()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()
    if args.check:
        return show_check()
    if args.test:
        return run_test()

    cmd, env, err = build_command()
    if err:
        print("\nTUNNEL PROBLEM:", err)
        return 1
    print("Starting tunnel:", provider(), "->", f"http://localhost:{PORT}")
    print("Keep this window open. Press Ctrl+C to stop.\n")
    try:
        while True:
            rc = run_once(cmd, env)
            print(f"\nTunnel program exited (code {rc}). Restarting in 10 seconds... (Ctrl+C to stop)")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nTunnel stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
