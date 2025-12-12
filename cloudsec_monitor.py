#!/usr/bin/env python3

import os
import time
import subprocess
from threading import Thread
from datetime import datetime

LOG_DIR = "/var/log/cloudsec"
FULL_LOG = os.path.join(LOG_DIR, "cloudsec-full.log")
ALERT_LOG = os.path.join(LOG_DIR, "cloudsec-alerts.log")

alert_keywords = [
    "error",
    "fail",
    "denied",
    "invalid",
    "sql",
    "union select",
    "drop table",
    "xss",
    "<script>",
    "csrf",
    "upload",
    "nmap",
    "masscan",
    "sqlmap",
    "injection",
    "brute",
    "password",
    "sudo",
    "permission denied",
]

os.makedirs(LOG_DIR, exist_ok=True)
for path in [FULL_LOG, ALERT_LOG]:
    if not os.path.exists(path):
        with open(path, "a"):
            pass

def ts():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

def write_full(line):
    line = line.rstrip("\n")
    with open(FULL_LOG, "a", encoding="utf-8", errors="ignore") as f:
        f.write(f"[{ts()}] {line}\n")

def write_alert(line):
    line = line.rstrip("\n")
    with open(ALERT_LOG, "a", encoding="utf-8", errors="ignore") as f:
        f.write(f"[{ts()}] {line}\n")

def watch_file(tag, path):
    if not os.path.exists(path):
        return
    cmd = ["tail", "-F", path]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in proc.stdout:
        line = line.rstrip("\n")
        tagged = f"[{tag}] {line}"
        write_full(tagged)
        l = line.lower()
        if any(w in l for w in alert_keywords):
            write_alert(tagged)

def monitor_syslog():
    watch_file("syslog", "/var/log/syslog")

def monitor_auth():
    watch_file("auth", "/var/log/auth.log")

def monitor_auditd():
    audit_paths = ["/var/log/audit/audit.log", "/var/log/audit.log"]
    for p in audit_paths:
        if os.path.exists(p):
            watch_file("auditd", p)
            return
    cmd = ["journalctl", "-f", "-u", "auditd.service"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    for line in proc.stdout:
        line = line.rstrip("\n")
        tagged = f"[auditd] {line}"
        write_full(tagged)
        l = line.lower()
        if any(w in l for w in alert_keywords):
            write_alert(tagged)

def monitor_conntrack():
    cmd = ["sudo", "conntrack", "-E", "-o", "extended"]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        return

    for line in proc.stdout:
        line = line.rstrip("\n")
        tagged = f"[network] {line}"
        write_full(tagged)
        l = line.lower()
        if any(w in l for w in alert_keywords):
            write_alert(tagged)

def monitor_docker_logs(container_name):
    cmd = ["sudo", "docker", "logs", "-f", container_name]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError:
        write_full(f"[dvwa-docker] docker not found on system")
        return

    for line in proc.stdout:
        line = line.rstrip("\n")
        tagged = f"[dvwa-docker] {line}"
        write_full(tagged)
        l = line.lower()
        if any(w in l for w in alert_keywords):
            write_alert(tagged)

if __name__ == "__main__":
    write_full("===== CloudSec Monitor Started =====")
    write_alert("===== CloudSec Monitor Started =====")

    Thread(target=monitor_syslog, daemon=True).start()
    Thread(target=monitor_auth, daemon=True).start()
    Thread(target=monitor_auditd, daemon=True).start()
    Thread(target=monitor_conntrack, daemon=True).start()
    Thread(target=monitor_docker_logs, args=("youthful_benz",), daemon=True).start()

    while True:
        time.sleep(1)
