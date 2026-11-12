← [Previous: Linux Troubleshooting](../02-linux/troubleshooting.md) | [Home](../README.md) | [Next: OSI Model →](./osi-model.md)

---

# Networking for Cloud Engineers

A solid understanding of networking is essential for cloud work. Every VPC, security group, load balancer, and DNS record is a networking concept. This section covers the fundamentals — from the OSI model through to Zero Trust — with cloud-specific applications throughout.

---

## Topics

| File | What it covers |
|------|---------------|
| [osi-model.md](osi-model.md) | 7-layer model, protocols at each layer, real-world relevance |
| [tcp-ip.md](tcp-ip.md) | TCP vs UDP, 3-way handshake, connection states, socket options |
| [dns.md](dns.md) | Resolution flow, record types, TTL, split-horizon, Route 53 |
| [http-https-tls.md](http-https-tls.md) | HTTP methods/headers/status codes, TLS handshake, certificates |
| [cidr-subnetting.md](cidr-subnetting.md) | Binary subnetting, CIDR notation, VPC design, reserved ranges |
| [nat-routing.md](nat-routing.md) | NAT types, routing tables, BGP basics, AWS route propagation |
| [firewalls-vpn.md](firewalls-vpn.md) | Stateful vs stateless, Security Groups, NACLs, VPN types |
| [load-balancing.md](load-balancing.md) | L4 vs L7, algorithms, ALB/NLB/CLB, health checks, sticky sessions |
| [cdn.md](cdn.md) | Edge locations, cache behaviour, CloudFront, cache invalidation |
| [zero-trust.md](zero-trust.md) | Zero Trust principles, identity-aware access, BeyondCorp pattern |
| [troubleshooting.md](troubleshooting.md) | Systematic network debugging, tools, cloud-specific patterns |

---

## Minimum Competency

Before moving to cloud networking (VPCs, security groups, Route 53), be confident with:

- [ ] What happens at each OSI layer when you open `https://example.com`
- [ ] Difference between TCP and UDP, and which protocols use which
- [ ] How DNS resolution works (recursive resolver → root → TLD → authoritative)
- [ ] Common DNS record types: A, AAAA, CNAME, MX, TXT, NS, SOA, PTR
- [ ] CIDR notation: what `/16`, `/24`, `/28` mean; how to calculate host count
- [ ] Private IP ranges (RFC 1918): 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- [ ] What NAT does and why it is necessary in cloud architectures
- [ ] Difference between a stateful firewall and a stateless ACL
- [ ] How TLS certificates work (CA chain, SNI, certificate validation)
- [ ] What a load balancer does at L4 vs L7

---

## OSI Quick Reference

```
Layer 7 — Application   HTTP, HTTPS, DNS, SSH, SMTP, FTP
Layer 6 — Presentation  TLS/SSL, encoding, compression
Layer 5 — Session       Session establishment, TLS session resumption
Layer 4 — Transport     TCP, UDP — ports, reliability, flow control
Layer 3 — Network       IP, ICMP, routing — logical addressing
Layer 2 — Data Link     Ethernet, MAC addresses, VLANs, ARP
Layer 1 — Physical      Cables, fibre, radio, voltage levels
```

---

## References

- [RFC 791 — IPv4](https://www.rfc-editor.org/rfc/rfc791)
- [RFC 793 — TCP](https://www.rfc-editor.org/rfc/rfc793)
- [RFC 1034/1035 — DNS](https://www.rfc-editor.org/rfc/rfc1034)
- [AWS VPC documentation](https://docs.aws.amazon.com/vpc/latest/userguide/)
- [Cloudflare Learning Center](https://www.cloudflare.com/learning/)
---

← [Previous: Linux Troubleshooting](../02-linux/troubleshooting.md) | [Home](../README.md) | [Next: OSI Model →](./osi-model.md)
