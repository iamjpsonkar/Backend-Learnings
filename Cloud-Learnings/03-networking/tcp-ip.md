← [Previous: OSI Model](./osi-model.md) | [Home](../README.md) | [Next: DNS →](./dns.md)

---

# TCP and UDP

TCP (Transmission Control Protocol) and UDP (User Datagram Protocol) are the two dominant Layer 4 transport protocols. Choosing between them — or tuning their behaviour — has significant impact on application performance and reliability.

---

## Protocol Comparison

| Property | TCP | UDP |
|----------|-----|-----|
| Connection | Connection-oriented (handshake) | Connectionless |
| Reliability | Guaranteed delivery, ordered | Best-effort, no ordering guarantee |
| Error checking | Yes (retransmit lost packets) | Checksum only (no retransmit) |
| Flow control | Yes (sliding window) | No |
| Congestion control | Yes (CUBIC, BBR) | No |
| Overhead | Higher (headers + state) | Lower (8-byte header) |
| Latency | Higher (handshake + ACKs) | Lower |
| Use cases | HTTP, SSH, SMTP, databases | DNS, NTP, QUIC, streaming, gaming |

---

## TCP — Detailed

### Three-Way Handshake

Before data flows, TCP establishes a connection:

```
Client                         Server
  │── SYN (seq=x) ──────────────▶│   Client wants to connect
  │◀── SYN-ACK (seq=y, ack=x+1) ─│   Server acknowledges, sends its seq
  │── ACK (ack=y+1) ─────────────▶│   Client acknowledges
  │                               │
  │══════ DATA TRANSFER ══════════│
  │                               │
  │── FIN ────────────────────────▶│  Client done sending
  │◀─ ACK ─────────────────────────│
  │◀─ FIN ─────────────────────────│  Server done sending
  │── ACK ────────────────────────▶│
```

- **SYN** (synchronise): initiates connection, sends initial sequence number
- **ACK** (acknowledge): confirms receipt of previous packet
- **FIN** (finish): graceful close — each direction closes independently
- **RST** (reset): abrupt close — sent on error or to reject a connection

### TCP Connection States

```bash
# View TCP states on a server
ss -tan state established        # all established connections
ss -tan state time-wait          # connections in TIME_WAIT
ss -s                            # summary by state

# Common states:
LISTEN        # waiting for incoming connections (server-side socket)
SYN_SENT      # sent SYN, waiting for SYN-ACK (client initiating)
SYN_RECEIVED  # received SYN, sent SYN-ACK (server, before final ACK)
ESTABLISHED   # connection active, data flowing
FIN_WAIT_1    # sent FIN, waiting for ACK
FIN_WAIT_2    # received ACK of FIN, waiting for server's FIN
TIME_WAIT     # both FINs received; waiting 2×MSL before close
CLOSE_WAIT    # received FIN, waiting for app to close its end
LAST_ACK      # sent FIN after CLOSE_WAIT, waiting for ACK
```

**TIME_WAIT**: A connection in TIME_WAIT holds the port for 2×MSL (Maximum Segment Lifetime, typically 60s). This is intentional — it prevents delayed packets from a dead connection being mistaken for a new connection. High TIME_WAIT count is normal on busy HTTP servers.

### Key TCP Header Fields

| Field | Size | Purpose |
|-------|------|---------|
| Source port | 16 bits | Identifies the sending application |
| Destination port | 16 bits | Identifies the target application |
| Sequence number | 32 bits | Position of this segment in the byte stream |
| Acknowledgment number | 32 bits | Next byte expected from the other side |
| Window size | 16 bits | Receive buffer space available (flow control) |
| Flags | 9 bits | SYN, ACK, FIN, RST, PSH, URG |
| Checksum | 16 bits | Error detection |

### Flow Control and Window Size

The **receive window** (RWND) tells the sender how much data the receiver can buffer. If the receiver is slow (e.g., busy app), it shrinks the window to slow the sender.

```bash
# View socket buffer sizes
cat /proc/sys/net/core/rmem_max      # max receive buffer (bytes)
cat /proc/sys/net/core/wmem_max      # max send buffer (bytes)
cat /proc/sys/net/ipv4/tcp_rmem      # min / default / max receive (bytes)
cat /proc/sys/net/ipv4/tcp_wmem      # min / default / max send (bytes)

# Increase for high-bandwidth, high-latency links (e.g., cross-region replication)
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.ipv4.tcp_rmem="4096 87380 134217728"
```

### Congestion Control

TCP detects network congestion by observing packet loss and RTT changes, then reduces the send rate. Common algorithms:

| Algorithm | Behaviour | Best for |
|-----------|-----------|---------|
| CUBIC (Linux default) | Aggressive after loss | LAN / moderate latency |
| BBR (Google) | Bandwidth + RTT based | High-latency, lossy (long-haul, Wi-Fi) |
| RENO | Classic, conservative | Older systems |

```bash
# Check current congestion control
cat /proc/sys/net/ipv4/tcp_congestion_control

# Switch to BBR (improves throughput on high-latency connections)
echo bbr | sudo tee /proc/sys/net/ipv4/tcp_congestion_control
```

### TCP Keep-Alives

TCP keep-alives detect dead connections (where the other end has disappeared without sending FIN/RST — e.g., network partition, NAT timeout).

```bash
# System-wide defaults (values in seconds)
cat /proc/sys/net/ipv4/tcp_keepalive_time      # idle time before first probe (default 7200s)
cat /proc/sys/net/ipv4/tcp_keepalive_intvl     # interval between probes (default 75s)
cat /proc/sys/net/ipv4/tcp_keepalive_probes    # probes before declaring dead (default 9)

# For cloud environments: reduce keepalive time to detect NAT timeouts faster
sudo sysctl -w net.ipv4.tcp_keepalive_time=60
sudo sysctl -w net.ipv4.tcp_keepalive_intvl=10
sudo sysctl -w net.ipv4.tcp_keepalive_probes=6
```

> **NAT timeouts**: AWS NAT Gateway times out idle TCP connections after 350 seconds. Set application-level or TCP keepalives to less than this to prevent silent drops.

---

## UDP — Detailed

UDP provides no connection, no ordering, and no retransmission. The application is responsible for any reliability it needs.

### UDP Header

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
├───────────────────────┬───────────────────────────────────────────┤
│   Source Port         │   Destination Port                        │
├───────────────────────┼───────────────────────────────────────────┤
│   Length              │   Checksum                                │
├───────────────────────┴───────────────────────────────────────────┤
│   Data ...                                                        │
└───────────────────────────────────────────────────────────────────┘
```

8-byte header (vs 20+ bytes for TCP). This is why DNS responses are fast.

### When to Use UDP

- **DNS**: single request/response; latency matters more than reliability; UDP over port 53
- **NTP**: time synchronisation; single packet; retry is handled by the client
- **DHCP**: broadcast-based; can't use TCP before having an IP
- **Real-time media**: VoIP, video conferencing (WebRTC), gaming — a late packet is worse than a lost one
- **QUIC**: HTTP/3 runs over QUIC, which is UDP + reliability built into the application layer

---

## Common Port Numbers

| Port | Protocol | Service |
|------|----------|---------|
| 20, 21 | TCP | FTP (data, control) |
| 22 | TCP | SSH |
| 23 | TCP | Telnet (insecure — avoid) |
| 25 | TCP | SMTP |
| 53 | TCP + UDP | DNS |
| 67, 68 | UDP | DHCP (server, client) |
| 80 | TCP | HTTP |
| 123 | UDP | NTP |
| 143 | TCP | IMAP |
| 389 | TCP + UDP | LDAP |
| 443 | TCP | HTTPS |
| 465, 587 | TCP | SMTP with TLS |
| 636 | TCP | LDAPS |
| 993 | TCP | IMAPS |
| 3306 | TCP | MySQL / MariaDB |
| 3389 | TCP | RDP |
| 5432 | TCP | PostgreSQL |
| 6379 | TCP | Redis |
| 8080, 8443 | TCP | Common HTTP/HTTPS alternates |
| 27017 | TCP | MongoDB |

---

## Ports and Ephemeral Ports

When a client connects to a server, the OS assigns a random **ephemeral (source) port** from the ephemeral range.

```bash
# View the ephemeral port range
cat /proc/sys/net/ipv4/ip_local_port_range
# Typically: 32768 60999 (Linux default)

# Expand if running out of ports (high-volume NAT or connection-heavy apps)
sudo sysctl -w net.ipv4.ip_local_port_range="1024 65535"
```

Under high load, you can exhaust the ephemeral port range — this manifests as `connection refused` or `Cannot assign requested address`.

---

## Viewing and Debugging Connections

```bash
# All listening services
ss -tulnp                     # TCP + UDP, listening, numeric, show process

# All established TCP connections
ss -tnp state established

# Connections to a specific port
ss -tnp 'dst :5432'           # connections going TO port 5432

# Count connections by state (health check)
ss -tan | awk '{print $1}' | sort | uniq -c | sort -rn

# Measure round-trip time and packet loss to a host
ping -c 10 db.internal

# Capture TCP traffic (requires root)
sudo tcpdump -i any -n "tcp port 443" -c 50
sudo tcpdump -i eth0 -n "host 10.0.1.50 and port 5432" -w /tmp/debug.pcap

# Test TCP connectivity (basic, no HTTP)
nc -zv hostname 5432          # connect test (verbose)
nc -zv hostname 5432 2>&1     # capture output

# Trace TCP connection with timing
curl -w "namelookup=%{time_namelookup}s connect=%{time_connect}s tls=%{time_appconnect}s total=%{time_total}s\n" \
     -o /dev/null -s https://api.example.com/health
```

---

## sysctl Tuning for Production

```bash
# /etc/sysctl.d/99-network.conf — common production settings

# Reuse TIME_WAIT sockets for new connections (safe for clients; careful on servers)
net.ipv4.tcp_tw_reuse = 1

# Maximum backlog of pending connections per socket
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535

# Reduce keepalive times for cloud environments
net.ipv4.tcp_keepalive_time = 60
net.ipv4.tcp_keepalive_intvl = 10
net.ipv4.tcp_keepalive_probes = 6

# BBR congestion control for long-haul connections
net.ipv4.tcp_congestion_control = bbr
net.core.default_qdisc = fq

# Apply without reboot
sudo sysctl --system
```

---

## References

- [RFC 793 — TCP](https://www.rfc-editor.org/rfc/rfc793)
- [RFC 768 — UDP](https://www.rfc-editor.org/rfc/rfc768)
- [Linux TCP tuning guide (Cloudflare Blog)](https://blog.cloudflare.com/optimizing-tcp-for-high-throughput-and-low-latency/)
- [ss(8) man page](https://man7.org/linux/man-pages/man8/ss.8.html)
- [AWS NAT Gateway connection timeout behaviour](https://docs.aws.amazon.com/vpc/latest/userguide/nat-gateway-troubleshooting.html)
---

← [Previous: OSI Model](./osi-model.md) | [Home](../README.md) | [Next: DNS →](./dns.md)
