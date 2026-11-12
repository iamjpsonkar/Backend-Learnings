← [Previous: GCP IAM](./README.md) | [Home](../../README.md) | [Next: Service Accounts →](./service-accounts.md)

---

# GCP IAM Basics

Cloud IAM controls who (identity) can do what (role) on which resource (resource). Every GCP API call is authorized by IAM.

---

## Core Concepts

| Concept | Description | AWS Equivalent |
|---------|-------------|----------------|
| **Principal** | Who is accessing (user, group, service account, domain) | IAM principal |
| **Role** | Collection of permissions | IAM policy |
| **Binding** | Attaches a role to a principal on a resource | Policy attachment |
| **Policy** | Set of bindings on a resource | Resource policy |
| **Permission** | Atomic operation (e.g., `compute.instances.create`) | IAM action |

---

## Principal Types

| Principal | Format | Use Case |
|-----------|--------|----------|
| Google Account | `user:alice@example.com` | Human users |
| Service Account | `serviceAccount:sa-name@PROJECT.iam.gserviceaccount.com` | Applications, VMs |
| Google Group | `group:team@example.com` | Team-level access |
| Google Workspace domain | `domain:example.com` | All users in an org |
| `allAuthenticatedUsers` | Any authenticated Google account | Public-but-authenticated |
| `allUsers` | Anyone, no auth required | Fully public |

---

## Role Types

| Type | Description | Examples |
|------|-------------|---------|
| **Basic** | Coarse-grained legacy roles — avoid in production | `roles/viewer`, `roles/editor`, `roles/owner` |
| **Predefined** | Service-specific, maintained by Google | `roles/storage.objectViewer`, `roles/container.developer` |
| **Custom** | You define exact permissions | `roles/my-org.deploymentManager` |

**Best practice**: Always use predefined roles over basic roles. Basic `roles/editor` grants write access to almost all services.

---

## Common Predefined Roles

```bash
# List all predefined roles for a service
gcloud iam roles list \
    --filter="name:roles/storage" \
    --format="table(name,title)"

# View permissions in a role
gcloud iam roles describe roles/storage.objectAdmin \
    --format="json(includedPermissions)"
```

| Service | Roles |
|---------|-------|
| Compute Engine | `roles/compute.viewer`, `roles/compute.instanceAdmin.v1`, `roles/compute.networkAdmin` |
| Cloud Storage | `roles/storage.objectViewer`, `roles/storage.objectCreator`, `roles/storage.objectAdmin`, `roles/storage.admin` |
| BigQuery | `roles/bigquery.dataViewer`, `roles/bigquery.dataEditor`, `roles/bigquery.jobUser`, `roles/bigquery.admin` |
| GKE | `roles/container.viewer`, `roles/container.developer`, `roles/container.admin`, `roles/container.clusterAdmin` |
| Cloud SQL | `roles/cloudsql.viewer`, `roles/cloudsql.client`, `roles/cloudsql.admin` |
| Secret Manager | `roles/secretmanager.secretAccessor`, `roles/secretmanager.secretVersionManager`, `roles/secretmanager.admin` |
| Cloud Run | `roles/run.viewer`, `roles/run.invoker`, `roles/run.developer`, `roles/run.admin` |

---

## Managing IAM Policies

```bash
PROJECT="my-app-prod-123456"

# Grant a role to a user
gcloud projects add-iam-policy-binding $PROJECT \
    --member="user:alice@example.com" \
    --role="roles/compute.viewer"

# Grant a role to a group
gcloud projects add-iam-policy-binding $PROJECT \
    --member="group:platform-team@example.com" \
    --role="roles/container.developer"

# Grant a role to a service account
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:my-app@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Remove a role binding
gcloud projects remove-iam-policy-binding $PROJECT \
    --member="user:alice@example.com" \
    --role="roles/compute.viewer"

# Get the full IAM policy for a project
gcloud projects get-iam-policy $PROJECT \
    --format="json"

# Get IAM policy in YAML (easier to read)
gcloud projects get-iam-policy $PROJECT \
    --format="yaml(bindings)"

# Set the entire IAM policy from a file (replaces existing policy — careful!)
gcloud projects set-iam-policy $PROJECT policy.json
```

---

## Resource-Level IAM

IAM can be applied at the resource level (not just project).

```bash
# Grant access to a specific Cloud Storage bucket
gcloud storage buckets add-iam-policy-binding gs://my-bucket \
    --member="serviceAccount:my-app@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Grant access to a specific secret
gcloud secrets add-iam-policy-binding my-secret \
    --project=$PROJECT \
    --member="serviceAccount:my-app@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Grant access to a specific BigQuery dataset
bq add-iam-policy-binding \
    --member="serviceAccount:analyst@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer" \
    $PROJECT:my_dataset

# Grant access to a specific Pub/Sub topic
gcloud pubsub topics add-iam-policy-binding my-topic \
    --member="serviceAccount:publisher@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"
```

---

## IAM Conditions

Conditions restrict when a role binding is effective.

```bash
# Grant access only during business hours (UTC)
gcloud projects add-iam-policy-binding $PROJECT \
    --member="user:contractor@example.com" \
    --role="roles/compute.instanceAdmin.v1" \
    --condition='expression=request.time.getHours("UTC")>=9 && request.time.getHours("UTC")<=17 && request.time.getDayOfWeek("UTC")>=1 && request.time.getDayOfWeek("UTC")<=5,title=BusinessHoursOnly'

# Grant access only to resources with a specific tag
gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:deploy@$PROJECT.iam.gserviceaccount.com" \
    --role="roles/compute.instanceAdmin.v1" \
    --condition='expression=resource.matchTag("env","production"),title=ProductionOnly'
```

---

## Custom Roles

```bash
# Create a custom role from scratch
gcloud iam roles create DeploymentManager \
    --project=$PROJECT \
    --title="Deployment Manager" \
    --description="Can deploy to GKE and update Cloud Run services" \
    --permissions="container.clusters.get,container.clusters.list,run.services.update,run.services.get" \
    --stage=GA

# Create from a YAML file
cat <<EOF > custom-role.yaml
title: "App Deployer"
description: "Deploy applications to GKE and Cloud Run"
stage: "GA"
includedPermissions:
  - container.clusters.get
  - container.clusters.list
  - container.operations.get
  - run.services.update
  - run.services.get
  - run.services.list
  - artifactregistry.repositories.downloadArtifacts
EOF

gcloud iam roles create AppDeployer \
    --project=$PROJECT \
    --file=custom-role.yaml

# Update a custom role (add permissions)
gcloud iam roles update AppDeployer \
    --project=$PROJECT \
    --add-permissions="clouddeploy.releases.create"

# List custom roles
gcloud iam roles list \
    --project=$PROJECT \
    --format="table(name,title,stage)"
```

---

## Audit Logging (Who Did What)

```bash
# Enable Data Access audit logs (charges apply)
# Set via: gcloud projects set-iam-policy with auditConfigs
cat <<EOF > audit-policy-patch.json
{
  "auditConfigs": [
    {
      "service": "storage.googleapis.com",
      "auditLogConfigs": [
        {"logType": "DATA_READ"},
        {"logType": "DATA_WRITE"}
      ]
    },
    {
      "service": "secretmanager.googleapis.com",
      "auditLogConfigs": [
        {"logType": "DATA_READ"}
      ]
    }
  ]
}
EOF

# Query audit logs in Cloud Logging
gcloud logging read \
    'protoPayload.serviceName="storage.googleapis.com" AND
     protoPayload.methodName="storage.objects.get" AND
     severity=INFO' \
    --project=$PROJECT \
    --limit=20 \
    --format="json"
```

---

## References

- [IAM overview](https://cloud.google.com/iam/docs/overview)
- [Predefined roles](https://cloud.google.com/iam/docs/understanding-roles)
- [IAM conditions](https://cloud.google.com/iam/docs/conditions-overview)
- [Custom roles](https://cloud.google.com/iam/docs/creating-custom-roles)

---

← [Previous: GCP IAM](./README.md) | [Home](../../README.md) | [Next: Service Accounts →](./service-accounts.md)
