# NetWatch

A small uptime monitor in the style of a NOC dashboard, written in Python with only the standard library.

NetWatch pings a list of devices on a schedule and records each result to a CSV log. When a host goes **down** or **recovers**, it prints an alert. When you stop it, it prints an uptime and latency summary.

I built it with Claude as an AI coding assistant. I used it to design the tool, review the code and test it against live and unreachable hosts.

## Features
- Pings all hosts in parallel, so one slow host doesn't hold up the others
- Works on Windows, macOS and Linux
- Handles a Windows quirk: `ping` can report success even when the reply was "Destination host unreachable"
- Writes a CSV log (timestamp, host, status, latency) that opens in Excel
- Prints an alert when a host changes state, plus an end-of-run summary with uptime %, average and maximum latency

## Usage
```
python netwatch.py hosts.txt                # check every 30 s until Ctrl+C
python netwatch.py hosts.txt -i 10 -n 6     # every 10 s for 6 rounds
python netwatch.py hosts.txt --once         # single check
```
Edit `hosts.txt` to list your own devices as `name, address`.

## Example output
```
[2026-11-06 14:02:10] Google DNS           8.8.8.8            UP  14 ms
[2026-11-06 14:02:10] Test - unreachable   10.255.255.1       DOWN
[2026-11-06 14:02:40] ALERT    Home router (192.168.1.1) is DOWN
[2026-11-06 14:03:10] RECOVERY Home router (192.168.1.1) is back UP (3 ms)
```

## Ideas for next versions
- Email or Discord/Slack webhook alerts
- Check TCP ports (e.g. 443, 3389) as well as ping
- A simple HTML status page generated from the log
