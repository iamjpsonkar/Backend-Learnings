← [Previous: Users & Permissions](./users-groups-permissions.md) | [Home](../README.md) | [Next: Package Managers →](./package-managers.md)

---

# Linux Processes and Services

## Processes

Every running program is a **process** with a unique **PID** (Process ID). Processes form a parent-child hierarchy rooted at PID 1 (systemd or init).

### Viewing Processes

```bash
# Snapshot of all processes
ps aux
# a = all users, u = user-oriented format, x = include processes without terminal

# Column meanings:
# USER  PID  %CPU  %MEM  VSZ    RSS    TTY  STAT  START  TIME  COMMAND
# root  1    0.0   0.1   168940 13312  ?    Ss    Jan01  0:05  /sbin/init

# Filter processes
ps aux | grep nginx
ps -p 1234                       # info for specific PID
ps --ppid 1234                   # children of a process
ps aux --sort=-%cpu | head -10   # top 10 by CPU usage
ps aux --sort=-%mem | head -10   # top 10 by memory usage

# Find PID by name
pgrep nginx                      # list PIDs matching name
pgrep -a nginx                   # with full command
pidof nginx                      # similar, returns all PIDs
```

### STAT Column Values

| Code | Meaning |
|------|---------|
| `S` | Sleeping (waiting for event) |
| `R` | Running or runnable |
| `D` | Uninterruptible sleep (usually I/O — cannot be killed) |
| `Z` | Zombie (dead but not cleaned up by parent) |
| `T` | Stopped (paused) |
| `s` | Session leader |
| `l` | Multi-threaded |
| `+` | In the foreground process group |
| `<` | High priority (nice < 0) |
| `N` | Low priority (nice > 0) |

### Interactive Process Viewers

```bash
top                              # built-in, press q to quit
                                 # keys: k (kill), r (renice), M (sort by mem), P (sort by cpu)
htop                             # improved top (install: apt install htop)
                                 # F1=help, F9=kill, F6=sort, F3=search
```

---

## Signals

Signals are software interrupts sent to processes to request some action.

```bash
# Send signals
kill PID                         # send SIGTERM (15) — polite request to stop
kill -9 PID                      # send SIGKILL — force kill (cannot be caught)
kill -HUP PID                    # send SIGHUP — reload config (many daemons use this)
kill -STOP PID                   # pause a process
kill -CONT PID                   # resume a paused process

# By name (kill all matching)
pkill nginx                      # send SIGTERM to all nginx processes
pkill -9 nginx                   # SIGKILL all nginx processes
pkill -HUP sshd                  # reload sshd config without restart
killall python3                  # kill by exact name
```

### Common Signals

| Signal | Number | Action | Use |
|--------|--------|--------|-----|
| `SIGHUP` | 1 | Hangup/reload | Reload daemons without restart |
| `SIGINT` | 2 | Interrupt | Ctrl+C in terminal |
| `SIGKILL` | 9 | Force kill | Cannot be caught or ignored — last resort |
| `SIGTERM` | 15 | Terminate | Graceful shutdown (default for `kill`) |
| `SIGSTOP` | 19 | Pause | Cannot be caught |
| `SIGCONT` | 18 | Continue | Resume a paused process |
| `SIGUSR1/2` | 10/12 | User-defined | App-specific (e.g., log rotation in nginx) |

> **Always try SIGTERM before SIGKILL.** SIGKILL cannot be caught by the application — it cannot clean up open files, flush buffers, or release locks. SIGTERM lets the application do a graceful shutdown.

---

## Process Priority (nice / renice)

**Nice value** ranges from -20 (highest priority) to +19 (lowest priority). Default is 0.

```bash
# Start a process with lower priority (good for background tasks)
nice -n 10 ./backup.sh
nice -n 19 find / -name "*.log"     # almost no CPU impact

# Change priority of a running process
renice -n 5 -p 1234                 # set nice=5 for PID 1234
renice -n -5 -p 1234                # increase priority (requires root)
renice -n 10 -u deploy              # lower priority for all deploy's processes
```

---

## Job Control

```bash
# Run in background
./long-script.sh &                   # start in background; shell prints [1] PID
nohup ./long-script.sh &             # survive terminal close (output to nohup.out)
nohup ./long-script.sh > out.log 2>&1 &  # custom output file

# Manage jobs
jobs                                 # list background jobs in current shell
fg                                   # bring most recent background job to foreground
fg %1                                # bring job 1 to foreground
bg %1                                # resume stopped job 1 in background
Ctrl+Z                               # suspend (pause) current foreground process
Ctrl+C                               # terminate current foreground process

# Disown (detach from shell without nohup)
./long-script.sh &
disown %1                            # process continues after shell exits
```

---

## systemd and Services

Modern Linux distributions use **systemd** as PID 1. It manages services (units), mounts, timers, sockets, and the boot process.

### systemctl — Control Services

```bash
# Service lifecycle
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx              # stop then start
sudo systemctl reload nginx               # reload config without full restart (if supported)
sudo systemctl try-restart nginx          # restart only if already running

# Enable/disable at boot
sudo systemctl enable nginx               # start at boot
sudo systemctl disable nginx              # don't start at boot
sudo systemctl enable --now nginx         # enable AND start immediately
sudo systemctl disable --now nginx        # disable AND stop immediately

# Query status
systemctl status nginx                    # detailed status with recent log lines
systemctl is-active nginx                 # prints 'active' or 'inactive'; exit code 0/1
systemctl is-enabled nginx                # prints 'enabled' or 'disabled'
systemctl is-failed nginx                 # exit code 0 if failed

# List units
systemctl list-units --type=service             # all running services
systemctl list-units --type=service --all       # include inactive
systemctl list-unit-files --type=service        # all installed services + enabled status
```

### Viewing Logs with journalctl

```bash
# All logs
journalctl                                 # all logs (oldest first), q to quit

# Service-specific
journalctl -u nginx                        # logs for nginx only
journalctl -u nginx -f                     # follow (live tail)
journalctl -u nginx --since "1 hour ago"
journalctl -u nginx --since "2024-01-15 10:00:00" --until "2024-01-15 11:00:00"

# Boot and time filters
journalctl -b                              # current boot only
journalctl -b -1                           # previous boot
journalctl --since yesterday
journalctl --since "2024-01-15" --until "2024-01-16"

# Filtering by priority
journalctl -p err                          # errors and above
journalctl -p warning -u sshd             # warnings and above for sshd

# Useful flags
journalctl -n 100                          # last 100 lines
journalctl -o json-pretty                  # JSON output (good for log shipping)
journalctl --no-pager | grep "FAILED"      # pipe to grep

# Disk usage by journal
journalctl --disk-usage
sudo journalctl --vacuum-size=100M         # trim journal to 100MB
sudo journalctl --vacuum-time=7d           # remove logs older than 7 days
```

### Writing a systemd Unit File

Unit files live in:
- `/lib/systemd/system/` — installed by packages (do not edit)
- `/etc/systemd/system/` — your custom units (override package units here)

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application
Documentation=https://github.com/example/myapp
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=myapp
Group=myapp
WorkingDirectory=/opt/myapp
ExecStart=/opt/myapp/bin/myapp --config /etc/myapp/config.yaml
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal
SyslogIdentifier=myapp
Environment=ENV=production
EnvironmentFile=-/etc/myapp/env   # - prefix = ignore if missing
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/var/lib/myapp /var/log/myapp

[Install]
WantedBy=multi-user.target
```

```bash
# After creating/editing a unit file:
sudo systemctl daemon-reload             # reload systemd config
sudo systemctl enable --now myapp        # enable and start
```

### Service Types

| Type | Behaviour | Use when |
|------|-----------|---------|
| `simple` | ExecStart is the main process | Most applications |
| `forking` | Process forks; parent exits | Traditional daemons that fork (nginx, apache) |
| `oneshot` | Run once then exit | One-time setup tasks |
| `notify` | Process sends ready notification via sd_notify | Systemd-aware apps |
| `idle` | Start after all other units finish | Low-priority tasks |

---

## Screen and tmux — Terminal Multiplexers

Essential for long-running processes on remote servers — sessions survive SSH disconnection.

### tmux (recommended)

```bash
# Start
tmux                                 # new session
tmux new -s deploy                   # named session

# Key bindings (default prefix: Ctrl+b)
Ctrl+b d        # detach (session keeps running)
Ctrl+b c        # new window
Ctrl+b n / p    # next / previous window
Ctrl+b 0-9      # switch to window number
Ctrl+b %        # split pane vertically
Ctrl+b "        # split pane horizontally
Ctrl+b arrow    # move between panes
Ctrl+b [        # scroll mode (q to exit)
Ctrl+b z        # zoom/unzoom pane

# Manage sessions
tmux ls                              # list sessions
tmux attach -t deploy                # re-attach to 'deploy' session
tmux kill-session -t deploy          # kill session
```

### screen (older alternative)

```bash
screen -S mysession                  # new named session
Ctrl+a d                             # detach
screen -r mysession                  # re-attach
screen -ls                           # list sessions
```

---

## Resource Monitoring

```bash
# CPU and memory at a glance
uptime                               # load averages (1m, 5m, 15m)
free -h                              # memory usage
cat /proc/loadavg                    # raw load average

# Load average interpretation:
# On a 2-core system:
# 1.0  = 50% busy
# 2.0  = 100% busy (one core fully loaded)
# 4.0  = 200% busy (queuing — investigate)

# Disk I/O
iostat -x 1 5                        # I/O stats, refresh every 1s, 5 times
iotop                                # interactive I/O monitor (apt install iotop)

# Network
netstat -tuln                        # listening ports (deprecated, use ss)
ss -tuln                             # listening TCP/UDP sockets
ss -tulnp                            # with process names (requires root)
ss -s                                # socket statistics summary
```

---

## References

- [systemd unit file options](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [journalctl manual](https://man7.org/linux/man-pages/man1/journalctl.1.html)
- [Linux signals reference](https://man7.org/linux/man-pages/man7/signal.7.html)
- [tmux cheatsheet](https://tmuxcheatsheet.com/)
---

← [Previous: Users & Permissions](./users-groups-permissions.md) | [Home](../README.md) | [Next: Package Managers →](./package-managers.md)
