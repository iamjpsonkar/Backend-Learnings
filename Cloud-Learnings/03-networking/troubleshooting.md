← [Previous: Zero Trust](./zero-trust.md) | [Home](../README.md) | [Next: Git & DevOps Basics →](../04-git-devops-basics/README.md)

---

# Network Troubleshooting

Systematic network debugging for cloud environments. Work from the outside in: DNS → connectivity → application layer. Gather evidence before drawing conclusions.

---

## General Methodology

```
1. Define the problem precisely
   - Who is affected? All users, specific regions, specific clients?
   - What exactly fails? Timeout, connection refused, wrong response, slow?
   - When did it start? Was anything deployed recently?

2. Determine the scope
   - Is it DNS, connectivity, TLS, or the application?
   - Is it one path (client → service) or all paths?

3. Use diagnostic tools in order:
   a. DNS resolution      (dig, nslookup)
   b. IP-level reach      (ping, traceroute, mtr)
   c. Port/TCP reach      (nc, curl with --connect-timeout)
   d. Application layer   (curl with verbose headers)
   e. Packet capture      (tcpdump — when all else fails)

4. Isolate the layer that fails
5. Fix, verify, document
```

---

## DNS Troubleshooting

```bash
# Step 1: does the name resolve?
dig api.example.com +short

# Step 2: what resolver is being used?
cat /etc/resolv.conf

# Step 3: bypass local resolver — query authoritative directly
dig @8.8.8.8 api.example.com       # Google public resolver
dig @169.254.169.253 api.example.com  # AWS VPC resolver (from EC2)

# Step 4: trace the full resolution path
dig +trace api.example.com

# Step 5: check if it's a negative cache / NXDOMAIN issue
dig api.example.com +nocmd +noall +answer
# If empty: NXDOMAIN — the name doesn't exist in DNS

# Step 6: check TTL (how long until caches refresh)
dig api.example.com +nocmd +noall +answer   # look at the number column

# Reverse lookup (IP → hostname)
dig -x 93.184.216.34 +short
```

### Common DNS Failures

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| NXDOMAIN | Record missing in hosted zone | Add the DNS record |
| Old IP still resolving | TTL not expired | Wait, or use `dig @authoritative-ns` to see current value |
| Works on host, fails in container | Container using different resolver | Check `/etc/resolv.conf` in container; check `ndots` setting |
| Works externally, fails inside VPC | Split-horizon not configured | Associate private hosted zone with VPC |
| Random failures | Resolver overload / UDP drops | `dig +tcp api.example.com` (force TCP); check resolver health |

---

## Connectivity Troubleshooting

### Ping

```bash
# Basic ICMP reachability
ping -c 4 10.0.1.50       # 4 packets to a private host

# Ping with timestamps
ping -D 10.0.1.50         # shows Unix timestamp per packet

# Flood ping (requires root, useful for packet loss testing)
sudo ping -f -c 1000 10.0.1.50 | tail -3
```

> ICMP may be blocked in cloud environments. If ping fails, try a TCP check before concluding unreachable.

### Traceroute / MTR

```bash
# Trace the route
traceroute api.example.com
traceroute -n api.example.com   # no DNS lookup (faster)

# MTR: continuous traceroute with loss stats (install: apt install mtr)
mtr --report api.example.com   # 10 cycles, then print report
mtr -n api.example.com         # live interactive mode, no DNS

# Output columns: Host, Loss%, Snt, Last, Avg, Best, Wrst, StDev
# High loss at one hop that recovers in later hops = ICMP deprioritised (normal)
# Loss at a hop that stays high = real packet loss
```

### TCP Port Testing

```bash
# Test if a port is open (prefer nc over telnet)
nc -zv hostname 443        # z = scan mode, v = verbose
nc -zv hostname 443 2>&1   # capture stderr too

# With timeout
nc -zvw 5 hostname 443     # 5-second timeout

# Test multiple ports quickly
for port in 80 443 22 8080; do
    nc -zw 2 hostname $port 2>&1 && echo "$port OPEN" || echo "$port CLOSED/FILTERED"
done

# Test UDP (less reliable — no handshake)
nc -zuv hostname 53        # test DNS UDP
```

### curl Timing Breakdown

```bash
# Detailed timing at each stage
curl -w "\n--- Timing ---\n\
dns_lookup:   %{time_namelookup}s\n\
tcp_connect:  %{time_connect}s\n\
tls_handshake:%{time_appconnect}s\n\
first_byte:   %{time_starttransfer}s\n\
total:        %{time_total}s\n\
http_code:    %{http_code}\n" \
     -o /dev/null -s https://api.example.com/health

# What the times mean:
# dns_lookup   = time for DNS resolution
# tcp_connect  = time for DNS + TCP 3-way handshake
# tls_handshake = time for DNS + TCP + TLS (subtract tcp_connect to get TLS time)
# first_byte   = time until first byte of response
# total        = complete response received
```

---

## AWS-Specific Troubleshooting

### VPC Flow Logs

VPC Flow Logs capture metadata about IP traffic in/out of network interfaces, subnets, or VPCs.

```bash
# Enable flow logs (to CloudWatch Logs)
aws ec2 create-flow-logs \
    --resource-type VPC \
    --resource-ids vpc-0def5678 \
    --traffic-type ALL \
    --log-group-name /vpc/flow-logs \
    --deliver-logs-permission-arn arn:aws:iam::123456789012:role/flowlogs-role

# Query flow logs with CloudWatch Insights
# (after enabling, allow ~15 minutes for logs to appear)
aws logs start-query \
    --log-group-name /vpc/flow-logs \
    --start-time $(date -d '1 hour ago' +%s) \
    --end-time $(date +%s) \
    --query-string 'fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, action, protocol
                    | filter dstAddr = "10.0.1.50" and action = "REJECT"
                    | stats count() by srcAddr
                    | sort count desc
                    | limit 20'
```

**Flow log record fields:**

```
version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status
2 123456789012 eni-0abc1234 10.0.1.5 10.0.1.50 54321 5432 6 10 2000 1700000000 1700000060 ACCEPT OK
2 123456789012 eni-0abc1234 10.0.2.5 10.0.1.50 12345 5432 6 5  500  1700000000 1700000060 REJECT OK
```

- `action = REJECT` → security group or NACL is blocking the traffic
- `action = ACCEPT` → traffic was allowed through
- `log-status = NODATA` → no traffic during the capture window
- `log-status = SKIPDATA` → logs were dropped (capacity issue)

### Security Group / NACL Diagnosis

```bash
# Check security group rules for a specific instance
INSTANCE_ID="i-0abc1234"
SG_IDS=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].SecurityGroups[*].GroupId' \
    --output text)

for sg in $SG_IDS; do
    echo "=== Security Group: $sg ==="
    aws ec2 describe-security-groups \
        --group-ids $sg \
        --query 'SecurityGroups[0].{Inbound:IpPermissions,Outbound:IpPermissionsEgress}'
done

# Check which subnet a network interface is in
aws ec2 describe-network-interfaces \
    --network-interface-ids eni-0abc1234 \
    --query 'NetworkInterfaces[0].{SubnetId:SubnetId,VpcId:VpcId}'

# Check the NACL for that subnet
aws ec2 describe-network-acls \
    --filters "Name=association.subnet-id,Values=subnet-0abc1234" \
    --query 'NetworkAcls[0].Entries'
```

### Routing Table Diagnosis

```bash
# Find the route table for a subnet
aws ec2 describe-route-tables \
    --filters "Name=association.subnet-id,Values=subnet-0abc1234" \
    --query 'RouteTables[0].{ID:RouteTableId,Routes:Routes}'

# Check if a specific destination is routed correctly
# Look for: destination CIDR that matches the target IP, active state of the route
aws ec2 describe-route-tables \
    --route-table-ids rtb-0abc1234 \
    --query 'RouteTables[0].Routes[*].{Dest:DestinationCidrBlock,Target:GatewayId,State:State}'
```

### NAT Gateway Troubleshooting

```bash
# Check NAT Gateway status
aws ec2 describe-nat-gateways \
    --nat-gateway-ids nat-0abc1234 \
    --query 'NatGateways[0].{State:State,SubnetId:SubnetId,PublicIp:NatGatewayAddresses[0].PublicIp}'

# Common issues:
# 1. NAT Gateway in a private subnet (should be in PUBLIC subnet)
# 2. Private subnet route table points to NAT Gateway in wrong AZ (higher cost but works)
# 3. NAT Gateway itself has no route to IGW in its subnet's route table
# 4. Elastic IP not associated (State: failed)

# Verify: public subnet that contains NAT Gateway has 0.0.0.0/0 → igw
aws ec2 describe-route-tables \
    --filters "Name=association.subnet-id,Values=<nat-gateway-subnet>" \
    --query 'RouteTables[0].Routes'
```

---

## TLS / HTTPS Troubleshooting

```bash
# Check certificate presented by a server
openssl s_client -connect api.example.com:443 -servername api.example.com < /dev/null 2>/dev/null \
    | openssl x509 -noout -subject -issuer -dates

# Check expiry only
echo | openssl s_client -connect api.example.com:443 -servername api.example.com 2>/dev/null \
    | openssl x509 -noout -enddate

# Test specific TLS version
openssl s_client -connect api.example.com:443 -tls1_2
openssl s_client -connect api.example.com:443 -tls1_3

# Verify full certificate chain
openssl s_client -connect api.example.com:443 -servername api.example.com \
    -CAfile /etc/ssl/certs/ca-certificates.crt < /dev/null 2>&1 | grep "Verify return"
# "Verify return code: 0 (ok)" = valid chain
# Anything else = problem

# Check if SNI is needed (serves different cert based on hostname)
openssl s_client -connect 93.184.216.34:443 -servername api.example.com < /dev/null 2>/dev/null \
    | openssl x509 -noout -subject
```

### Common TLS Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `SSL: CERTIFICATE_VERIFY_FAILED` | Cert expired, wrong hostname, untrusted CA | Check cert validity, hostname, CA chain |
| `SSL handshake failed` | TLS version mismatch, cipher mismatch | Check server TLS config; `--tlsv1.2` or `--tlsv1.3` |
| `certificate has expired` | Cert not renewed | Renew/replace cert; check ACM auto-renewal |
| `hostname doesn't match` | Using IP instead of hostname; SANs mismatch | Use correct hostname; check cert SANs |
| `self signed certificate` | Test/internal cert not in trust store | Add CA to trust store, or use `-k` for testing |

---

## Load Balancer Troubleshooting

```bash
# ALB: check target group health
aws elbv2 describe-target-health \
    --target-group-arn arn:...:targetgroup/web-tg/...

# Output shows: TargetHealth.State = healthy | unhealthy | draining | unused
# TargetHealth.Description = reason for unhealthy state

# Check ALB access logs (after enabling to S3)
aws s3 cp s3://my-access-logs-bucket/alb-logs/ ./alb-logs/ --recursive --quiet
grep " 502 " ./alb-logs/*.log | head -20
grep " 504 " ./alb-logs/*.log | head -20

# CloudWatch metrics for ALB
aws cloudwatch get-metric-statistics \
    --namespace AWS/ApplicationELB \
    --metric-name HTTPCode_Target_5XX_Count \
    --dimensions Name=LoadBalancer,Value=app/my-alb/abc123 \
    --start-time $(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
    --period 60 \
    --statistics Sum

# Understand ALB error codes:
# 502 = backend returned invalid response (app crashed, wrong port, no response)
# 503 = all targets unhealthy or target group empty
# 504 = backend timeout (app took too long; check idle timeout setting)
```

---

## Packet Capture

When all other tools fail, capture actual packets:

```bash
# Capture all traffic on an interface
sudo tcpdump -i eth0 -n

# Filter by host and port
sudo tcpdump -i any -n "host 10.0.1.50 and port 5432"

# Capture and save to file (analyse with Wireshark)
sudo tcpdump -i eth0 -n -w /tmp/capture.pcap "port 443"

# Read saved capture
tcpdump -r /tmp/capture.pcap -n

# Capture HTTP requests (unencrypted only)
sudo tcpdump -i eth0 -A -s 0 "tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)"

# Show packet count summary by type
sudo tcpdump -i eth0 -n -c 1000 2>/dev/null | awk '{print $NF}' | sort | uniq -c | sort -rn
```

---

## Tools Quick Reference

| Tool | Purpose | Install |
|------|---------|---------|
| `dig` | DNS lookup | `bind-utils` / `dnsutils` |
| `nslookup` | Basic DNS lookup | Usually pre-installed |
| `ping` | ICMP reachability | Pre-installed |
| `traceroute` | Hop-by-hop path | `traceroute` |
| `mtr` | Continuous traceroute with stats | `mtr` |
| `nc` | TCP/UDP port test | `netcat` |
| `ss` | Socket statistics | Pre-installed (Linux) |
| `curl` | Full HTTP testing | Usually pre-installed |
| `tcpdump` | Packet capture | `tcpdump` |
| `openssl s_client` | TLS testing | `openssl` |
| `iperf3` | Bandwidth testing | `iperf3` |
| `nmap` | Port scanning (testing/security) | `nmap` |

```bash
# Install common troubleshooting tools
sudo apt install -y dnsutils traceroute mtr netcat-openbsd tcpdump iperf3 nmap   # Ubuntu
sudo dnf install -y bind-utils traceroute mtr ncat tcpdump iperf3 nmap            # Amazon Linux
```

---

## Systematic Checklist for "Cannot Connect to Service"

```
[ ] DNS: does the hostname resolve?
    dig hostname +short

[ ] Routing: is there a path to the IP?
    ip route get <ip>
    traceroute -n <ip>

[ ] Firewall (source): does outbound traffic leave this host?
    ss -tnp | grep ESTABLISHED   (existing connections)
    nc -zv <host> <port>

[ ] Firewall (destination): is the port open on the target?
    nc -zv <target-host> <port>

[ ] AWS Security Groups: is the rule present?
    Inbound: source SG or CIDR, protocol, port

[ ] AWS NACL: is there an allow rule (and a return traffic rule)?
    Both inbound AND outbound must be allowed

[ ] AWS Route Table: is there a route for the destination?
    0.0.0.0/0 → IGW (public subnet) or NAT (private subnet)

[ ] TLS: is the certificate valid?
    openssl s_client -connect host:port -servername host

[ ] Application: is the service actually listening?
    ss -tulnp | grep <port>   (on target host)
    systemctl status <service>

[ ] Flow Logs: what does AWS say?
    ACCEPT = allowed through, problem is higher layer
    REJECT = security group or NACL blocking
```

---

## References

- [AWS VPC Flow Logs](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html)
- [AWS ELB troubleshooting](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-troubleshooting.html)
- [tcpdump manual](https://www.tcpdump.org/manpages/tcpdump.1.html)
- [mtr project](https://www.bitwizard.nl/mtr/)
- [Brendan Gregg: Network Performance](https://www.brendangregg.com/blog/2014-09-06/linux-ftrace-tcp-retransmit-tracing.html)
---

← [Previous: Zero Trust](./zero-trust.md) | [Home](../README.md) | [Next: Git & DevOps Basics →](../04-git-devops-basics/README.md)
