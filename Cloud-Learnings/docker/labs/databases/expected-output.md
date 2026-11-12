# Expected Output — Databases

## PostgreSQL \dt

```
           List of relations
 Schema |  Name  | Type  |  Owner
--------+--------+-------+---------
 app    | items  | table | labuser
 app    | orders | table | labuser
 app    | users  | table | labuser
```

## PostgreSQL SELECT users

```
 id | username |         email          |         created_at
----+----------+------------------------+----------------------------
  1 | alice    | alice@example.local    | 2024-01-01 12:00:00
  2 | bob      | bob@example.local      | 2024-01-01 12:00:00
  3 | carol    | carol@example.local    | 2024-01-01 12:00:00
```

## MongoDB find users

```json
[
  {"_id": "...", "username": "alice", "email": "alice@example.local", "tags": ["admin", "user"]},
  {"_id": "...", "username": "bob", "email": "bob@example.local", "tags": ["user"]}
]
```

## Redis INFO server (snippet)

```
# Server
redis_version:7.2.0
redis_mode:standalone
os:Linux
tcp_port:6379
uptime_in_seconds:3600
```

## Backup file

```bash
ls -lh backup.sql
# -rw-r--r-- 1 user group 4.2K Jan 1 12:00 backup.sql

head -5 backup.sql
# --
# -- PostgreSQL database dump
# --
# -- Dumped from database version 16.x
```
