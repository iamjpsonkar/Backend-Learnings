# Hints — Linux Debugging

Read hints one at a time. Only move to the next if still stuck.

---

## Hint 1 — User identity

```sh
id
# uid=101(nginx) gid=101(nginx) groups=101(nginx)
whoami
# nginx
```

---

## Hint 2 — Process list in Alpine

Alpine uses BusyBox. The `ps` command works but may look different:
```sh
ps aux
# or with full format:
ps -ef
```

---

## Hint 3 — Port scanning without netstat

If `netstat` is missing:
```sh
ss -tlnp      # Show TCP listening sockets
cat /proc/net/tcp   # Raw kernel socket table (hex ports)
```

To decode hex port (e.g. 0050 = 80):
```sh
printf "%d\n" 0x0050
```

---

## Hint 4 — Finding config files

```sh
find /etc/nginx -type f -name "*.conf"
cat /etc/nginx/nginx.conf
```

---

## Hint 5 — Disk usage

```sh
df -h /          # Space on root partition
du -sh /var/*    # Space per directory under /var
```

---

## Hint 6 — File permissions explained

```
-rw-r--r-- 1 root root 648 Jan  1 00:00 nginx.conf
│││││││││
│││││││└── other: r-- (read only)
│││││││
│││││└──── group: r-- (read only)
│││││
│└──────── owner: rw- (read + write)
└───────── type: - (regular file)
```

If you are `nginx` user and file is owned by `root`, you can READ but not WRITE.
