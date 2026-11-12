← [Previous: NAT & Routing](./nat-routing.md) | [Home](../README.md) | [Next: Load Balancing →](./load-balancing.md)

---

# Firewalls and VPN

Firewalls control which network traffic is allowed or denied. VPNs create encrypted tunnels over the public internet. Both are fundamental to cloud security architecture.

---

## Firewall Fundamentals

### Stateful vs Stateless Firewalls

| Property | Stateful | Stateless |
|----------|---------|-----------|
| Tracks connections | Yes — maintains connection table | No — evaluates each packet independently |
| Return traffic | Allowed automatically | Must explicitly allow return traffic |
| Rules | Single rule per direction | Separate rules for outbound + inbound return |
| Performance | Slightly more overhead | Higher throughput (no state table) |
| AWS equivalent | Security Groups | Network ACLs (NACLs) |

**Stateful example (Security Group)**:
```
Inbound: allow TCP 443 from 0.0.0.0/0
→ Return traffic (TCP ACK from server to client) is automatically allowed
```

**Stateless example (NACL)**:
```
Inbound:  allow TCP 443 from 0.0.0.0/0           (client → server)
Outbound: allow TCP 1024-65535 to 0.0.0.0/0      (return traffic, ephemeral ports)
```

---

## AWS Security Groups

Security Groups are virtual firewalls attached to ENIs (network interfaces), not to subnets. They are stateful.

### Key Properties

- Default: deny all inbound, allow all outbound
- Rules are **allow-only** — no explicit deny (to deny, just don't add a rule)
- Up to 60 rules per security group (can be raised)
- Multiple security groups can be attached to one instance
- Rules can reference other security groups as source/destination (within same VPC)
- Changes take effect immediately

### Managing Security Groups

```bash
# Create a security group
aws ec2 create-security-group \
    --group-name web-server-sg \
    --description "Allow HTTPS from internet" \
    --vpc-id vpc-0def5678

# Allow HTTPS inbound from internet
aws ec2 authorize-security-group-ingress \
    --group-id sg-0abc1234 \
    --protocol tcp --port 443 \
    --cidr 0.0.0.0/0

# Allow SSH from a specific IP
aws ec2 authorize-security-group-ingress \
    --group-id sg-0abc1234 \
    --protocol tcp --port 22 \
    --cidr 203.0.113.0/32

# Allow MySQL from another security group (same VPC)
aws ec2 authorize-security-group-ingress \
    --group-id sg-database \
    --protocol tcp --port 3306 \
    --source-group sg-application

# View rules
aws ec2 describe-security-groups \
    --group-ids sg-0abc1234

# Remove a rule
aws ec2 revoke-security-group-ingress \
    --group-id sg-0abc1234 \
    --protocol tcp --port 22 \
    --cidr 203.0.113.0/32
```

### Security Group Design Patterns

```
Internet  →  [sg-alb: 80,443 from 0.0.0.0/0]  →  ALB
ALB       →  [sg-web: 8080 from sg-alb]         →  EC2 web tier
EC2 web   →  [sg-db:  5432 from sg-web]          →  RDS
```

- Never allow `0.0.0.0/0` to SSH/RDP — use AWS SSM Session Manager instead
- Use security group references (not CIDR) for internal tier-to-tier traffic
- Create a "management" security group for SSM/monitoring tools and attach it to all instances

---

## AWS Network ACLs (NACLs)

NACLs are stateless firewalls applied at the **subnet level**. Every subnet has exactly one NACL (default or custom). Rules are evaluated in **number order** — lowest number first — and the first match wins.

### Key Properties

- Separate inbound and outbound rule sets
- Rules have a number (priority): lower = evaluated first
- Supports explicit **DENY** rules (unlike security groups)
- Default NACL allows all traffic
- Custom NACLs deny all by default
- Applied to all traffic entering/leaving the subnet

### NACL Rule Example

```
Inbound rules:
Rule 100: Allow  TCP  443  from 0.0.0.0/0
Rule 200: Allow  TCP  80   from 0.0.0.0/0
Rule 300: Allow  TCP  1024-65535 from 0.0.0.0/0  ← ephemeral ports for return traffic
Rule *:   Deny   All  All  from 0.0.0.0/0         ← implicit deny (cannot change)

Outbound rules:
Rule 100: Allow  TCP  443  to 0.0.0.0/0
Rule 200: Allow  TCP  1024-65535 to 0.0.0.0/0
Rule *:   Deny   All  All  to 0.0.0.0/0
```

```bash
# Create a NACL
aws ec2 create-network-acl --vpc-id vpc-0def5678

# Add an inbound rule (allow HTTPS)
aws ec2 create-network-acl-entry \
    --network-acl-id acl-0abc1234 \
    --rule-number 100 \
    --protocol tcp \
    --rule-action allow \
    --ingress \
    --cidr-block 0.0.0.0/0 \
    --port-range From=443,To=443

# Add an explicit DENY for a known bad IP
aws ec2 create-network-acl-entry \
    --network-acl-id acl-0abc1234 \
    --rule-number 50 \
    --protocol -1 \
    --rule-action deny \
    --ingress \
    --cidr-block 198.51.100.0/24

# Associate with a subnet
aws ec2 associate-network-acl \
    --network-acl-id acl-0abc1234 \
    --subnet-id subnet-0def5678
```

---

## Security Groups vs NACLs Summary

| Feature | Security Groups | NACLs |
|---------|----------------|-------|
| Level | Instance (ENI) | Subnet |
| Statefulness | Stateful | Stateless |
| Rule types | Allow only | Allow + Deny |
| Rule evaluation | All rules checked | First match wins (ordered) |
| Scope | Instance-level | All traffic through subnet |
| Default | Deny all inbound | Depends on type (default allows all) |
| Use for | Normal traffic control | Blocking known-bad IPs, compliance |

**Use security groups for most traffic control. Use NACLs for subnet-level blocking (DDoS mitigation, compliance boundaries).**

---

## AWS Firewall Manager and Network Firewall

### AWS Network Firewall

A managed, stateful firewall at the VPC level — more powerful than NACLs. Supports:
- Stateful inspection rules (Suricata-compatible)
- Domain-based filtering (block `*.badsite.com`)
- TLS inspection (with certificates)
- Intrusion Detection/Prevention (IDS/IPS)

Deployed in dedicated firewall subnets; traffic is routed through it via route table changes.

---

## VPN — Virtual Private Network

VPNs create encrypted tunnels over the public internet, allowing private traffic to flow securely between networks.

### Types of VPN

| Type | Use case |
|------|---------|
| **Site-to-Site VPN** | Connect on-premises network to cloud VPC |
| **Client VPN** | Individual user devices to a private network |
| **Overlay VPN (e.g., WireGuard, OpenVPN)** | Mesh between servers without cloud-managed VPN |

---

## AWS Site-to-Site VPN

Connects your on-premises network to an AWS VPC via IPsec tunnels.

```
On-premises network    ←──── IPsec tunnels ────▶   AWS VPC
(Customer Gateway)                              (Virtual Private Gateway / TGW)
```

- **Two tunnels** per connection (redundancy) — each terminates in a different AZ
- Each tunnel: 1.25 Gbps bandwidth limit
- Supports static routes or BGP route propagation
- VPN connection is terminated at a **Virtual Private Gateway (VGW)** or **Transit Gateway**

```bash
# Step 1: Create Customer Gateway (represents your on-premises router)
aws ec2 create-customer-gateway \
    --type ipsec.1 \
    --public-ip 203.0.113.10 \    # your router's public IP
    --bgp-asn 65000

# Step 2: Create Virtual Private Gateway
aws ec2 create-vpn-gateway --type ipsec.1
aws ec2 attach-vpn-gateway \
    --vpn-gateway-id vgw-0abc1234 \
    --vpc-id vpc-0def5678

# Step 3: Create VPN connection
aws ec2 create-vpn-connection \
    --type ipsec.1 \
    --customer-gateway-id cgw-0abc1234 \
    --vpn-gateway-id vgw-0abc1234 \
    --options StaticRoutesOnly=false  # false = use BGP

# Step 4: Download configuration (contains pre-shared keys, tunnel IPs)
aws ec2 describe-vpn-connections \
    --vpn-connection-ids vpn-0abc1234 \
    --query 'VpnConnections[0].CustomerGatewayConfiguration'

# Step 5: Enable route propagation so VGW routes appear in route table
aws ec2 enable-vgw-route-propagation \
    --route-table-id rtb-0abc1234 \
    --gateway-id vgw-0abc1234
```

### IPsec VPN Components

| Component | Purpose |
|-----------|---------|
| **IKE (Phase 1)** | Authenticates peers, establishes secure channel, agrees on encryption |
| **IPsec SA (Phase 2)** | Negotiates the tunnel parameters for actual data encryption |
| **Pre-Shared Key (PSK)** | Shared secret used in IKE Phase 1 (in AWS, set per tunnel) |
| **ESP (Encapsulating Security Payload)** | Encrypts + authenticates data packets |
| **AH (Authentication Header)** | Authentication only, no encryption (rarely used) |

---

## AWS Client VPN

Managed OpenVPN-compatible service allowing individual users to connect to a VPC.

```bash
# Create Client VPN endpoint
aws ec2 create-client-vpn-endpoint \
    --client-cidr-block 172.31.0.0/16 \
    --server-certificate-arn arn:aws:acm:...:certificate/... \
    --authentication-options Type=certificate-authentication,MutualAuthentication={ClientRootCertificateChainArn=...} \
    --connection-log-options Enabled=true,CloudwatchLogGroup=/aws/client-vpn

# Associate with a subnet (enables access to that VPC)
aws ec2 associate-client-vpn-target-network \
    --client-vpn-endpoint-id cvpn-endpoint-0abc1234 \
    --subnet-id subnet-0def5678

# Add authorization rule (allow all users to access VPC)
aws ec2 authorize-client-vpn-ingress \
    --client-vpn-endpoint-id cvpn-endpoint-0abc1234 \
    --target-network-cidr 10.0.0.0/16 \
    --authorize-all-groups
```

---

## WireGuard (Self-Managed Overlay VPN)

WireGuard is a fast, simple VPN suitable for connecting servers or as a self-managed client VPN on EC2.

```bash
# Install
sudo apt install wireguard    # Ubuntu
sudo dnf install wireguard-tools  # Amazon Linux

# Generate key pair
wg genkey | tee privatekey | wg pubkey > publickey

# /etc/wireguard/wg0.conf (server)
[Interface]
Address = 10.100.0.1/24
ListenPort = 51820
PrivateKey = <server-private-key>

[Peer]
PublicKey = <client-public-key>
AllowedIPs = 10.100.0.2/32

# Start and enable
sudo systemctl enable --now wg-quick@wg0
sudo wg show    # status
```

---

## iptables — Linux Packet Filtering

iptables is the Linux kernel firewall. Less common in cloud (security groups cover most use cases), but still useful for instance-level filtering and NAT.

```bash
# View current rules
sudo iptables -L -n -v --line-numbers

# Allow inbound port 443
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Drop all inbound traffic from a specific IP
sudo iptables -A INPUT -s 198.51.100.5 -j DROP

# Rate-limit SSH (prevent brute force)
sudo iptables -A INPUT -p tcp --dport 22 -m state --state NEW \
    -m recent --set --name SSH
sudo iptables -A INPUT -p tcp --dport 22 -m state --state NEW \
    -m recent --update --seconds 60 --hitcount 10 --name SSH -j DROP

# Flush all rules (resets to allow-all — careful)
sudo iptables -F

# Save rules persistently
sudo iptables-save > /etc/iptables/rules.v4
sudo apt install iptables-persistent   # auto-restores on boot
```

---

## References

- [AWS Security Groups documentation](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)
- [AWS Network ACLs documentation](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)
- [AWS Site-to-Site VPN](https://docs.aws.amazon.com/vpn/latest/s2svpn/VPC_VPN.html)
- [AWS Client VPN](https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/what-is.html)
- [WireGuard documentation](https://www.wireguard.com/)
---

← [Previous: NAT & Routing](./nat-routing.md) | [Home](../README.md) | [Next: Load Balancing →](./load-balancing.md)
