← [Previous: Docker](./docker.md) | [Home](../README.md) | [Next: Glossary →](../25-glossary/README.md)

---

# Linux Cheatsheet

```bash
# ── FILES AND DIRECTORIES ──────────────────────────────────────────────────────
ls -lah                                 # list with sizes, hidden files
ls -lt                                  # sort by modification time
find /app -name "*.log" -mtime -1       # files modified in last 24h
find /app -size +100M -type f           # files larger than 100 MB
find /var -name "*.conf" -exec ls -lh {} \;

stat file.txt                           # file metadata (size, inode, timestamps)
file unknown-file                       # detect file type

cp -a src/ dest/                        # copy preserving permissions/timestamps
cp -r dir/ dest/                        # recursive copy
rsync -avz --progress src/ user@host:dest/  # sync with progress

# ── TEXT PROCESSING ────────────────────────────────────────────────────────────
grep -r "ERROR" /var/log/              # recursive search
grep -i "error" file.log               # case-insensitive
grep -v "DEBUG" file.log               # exclude matches
grep -n "pattern" file.log             # show line numbers
grep -c "ERROR" file.log               # count matches
grep -A 3 -B 2 "CRITICAL" file.log    # 3 lines after, 2 before match
grep -E "ERROR|WARN" file.log          # extended regex (multiple patterns)

# View logs
tail -f /var/log/app.log               # follow log file
tail -n 100 /var/log/app.log           # last 100 lines
head -n 50 /var/log/app.log            # first 50 lines
less +F /var/log/app.log               # less with follow mode (Ctrl-C to stop follow)

# Count and sort
cat access.log | awk '{print $1}' | sort | uniq -c | sort -rn | head -10
wc -l file.log                         # line count

# Column extraction
cat file.csv | cut -d, -f1,3           # columns 1 and 3
cat data.txt | awk '{print $2, $5}'    # fields 2 and 5

# Stream editing
sed -n '100,200p' file.log             # print lines 100-200
sed 's/old/new/g' file.txt             # replace all occurrences
sed -i 's/127.0.0.1/0.0.0.0/g' app.conf  # in-place edit

# JSON parsing
cat response.json | python3 -m json.tool     # pretty print
curl -s api/endpoint | jq '.data[0].name'   # extract field
cat events.ndjson | jq -c 'select(.level == "ERROR")'  # filter

# ── PROCESSES ──────────────────────────────────────────────────────────────────
ps aux                                 # all processes
ps aux | grep python                   # find process
pgrep -f "uvicorn"                     # get PIDs matching pattern
pkill -f "uvicorn"                     # kill processes matching pattern

# Interactive process viewer
top                                    # basic
htop                                   # better (install if not present)

# Process tree
pstree -p

# Signals
kill -15 PID                           # SIGTERM (graceful)
kill -9 PID                            # SIGKILL (force)
kill -1 PID                            # SIGHUP (reload config)
killall nginx                          # kill all processes named nginx

# Background jobs
command &                              # run in background
nohup command &                        # persist after logout
nohup command > output.log 2>&1 &     # redirect output
jobs                                   # list background jobs
fg %1                                  # bring job 1 to foreground
disown %1                              # detach job from shell

# ── DISK AND MEMORY ────────────────────────────────────────────────────────────
df -h                                  # disk usage by filesystem
du -sh /var/log/*                      # size of each item in dir
du -sh * | sort -h | tail -10          # largest items in current dir

free -h                                # memory usage
vmstat 1 5                             # system stats every 1s, 5 times
iostat -x 1                            # disk I/O stats

# Find what's using disk
ncdu /var                              # interactive (install ncdu)

# ── NETWORKING ─────────────────────────────────────────────────────────────────
ip addr show                           # IP addresses (modern)
ifconfig                               # IP addresses (older)
ip route show                          # routing table

ss -tlnp                               # TCP listening ports + PIDs
netstat -tlnp                          # older equivalent
lsof -i :8080                          # what's using port 8080

# Connectivity testing
ping -c 4 8.8.8.8
curl -sv https://api.example.com/health 2>&1  # verbose HTTP
curl -w "\n%{http_code} %{time_total}s\n" -sf https://api.example.com/
nc -zv host 5432                       # test TCP port
traceroute api.example.com
mtr api.example.com                    # combined ping + traceroute

# DNS
nslookup api.example.com
dig api.example.com
dig +short api.example.com
dig api.example.com @8.8.8.8           # query specific DNS server

# ── SERVICES (SYSTEMD) ─────────────────────────────────────────────────────────
systemctl status myapp                 # service status
systemctl start myapp
systemctl stop myapp
systemctl restart myapp
systemctl reload myapp                 # reload config without restart
systemctl enable myapp                 # start on boot
systemctl disable myapp
journalctl -u myapp -f                 # follow service logs
journalctl -u myapp --since "1 hour ago"
journalctl -u myapp -n 100             # last 100 lines

# ── PERMISSIONS ────────────────────────────────────────────────────────────────
chmod 755 script.sh                    # rwxr-xr-x
chmod +x script.sh                     # add execute
chmod -R 644 /app/config/              # recursive
chown appuser:appgroup file.txt        # change owner:group
chown -R appuser:appgroup /app/

# ── ARCHIVES ───────────────────────────────────────────────────────────────────
tar -czf archive.tar.gz ./dir/         # create gzipped tar
tar -xzf archive.tar.gz                # extract
tar -tzf archive.tar.gz                # list contents
zip -r archive.zip ./dir/
unzip archive.zip

# ── ENVIRONMENT AND SHELL ──────────────────────────────────────────────────────
env                                    # all environment variables
env | grep -i aws                      # filter env vars
export MY_VAR=value                    # set env var for session
unset MY_VAR                           # remove env var

which python3                          # locate command
type python3                           # same, with alias detection
command -v python3                     # portable version

history                                # command history
history | grep docker | tail -20       # search history
!!                                     # repeat last command
!$                                     # last argument of previous command
Ctrl+R                                 # reverse search history

# ── USEFUL PATTERNS ────────────────────────────────────────────────────────────
# Watch a command (refresh every 2s)
watch -n 2 'df -h && echo "---" && free -h'

# Run on multiple hosts
for HOST in web-01 web-02 web-03; do
    echo "=== $HOST ==="; ssh $HOST 'systemctl status myapp | head -5'
done

# Measure command time
time curl -sf https://api.example.com/health

# Redirect stderr to stdout
command 2>&1 | grep ERROR

# Ignore errors in pipeline
set +e; command; set -e
```

---

← [Previous: Docker](./docker.md) | [Home](../README.md) | [Next: Glossary →](../25-glossary/README.md)
