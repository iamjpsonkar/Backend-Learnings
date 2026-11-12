← [Previous: Strategy](./strategy.md) | [Home](../README.md) | [Next: Identity →](./identity.md)

---

# Multi-Cloud Networking

Connecting workloads across cloud providers requires either public internet (with encryption), managed VPN tunnels, or dedicated interconnect circuits. The right choice depends on bandwidth, latency, cost, and security requirements.

---

## Connectivity Options

```
Option                  Bandwidth    Latency    Cost      Use case
───────────────────────────────────────────────────────────────────
Public internet + TLS   Variable     Variable   Low       Dev/test, low-volume APIs
Site-to-site VPN        1-2 Gbps     ~50-100ms  Medium    Production inter-cloud
Cloud Exchange          1-100 Gbps   ~5-20ms    High      High-bandwidth, low-latency
Dedicated interconnect  10-100 Gbps  ~2-10ms    Very high Large-scale enterprise
```

---

## Site-to-Site VPN: AWS to GCP

### AWS Side (Virtual Private Gateway)

```bash
# Step 1: Create Customer Gateway (represents GCP's VPN endpoint)
# GCP HA VPN uses two IPs — create two CG entries
GCP_VPN_IP1="34.x.x.x"   # GCP HA VPN interface 0 external IP
GCP_VPN_IP2="34.x.x.y"   # GCP HA VPN interface 1 external IP

CGW_ID_1=$(aws ec2 create-customer-gateway \
    --type ipsec.1 \
    --public-ip $GCP_VPN_IP1 \
    --bgp-asn 65000 \
    --query 'CustomerGateway.CustomerGatewayId' --output text)

CGW_ID_2=$(aws ec2 create-customer-gateway \
    --type ipsec.1 \
    --public-ip $GCP_VPN_IP2 \
    --bgp-asn 65000 \
    --query 'CustomerGateway.CustomerGatewayId' --output text)

# Step 2: Create Virtual Private Gateway and attach to VPC
VGW_ID=$(aws ec2 create-vpn-gateway \
    --type ipsec.1 \
    --amazon-side-asn 64512 \
    --query 'VpnGateway.VpnGatewayId' --output text)

aws ec2 attach-vpn-gateway \
    --vpn-gateway-id $VGW_ID \
    --vpc-id $VPC_ID

# Enable route propagation for the VGW
aws ec2 enable-vgw-route-propagation \
    --gateway-id $VGW_ID \
    --route-table-id $PRIVATE_ROUTE_TABLE_ID

# Step 3: Create VPN connections (one per GCP HA VPN interface)
VPN_CONN_1=$(aws ec2 create-vpn-connection \
    --type ipsec.1 \
    --customer-gateway-id $CGW_ID_1 \
    --vpn-gateway-id $VGW_ID \
    --options '{
        "StaticRoutesOnly": false,
        "TunnelOptions": [
            {"PreSharedKey": "pre-shared-key-1", "TunnelInsideCidr": "169.254.10.0/30"},
            {"PreSharedKey": "pre-shared-key-2", "TunnelInsideCidr": "169.254.11.0/30"}
        ]
    }' \
    --query 'VpnConnection.VpnConnectionId' --output text)

# Download VPN configuration file (contains IPs and pre-shared keys for GCP)
aws ec2 describe-vpn-connections \
    --vpn-connection-ids $VPN_CONN_1 \
    --query 'VpnConnections[0].CustomerGatewayConfiguration' \
    --output text > vpn-config-for-gcp.xml
```

### GCP Side (HA VPN)

```bash
# Step 1: Create HA VPN Gateway in GCP
gcloud compute vpn-gateways create aws-vpn-gateway \
    --network default \
    --region us-central1

# Get the two external IPs assigned to the GCP HA VPN gateway
# (use these as CGW IPs on AWS side above)
gcloud compute vpn-gateways describe aws-vpn-gateway \
    --region us-central1 \
    --format 'value(vpnInterfaces[0].ipAddress, vpnInterfaces[1].ipAddress)'

# Step 2: Create external VPN gateway (represents AWS side)
AWS_VPN_IP1="52.x.x.x"   # From AWS VPN connection tunnel 1 outside IP
AWS_VPN_IP2="52.x.x.y"   # From AWS VPN connection tunnel 2 outside IP

gcloud compute external-vpn-gateways create aws-external-gateway \
    --redundancy-type TWO_IPS_REDUNDANCY \
    --interfaces 0=$AWS_VPN_IP1,1=$AWS_VPN_IP2

# Step 3: Create VPN tunnels (4 total for full redundancy)
gcloud compute vpn-tunnels create aws-tunnel-1 \
    --peer-external-gateway aws-external-gateway \
    --peer-external-gateway-interface 0 \
    --region us-central1 \
    --ike-version 2 \
    --shared-secret "pre-shared-key-1" \
    --router aws-vpn-router \
    --vpn-gateway aws-vpn-gateway \
    --vpn-gateway-region us-central1 \
    --interface 0

# Step 4: Configure BGP on Cloud Router
gcloud compute routers add-bgp-peer aws-vpn-router \
    --region us-central1 \
    --interface aws-tunnel-1 \
    --peer-name aws-bgp-peer-1 \
    --peer-asn 64512 \
    --peer-ip-address 169.254.10.1 \
    --ip-address 169.254.10.2

# Step 5: Verify tunnel status
gcloud compute vpn-tunnels describe aws-tunnel-1 \
    --region us-central1 \
    --format 'value(status, detailedStatus)'
```

---

## AWS Transit Gateway for Multi-Cloud Hub

```
On-premises DC
     │ Direct Connect
     │
AWS Transit Gateway ─── VPC A (prod)
     │                ─── VPC B (staging)
     │                ─── VPC C (data)
     │ VPN
     │
GCP VPC (analytics)

Azure VNet (identity)
     │ ExpressRoute Global Reach
     │
(Requires using a carrier network or co-location exchange)
```

```bash
# Create Transit Gateway
TGW_ID=$(aws ec2 create-transit-gateway \
    --description "Multi-cloud hub" \
    --options '{
        "AmazonSideAsn": 64512,
        "AutoAcceptSharedAttachments": "disable",
        "DefaultRouteTableAssociation": "enable",
        "DefaultRouteTablePropagation": "enable",
        "VpnEcmpSupport": "enable",
        "DnsSupport": "enable",
        "MulticastSupport": "disable"
    }' \
    --query 'TransitGateway.TransitGatewayId' --output text)

# Attach production VPC
aws ec2 create-transit-gateway-vpc-attachment \
    --transit-gateway-id $TGW_ID \
    --vpc-id $PROD_VPC_ID \
    --subnet-ids $SUBNET_A $SUBNET_B $SUBNET_C

# Create VPN attachment for GCP connection
aws ec2 create-transit-gateway-connect \
    --transport-transit-gateway-attachment-id $VPN_ATTACHMENT_ID \
    --options '{Protocol: gre}'

# Route table: allow inter-VPC and VPN traffic
aws ec2 create-transit-gateway-route \
    --transit-gateway-route-table-id $TGW_RT_ID \
    --destination-cidr-block 10.2.0.0/16 \  # GCP VPC CIDR
    --transit-gateway-attachment-id $VPN_ATTACHMENT_ID
```

---

## AWS Direct Connect + Azure ExpressRoute

For high-bandwidth, low-latency connections to both AWS and Azure from on-premises:

```
On-premises DC
     │
     ├──── Direct Connect (10 Gbps) ────► AWS
     │
     └──── ExpressRoute (10 Gbps) ───────► Azure

AWS ◄──── Not directly connected ────► Azure
    (Use internet VPN or co-location exchange for AWS-Azure direct)
```

```bash
# AWS Direct Connect: create connection (ordered through AWS console or partner)
aws directconnect create-connection \
    --location EqDC2 \
    --bandwidth 10Gbps \
    --connection-name prod-dc-east

# Create Virtual Interface (private — connects to VPC)
aws directconnect create-private-virtual-interface \
    --connection-id $CONNECTION_ID \
    --new-private-virtual-interface '{
        "virtualInterfaceName": "prod-private-vif",
        "vlan": 101,
        "asn": 65001,
        "authKey": "bgp-auth-key",
        "amazonAddress": "175.45.176.1/30",
        "customerAddress": "175.45.176.2/30",
        "virtualGatewayId": "'$VGW_ID'"
    }'
```

---

## DNS Resolution Across Clouds

```bash
# AWS: Route 53 private hosted zone for internal service discovery
# Create zone for AWS services
aws route53 create-hosted-zone \
    --name internal.aws.myapp.com \
    --caller-reference $(uuidgen) \
    --hosted-zone-config PrivateZone=true \
    --vpc VPCRegion=us-east-1,VPCId=$VPC_ID

# Add A record for a service
aws route53 change-resource-record-sets \
    --hosted-zone-id $ZONE_ID \
    --change-batch '{
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "orders-api.internal.aws.myapp.com",
                "Type": "A",
                "TTL": 60,
                "ResourceRecords": [{"Value": "10.0.1.50"}]
            }
        }]
    }'

# GCP: Cloud DNS for GCP-internal services
gcloud dns managed-zones create gcp-internal-zone \
    --description "GCP internal services" \
    --dns-name internal.gcp.myapp.com \
    --visibility private \
    --networks default

gcloud dns record-sets create analytics-api.internal.gcp.myapp.com \
    --zone gcp-internal-zone \
    --type A \
    --ttl 60 \
    --rrdatas 10.1.0.50

# Cross-cloud DNS: register each cloud's DNS zone in the other
# AWS → GCP: add conditional forwarder in Route 53 for internal.gcp.myapp.com
aws route53resolver create-firewall-rule-group \
    --name gcp-resolver

# Create forwarding rule for GCP zone
aws route53resolver create-resolver-rule \
    --creator-request-id $(uuidgen) \
    --domain-name internal.gcp.myapp.com \
    --rule-type FORWARD \
    --target-ips '[{"Ip":"10.1.0.2","Port":53}]' \  # GCP Cloud DNS resolver IP via VPN
    --resolver-endpoint-id $OUTBOUND_ENDPOINT_ID
```

---

## References

- [AWS VPN to GCP HA VPN guide](https://cloud.google.com/network-connectivity/docs/vpn/tutorials/create-ha-vpn-connections-google-and-aws)
- [AWS Transit Gateway](https://docs.aws.amazon.com/vpc/latest/tgw/)
- [AWS Direct Connect](https://docs.aws.amazon.com/directconnect/latest/UserGuide/)
- [Azure ExpressRoute](https://learn.microsoft.com/en-us/azure/expressroute/)

---

← [Previous: Strategy](./strategy.md) | [Home](../README.md) | [Next: Identity →](./identity.md)
