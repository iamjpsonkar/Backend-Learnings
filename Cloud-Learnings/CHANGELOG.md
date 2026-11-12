# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Planned
- Cloud foundations (00-foundations, 01-cloud-fundamentals)
- Linux documentation (02-linux)
- Networking documentation (03-networking)
- Full AWS section expansion (05-aws all sub-sections)
- Azure, GCP, and other clouds
- Kubernetes, Terraform, Ansible
- CI/CD, Security, Observability, SRE, FinOps

---

## [Batch 1] — 2026-05-31

### Added
- Repository renamed from AWS-Learnings to **Cloud-Learnings**
- New root structure: CONTRIBUTING.md, LICENSE (MIT), CODE_OF_CONDUCT.md, SECURITY.md, CHANGELOG.md
- `.gitignore` with standard exclusions
- `.github/` — workflow files for link validation and Markdown linting
- `.github/ISSUE_TEMPLATE/` — bug report, content gap, new topic templates
- `.github/PULL_REQUEST_TEMPLATE.md`
- `05-aws/` directory with 14 sub-sections, README files, and migrated content
- `assets/images/aws/` with all images migrated from `src/`

### Migrated
- `docs/aws-overview.md` → `05-aws/README.md` (image refs updated)
- `docs/ec2.md` → `05-aws/04-compute/ec2.md` (image refs updated)
- `docs/s3.md` → `05-aws/05-storage/s3.md` (image refs updated)
- `docs/dns.md` → `05-aws/03-networking/route53.md` (image refs updated)
- `docs/system-manager.md` → `05-aws/11-management/systems-manager.md` (image refs updated)
- `src/aws/*.png` → `assets/images/aws/aws/`
- `src/ec2/*.png` → `assets/images/aws/ec2/`
- `src/s3/*.png` → `assets/images/aws/s3/`
- `src/dns/*.png` → `assets/images/aws/dns/`

### Removed
- Old `docs/` directory
- Old `src/` directory
- Old `INDEX.md`

---

## [Pre-Batch-1] — Prior commits

### Added
- Initial AWS documentation: overview, EC2, S3, DNS, Systems Manager
- Supporting images in `src/`
