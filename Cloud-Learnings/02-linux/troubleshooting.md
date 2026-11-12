← [Previous: Cron & Scheduling](./cron-scheduling.md) | [Home](../README.md) | [Next: Networking →](../03-networking/README.md)

---

# Linux Troubleshooting

A systematic approach to diagnosing common production problems. Work from symptoms to root cause — do not guess and restart services before gathering evidence.

---

## General Methodology

```
1. Gather symptoms     — what exactly is failing, when did it start?
2. Check recent events — recent deploys, config changes, cron jobs, kernel updates
3. Examine logs        — journalctl, /var/log/, application logs
4. Observe resources   — CPU, memory, disk, network, file descriptors
5. Form hypothesis     — single most likely cause
6. Test hypothesis     — targeted investigation, not blind restarts
7. Fix and verify      — confirm the issue is resolved, not just masked
8. Document            — what happened, why, how it was fixed
```

---

## Disk Full

### Symptoms

- `No space left on device` in application logs
- Services failing to write logs or create temp files
- `df -h` shows 100% on a partition

### Diagnosis

```bash
# Step 1: identify which filesystem is full
df -h

# Step 2: find the large directories
du -sh /var/log/*        # often the culprit on servers
du -h --max-depth=2 / 2>/dev/null | sort -rh | head -20

# Step 3: find large individual files
find / -type f -size +500M -exec ls -lh {} \; 2>/dev/null

# Step 4: find deleted files still held open (common with log files)
# A process writes to a deleted file — space is not freed until the process closes it
lsof | grep deleted | awk '{print $7, $9}' | sort -rh | head -20

# Step 5: check inode exhaustion (separate from block space)
df -i
# If Use% shows 100% on inodes, there are too many small files
# Find the directories with the most files:
find / -xdev -printf '%h\n' 2>/dev/null | sort | uniq -c | sort -rn | head -20
```

### Fix

```bash
# 1. Clear old log files (check before deleting)
sudo journalctl --disk-usage
sudo journalctl --vacuum-time=7d          # keep last 7 days of journal
sudo journalctl --vacuum-size=100M        # or keep under 100MB

# 2. Clear package manager caches
sudo apt clean                            # Ubuntu
sudo dnf clean all                        # Amazon Linux / RHEL
sudo docker system prune -f              # remove unused Docker layers/images

# 3. Truncate a log file that's growing too fast (do NOT delete it if a process has it open)
> /var/log/app/error.log                  # truncate to zero bytes without removing

# 4. Release space from deleted-but-open files without restart
# Kill the process holding the deleted file open — it will reopen/recreate it
kill -HUP $(lsof | grep deleted | grep "app.log" | awk '{print $2}')

# 5. Find and remove old application artifacts
find /opt/releases -maxdepth 1 -type d -mtime +30 | sort | head -n -3 | xargs rm -rf
```

---

## High CPU

### Symptoms

- Load average significantly above CPU count (`uptime`)
- Application response times degraded
- Server unresponsive to SSH or commands are slow

### Diagnosis

```bash
# Step 1: check load average vs CPU count
uptime
# Load 8.0 on a 2-core instance = heavily overloaded
nproc                         # number of logical CPUs

# Step 2: find the CPU-consuming processes
top                           # press P to sort by CPU
# or non-interactive snapshot:
ps aux --sort=-%cpu | head -15

# Step 3: identify the process
ps -p <PID> -o pid,comm,cmd,args,pcpu,pmem

# Step 4: check if it is a kernel issue (CPU in system mode)
top                           # look at %sy column (system time)
# High sy = kernel space work — check disk I/O, context switches
vmstat 1 5
# Check context switches (cs column) and interrupts (in column)

# Step 5: per-thread CPU if a process has many threads
ps -L -p <PID> --sort=-%cpu | head -20

# Step 6: trace what a process is actually doing
strace -p <PID> -c -f         # system call summary, 30s then Ctrl+C
# or follow a specific call:
strace -p <PID> -e openat,read,write 2>&1 | head -50
```

### Fix

```bash
# Reduce priority of a runaway background job
renice -n 10 -p <PID>

# Kill gracefully, then force if needed
kill <PID>
sleep 10 && kill -9 <PID>     # only if SIGTERM doesn't work

# If a service is looping/stuck, restart it
sudo systemctl restart <service>

# If the issue recurs, check logs for errors that trigger a tight loop
journalctl -u <service> --since "1 hour ago" -p warning
```

---

## Memory Exhaustion / OOM

### Symptoms

- Processes killed with `Out of memory: Kill process`
- Application suddenly exits
- `free -h` shows little or no free + cached memory

### Diagnosis

```bash
# Step 1: current memory usage
free -h
# Buffers/cache is reclaimable — "available" is the key number

# Step 2: top memory consumers
ps aux --sort=-%mem | head -15

# Step 3: check if OOM killer fired recently
dmesg | grep -i "killed process"
journalctl -k | grep -i "out of memory"   # kernel messages
grep -i "oom\|killed" /var/log/syslog | tail -30

# Step 4: which service was killed?
dmesg | grep "oom_kill_process\|Killed process"

# Step 5: memory detail for a specific process
cat /proc/<PID>/status | grep -E "Vm|Rss|Swap"
pmap <PID> | tail -5          # virtual memory map summary
```

### Fix

```bash
# Temporary: drop reclaimable caches (safe — kernel will re-fill as needed)
sync
echo 3 | sudo tee /proc/sys/vm/drop_caches

# Add swap as emergency buffer (not a long-term solution)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
# To persist across reboots, add to /etc/fstab:
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Tune OOM killer score (higher = more likely to be killed first)
echo 500 > /proc/<PID>/oom_score_adj    # 1000 = always kill first, -1000 = never kill

# Longer term: add memory, right-size the instance, or fix the memory leak
```

---

## Network Debugging

### Connectivity Check

```bash
# Is the problem local or remote?

# 1. Can we reach the gateway?
ip route show
ping -c 3 $(ip route | grep default | awk '{print $3}')

# 2. DNS resolution
dig google.com                      # full DNS response
nslookup google.com                 # alternative
cat /etc/resolv.conf                # which DNS servers are configured?

# 3. Can we reach external IPs?
ping -c 3 8.8.8.8                  # if this works but DNS fails → DNS problem

# 4. Specific host and port
nc -zv hostname 443                 # TCP connect test (verbose)
nc -zv 10.0.1.50 5432               # test RDS/internal port
curl -v --max-time 5 https://api.example.com/health   # full HTTP request

# 5. Trace the path
traceroute api.example.com
mtr --report api.example.com        # combined ping + traceroute (install mtr)
```

### Listening Ports and Open Connections

```bash
# What ports is this machine listening on?
ss -tulnp                           # TCP/UDP listening, with process name (needs root)
netstat -tulnp                      # older equivalent

# Active connections
ss -tnp                             # established TCP connections with process
ss -s                               # statistics summary

# Is the expected service listening?
ss -tulnp | grep ':80'
ss -tulnp | grep ':5432'

# How many connections per remote IP?
ss -tn state established | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -10
```

### Firewall / Security Group Debugging

```bash
# Linux firewall rules (iptables)
sudo iptables -L -n -v --line-numbers   # list all rules

# Modern nftables (Amazon Linux 2023 / RHEL 8+)
sudo nft list ruleset

# Check if firewalld is running
sudo firewall-cmd --list-all

# Test inbound connectivity from another host
nc -zv <server-ip> <port>           # run from a test client

# Capture traffic to verify packets arrive
sudo tcpdump -i any -n "port 443 and host 10.0.1.50" -c 20
sudo tcpdump -i eth0 -n "tcp port 5432" -w /tmp/capture.pcap   # save for analysis
```

---

## Service Failures

### Systematic Service Diagnosis

```bash
# Step 1: check status and recent events
systemctl status <service>

# Step 2: recent logs (most important)
journalctl -u <service> --since "30 minutes ago"
journalctl -u <service> -n 100              # last 100 lines
journalctl -u <service> -p err              # errors only

# Step 3: check if it's trying to restart repeatedly
systemctl show <service> --property=ActiveState,SubState,NRestarts,Result

# Step 4: manual start to see output directly
sudo systemctl stop <service>
sudo -u <service-user> /path/to/binary --config /etc/service/config.yaml
# This shows the startup error interactively

# Step 5: validate config files
nginx -t                                    # nginx config test
apache2ctl configtest                       # Apache
sshd -t                                     # sshd config
/usr/sbin/postfix check                     # Postfix
```

### Systemd Journal Gaps

```bash
# Show boot events (find when things started going wrong)
journalctl --list-boots                     # list all boots
journalctl -b -1                            # last boot's logs
journalctl -b 0 --since "boot"             # current boot from start

# Check for service crash patterns
journalctl -u <service> | grep -E "start|stop|fail|error|crash" -i
```

---

## Log Analysis Patterns

```bash
# Count error frequency over time
awk '{print $4}' /var/log/nginx/error.log \
    | cut -c1-14 \
    | sort | uniq -c | sort -rn | head -20

# Find the most common log messages (identify dominant errors)
grep "ERROR" /var/log/app/app.log \
    | sed 's/[0-9]\{4\}-[0-9-]\{7\}T[0-9:\.Z]*//g' \
    | sort | uniq -c | sort -rn | head -20

# Tail multiple log files simultaneously
tail -f /var/log/nginx/error.log /var/log/app/app.log

# Search across all logs for a specific event
journalctl --since "2024-01-15 10:00" --until "2024-01-15 11:00" | grep "database"
grep -r "connection refused" /var/log/ 2>/dev/null

# Extract unique IPs hitting an nginx endpoint
awk '$7 == "/api/endpoint" {print $1}' /var/log/nginx/access.log \
    | sort | uniq -c | sort -rn | head -20
```

---

## Performance Profiling

```bash
# CPU profiling: what is taking CPU time?
perf top                            # live CPU profiler (install linux-tools)
perf record -g -p <PID> -- sleep 30 && perf report   # profile for 30s

# I/O bottleneck
iostat -x 1 5                       # extended disk stats; look at %util and await
iotop                               # interactive per-process I/O (install iotop)

# Check for I/O wait (iowait column in top/vmstat)
vmstat 1 5
# If wa column > 10% → I/O is a bottleneck

# File descriptor exhaustion
cat /proc/sys/fs/file-max           # system-wide max open files
lsof | wc -l                        # current open file handles system-wide
lsof -p <PID> | wc -l              # open files for one process

# Increase fd limit if needed (requires root)
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf
# Apply without reboot:
ulimit -n 65536                     # current shell only
```

---

## Boot Problems

```bash
# View boot messages
dmesg | less                        # kernel ring buffer
dmesg | grep -E "error|fail|warn" -i | head -40
journalctl -b --priority=warning    # warnings and above from current boot

# Check fstab for bad mount entries (common cause of boot failure)
sudo mount -a -v                    # try all fstab mounts; errors are printed

# Recovery: if system won't boot due to fstab error
# 1. Boot into rescue/emergency mode via cloud console or grub
# 2. Mount root filesystem read-write:
mount -o remount,rw /
# 3. Edit /etc/fstab and fix the bad entry
# 4. Reboot

# Common boot failure: systemd unit stuck
systemctl list-jobs                 # show running/waiting jobs during boot
systemctl list-units --state=failed # failed units

# Boot sequence analysis
systemd-analyze                     # total boot time
systemd-analyze blame               # time per unit, sorted
systemd-analyze critical-chain      # the slowest chain
```

---

## Common One-Liner Diagnostics

```bash
# Who is logged in and what are they doing?
who
w

# Last logins and reboots
last | head -20

# Recent failed logins
lastb | head -20                    # requires root

# Recent sudo usage
grep sudo /var/log/auth.log | tail -20

# Are there zombie processes?
ps aux | awk '$8=="Z" {print $0}'

# File handles in use vs limit
cat /proc/sys/fs/file-nr            # used | free | max

# Check if a process is swapping heavily
cat /proc/<PID>/status | grep VmSwap

# What changed recently (last 24h)
find /etc -newer /proc/1/cmdline -type f 2>/dev/null | head -20
rpm -qa --last | head -20           # recently installed packages (RHEL)
dpkg -l | grep '^ii' | tail -20    # recently installed packages (Ubuntu; approximate)

# Watch system metrics continuously (refresh every 2s)
watch -n2 'uptime; free -h; df -h /'
```

---

## EC2 / Cloud-Specific Debugging

```bash
# Cloud-init / user data script output
cat /var/log/cloud-init-output.log
cat /var/log/cloud-init.log

# Instance metadata (available from inside the instance)
curl -s http://169.254.169.254/latest/meta-data/instance-id
curl -s http://169.254.169.254/latest/meta-data/public-ipv4
curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone

# Check instance identity document (signed by AWS)
curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | python3 -m json.tool

# SSM Agent status (required for Session Manager and Run Command)
systemctl status amazon-ssm-agent
sudo systemctl restart amazon-ssm-agent

# CloudWatch Agent logs
cat /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log | tail -50

# EBS volume visible to OS?
lsblk                               # list block devices
ls /dev/xvd*                        # list EBS volumes
file -s /dev/xvdb                   # check if filesystem present (or unformatted)
```

---

## References

- [Linux Performance Analysis in 60 Seconds (Netflix Tech Blog)](https://www.brendangregg.com/Articles/Netflix_Linux_Perf_Analysis_60s.pdf)
- [strace manual](https://man7.org/linux/man-pages/man1/strace.1.html)
- [ss command reference](https://man7.org/linux/man-pages/man8/ss.8.html)
- [Brendan Gregg's Linux Performance Tools](https://www.brendangregg.com/linuxperf.html)
- [AWS EC2 troubleshooting guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/TroubleshootingInstances.html)
---

← [Previous: Cron & Scheduling](./cron-scheduling.md) | [Home](../README.md) | [Next: Networking →](../03-networking/README.md)
