← [Previous: CIDR & Subnetting](./cidr-subnetting.md) | [Home](../README.md) | [Next: Firewalls & VPN →](./firewalls-vpn.md)

---

# NAT and Routing

NAT (Network Address Translation) allows private IP addresses to reach the internet without being publicly routable. Routing determines the path packets take between networks. Both are core to cloud VPC architecture.

---

## Routing Fundamentals

A **routing table** is a list of rules that tell a router where to forward packets. Each rule maps a destination CIDR to a "next hop" (gateway, interface, or target).

### How Route Lookup Works

```
Packet destination: 8.8.8.8

Route table:
  10.0.0.0/16  →  local           (VPC traffic — stay local)
  0.0.0.0/0    →  igw-0abc1234    (everything else → internet gateway)

Longest-prefix match wins:
  8.8.8.8 matches 0.0.0.0/0 (32 - 0 = 0 matching bits)
  10.0.1.5 matches 10.0.0.0/16 (16 matching bits, more specific → wins)
```

**Longest prefix match**: the most specific (longest) matching CIDR wins. A /32 beats /24 beats /16 beats /0.

---

## NAT Types

### SNAT — Source NAT

Replaces the **source** IP and/or port in outgoing packets. Used to allow private hosts to reach the internet.

```
Private host:   10.0.1.5:54321  →  8.8.8.8:53
NAT Gateway:    54.12.34.56:1024 →  8.8.8.8:53   (source rewritten)
Return traffic: 8.8.8.8:53  →  54.12.34.56:1024  (NAT translates back to 10.0.1.5:54321)
```

The NAT device maintains a **translation table** mapping internal (IP:port) to external (IP:port) pairs.

### DNAT — Destination NAT

Replaces the **destination** IP and/or port in incoming packets. Used for port forwarding and load balancing.

```
External client: 1.2.3.4:54321  →  54.12.34.56:80
After DNAT:      1.2.3.4:54321  →  10.0.1.10:8080  (port forwarded to internal server)
```

### PAT — Port Address Translation (NAT Overload)

Multiple internal IPs sharing one external IP by using different source ports. This is how home routers and cloud NAT Gateways work — thousands of internal hosts share one public IP via different port mappings.

---

## AWS VPC Routing Components

### Internet Gateway (IGW)

- Provides internet access to/from public subnets
- Performs NAT for instances with Elastic IPs (public IPv4): translates public IP ↔ private IP
- One IGW per VPC; highly available, no bandwidth limit
- Attached to the VPC; referenced in route tables

```bash
# Create and attach an IGW
aws ec2 create-internet-gateway
aws ec2 attach-internet-gateway \
    --internet-gateway-id igw-0abc1234 \
    --vpc-id vpc-0def5678

# Add default route to public subnet route table
aws ec2 create-route \
    --route-table-id rtb-0abc1234 \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id igw-0abc1234
```

### NAT Gateway

- Allows **private subnet** instances to reach the internet (outbound only)
- Deployed in a **public subnet** with an Elastic IP
- Managed by AWS — no maintenance required
- Scales automatically; charged per hour + per GB processed
- One NAT Gateway per AZ for HA (NAT Gateways are AZ-specific)

```
Private subnet route table:
  10.0.0.0/16  →  local
  0.0.0.0/0    →  nat-0abc1234   (NAT Gateway in public subnet)

Public subnet route table:
  10.0.0.0/16  →  local
  0.0.0.0/0    →  igw-0abc1234   (Internet Gateway)
```

```bash
# Allocate Elastic IP
aws ec2 allocate-address --domain vpc

# Create NAT Gateway in a public subnet
aws ec2 create-nat-gateway \
    --subnet-id subnet-public-az-a \
    --allocation-id eipalloc-0abc1234

# Wait for it to become available
aws ec2 wait nat-gateway-available --nat-gateway-ids nat-0abc1234

# Route private subnet traffic through NAT Gateway
aws ec2 create-route \
    --route-table-id rtb-private-az-a \
    --destination-cidr-block 0.0.0.0/0 \
    --nat-gateway-id nat-0abc1234
```

### NAT Instance (Legacy — Avoid)

An EC2 instance configured to perform NAT. Requires:
- Source/destination check disabled on the ENI
- OS-level IP forwarding enabled
- iptables masquerade rule

Still supported but use NAT Gateway in production — NAT instances are a single point of failure, require maintenance, and are manually scaled.

### Egress-Only Internet Gateway

For **IPv6** outbound-only traffic from private subnets (IPv6 equivalent of NAT Gateway; IPv6 addresses are all public, so this is the only way to restrict them to outbound-only).

```bash
aws ec2 create-egress-only-internet-gateway --vpc-id vpc-0def5678

# Add to private subnet IPv6 route table
aws ec2 create-route \
    --route-table-id rtb-private \
    --destination-ipv6-cidr-block ::/0 \
    --egress-only-internet-gateway-id eigw-0abc1234
```

---

## Route Table Structure

Each route table is associated with one or more subnets. A subnet not explicitly associated uses the **main (default) route table**.

```bash
# Create a route table
aws ec2 create-route-table --vpc-id vpc-0def5678

# Associate with a subnet
aws ec2 associate-route-table \
    --route-table-id rtb-0abc1234 \
    --subnet-id subnet-0def5678

# View routes
aws ec2 describe-route-tables \
    --route-table-ids rtb-0abc1234 \
    --query 'RouteTables[0].Routes'

# Add a static route (e.g., to a Transit Gateway)
aws ec2 create-route \
    --route-table-id rtb-0abc1234 \
    --destination-cidr-block 172.16.0.0/12 \
    --transit-gateway-id tgw-0abc1234
```

---

## VPC Peering

VPC peering connects two VPCs so traffic routes directly between them (no internet, no gateway appliances). Traffic stays on the AWS backbone.

```
VPC A (10.0.0.0/16)  ←──── peering ────▶  VPC B (10.1.0.0/16)
```

Requirements:
- CIDRs must not overlap
- Peering is **not transitive**: A↔B and B↔C does not mean A↔C
- Must add routes in both VPCs' route tables
- Works across accounts and regions

```bash
# Create peering connection (requester side)
aws ec2 create-vpc-peering-connection \
    --vpc-id vpc-A \
    --peer-vpc-id vpc-B \
    --peer-region us-west-2

# Accept the peering (accepter side)
aws ec2 accept-vpc-peering-connection \
    --vpc-peering-connection-id pcx-0abc1234

# Add routes in both VPCs
# In VPC A's route table: 10.1.0.0/16 → pcx-0abc1234
# In VPC B's route table: 10.0.0.0/16 → pcx-0abc1234
aws ec2 create-route \
    --route-table-id rtb-vpc-a \
    --destination-cidr-block 10.1.0.0/16 \
    --vpc-peering-connection-id pcx-0abc1234
```

---

## Transit Gateway

A Transit Gateway (TGW) acts as a regional router hub — connecting multiple VPCs, VPNs, and Direct Connect in a hub-and-spoke topology. Eliminates the need for full mesh VPC peering.

```
           ┌──────────────────────────────────┐
VPC A ─────┤                                  ├───── VPN to on-premises
VPC B ─────┤       Transit Gateway            ├───── Direct Connect
VPC C ─────┤                                  ├───── VPC D (another account)
           └──────────────────────────────────┘
```

- Each VPC attaches to the TGW with a TGW attachment
- TGW has its own route tables (separate from VPC route tables)
- Supports route propagation from VPN and Direct Connect
- Can be shared across AWS accounts via RAM (Resource Access Manager)

```bash
# Attach a VPC to a Transit Gateway
aws ec2 create-transit-gateway-vpc-attachment \
    --transit-gateway-id tgw-0abc1234 \
    --vpc-id vpc-0def5678 \
    --subnet-ids subnet-az-a subnet-az-b

# Add route in VPC pointing to TGW
aws ec2 create-route \
    --route-table-id rtb-vpc \
    --destination-cidr-block 10.0.0.0/8 \
    --transit-gateway-id tgw-0abc1234
```

---

## BGP Basics

BGP (Border Gateway Protocol) is the routing protocol of the internet — and of AWS Direct Connect and Site-to-Site VPN.

| Concept | Meaning |
|---------|---------|
| **AS (Autonomous System)** | A network under a single administrative control; has a unique ASN |
| **ASN** | Autonomous System Number (AWS uses 7224 for BGP on Direct Connect; you configure your own) |
| **Route advertisement** | Announcing which prefixes your AS can reach |
| **BGP peer** | A neighbour AS you exchange routes with |
| **eBGP** | External BGP — between different ASes (your on-premises router ↔ AWS) |
| **iBGP** | Internal BGP — within the same AS |

In AWS:
- **Site-to-Site VPN**: supports static routes or BGP route propagation
- **Direct Connect**: BGP is required; you advertise your on-premises prefixes, AWS advertises its VPC prefixes
- **Transit Gateway route propagation**: TGW can propagate BGP-learned routes into its route tables automatically

---

## Linux IP Forwarding

To make a Linux instance route packets (act as a NAT instance, VPN endpoint, or router):

```bash
# Check current state
cat /proc/sys/net/ipv4/ip_forward    # 1 = enabled, 0 = disabled

# Enable temporarily
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward

# Enable permanently
echo "net.ipv4.ip_forward = 1" | sudo tee /etc/sysctl.d/99-ip-forward.conf
sudo sysctl -p /etc/sysctl.d/99-ip-forward.conf

# SNAT with iptables (for NAT instance)
sudo iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

---

## Viewing Routes

```bash
# Linux routing table
ip route show
route -n           # older format

# AWS route table (CLI)
aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=vpc-0def5678" \
    --query 'RouteTables[].{ID:RouteTableId,Routes:Routes}'
```

---

## References

- [AWS VPC routing documentation](https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html)
- [AWS NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html)
- [AWS Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html)
- [RFC 4271 — BGP-4](https://www.rfc-editor.org/rfc/rfc4271)
---

← [Previous: CIDR & Subnetting](./cidr-subnetting.md) | [Home](../README.md) | [Next: Firewalls & VPN →](./firewalls-vpn.md)
