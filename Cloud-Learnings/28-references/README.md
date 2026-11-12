← [Previous: DevOps & SRE](../27-interview-prep/devops-sre.md) | [Home](../README.md)

---

# References

Curated references for cloud engineering, DevOps, and SRE. These are the primary sources — official documentation, foundational books, and actively-maintained tools. Organised by topic so you can go deep on whatever you are working on.

---

## Official Documentation

### AWS

| Resource | URL |
|----------|-----|
| AWS Documentation (all services) | https://docs.aws.amazon.com |
| AWS Architecture Center | https://aws.amazon.com/architecture |
| AWS Well-Architected Framework | https://docs.aws.amazon.com/wellarchitected/latest/framework |
| AWS CLI Reference | https://awscli.amazonaws.com/v2/documentation/api/latest/index.html |
| AWS Solutions Library | https://aws.amazon.com/solutions |
| AWS Prescriptive Guidance | https://docs.aws.amazon.com/prescriptive-guidance/latest |

### Azure

| Resource | URL |
|----------|-----|
| Azure Documentation | https://learn.microsoft.com/azure |
| Azure Architecture Center | https://learn.microsoft.com/azure/architecture |
| Azure Well-Architected Framework | https://learn.microsoft.com/azure/well-architected |
| Azure CLI Reference | https://learn.microsoft.com/cli/azure |

### GCP

| Resource | URL |
|----------|-----|
| Google Cloud Documentation | https://cloud.google.com/docs |
| Google Cloud Architecture Framework | https://cloud.google.com/architecture/framework |
| gcloud CLI Reference | https://cloud.google.com/sdk/gcloud/reference |

---

## Books

### Cloud and Infrastructure

| Title | Authors | Key Topics |
|-------|---------|------------|
| *Cloud Native Patterns* | Cornelia Davis | Service decomposition, resilience patterns |
| *Designing Distributed Systems* | Brendan Burns | Distributed patterns on Kubernetes |
| *The Phoenix Project* | Kim, Behr, Spafford | DevOps culture and flow |
| *Accelerate* | Forsgren, Humble, Kim | DORA metrics, delivery performance |

### SRE and Reliability

| Title | Authors | Key Topics |
|-------|---------|------------|
| *Site Reliability Engineering* | Google SRE Team | SRE philosophy, error budgets, on-call |
| *The Site Reliability Workbook* | Google SRE Team | Practical SRE implementation |
| *Implementing Service Level Objectives* | Alex Hidalgo | SLO tooling and measurement |
| *Chaos Engineering* | Rosenthal et al. | Controlled failure experiments |
| *Database Reliability Engineering* | Campbell, Majors | Applying SRE to databases |

### Security

| Title | Authors | Key Topics |
|-------|---------|------------|
| *Hacking: The Art of Exploitation* | Jon Erickson | Low-level security fundamentals |
| *The Web Application Hacker's Handbook* | Stuttard, Pinto | Web security, OWASP |
| *AWS Security* | Dylan Shields | Practical AWS security |

### Infrastructure as Code

| Title | Authors | Key Topics |
|-------|---------|------------|
| *Terraform: Up & Running* | Yevgeniy Brikman | Terraform patterns, modules, state |
| *Infrastructure as Code* | Kief Morris | Principles across all IaC tools |

---

## Kubernetes

| Resource | Notes |
|----------|-------|
| Kubernetes Documentation | https://kubernetes.io/docs |
| kubectl Cheat Sheet | https://kubernetes.io/docs/reference/kubectl/cheatsheet |
| Kubernetes the Hard Way | Kelsey Hightower's manual bootstrap walkthrough |
| Helm Documentation | https://helm.sh/docs |
| Kustomize Documentation | https://kubectl.docs.kubernetes.io/references/kustomize |
| Kubernetes Failure Stories | https://k8s.af — real-world outpost mortems |

---

## Observability

| Resource | Notes |
|----------|-------|
| Prometheus Documentation | https://prometheus.io/docs |
| PromQL Cheat Sheet | https://promlabs.com/promql-cheat-sheet |
| Grafana Documentation | https://grafana.com/docs |
| OpenTelemetry Documentation | https://opentelemetry.io/docs |
| Loki Documentation | https://grafana.com/docs/loki/latest |
| Jaeger Documentation | https://www.jaegertracing.io/docs |

---

## Infrastructure as Code

| Resource | Notes |
|----------|-------|
| Terraform Documentation | https://developer.hashicorp.com/terraform/docs |
| Terraform Registry | https://registry.terraform.io — modules and providers |
| OpenTofu Documentation | https://opentofu.org/docs |
| Ansible Documentation | https://docs.ansible.com |
| Pulumi Documentation | https://www.pulumi.com/docs |

---

## CI/CD and GitOps

| Resource | Notes |
|----------|-------|
| GitHub Actions Documentation | https://docs.github.com/actions |
| GitHub Actions Marketplace | https://github.com/marketplace?type=actions |
| ArgoCD Documentation | https://argo-cd.readthedocs.io |
| Flux Documentation | https://fluxcd.io/docs |
| GitLab CI/CD Documentation | https://docs.gitlab.com/ee/ci |

---

## Security

| Resource | Notes |
|----------|-------|
| OWASP Top 10 | https://owasp.org/www-project-top-ten |
| OWASP Cheat Sheet Series | https://cheatsheetseries.owasp.org |
| AWS Security Best Practices | https://docs.aws.amazon.com/security |
| CIS Benchmarks | https://www.cisecurity.org/cis-benchmarks — hardening guides |
| SLSA Framework | https://slsa.dev — supply chain security levels |
| NVD (CVE Database) | https://nvd.nist.gov |

---

## Networking

| Resource | Notes |
|----------|-------|
| RFC 791 (IP) | https://datatracker.ietf.org/doc/html/rfc791 |
| RFC 793 (TCP) | https://datatracker.ietf.org/doc/html/rfc793 |
| Cloudflare Learning Center | https://www.cloudflare.com/learning — DNS, TLS, HTTP |
| Julia Evans — Networking Zines | https://wizardzines.com — approachable deep dives |

---

## Certifications

| Certification | Provider | Level | Guide |
|--------------|----------|-------|-------|
| AWS Cloud Practitioner | AWS | Foundational | https://aws.amazon.com/certification/certified-cloud-practitioner |
| AWS Solutions Architect Associate | AWS | Associate | https://aws.amazon.com/certification/certified-solutions-architect-associate |
| AWS DevOps Engineer Professional | AWS | Professional | https://aws.amazon.com/certification/certified-devops-engineer-professional |
| CKA — Certified Kubernetes Administrator | CNCF | Practitioner | https://training.linuxfoundation.org/certification/certified-kubernetes-administrator-cka |
| CKAD — Certified Kubernetes Application Developer | CNCF | Practitioner | https://training.linuxfoundation.org/certification/certified-kubernetes-application-developer-ckad |
| Prometheus Certified Associate | CNCF | Associate | https://training.linuxfoundation.org/certification/prometheus-certified-associate |
| HashiCorp Terraform Associate | HashiCorp | Associate | https://www.hashicorp.com/certifications/terraform-associate |
| Google Associate Cloud Engineer | Google | Associate | https://cloud.google.com/certification/cloud-engineer |
| Azure Administrator Associate | Microsoft | Associate | https://learn.microsoft.com/certifications/azure-administrator |

---

## Practice and Labs

| Resource | Notes |
|----------|-------|
| AWS Free Tier | 12-month free tier + always-free services |
| GCP Free Tier | $300 credit for 90 days + always-free resources |
| Azure Free Account | $200 credit for 30 days + 12 months free services |
| KodeKloud | Hands-on labs for Kubernetes, Terraform, Linux |
| Killercoda | Browser-based Linux and Kubernetes labs |
| play-with-docker | Browser-based Docker playground |
| A Cloud Guru / Pluralsight | Video courses with sandboxed labs |

---

## Community

| Resource | Notes |
|----------|-------|
| CNCF Slack | https://slack.cncf.io — Kubernetes, OpenTelemetry, Helm, ArgoCD communities |
| AWS re:Post | https://repost.aws — AWS Q&A community |
| HashiCorp Discuss | https://discuss.hashicorp.com |
| DevOps subreddit | https://reddit.com/r/devops |
| SRE subreddit | https://reddit.com/r/sre |
| Hacker News | https://news.ycombinator.com — for keeping up with the field |

---

← [Previous: DevOps & SRE](../27-interview-prep/devops-sre.md) | [Home](../README.md)
