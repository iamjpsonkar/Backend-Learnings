← [Previous: Cloud Concepts](./cloud-concepts.md) | [Home](../README.md) | [Next: Deployment Models →](./deployment-models.md)

---

# Cloud Service Models: IaaS, PaaS, SaaS, FaaS

Cloud services are delivered in four primary models. The key difference between them is **how much you manage vs how much the provider manages**.

---

## The Core Question

Every cloud service model answers one question differently:

> **How much infrastructure are you responsible for?**

The more the provider manages, the less flexibility you have — but the less operational burden you carry.

---

## IaaS — Infrastructure as a Service

### What It Is

The provider gives you raw infrastructure: virtual machines, networking, and storage. You manage everything above the hypervisor.

### What You Manage

- Operating system (install, patch, harden)
- Runtime (Python, Java, Node.js)
- Middleware (web server, application server)
- Application code
- Data

### What the Provider Manages

- Physical hardware
- Networking equipment
- Data center facilities
- Hypervisor / virtualization layer

### Examples

| Provider | Service |
|---------|---------|
| AWS | EC2, EBS, VPC |
| Azure | Azure Virtual Machines, Azure Disk |
| GCP | Google Compute Engine |
| Other | DigitalOcean Droplets, Linode |

### When to Use IaaS

- You need full control over the OS configuration
- You're running legacy applications that require specific OS versions
- Your team has strong Linux/Windows administration skills
- You need to run software not supported by higher-level services

### Trade-offs

| Pro | Con |
|-----|-----|
| Maximum flexibility and control | You own OS patching and maintenance |
| Run any software on any OS | Higher operational burden |
| Predictable performance tuning | Slower to provision and configure |
| Familiar mental model (it's just a server) | More security surface to manage |

---

## PaaS — Platform as a Service

### What It Is

The provider manages the infrastructure, OS, runtime, and middleware. You deploy application code and manage data only.

### What You Manage

- Application code
- Data
- Configuration (environment variables, scaling rules)

### What the Provider Manages

- Everything in IaaS, plus:
- Operating system
- Runtime environment
- Middleware, web server, load balancer
- Automatic scaling (usually)

### Examples

| Provider | Service |
|---------|---------|
| AWS | Elastic Beanstalk, App Runner, RDS, Aurora |
| Azure | Azure App Service, Azure SQL Database |
| GCP | App Engine, Cloud SQL, Cloud Run |
| Other | Heroku, Railway, Render |

### When to Use PaaS

- You want to focus on writing application code, not managing servers
- Your team lacks deep infrastructure expertise
- You need to deploy quickly with minimal ops overhead
- Your application fits a standard runtime (Python/Node/Java/Go web apps)

### Trade-offs

| Pro | Con |
|-----|-----|
| No OS maintenance | Less control over environment |
| Automatic patching | Harder to debug infrastructure issues |
| Built-in scaling | Vendor lock-in risk |
| Faster time to deploy | May not support custom runtimes or OS-level dependencies |

---

## SaaS — Software as a Service

### What It Is

The provider delivers a fully functional application over the internet. You use the software — you manage only your data and user configuration.

### What You Manage

- Your data
- User access and permissions within the application
- Application-level configuration (settings, integrations)

### What the Provider Manages

- Everything: infrastructure, OS, runtime, middleware, application code, updates

### Examples

| Category | Examples |
|---------|---------|
| Email | Gmail, Microsoft 365 Outlook |
| Source control | GitHub, GitLab |
| CRM | Salesforce |
| HR/Payroll | Workday, BambooHR |
| Communication | Slack, Zoom |
| Monitoring | Datadog, New Relic |

### When to Use SaaS

- You need a well-defined function (email, CRM, project management)
- You don't want to build or maintain that function yourself
- Your team doesn't need customization beyond configuration

### Trade-offs

| Pro | Con |
|-----|-----|
| Zero infrastructure management | Least control |
| Automatic updates and improvements | Data portability concerns |
| Instant onboarding | Pricing per seat can scale quickly |
| Low technical barrier | Limited customization |

---

## FaaS — Function as a Service (Serverless Compute)

### What It Is

You write individual functions (small units of code). The provider runs them in response to events and handles all infrastructure — including scaling to zero.

### What You Manage

- Function code (the handler)
- Trigger configuration (what event invokes the function)
- Function settings (memory, timeout, environment variables)

### What the Provider Manages

- Everything, plus:
- Container lifecycle (create, run, destroy)
- Scaling from zero to thousands of concurrent executions
- Billing per invocation (not per idle server)

### Examples

| Provider | Service |
|---------|---------|
| AWS | Lambda |
| Azure | Azure Functions |
| GCP | Cloud Functions, Cloud Run (container-based) |
| Other | Cloudflare Workers, Vercel Edge Functions |

### When to Use FaaS

- Event-driven workloads (API calls, file uploads, queue messages, scheduled tasks)
- Infrequent or unpredictable traffic — pay only when code runs
- You want zero infrastructure management
- Short-lived tasks (under 15 minutes for AWS Lambda)

### Trade-offs

| Pro | Con |
|-----|-----|
| Zero server management | Cold starts add latency |
| True pay-per-use | Execution time limits |
| Scales to zero (no idle cost) | Harder to test locally |
| Auto-scales infinitely | Stateless — no persistent connections |

---

## Side-by-Side Comparison

```
                     You manage ←——————————————————————→ Provider manages

On-Premises   ████████████████████████████████████  (everything)
IaaS          ████████████████████░░░░░░░░░░░░░░░░  (app + OS)
PaaS          ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  (app + data)
SaaS          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  (data only)
FaaS          ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  (function code)
```

| Layer | On-Prem | IaaS | PaaS | SaaS | FaaS |
|-------|---------|------|------|------|------|
| Application | You | You | You | Provider | You (function) |
| Data | You | You | You | You | You |
| Runtime | You | You | Provider | Provider | Provider |
| Middleware | You | You | Provider | Provider | Provider |
| OS | You | You | Provider | Provider | Provider |
| Virtualization | You | Provider | Provider | Provider | Provider |
| Hardware | You | Provider | Provider | Provider | Provider |

---

## Choosing the Right Model

| Question | Guidance |
|----------|---------|
| Need full control over the OS? | IaaS |
| Want to just deploy code to a managed platform? | PaaS |
| Building event-driven or async tasks? | FaaS |
| Need an off-the-shelf application? | SaaS |
| Running legacy apps with specific OS requirements? | IaaS |
| Minimizing ops overhead is the priority? | PaaS or FaaS |
| Traffic is very spiky or unpredictable? | FaaS |
| Need global CDN with zero infrastructure? | SaaS or FaaS at edge |

In practice, most architectures use a combination: FaaS for async processing, PaaS for the API, IaaS for legacy workloads, and SaaS for tools like monitoring and CI/CD.

---

## References

- [AWS: Types of cloud computing](https://aws.amazon.com/types-of-cloud-computing/)
- [Azure: IaaS, PaaS, SaaS](https://azure.microsoft.com/en-us/resources/cloud-computing-dictionary/what-is-iaas/)
- [GCP: Cloud computing services](https://cloud.google.com/learn/paas-vs-iaas-vs-saas)
---

← [Previous: Cloud Concepts](./cloud-concepts.md) | [Home](../README.md) | [Next: Deployment Models →](./deployment-models.md)
