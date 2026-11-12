← [Previous: CloudFormation](./cloudformation.md) | [Home](../../README.md) | [Next: Terraform on AWS →](./terraform-on-aws.md)

---

# AWS CDK (Cloud Development Kit)

CDK lets you define AWS infrastructure using real programming languages — Python, TypeScript, Java, C#, or Go. It compiles your code into a CloudFormation template (synthesize), then deploys via CloudFormation. You get IDE autocompletion, type safety, loops, and abstractions that YAML cannot offer.

---

## Core Concepts

| Concept | Meaning |
|---------|---------|
| **App** | Root of the CDK application — contains one or more stacks |
| **Stack** | Maps 1:1 to a CloudFormation stack; unit of deployment |
| **Construct** | A reusable cloud component (L1 = raw CFN, L2 = opinionated AWS, L3 = patterns) |
| **L1 construct** | Direct CloudFormation resource (`CfnBucket`) — full control, verbose |
| **L2 construct** | High-level, opinionated AWS resource (`s3.Bucket`) — handles defaults, grants |
| **L3 construct (pattern)** | Multi-resource pattern (`aws_ecs_patterns.ApplicationLoadBalancedFargateService`) |
| **synth** | Converts CDK code → CloudFormation template (stored in `cdk.out/`) |
| **deploy** | Synthesizes then deploys via CloudFormation |
| **context** | Key-value runtime configuration (account, region, feature flags) |
| **Aspect** | Visitor that traverses all constructs to enforce policies (e.g., tag everything) |

---

## Setup

```bash
# Install CDK CLI
npm install -g aws-cdk

# Verify
cdk --version

# Initialize a new Python CDK project
mkdir my-app-infra && cd my-app-infra
cdk init app --language python

# Install dependencies
pip install -r requirements.txt

# Bootstrap the account/region (one-time per account/region)
# Creates a CDKToolkit stack with an S3 bucket and IAM roles
cdk bootstrap aws://123456789012/us-east-1
```

---

## CDK Application Structure (Python)

```
my-app-infra/
├── app.py                  # Entry point — instantiates the App and Stacks
├── my_app_infra/
│   ├── __init__.py
│   ├── network_stack.py    # VPC, subnets, security groups
│   ├── compute_stack.py    # ECS service, ALB
│   └── data_stack.py       # RDS, ElastiCache
├── tests/
│   └── unit/
│       └── test_network_stack.py
├── cdk.json                # CDK app configuration and context
└── requirements.txt
```

### app.py

```python
#!/usr/bin/env python3
import aws_cdk as cdk
from my_app_infra.network_stack import NetworkStack
from my_app_infra.compute_stack import ComputeStack

app = cdk.App()

env_prod = cdk.Environment(account="123456789012", region="us-east-1")

network = NetworkStack(app, "MyApp-Network", env=env_prod)
ComputeStack(app, "MyApp-Compute", vpc=network.vpc, env=env_prod)

app.synth()
```

---

## Network Stack (L2 Constructs)

```python
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
from constructs import Construct


class NetworkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC with 2 AZs, public + private subnets, NAT Gateway in each AZ
        self.vpc = ec2.Vpc(
            self, "VPC",
            max_azs=2,
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            nat_gateways=1,  # 1 NAT GW costs ~$33/month; use 2 for HA
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=28,
                ),
            ],
        )

        # VPC Flow Logs to CloudWatch
        self.vpc.add_flow_log(
            "FlowLogs",
            destination=ec2.FlowLogDestination.to_cloud_watch_logs(),
            traffic_type=ec2.FlowLogTrafficType.ALL,
        )

        # Export VPC ID as CloudFormation output
        cdk.CfnOutput(self, "VPCId", value=self.vpc.vpc_id, export_name="MyApp-VPCId")
```

---

## Compute Stack (ECS Fargate with ALB — L3 Pattern)

```python
import aws_cdk as cdk
from aws_cdk import (
    Stack, Duration,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr as ecr,
    aws_certificatemanager as acm,
    aws_route53 as route53,
    aws_logs as logs,
)
from constructs import Construct


class ComputeStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ECS Cluster with Container Insights
        cluster = ecs.Cluster(
            self, "Cluster",
            vpc=vpc,
            container_insights=True,
            cluster_name="production",
        )

        # ECR repository
        repo = ecr.Repository.from_repository_name(
            self, "Repo", "my-app/backend"
        )

        # Log group for the service
        log_group = logs.LogGroup(
            self, "LogGroup",
            log_group_name="/ecs/my-app-backend",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # ApplicationLoadBalancedFargateService — L3 pattern
        # Creates: task def, service, ALB, listener, target group, security groups
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "Service",
            cluster=cluster,
            cpu=512,
            memory_limit_mib=1024,
            desired_count=2,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(repo, tag="latest"),
                container_port=8080,
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="ecs",
                    log_group=log_group,
                ),
                environment={
                    "APP_ENV": "production",
                    "PORT": "8080",
                },
            ),
            public_load_balancer=True,
            redirect_http=True,
            health_check_grace_period=Duration.seconds(60),
        )

        # Health check
        fargate_service.target_group.configure_health_check(
            path="/health",
            healthy_http_codes="200",
            interval=Duration.seconds(30),
            timeout=Duration.seconds(5),
            healthy_threshold_count=2,
            unhealthy_threshold_count=3,
        )

        # Auto scaling
        scaling = fargate_service.service.auto_scale_task_count(
            min_capacity=2,
            max_capacity=20,
        )
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=60,
            scale_in_cooldown=Duration.minutes(5),
            scale_out_cooldown=Duration.minutes(1),
        )
        scaling.scale_on_request_count(
            "RequestScaling",
            requests_per_target=1000,
            target_group=fargate_service.target_group,
            scale_in_cooldown=Duration.minutes(5),
            scale_out_cooldown=Duration.minutes(1),
        )

        cdk.CfnOutput(self, "LoadBalancerDNS",
                      value=fargate_service.load_balancer.load_balancer_dns_name)
```

---

## CDK Commands

```bash
# Synthesize — generates CloudFormation in cdk.out/
cdk synth

# Show diff between deployed and local code
cdk diff MyApp-Compute

# Deploy a specific stack
cdk deploy MyApp-Network

# Deploy all stacks (in dependency order)
cdk deploy --all

# Deploy without confirmation prompt (CI/CD)
cdk deploy MyApp-Compute --require-approval never

# Destroy a stack (with confirmation)
cdk destroy MyApp-Compute

# List stacks
cdk list

# Open in CloudFormation console
cdk deploy MyApp-Compute --outputs-file cdk-outputs.json
```

---

## Aspects — Enforce Policies Across All Constructs

```python
import aws_cdk as cdk
from aws_cdk import IAspect, aws_s3 as s3
import jsii


@jsii.implements(IAspect)
class EnforceEncryptionAspect:
    """Ensure all S3 buckets have versioning and encryption enabled."""

    def visit(self, node) -> None:
        if isinstance(node, s3.CfnBucket):
            if not node.versioning_configuration:
                node.versioning_configuration = s3.CfnBucket.VersioningConfigurationProperty(
                    status="Enabled"
                )


@jsii.implements(IAspect)
class TaggingAspect:
    """Apply mandatory tags to every resource."""

    def __init__(self, env: str, team: str):
        self.env = env
        self.team = team

    def visit(self, node) -> None:
        if cdk.TagManager.is_taggable(node):
            cdk.Tags.of(node).add("Environment", self.env)
            cdk.Tags.of(node).add("Team", self.team)
            cdk.Tags.of(node).add("ManagedBy", "CDK")


# In app.py — apply aspects to the entire app
cdk.Aspects.of(app).add(TaggingAspect(env="production", team="platform"))
cdk.Aspects.of(network).add(EnforceEncryptionAspect())
```

---

## Testing CDK Stacks

```python
# tests/unit/test_network_stack.py
import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
from my_app_infra.network_stack import NetworkStack


def test_vpc_created():
    app = cdk.App()
    stack = NetworkStack(app, "TestNetworkStack",
                         env=cdk.Environment(account="123456789012", region="us-east-1"))
    template = Template.from_stack(stack)

    # Assert VPC exists with correct CIDR
    template.has_resource_properties("AWS::EC2::VPC", {
        "CidrBlock": "10.0.0.0/16",
        "EnableDnsHostnames": True,
        "EnableDnsSupport": True,
    })


def test_flow_logs_enabled():
    app = cdk.App()
    stack = NetworkStack(app, "TestNetworkStack",
                         env=cdk.Environment(account="123456789012", region="us-east-1"))
    template = Template.from_stack(stack)

    # Assert Flow Logs resource exists
    template.resource_count_is("AWS::EC2::FlowLog", 1)


def test_nat_gateway_count():
    app = cdk.App()
    stack = NetworkStack(app, "TestNetworkStack",
                         env=cdk.Environment(account="123456789012", region="us-east-1"))
    template = Template.from_stack(stack)

    # 1 NAT Gateway as configured
    template.resource_count_is("AWS::EC2::NatGateway", 1)
```

```bash
# Run tests
pytest tests/
```

---

## References

- [CDK documentation](https://docs.aws.amazon.com/cdk/v2/guide/)
- [CDK API reference (Python)](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [CDK Patterns (L3 constructs)](https://cdkpatterns.com/)
- [cdk-nag (security rules)](https://github.com/cdklabs/cdk-nag)
---

← [Previous: CloudFormation](./cloudformation.md) | [Home](../../README.md) | [Next: Terraform on AWS →](./terraform-on-aws.md)
