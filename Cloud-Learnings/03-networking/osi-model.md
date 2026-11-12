← [Previous: Networking](./README.md) | [Home](../README.md) | [Next: TCP/IP →](./tcp-ip.md)

---

# OSI Model

The **Open Systems Interconnection (OSI)** model is a conceptual framework that describes how data moves across a network in seven distinct layers. Each layer has a specific responsibility and communicates with the layers directly above and below it.

---

## The Seven Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 7 — Application   │  HTTP, HTTPS, DNS, SSH, SMTP, FTP    │
├─────────────────────────────────────────────────────────────────┤
│  Layer 6 — Presentation  │  TLS/SSL, JPEG, gzip, character sets │
├─────────────────────────────────────────────────────────────────┤
│  Layer 5 — Session       │  Session setup/teardown, RPC, sockets│
├─────────────────────────────────────────────────────────────────┤
│  Layer 4 — Transport     │  TCP, UDP — ports, reliability       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3 — Network       │  IP, ICMP, OSPF, BGP — routing       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2 — Data Link     │  Ethernet, MAC, ARP, VLANs, switches │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1 — Physical      │  Cables, fibre, radio, voltage        │
└─────────────────────────────────────────────────────────────────┘
```

Data flows **down** the stack on the sender side (encapsulation) and **up** the stack on the receiver side (decapsulation). Each layer adds a header (and sometimes a trailer) wrapping the layer above — this is called a **PDU (Protocol Data Unit)**.

| Layer | PDU name |
|-------|----------|
| 4 — Transport | Segment (TCP) / Datagram (UDP) |
| 3 — Network | Packet |
| 2 — Data Link | Frame |
| 1 — Physical | Bit |

---

## Layer-by-Layer Breakdown

### Layer 1 — Physical

Transmits raw bits over a physical medium. No addressing, no error correction at this layer.

- **Media**: coaxial, twisted pair (Cat5e/Cat6), fibre (single-mode, multi-mode), radio (Wi-Fi, LTE)
- **Devices**: hubs, repeaters, physical NICs
- **Cloud relevance**: AWS Direct Connect uses physical fibre connections between your data centre and AWS. The speed tier (1 Gbps, 10 Gbps, 100 Gbps) is a Layer 1 concern.

### Layer 2 — Data Link

Transfers frames between nodes on the **same network segment**. Provides MAC addressing and basic error detection.

- **Protocols**: Ethernet (IEEE 802.3), Wi-Fi (IEEE 802.11), VLAN (802.1Q)
- **Devices**: switches, bridges, wireless access points
- **ARP (Address Resolution Protocol)**: resolves an IP address to a MAC address on a local segment
- **Cloud relevance**: within an AWS VPC, traffic between instances in the same subnet is switched at Layer 2 (handled by the hypervisor). Security groups are **not** Layer 2 — they operate at Layer 3/4.

### Layer 3 — Network

Routes packets between different networks. Provides logical (IP) addressing and path selection.

- **Protocols**: IPv4, IPv6, ICMP, OSPF, BGP, EIGRP
- **Devices**: routers, Layer 3 switches, firewalls
- **Key concepts**: subnets, routing tables, TTL (Time to Live), fragmentation
- **Cloud relevance**: VPC route tables are Layer 3. NAT Gateways operate at Layer 3. Security Groups inspect Layer 3 (source/destination IP) and Layer 4 (port/protocol). NACLs operate at Layer 3/4.

### Layer 4 — Transport

End-to-end communication between applications. Provides port-based addressing, reliability (TCP), or low-latency delivery (UDP).

- **Protocols**: TCP (connection-oriented), UDP (connectionless)
- **Key concepts**: source/destination ports, 3-way handshake, flow control, congestion control, sequence numbers
- **Cloud relevance**: NLBs (Network Load Balancers) operate at Layer 4. Security Group rules specify TCP/UDP port ranges. NAT translates Layer 3/4 headers.

### Layer 5 — Session

Establishes, manages, and terminates sessions between applications. In practice, this layer is largely subsumed by Layer 4 (TCP connections) or Layer 7 (TLS session tickets, RPC sessions).

- **Protocols**: RPC, NetBIOS, PPTP (control channel)
- **Cloud relevance**: TLS session resumption, database connection pooling, and gRPC streaming operate at this conceptual layer.

### Layer 6 — Presentation

Translates data formats between the application and the network. Handles encryption, encoding, and compression.

- **Protocols/formats**: TLS/SSL (encryption), JSON/XML (data serialisation), gzip (compression), Base64
- **Cloud relevance**: TLS termination on an ALB or CloudFront is a Layer 6 concern — decrypting HTTPS before forwarding to the backend.

### Layer 7 — Application

The layer closest to the user. Defines the protocol the application uses to communicate.

- **Protocols**: HTTP/HTTPS, DNS, SMTP, FTP, SSH, LDAP, SNMP, gRPC, WebSocket
- **Devices**: load balancers (L7), API gateways, WAFs, CDNs
- **Cloud relevance**: ALB (Application Load Balancer) operates at Layer 7 — it can inspect HTTP headers, path, host header, and query strings to make routing decisions. AWS WAF operates at Layer 7.

---

## Practical Example: What Happens When You Open https://example.com

```
Browser                              Server
   │                                    │
   │  1. App (L7): HTTP GET /           │
   │  2. Presentation (L6): TLS encrypt │
   │  3. Transport (L4): TCP segment    │
   │     src_port=54321, dst_port=443   │
   │  4. Network (L3): IP packet        │
   │     src=192.168.1.5, dst=93.184.216.34
   │  5. Data Link (L2): Ethernet frame │
   │     src_mac=AA:BB dst_mac=gateway  │
   │  6. Physical (L1): electrical bits │──────────────────────────▶
   │                                    │
   │  ◀─── Reverse path on response ────│
```

Steps that happen before the request is sent:
1. DNS lookup (`example.com` → `93.184.216.34`) — L7/L3
2. TCP 3-way handshake — L4
3. TLS handshake — L5/L6
4. HTTP GET — L7

---

## Mnemonic

**Top-down (sender):** **A**ll **P**eople **S**eem **T**o **N**eed **D**ata **P**rocessing
**Bottom-up (receiver):** **P**lease **D**o **N**ot **T**hrow **S**ausage **P**izza **A**way

---

## OSI vs TCP/IP Model

In practice, the **TCP/IP model** (used in real implementations) collapses the 7 OSI layers into 4:

| TCP/IP Layer | OSI Layers |
|--------------|-----------|
| Application | 5 + 6 + 7 |
| Transport | 4 |
| Internet | 3 |
| Network Access | 1 + 2 |

When engineers say "Layer 4 load balancer" or "Layer 7 routing", they are referring to OSI layers — this convention is universal in cloud networking documentation.

---

## Cloud Networking Mapped to OSI

| AWS Service | OSI Layer | Why |
|-------------|-----------|-----|
| Direct Connect | 1 / 2 | Physical fibre + VLAN (802.1Q) |
| VPC (subnets, route tables) | 3 | IP routing |
| Security Groups, NACLs | 3 / 4 | IP + port filtering |
| NAT Gateway | 3 / 4 | IP/port translation |
| Network Load Balancer | 4 | TCP/UDP routing by port |
| Application Load Balancer | 7 | HTTP path/header routing |
| CloudFront | 7 | HTTP cache + TLS termination |
| Route 53 | 7 | DNS |
| AWS WAF | 7 | HTTP request inspection |

---

## References

- [OSI model — RFC 1122 (Internet layer requirements)](https://www.rfc-editor.org/rfc/rfc1122)
- [Cloudflare: What is the OSI model?](https://www.cloudflare.com/learning/ddos/glossary/open-systems-interconnection-model-osi/)
- [AWS Networking Fundamentals](https://aws.amazon.com/getting-started/hands-on/build-serverless-web-app-lambda-apigateway-s3-dynamodb-cognito/)
---

← [Previous: Networking](./README.md) | [Home](../README.md) | [Next: TCP/IP →](./tcp-ip.md)
