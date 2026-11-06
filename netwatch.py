"""NetWatch - a small NOC-style uptime monitor.

Pings every host in a list on a fixed interval, records latency and up/down state to a CSV log,
and prints an alert whenever a host goes DOWN or RECOVERS. Python standard library only.

Usage:
    python netwatch.py hosts.txt                 # check every 30 s until Ctrl+C
    python netwatch.py hosts.txt -i 10 -n 6      # every 10 s, 6 rounds, then summary
    python netwatch.py hosts.txt --once          # one round, then summary
"""
import argparse
import csv
import platform
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

IS_WINDOWS = platform.system() == "Windows"
LATENCY_RE = re.compile(r"time[=<]\s*([\d.]+)\s*ms", re.IGNORECASE)


def load_hosts(path):
    """Read 'name,address' or just 'address' per line; '#' starts a comment."""
    hosts = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            name, addr = (parts[0], parts[1]) if len(parts) > 1 else (parts[0], parts[0])
            hosts.append((name, addr))
    return hosts


def ping(addr, timeout_ms=1000):
    """Return latency in ms if the host answered, else None."""
    if IS_WINDOWS:
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), addr]
    else:
        cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), addr]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_ms / 1000 + 3).stdout
    except subprocess.TimeoutExpired:
        return None
    # Windows ping can exit 0 on "Destination host unreachable", so look for a real reply (TTL).
    if "ttl=" not in out.lower():
        return None
    m = LATENCY_RE.search(out)
    return float(m.group(1)) if m else 0.0


def main():
    ap = argparse.ArgumentParser(description="Ping a list of hosts and alert on state changes.")
    ap.add_argument("hosts_file")
    ap.add_argument("-i", "--interval", type=int, default=30, help="seconds between rounds (default 30)")
    ap.add_argument("-n", "--rounds", type=int, default=0, help="stop after N rounds (default: run until Ctrl+C)")
    ap.add_argument("--once", action="store_true", help="run a single round")
    ap.add_argument("-t", "--timeout", type=int, default=1000, help="ping timeout in ms (default 1000)")
    ap.add_argument("-l", "--log", default="netwatch_log.csv", help="CSV log file (default netwatch_log.csv)")
    args = ap.parse_args()
    rounds = 1 if args.once else args.rounds

    hosts = load_hosts(args.hosts_file)
    if not hosts:
        raise SystemExit("No hosts found in " + args.hosts_file)
    state = {name: None for name, _ in hosts}          # None = unknown, True = up, False = down
    stats = {name: {"up": 0, "total": 0, "lat": []} for name, _ in hosts}

    new_log = True
    try:
        new_log = open(args.log, encoding="utf-8").read(1) == ""
    except FileNotFoundError:
        pass
    log = open(args.log, "a", newline="", encoding="utf-8")
    writer = csv.writer(log)
    if new_log:
        writer.writerow(["timestamp", "name", "address", "status", "latency_ms"])

    print(f"NetWatch: monitoring {len(hosts)} hosts every {args.interval}s. Logging to {args.log}. Ctrl+C to stop.")
    n = 0
    try:
        while True:
            n += 1
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with ThreadPoolExecutor(max_workers=min(32, len(hosts))) as pool:
                results = list(pool.map(lambda h: ping(h[1], args.timeout), hosts))
            for (name, addr), lat in zip(hosts, results):
                up = lat is not None
                s = stats[name]
                s["total"] += 1
                if up:
                    s["up"] += 1
                    s["lat"].append(lat)
                writer.writerow([ts, name, addr, "UP" if up else "DOWN", "" if lat is None else lat])
                prev = state[name]
                if prev is None:
                    print(f"[{ts}] {name:<20} {addr:<18} {'UP' if up else 'DOWN'}"
                          + (f"  {lat:.0f} ms" if up else ""))
                elif prev and not up:
                    print(f"[{ts}] ALERT    {name} ({addr}) is DOWN")
                elif not prev and up:
                    print(f"[{ts}] RECOVERY {name} ({addr}) is back UP ({lat:.0f} ms)")
                state[name] = up
            log.flush()
            if rounds and n >= rounds:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print()
    finally:
        log.close()

    print("\nSummary")
    print(f"{'Host':<20} {'Uptime':>8} {'Avg ms':>8} {'Max ms':>8}  Status")
    for name, _ in hosts:
        s = stats[name]
        if not s["total"]:
            continue
        uptime = 100 * s["up"] / s["total"]
        avg = f"{sum(s['lat']) / len(s['lat']):.1f}" if s["lat"] else "-"
        mx = f"{max(s['lat']):.0f}" if s["lat"] else "-"
        print(f"{name:<20} {uptime:>7.1f}% {avg:>8} {mx:>8}  {'UP' if state[name] else 'DOWN'}")


if __name__ == "__main__":
    main()
