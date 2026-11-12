← [Previous: GCP Account Setup](./README.md) | [Home](../../README.md) | [Next: Projects →](./projects.md)

---

# gcloud CLI

`gcloud` is the primary command-line tool for Google Cloud. It manages authentication, projects, compute resources, and nearly every GCP service.

---

## Installation

```bash
# macOS — via Homebrew
brew install --cask google-cloud-sdk

# Linux (Debian/Ubuntu)
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | sudo tee /etc/apt/sources.list.d/google-cloud-sdk.list
sudo apt-get update && sudo apt-get install google-cloud-sdk

# Verify
gcloud version

# Update to latest
gcloud components update
```

---

## Authentication

```bash
# Interactive login (opens browser)
gcloud auth login

# Application Default Credentials (for SDK use in code)
gcloud auth application-default login

# Service account authentication (for CI/CD)
gcloud auth activate-service-account \
    --key-file=/path/to/service-account-key.json

# Verify active account
gcloud auth list

# Print current access token (for debugging)
gcloud auth print-access-token

# Revoke credentials
gcloud auth revoke user@example.com
```

---

## Configuration — Named Configs

Named configurations let you switch between projects, accounts, and regions instantly.

```bash
# Create a named configuration
gcloud config configurations create my-app-prod
gcloud config configurations create my-app-dev

# Activate a configuration
gcloud config configurations activate my-app-prod

# Set properties in the active config
gcloud config set project my-app-prod-123456
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
gcloud config set account user@example.com

# View current configuration
gcloud config list

# List all configurations
gcloud config configurations list

# Describe a specific configuration
gcloud config configurations describe my-app-prod

# Delete a configuration
gcloud config configurations delete my-app-dev
```

---

## Project Management

```bash
# Set default project
gcloud config set project PROJECT_ID

# Show current project
gcloud config get-value project

# List all accessible projects
gcloud projects list --format="table(projectId,name,projectNumber,lifecycleState)"

# Describe a project
gcloud projects describe PROJECT_ID

# Create a new project
gcloud projects create my-new-project-id \
    --name="My New Project" \
    --folder=FOLDER_ID  # Optional — place in a folder

# Delete a project (30-day grace period before permanent deletion)
gcloud projects delete PROJECT_ID
```

---

## Cloud Shell

Cloud Shell provides a browser-based terminal with gcloud pre-installed and authenticated.

```bash
# Key facts:
# - 5 GB persistent $HOME disk
# - Ephemeral VM (e2-small) provisioned per session
# - Access at: console.cloud.google.com → Activate Cloud Shell
# - Direct link: shell.cloud.google.com

# In Cloud Shell — gcloud is already authenticated to your account
gcloud auth list   # Shows your account

# Cloud Shell editor — full VS Code-based editor
# Access via the "Open Editor" button in Cloud Shell
```

---

## Useful Flags and Output Formats

```bash
# Output formats
gcloud compute instances list --format="json"
gcloud compute instances list --format="yaml"
gcloud compute instances list --format="table(name,status,zone)"
gcloud compute instances list --format="value(name)"  # Just the values, one per line
gcloud compute instances list --format="csv(name,status)"

# Filter results
gcloud compute instances list \
    --filter="status=RUNNING AND zone:us-central1"

# Sort
gcloud compute instances list \
    --sort-by=name

# Quiet mode (suppress prompts, useful in scripts)
gcloud compute instances delete my-vm --quiet

# Async (don't wait for long operations)
gcloud compute instances create my-vm \
    --image-family debian-12 \
    --image-project debian-cloud \
    --async

# Impersonate a service account (for testing)
gcloud compute instances list \
    --impersonate-service-account=sa-name@PROJECT_ID.iam.gserviceaccount.com
```

---

## Installing Additional Components

```bash
# List available components
gcloud components list

# Install kubectl (for GKE)
gcloud components install kubectl

# Install beta components
gcloud components install beta

# Install gsutil (Cloud Storage CLI)
gcloud components install gsutil
# Note: gsutil is being replaced by gcloud storage commands
```

---

## gcloud storage (Replacing gsutil)

```bash
# Copy files to/from GCS
gcloud storage cp ./local-file.txt gs://my-bucket/path/
gcloud storage cp gs://my-bucket/path/file.txt ./local-file.txt

# Recursive copy (sync a directory)
gcloud storage rsync ./dist gs://my-bucket/dist --recursive --delete-unmatched-destination-objects

# List bucket contents
gcloud storage ls gs://my-bucket/
gcloud storage ls --long gs://my-bucket/

# Create a bucket
gcloud storage buckets create gs://my-new-bucket \
    --location=us-central1 \
    --uniform-bucket-level-access

# Make a file publicly readable
gcloud storage objects update gs://my-bucket/file.txt \
    --add-acl-grant=entity=AllUsers,role=READER
```

---

## References

- [gcloud CLI documentation](https://cloud.google.com/sdk/gcloud)
- [gcloud cheat sheet](https://cloud.google.com/sdk/docs/cheatsheet)
- [Named configurations](https://cloud.google.com/sdk/docs/configurations)
- [Output formats](https://cloud.google.com/sdk/docs/scripting-gcloud)

---

← [Previous: GCP Account Setup](./README.md) | [Home](../../README.md) | [Next: Projects →](./projects.md)
