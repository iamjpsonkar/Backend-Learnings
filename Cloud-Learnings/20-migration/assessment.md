← [Previous: Migration Overview](./README.md) | [Home](../README.md) | [Next: Lift & Shift →](./lift-and-shift.md)

---

# Migration Assessment

A migration assessment answers three questions: **what do you have**, **what should you do with it**, and **can you afford it**. Get these wrong and you migrate the wrong things in the wrong order at the wrong cost.

---

## Discovery

### Automated Discovery with AWS Application Discovery Service

```bash
# Deploy Discovery Agent on on-premises servers
# Download from AWS console or S3
wget https://s3-us-west-2.amazonaws.com/aws-discovery-agent.us-west-2/linux/latest/aws-discovery-agent.tar.gz
tar -xzf aws-discovery-agent.tar.gz
sudo bash install -r us-east-1 -k ACCESS_KEY -s SECRET_KEY

# Start collection
aws discovery start-data-collection-by-agent-ids \
    --agent-ids $AGENT_ID

# After 2+ weeks of data collection, export
aws discovery start-export-task \
    --export-data-format CSV \
    --filters name=resourceType,values=SERVER,condition=EQUALS

EXPORT_ID=$(aws discovery describe-export-tasks \
    --query 'exportsInfo[0].exportId' --output text)

aws discovery describe-export-tasks \
    --export-ids $EXPORT_ID \
    --query 'exportsInfo[0].configurationsDownloadUrl' --output text
```

### Server Inventory via AWS Migration Hub

```bash
# Import existing inventory via CSV
# Required columns: ExternalId, VMware.MoRefId or IPAddress, ServerInfo.HostName
# Optional: CPUCount, RAMGiB, OSName, OSVersion

aws migrationhub-config get-home-region

# Import servers
aws discovery start-import-task \
    --name "on-prem-inventory-$(date +%Y%m%d)" \
    --import-url s3://migration-bucket/inventory.csv

# Check import status
aws discovery describe-import-tasks \
    --filters name=importTaskId,values=$IMPORT_TASK_ID
```

### Application Dependency Mapping

```bash
# View discovered network connections
aws discovery list-configurations \
    --configuration-type CONNECTION \
    --filters name=sourceServerIpAddress,values=10.0.1.50,condition=EQUALS \
    --query 'configurations[*].{Source:sourceServerIpAddress,Dest:destinationServerIpAddress,Port:destinationPort}'

# Export dependency graph to Migration Hub
aws discovery associate-configuration-items-to-application \
    --application-configuration-id $APP_ID \
    --configuration-ids $SERVER_ID_1 $SERVER_ID_2 $SERVER_ID_3
```

### Manual Discovery Questionnaire

```yaml
# server-discovery-template.yaml
server:
  hostname: ""
  ip_address: ""
  os: ""
  cpu_cores: 0
  ram_gb: 0
  disk_gb: 0

application:
  name: ""
  business_owner: ""
  technical_owner: ""
  tier: ""             # web / app / db / batch / middleware
  criticality: ""      # critical / high / medium / low

dependencies:
  inbound_from: []     # list of app/server names
  outbound_to: []      # list of app/server names
  external_apis: []    # third-party services

characteristics:
  last_modified_year: 0
  codebase_language: ""
  has_hardcoded_ips: false
  uses_local_filesystem: false
  windows_specific_features: false   # COM, DCOM, MSMQ, etc.
  requires_gpu: false
  license_type: ""     # perpetual / subscription / open-source

sla:
  uptime_requirement: ""   # e.g., "99.9%"
  maintenance_window: ""
  rpo_hours: 0
  rto_hours: 0
```

---

## 6Rs Mapping

Apply the 6Rs decision framework to each application after discovery.

```python
from dataclasses import dataclass
from enum import Enum


class MigrationStrategy(str, Enum):
    RETIRE = "Retire"
    RETAIN = "Retain"
    REHOST = "Rehost"
    REPLATFORM = "Replatform"
    REPURCHASE = "Repurchase"
    REFACTOR = "Refactor"


@dataclass
class ApplicationProfile:
    name: str
    business_value: int      # 1-5 (1=low, 5=critical)
    technical_complexity: int  # 1-5 (1=simple, 5=very complex)
    cloud_compatibility: int   # 1-5 (1=incompatible, 5=cloud-native ready)
    end_of_life: bool
    has_saas_replacement: bool
    strategic_importance: bool


def determine_migration_strategy(app: ApplicationProfile) -> MigrationStrategy:
    """
    Heuristic 6Rs classifier. Override with human judgment for edge cases.
    """
    if app.end_of_life:
        return MigrationStrategy.RETIRE

    if app.has_saas_replacement and not app.strategic_importance:
        return MigrationStrategy.REPURCHASE

    if app.cloud_compatibility >= 4:
        if app.technical_complexity <= 2:
            return MigrationStrategy.REHOST
        return MigrationStrategy.REPLATFORM

    if app.business_value >= 4 and app.strategic_importance:
        return MigrationStrategy.REFACTOR

    if app.technical_complexity >= 4 or app.cloud_compatibility <= 2:
        return MigrationStrategy.RETAIN

    return MigrationStrategy.REPLATFORM


# Example portfolio assessment
applications = [
    ApplicationProfile("legacy-billing", 5, 4, 2, False, False, True),
    ApplicationProfile("old-reporting", 2, 3, 3, True, False, False),
    ApplicationProfile("hr-system", 3, 2, 3, False, True, False),
    ApplicationProfile("order-api", 5, 3, 4, False, False, True),
    ApplicationProfile("inventory-svc", 4, 2, 4, False, False, False),
]

portfolio_map = {
    app.name: determine_migration_strategy(app)
    for app in applications
}

for name, strategy in portfolio_map.items():
    print(f"{name:25s} → {strategy.value}")
# legacy-billing            → Refactor
# old-reporting             → Retire
# hr-system                 → Repurchase
# order-api                 → Replatform
# inventory-svc             → Rehost
```

### 6Rs Decision Tree

```
Is the app still needed?
    No → Retire
    Yes ↓

Is there a good SaaS replacement?
    Yes + not strategic → Repurchase
    No ↓

Is cloud compatibility high (4-5)?
    Yes + low complexity → Rehost
    Yes + medium complexity → Replatform
    No ↓

Is it strategically important with high business value?
    Yes → Refactor
    No ↓

Is it too complex or incompatible to move now?
    Yes → Retain
    No → Replatform
```

---

## TCO Analysis

### AWS Migration Evaluator

```bash
# Export on-premises cost data
# Migration Evaluator agent collects: CPU util, RAM util, storage, network

# After assessment period, request business case
aws migrationevaluator create-assessment \
    --assessment-targets '[{
        "assessmentTargetName": "datacenter-east",
        "configurations": {
            "vcenterBasedCollection": {
                "vcCenterConfigurationList": [{
                    "vcCenterHostname": "vcenter.internal",
                    "vcCenterUsername": "readonly-svc",
                    "vcCenterPassword": "SECRET"
                }]
            }
        }
    }]'
```

### Manual TCO Model

```python
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class OnPremCosts:
    """Annual on-premises costs in USD."""
    server_hardware: float          # amortized capex (3-5 year lifecycle)
    network_hardware: float
    datacenter_space_power: float   # rack space + power + cooling
    os_licenses: float
    database_licenses: float
    other_software_licenses: float
    staff_operations: float         # FTE cost for infrastructure ops
    maintenance_contracts: float
    backup_storage: float


@dataclass
class CloudCosts:
    """Annual cloud costs in USD."""
    compute: float          # EC2/ECS/EKS
    storage: float          # EBS/S3/EFS
    database: float         # RDS/DynamoDB
    network: float          # data transfer + load balancers
    support: float          # Business/Enterprise support plan
    migration_tooling: float  # MGN, DMS, Snow devices (one-time amortized)


@dataclass
class TCOResult:
    on_prem_annual: float
    cloud_annual: float
    migration_cost_one_time: float
    savings_annual: float
    payback_months: float
    three_year_savings: float


def calculate_tco(
    on_prem: OnPremCosts,
    cloud: CloudCosts,
    migration_cost_one_time: float,
    cloud_discount_pct: float = 0.30,  # Savings Plans / RIs
) -> TCOResult:
    on_prem_annual = sum([
        on_prem.server_hardware,
        on_prem.network_hardware,
        on_prem.datacenter_space_power,
        on_prem.os_licenses,
        on_prem.database_licenses,
        on_prem.other_software_licenses,
        on_prem.staff_operations,
        on_prem.maintenance_contracts,
        on_prem.backup_storage,
    ])

    cloud_base = sum([
        cloud.compute,
        cloud.storage,
        cloud.database,
        cloud.network,
        cloud.support,
        cloud.migration_tooling,
    ])
    cloud_annual = cloud_base * (1 - cloud_discount_pct)

    savings_annual = on_prem_annual - cloud_annual
    payback_months = (migration_cost_one_time / savings_annual * 12) if savings_annual > 0 else float("inf")
    three_year_savings = (savings_annual * 3) - migration_cost_one_time

    return TCOResult(
        on_prem_annual=round(on_prem_annual, 0),
        cloud_annual=round(cloud_annual, 0),
        migration_cost_one_time=migration_cost_one_time,
        savings_annual=round(savings_annual, 0),
        payback_months=round(payback_months, 1),
        three_year_savings=round(three_year_savings, 0),
    )


# Example
result = calculate_tco(
    on_prem=OnPremCosts(
        server_hardware=120_000,
        network_hardware=30_000,
        datacenter_space_power=80_000,
        os_licenses=40_000,
        database_licenses=150_000,
        other_software_licenses=25_000,
        staff_operations=350_000,
        maintenance_contracts=60_000,
        backup_storage=15_000,
    ),
    cloud=CloudCosts(
        compute=180_000,
        storage=20_000,
        database=60_000,
        network=15_000,
        support=25_000,
        migration_tooling=10_000,
    ),
    migration_cost_one_time=200_000,
    cloud_discount_pct=0.35,
)

print(f"On-prem annual:    ${result.on_prem_annual:>10,.0f}")
print(f"Cloud annual:      ${result.cloud_annual:>10,.0f}")
print(f"Annual savings:    ${result.savings_annual:>10,.0f}")
print(f"Migration cost:    ${result.migration_cost_one_time:>10,.0f}")
print(f"Payback period:    {result.payback_months:>9.1f} months")
print(f"3-year net savings:${result.three_year_savings:>10,.0f}")
```

---

## Migration Readiness

### Migration Readiness Assessment (MRA)

```yaml
# migration-readiness-scorecard.yaml
# Score each area 1-5 (1=not ready, 5=fully ready)

organizational:
  executive_sponsorship: 0      # C-suite buy-in and budget approval
  cloud_strategy_defined: 0     # Target architecture documented
  change_management: 0          # Training and communication plan
  budget_approved: 0            # Funding secured for 18+ months

technical:
  application_inventory_complete: 0   # All apps discovered and profiled
  dependency_mapping_done: 0          # Network/data deps documented
  target_architecture_designed: 0     # AWS landing zone / account structure
  security_controls_defined: 0        # IAM, network, encryption baseline
  monitoring_strategy: 0              # Observability toolchain selected

operational:
  runbooks_exist: 0             # Ops procedures documented
  dr_plan_defined: 0            # RTO/RPO targets set and validated
  support_model: 0              # Cloud support tier + escalation path
  team_cloud_skills: 0          # AWS certs / hands-on experience

scoring:
  # 1-2: Not ready — address gaps before starting
  # 3:   Partially ready — proceed with high-risk mitigation
  # 4-5: Ready — proceed with standard controls
```

### Wave Planning

```python
from dataclasses import dataclass
from typing import List


@dataclass
class Application:
    name: str
    strategy: str
    business_value: int      # 1-5
    migration_complexity: int  # 1-5
    dependencies: List[str]  # application names


def plan_waves(apps: List[Application]) -> dict:
    """
    Wave planning heuristic:
    - Wave 1: Low complexity, low dependencies (prove the model)
    - Wave 2: Medium complexity, some dependencies (build confidence)
    - Wave 3: High value / high complexity (strategic workloads)
    - Wave 4: Complex interdependencies (tackle after 1-3)
    """
    waves = {1: [], 2: [], 3: [], 4: []}

    for app in apps:
        if app.strategy == "Retire":
            continue

        dep_count = len(app.dependencies)
        complexity = app.migration_complexity

        if complexity <= 2 and dep_count == 0:
            waves[1].append(app.name)
        elif complexity <= 3 and dep_count <= 2:
            waves[2].append(app.name)
        elif app.business_value >= 4 and complexity <= 4:
            waves[3].append(app.name)
        else:
            waves[4].append(app.name)

    return waves


apps = [
    Application("static-website", "Rehost", 2, 1, []),
    Application("batch-reports", "Replatform", 2, 2, []),
    Application("auth-service", "Replatform", 4, 3, ["user-db"]),
    Application("order-api", "Refactor", 5, 4, ["inventory", "payment", "user-db"]),
    Application("legacy-erp", "Retain", 3, 5, ["billing", "hr", "reporting"]),
]

wave_plan = plan_waves(apps)
for wave, app_list in wave_plan.items():
    if app_list:
        print(f"Wave {wave}: {', '.join(app_list)}")
```

---

## References

- [AWS Migration Hub](https://docs.aws.amazon.com/migrationhub/latest/ug/)
- [AWS Application Discovery Service](https://docs.aws.amazon.com/application-discovery/latest/userguide/)
- [AWS Migration Evaluator](https://aws.amazon.com/migration-evaluator/)
- [Migration Readiness Assessment](https://aws.amazon.com/migration-acceleration-program/)

---

← [Previous: Migration Overview](./README.md) | [Home](../README.md) | [Next: Lift & Shift →](./lift-and-shift.md)
