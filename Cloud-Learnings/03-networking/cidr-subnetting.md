← [Previous: DNS](./dns.md) | [Home](../README.md) | [Next: NAT & Routing →](./nat-routing.md)

---

# CIDR and Subnetting

CIDR (Classless Inter-Domain Routing) is the notation and method used to describe IP address ranges. Every VPC, subnet, security group rule, and routing decision in the cloud uses CIDR. Getting subnetting right at the start prevents painful re-architectures later.

---

## Binary Fundamentals

An IPv4 address is **32 bits** written as four decimal octets:

```
192.168.10.50
│   │   │  └── octet 4: 0011 0010 = 50
│   │   └───── octet 3: 0000 1010 = 10
│   └───────── octet 2: 1010 1000 = 168
└───────────── octet 1: 1100 0000 = 192

Full binary: 11000000.10101000.00001010.00110010
```

### Bit Value Reference

| Bit position (right to left) | Value |
|------------------------------|-------|
| 1 | 1 |
| 2 | 2 |
| 3 | 4 |
| 4 | 8 |
| 5 | 16 |
| 6 | 32 |
| 7 | 64 |
| 8 | 128 |

---

## CIDR Notation

CIDR notation appends a **prefix length** (the number of fixed bits) to an IP address:

```
10.0.0.0/16
│       └── 16 bits are the network portion (fixed)
└────────── base address

Network bits: 1111 1111 1111 1111 0000 0000 0000 0000  (subnet mask)
              = 255.255.0.0

Host bits: 32 - 16 = 16 bits → 2^16 = 65,536 addresses
           Usable: 65,534 (subtract network + broadcast)
```

### Prefix Length to Subnet Mask

| Prefix | Subnet Mask | Hosts | Notes |
|--------|-------------|-------|-------|
| /8 | 255.0.0.0 | 16,777,214 | Class A range |
| /12 | 255.240.0.0 | 1,048,574 | 172.16.0.0/12 private range |
| /16 | 255.255.0.0 | 65,534 | Typical VPC size |
| /20 | 255.255.240.0 | 4,094 | Large subnet |
| /22 | 255.255.252.0 | 1,022 | Medium subnet |
| /24 | 255.255.255.0 | 254 | Standard subnet |
| /26 | 255.255.255.192 | 62 | Small subnet |
| /27 | 255.255.255.224 | 30 | Very small subnet |
| /28 | 255.255.255.240 | 14 | AWS minimum subnet size |
| /29 | 255.255.255.248 | 6 | Tiny (6 hosts) |
| /30 | 255.255.255.252 | 2 | Point-to-point links |
| /31 | 255.255.255.254 | 2 | RFC 3021 — no broadcast needed |
| /32 | 255.255.255.255 | 1 | Single host (security group rules) |

**Formula**: Hosts = 2^(32 - prefix) - 2 (subtract network address and broadcast)

---

## Private (RFC 1918) Address Ranges

These ranges are not routable on the public internet. Always use them for internal networks:

| Range | CIDR | Addresses | Common use |
|-------|------|-----------|-----------|
| 10.0.0.0 – 10.255.255.255 | 10.0.0.0/8 | 16,777,216 | Enterprise networks, VPCs |
| 172.16.0.0 – 172.31.255.255 | 172.16.0.0/12 | 1,048,576 | Docker default, some VPCs |
| 192.168.0.0 – 192.168.255.255 | 192.168.0.0/16 | 65,536 | Home/small office networks |

**Other reserved ranges:**

| Range | Purpose |
|-------|---------|
| `127.0.0.0/8` | Loopback (localhost) |
| `169.254.0.0/16` | Link-local / APIPA (AWS instance metadata lives here) |
| `224.0.0.0/4` | Multicast |
| `100.64.0.0/10` | Carrier-grade NAT (RFC 6598) |
| `0.0.0.0/0` | Default route (all traffic) in routing tables |

---

## Subnetting a Network

### Example: Dividing 10.0.0.0/16 into /24 subnets

A /16 contains 256 × /24 subnets:

```
10.0.0.0/24    (256 addresses: 10.0.0.0  – 10.0.0.255)
10.0.1.0/24    (256 addresses: 10.0.1.0  – 10.0.1.255)
10.0.2.0/24    (256 addresses: 10.0.2.0  – 10.0.2.255)
...
10.0.255.0/24  (256 addresses: 10.0.255.0 – 10.0.255.255)
```

### Determining Network and Broadcast Address

For `10.0.1.0/24`:
- **Network address**: 10.0.1.0 (all host bits = 0) — not usable
- **Broadcast address**: 10.0.1.255 (all host bits = 1) — not usable
- **Usable range**: 10.0.1.1 – 10.0.1.254 (254 hosts)

For `10.0.1.64/26`:
- 64 in binary = 0100 0000; mask = 1111 1111
- Network: 10.0.1.64
- Broadcast: 10.0.1.127 (10.0.1.0100 0000 to 10.0.1.0111 1111)
- Usable range: 10.0.1.65 – 10.0.1.126 (62 hosts)

### Quick Check Tool

```bash
# Use ipcalc (most Linux distros)
ipcalc 10.0.1.0/24
ipcalc 192.168.10.0/26

# Or with Python (no install needed)
python3 -c "import ipaddress; n = ipaddress.ip_network('10.0.1.0/24'); print(f'Hosts: {n.num_addresses-2}, First: {list(n.hosts())[0]}, Last: {list(n.hosts())[-1]}')"
```

---

## VPC Design Patterns

### AWS Reserved Addresses per Subnet

AWS reserves **5 addresses** in every subnet (not 2):

```
10.0.1.0   — Network address
10.0.1.1   — AWS VPC router
10.0.1.2   — AWS DNS server (VPC base + 2)
10.0.1.3   — Reserved for future use
10.0.1.255 — Broadcast (reserved but not used in VPC)
```

So a /24 gives you 256 - 5 = **251 usable addresses** in AWS.

### Recommended VPC CIDR Size

| VPC size | CIDR | Why |
|----------|------|-----|
| Small dev | /24 | 251 usable IPs |
| Medium | /22 | ~1,000 IPs |
| Standard | /20 | ~4,000 IPs |
| Large | /16 | ~65,000 IPs (common) |
| Very large | /8 | 16M+ IPs (enterprise) |

**Rule**: Size your VPC larger than you think you need. Expanding a VPC CIDR later (via secondary CIDRs) adds complexity.

### Multi-AZ Subnet Layout (Standard Pattern)

```
VPC: 10.0.0.0/16

                  AZ-A              AZ-B              AZ-C
Public subnets    10.0.0.0/24       10.0.1.0/24       10.0.2.0/24
Private subnets   10.0.10.0/24      10.0.11.0/24      10.0.12.0/24
Database subnets  10.0.20.0/24      10.0.21.0/24      10.0.22.0/24
```

**Key rules:**
- Each subnet is in exactly one AZ
- Public subnets: have a route to an Internet Gateway; instances may have public IPs
- Private subnets: no direct internet route; outbound via NAT Gateway
- Database subnets: no internet access; only reachable from private subnets
- Each tier in its own CIDR block makes security group rules and NACLs easier to write

### Avoiding CIDR Conflicts

VPC peering and VPN connections require non-overlapping CIDRs. Plan your address space:

```
Production VPC:   10.0.0.0/16
Staging VPC:      10.1.0.0/16
Development VPC:  10.2.0.0/16
On-premises:      172.16.0.0/12
```

Avoid using `192.168.0.0/16` for VPCs — it conflicts with virtually every home network and VPN client.

---

## CIDR in Security Group Rules

Security groups accept CIDR notation as source/destination:

```bash
# Allow SSH only from a specific IP
aws ec2 authorize-security-group-ingress \
    --group-id sg-12345678 \
    --protocol tcp --port 22 \
    --cidr 203.0.113.0/32    # /32 = exactly one IP

# Allow HTTPS from anywhere
aws ec2 authorize-security-group-ingress \
    --group-id sg-12345678 \
    --protocol tcp --port 443 \
    --cidr 0.0.0.0/0

# Allow all traffic from within the VPC (10.0.0.0/16)
aws ec2 authorize-security-group-ingress \
    --group-id sg-12345678 \
    --protocol all --port -1 \
    --cidr 10.0.0.0/16
```

---

## IPv6

IPv6 addresses are 128 bits, written as eight groups of four hex digits:

```
2001:0db8:85a3:0000:0000:8a2e:0370:7334
     shortened:
2001:db8:85a3::8a2e:370:7334   (:: = consecutive zero groups)
```

AWS VPCs support dual-stack (IPv4 + IPv6). AWS assigns `/56` VPC CIDRs and `/64` subnet CIDRs from AWS-owned or BYOIP IPv6 ranges.

```bash
# Check if an instance has an IPv6 address
curl -s http://[fd00:ec2::254]/latest/meta-data/ipv6
```

---

## References

- [RFC 1918 — Private Address Allocation](https://www.rfc-editor.org/rfc/rfc1918)
- [RFC 4632 — CIDR](https://www.rfc-editor.org/rfc/rfc4632)
- [AWS VPC CIDR guidance](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-cidr-blocks.html)
- [Subnet calculator — subnet.tools](https://subnet.tools/)
---

← [Previous: DNS](./dns.md) | [Home](../README.md) | [Next: NAT & Routing →](./nat-routing.md)
