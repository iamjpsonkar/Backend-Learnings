← [Previous: SSH, SCP & rsync](./ssh-scp-rsync.md) | [Home](../README.md) | [Next: Linux Troubleshooting →](./troubleshooting.md)

---

# Cron and Task Scheduling

## Cron Overview

`cron` is the standard Unix scheduler. It runs commands at specified times using a daemon (`crond` or `cron`) that wakes every minute to check for matching jobs.

---

## Cron Syntax

```
┌─────────── minute        (0–59)
│ ┌───────── hour          (0–23)
│ │ ┌─────── day of month  (1–31)
│ │ │ ┌───── month         (1–12 or jan–dec)
│ │ │ │ ┌─── day of week   (0–7, both 0 and 7 = Sunday, or mon–sun)
│ │ │ │ │
* * * * *  command to execute
```

### Special Characters

| Character | Meaning | Example |
|-----------|---------|---------|
| `*` | Any value | `* * * * *` = every minute |
| `,` | List | `1,15,30 * * * *` = at :01, :15, :30 |
| `-` | Range | `1-5 * * * *` = minutes 1 through 5 |
| `/` | Step | `*/15 * * * *` = every 15 minutes |

### Common Examples

```bash
# Every minute
* * * * * /usr/local/bin/check-service.sh

# Every 15 minutes
*/15 * * * * /usr/local/bin/poll-queue.sh

# Every hour at :00
0 * * * * /usr/local/bin/hourly-report.sh

# Daily at 02:30
30 2 * * * /usr/local/bin/backup.sh

# Every weekday (Mon–Fri) at 08:00
0 8 * * 1-5 /usr/local/bin/morning-report.sh

# First day of every month at midnight
0 0 1 * * /usr/local/bin/monthly-cleanup.sh

# Every Sunday at 04:00
0 4 * * 0 /usr/local/bin/weekly-maintenance.sh

# Every 6 hours
0 */6 * * * /usr/local/bin/sync.sh

# At 09:00, 12:00, and 17:00
0 9,12,17 * * * /usr/local/bin/notify.sh
```

### Shorthand Strings

Many cron implementations support these aliases:

| Shorthand | Equivalent | When |
|-----------|-----------|------|
| `@reboot` | — | Once at startup |
| `@hourly` | `0 * * * *` | Every hour at :00 |
| `@daily` / `@midnight` | `0 0 * * *` | Daily at midnight |
| `@weekly` | `0 0 * * 0` | Every Sunday midnight |
| `@monthly` | `0 0 1 * *` | First of month at midnight |
| `@yearly` / `@annually` | `0 0 1 1 *` | January 1 midnight |

---

## crontab — User Cron Jobs

Each user has their own crontab. The `crontab` command manages it.

```bash
# Edit current user's crontab (opens $EDITOR)
crontab -e

# List current crontab
crontab -l

# Remove all cron jobs for current user (dangerous — no confirmation)
crontab -r

# Edit another user's crontab (requires root)
sudo crontab -u deploy -e

# List another user's crontab
sudo crontab -u deploy -l
```

### Best Practices for Crontab Entries

```bash
# Use full paths — cron has a minimal PATH (/usr/bin:/bin)
30 2 * * * /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1

# Set MAILTO to send job output to an email address (or suppress)
MAILTO=""         # suppress all email output
MAILTO=ops@company.com  # send output/errors to this address

# Set environment variables at the top of crontab
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
HOME=/home/deploy

# Redirect stdout and stderr to a log file
30 2 * * * /scripts/backup.sh >> /var/log/backup.log 2>&1

# Discard all output (silent job)
*/5 * * * * /scripts/check.sh > /dev/null 2>&1

# Log with timestamp
0 * * * * echo "$(date '+\%Y-\%m-\%d \%H:\%M:\%S') Starting job" >> /var/log/job.log && /scripts/job.sh >> /var/log/job.log 2>&1
```

---

## System-Wide Cron Locations

```bash
/etc/crontab          # system-wide crontab (has USERNAME field)
/etc/cron.d/          # drop-in directory for system cron jobs
/etc/cron.hourly/     # scripts run every hour
/etc/cron.daily/      # scripts run every day
/etc/cron.weekly/     # scripts run every week
/etc/cron.monthly/    # scripts run every month
```

### /etc/crontab Format (Has Extra User Field)

```bash
# /etc/crontab — system cron with user column
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# m  h  dom  mon  dow   user    command
  30 2  *    *    *     root    /usr/local/bin/backup.sh
  0  *  *    *    *     deploy  /opt/app/scripts/poll.sh
```

### /etc/cron.d/ Drop-in Files

Preferred for package-installed jobs — cleaner than editing `/etc/crontab` directly.

```bash
# Create a drop-in for myapp
cat > /etc/cron.d/myapp << 'EOF'
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=""

# Cleanup temp files every day at 03:15 as deploy user
15 3 * * * deploy /opt/myapp/scripts/cleanup.sh >> /var/log/myapp/cleanup.log 2>&1

# Health check every 5 minutes
*/5 * * * * deploy /opt/myapp/scripts/health-check.sh > /dev/null 2>&1
EOF

chmod 644 /etc/cron.d/myapp    # must be 644 or 600; world-writable files are ignored
```

### Drop-in Script Files (cron.hourly / daily / weekly / monthly)

Place executable scripts (no extension needed) in these directories. The `run-parts` command executes them:

```bash
# Install a daily script
cat > /etc/cron.daily/cleanup-logs << 'EOF'
#!/bin/bash
find /var/log/app -name "*.log" -mtime +30 -delete
EOF
chmod +x /etc/cron.daily/cleanup-logs

# Test with run-parts
sudo run-parts --test /etc/cron.daily    # list scripts that would run
sudo run-parts /etc/cron.daily           # actually run them
```

---

## Anacron — Handling Missed Jobs on Non-24/7 Systems

`anacron` runs jobs that were missed when the system was off. It does not handle minute/hour granularity — only daily, weekly, monthly.

```bash
# /etc/anacrontab format
# period  delay  job-id   command
  1       5      daily    run-parts /etc/cron.daily
  7       10     weekly   run-parts /etc/cron.weekly
  30      15     monthly  run-parts /etc/cron.monthly
```

- **period**: frequency in days
- **delay**: minutes to wait after boot before running
- **job-id**: used for tracking last run time in `/var/spool/anacron/`

---

## Debugging Cron Jobs

```bash
# Check if cron daemon is running
systemctl status cron       # Ubuntu/Debian
systemctl status crond      # Amazon Linux / RHEL

# Cron logs
grep CRON /var/log/syslog   # Ubuntu/Debian
journalctl -u cron          # systems with journald
grep cron /var/log/messages # RHEL / Amazon Linux

# Watch live cron execution
tail -f /var/log/syslog | grep CRON

# Test your script manually as the cron user
sudo -u deploy bash -c '/opt/app/scripts/backup.sh >> /tmp/backup-test.log 2>&1'

# Replicate minimal cron environment
env -i HOME=/home/deploy USER=deploy \
    PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin \
    /bin/bash -c '/opt/app/scripts/backup.sh'
```

### Common Cron Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| Job runs manually but not from cron | Script uses relative paths or missing env vars | Use absolute paths; set PATH in crontab |
| Job output not visible | Output redirected to /dev/null | Redirect to a log file temporarily |
| No log entry at all | Cron daemon not running | `systemctl start cron` |
| Job file in /etc/cron.d/ ignored | Wrong permissions | `chmod 644 /etc/cron.d/myfile` |
| /etc/cron.daily script ignored | Has file extension | Remove extension: `script.sh` → `script` |
| `Permission denied` errors | Script not executable | `chmod +x /path/to/script.sh` |

---

## systemd Timers — Modern Alternative to Cron

systemd timers are more powerful than cron: they support dependencies, can activate on events, log to journald automatically, and show precise last/next run times.

### Create a Timer

Every timer needs a companion `.service` unit:

```ini
# /etc/systemd/system/backup.service
[Unit]
Description=Daily database backup
After=network.target

[Service]
Type=oneshot
User=deploy
ExecStart=/opt/app/scripts/backup.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=backup
```

```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Run backup daily at 02:30
Requires=backup.service

[Timer]
OnCalendar=*-*-* 02:30:00     # daily at 02:30
AccuracySec=1min               # allow up to 1 min drift (saves wake-ups)
Persistent=true                # run missed jobs after downtime

[Install]
WantedBy=timers.target
```

```bash
# Enable and start the timer (not the service)
sudo systemctl daemon-reload
sudo systemctl enable --now backup.timer

# Check status
systemctl status backup.timer
systemctl list-timers --all    # show all timers with last/next run times

# Run immediately (for testing)
sudo systemctl start backup.service

# View logs
journalctl -u backup.service --since "1 hour ago"
```

### Timer Calendar Syntax

```
OnCalendar=*-*-* 02:30:00     # daily at 02:30
OnCalendar=Mon *-*-* 08:00:00 # every Monday at 08:00
OnCalendar=*:0/15             # every 15 minutes
OnCalendar=hourly             # shorthand for *-*-* *:00:00
OnCalendar=daily              # shorthand for *-*-* 00:00:00
OnCalendar=weekly             # shorthand for Mon *-*-* 00:00:00
OnCalendar=monthly            # shorthand for *-*-01 00:00:00
```

```bash
# Validate calendar expression
systemd-analyze calendar "Mon *-*-* 08:00:00"
```

### Monotonic Timers (Relative Timers)

Useful for running jobs a fixed time after boot or last run:

```ini
[Timer]
OnBootSec=5min          # 5 minutes after boot
OnUnitActiveSec=1h      # 1 hour after the service last ran
```

---

## at — One-Time Scheduled Jobs

`at` runs a command once at a specific time. Unlike cron, it does not repeat.

```bash
# Install at
sudo apt install at    # Ubuntu
sudo dnf install at    # Amazon Linux / RHEL

# Schedule a command
echo "/opt/scripts/deploy.sh" | at 14:30
echo "/opt/scripts/restart.sh" | at now + 2 hours
echo "/opt/scripts/cleanup.sh" | at midnight

# Schedule from a script file
at 03:00 < /opt/scripts/maintenance.sh

# List pending jobs
atq

# View job contents
at -c 3        # show job number 3

# Remove a job
atrm 3         # remove job number 3
```

---

## Cloud Scheduling Alternatives

For workloads running on AWS, managed scheduling services avoid the need to maintain a server just for cron.

### Amazon EventBridge Scheduler

Fully managed scheduler — no EC2 required, sub-minute precision, flexible targets (Lambda, ECS, Step Functions, API destinations).

```bash
# Create a schedule to invoke a Lambda every 15 minutes
aws scheduler create-schedule \
    --name every-15-minutes \
    --schedule-expression "rate(15 minutes)" \
    --flexible-time-window Mode=OFF \
    --target '{
        "Arn": "arn:aws:lambda:us-east-1:123456789012:function:my-function",
        "RoleArn": "arn:aws:iam::123456789012:role/scheduler-role"
    }'

# Create a one-time schedule (at equivalent)
aws scheduler create-schedule \
    --name one-time-deploy \
    --schedule-expression "at(2024-12-31T23:59:00)" \
    --flexible-time-window Mode=OFF \
    --target '{"Arn": "...", "RoleArn": "..."}'
```

### When to Use What

| Use case | Best tool |
|----------|----------|
| Anything on an EC2 instance | cron or systemd timer |
| Jobs that should survive reboots | systemd timer with `Persistent=true` |
| Complex dependencies between jobs | systemd timer |
| Serverless / Lambda invocation | EventBridge Scheduler |
| One-off scheduled task on server | `at` |
| Cross-account, cross-region scheduling | EventBridge Scheduler |

---

## References

- [crontab(5) man page](https://man7.org/linux/man-pages/man5/crontab.5.html)
- [systemd.timer man page](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)
- [systemd OnCalendar syntax](https://www.freedesktop.org/software/systemd/man/systemd.time.html)
- [Amazon EventBridge Scheduler](https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html)
- [crontab.guru — interactive cron expression builder](https://crontab.guru/)
---

← [Previous: SSH, SCP & rsync](./ssh-scp-rsync.md) | [Home](../README.md) | [Next: Linux Troubleshooting →](./troubleshooting.md)
