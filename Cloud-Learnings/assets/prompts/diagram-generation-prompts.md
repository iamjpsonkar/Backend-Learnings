# Diagram Generation Prompts

Prompts for generating Mermaid, Draw.io, and SVG diagrams for Cloud-Learnings.

## Mermaid Diagram Prompts

Use these prompts with Claude, ChatGPT, or Gemini to generate Mermaid source (`.mmd`) files.
Save output to `assets/diagrams/mermaid/` and render with `./scripts/generate-diagrams.sh`.

---

### Cloud Service Models (IaaS / PaaS / SaaS / FaaS)

```
Generate a Mermaid graph diagram comparing cloud service models.
Show four columns: IaaS, PaaS, SaaS, FaaS.
Each column should list: Hardware, Networking, OS, Runtime, Middleware, Data, Application.
Color items managed by the provider in green and items managed by the user in blue.
Use subgraph blocks for each service model. Add a title.
Use Mermaid graph TD syntax. Output only the raw Mermaid code with no explanation.
```

### AWS Three-Tier Architecture

```
Generate a Mermaid flowchart (graph TD) showing a standard AWS 3-tier web application.
Tiers: Presentation (CloudFront + S3 static assets), Application (ALB + EC2 Auto Scaling
Group), Data (RDS Multi-AZ + ElastiCache).
Show traffic flow from Internet → CloudFront → ALB → EC2 → RDS.
Show ElastiCache as a cache layer between EC2 and RDS.
Include security groups as dashed boxes around compute and data tiers.
Output only raw Mermaid code, no markdown fences, no explanation.
```

### Kubernetes Pod Lifecycle

```
Generate a Mermaid stateDiagram-v2 showing the Kubernetes pod lifecycle.
States: Pending → Running → Succeeded (terminal, green).
From Running → Failed (terminal, red) if container exits non-zero.
From Running → Unknown if node communication is lost.
Show the CrashLoopBackOff sub-state from Failed when restartPolicy=Always.
Show the OOMKilled transition from Running.
Output only raw Mermaid stateDiagram-v2 code with no markdown fence or explanation.
```

### CI/CD Pipeline Flow

```
Generate a Mermaid flowchart (graph LR, left to right) for a typical CI/CD pipeline.
Stages: Developer pushes code → GitHub Actions triggered → Run tests →
Build Docker image → Push to ECR → Deploy to staging → Run smoke tests →
(if pass) Deploy to production → Send notification.
Add a failure path from any stage back to "Fix and re-push".
Use different node shapes: rectangles for steps, diamonds for decisions.
Output only raw Mermaid code.
```

### IAM Policy Evaluation Logic

```
Generate a Mermaid flowchart (graph TD) showing AWS IAM policy evaluation.
Start node: "API Request received".
Decision nodes in order: 1) "Explicit Deny in any policy?" → Yes → Deny (red).
2) "SCP allows action?" → No → Deny. 3) "Resource policy allows?" → Yes → Allow (green).
4) "Identity policy allows?" → Yes → Allow. 5) "Permission boundary allows?" → No → Deny.
Default: Deny. Show all paths clearly.
Output only raw Mermaid code.
```

### DNS Resolution Process

```
Generate a Mermaid sequenceDiagram showing the DNS resolution process.
Participants: Browser, OS Resolver, Recursive Resolver, Root Name Server,
TLD Name Server (.com), Authoritative Name Server.
Show the full resolution for "www.example.com":
1) Browser checks local cache (cache miss).
2) OS Resolver checks its cache (cache miss).
3) Query sent to Recursive Resolver.
4) Recursive Resolver queries Root Name Server → gets .com TLD server address.
5) Recursive Resolver queries TLD Name Server → gets authoritative NS address.
6) Recursive Resolver queries Authoritative Name Server → gets IP.
7) IP returned to Browser. Browser caches result.
Output only raw Mermaid sequenceDiagram code.
```

### Terraform Workflow

```
Generate a Mermaid stateDiagram-v2 showing the Terraform workflow.
States: Write HCL Config → terraform init → terraform plan → Review Plan →
(if approved) terraform apply → Infrastructure Created.
Show terraform destroy as a transition from Infrastructure Created → Destroyed.
Show terraform state as a parallel process that maintains state throughout.
Add error states: init failure, plan failure, apply failure with rollback arrows.
Output only raw Mermaid code.
```

### S3 Lifecycle Policy Flow

```
Generate a Mermaid flowchart (graph LR) showing S3 object lifecycle transitions.
Start: Object uploaded → S3 Standard.
After 30 days → S3 Standard-IA.
After 90 days → S3 Glacier Instant Retrieval.
After 180 days → S3 Glacier Deep Archive.
After 365 days → Permanent deletion.
Show the optional Intelligent-Tiering path as an alternative track.
Show versioning as a branching path where old versions follow a separate lifecycle.
Output only raw Mermaid code.
```

---

## Draw.io / Diagrams.net Prompts

Use these descriptions to build diagrams manually in Draw.io (`assets/diagrams/drawio/`).

### AWS Well-Architected Framework Pillars

```
Create a Draw.io diagram showing the 6 AWS Well-Architected Framework pillars as
a hexagonal arrangement. Each hexagon: Operational Excellence, Security, Reliability,
Performance Efficiency, Cost Optimization, Sustainability. Center circle: "Well-Architected
Workload". Each pillar has 3 key sub-items listed below the hexagon.
Use AWS orange (#FF9900) for the center, light grey for pillars, white background.
```

### Multi-Cloud Architecture

```
Create a Draw.io architecture diagram showing a multi-cloud setup.
Left side: AWS (primary) — EC2, RDS, S3.
Right side: GCP (secondary/DR) — GCE, Cloud SQL, GCS.
Center: HashiCorp Terraform managing both clouds.
Middle layer: A global load balancer (Cloudflare) routing traffic to both.
Show VPN/interconnect between AWS and GCP.
Use official brand colors for each cloud. Clean white background.
```

---

## Tips for Mermaid Prompt Engineering

1. **Specify diagram type explicitly** — `graph TD`, `sequenceDiagram`, `stateDiagram-v2`, `flowchart LR`
2. **Ask for raw code only** — "Output only raw Mermaid code, no markdown fences, no explanation"
3. **Describe direction** — TB (top-bottom), LR (left-right), TD (top-down)
4. **Name all nodes** — list every component so nothing is omitted
5. **Describe all edges** — list each connection and its label
6. **Specify styling** — `classDef` colors if you want consistent styles
7. **Validate output** — paste into [mermaid.live](https://mermaid.live) to verify it renders
8. **Iterate** — add "Fix this error: ..." to refine a broken diagram

## Rendering Mermaid to SVG

After saving a `.mmd` file to `assets/diagrams/mermaid/`:

```bash
# Render all Mermaid diagrams to SVG
./scripts/generate-diagrams.sh

# Render a single file
./scripts/generate-diagrams.sh assets/diagrams/mermaid/aws-vpc-architecture.mmd
```

## Referencing Diagrams in Markdown

```markdown
<!-- Mermaid inline (renders on GitHub) -->
```mermaid
graph TD
    A --> B
```

<!-- SVG asset (use when Mermaid inline is too complex) -->
<img src="../../assets/diagrams/svg/aws-vpc-architecture.svg" alt="AWS VPC Architecture"/>
```
