← [Previous: Incident Response](./incident-response.md) | [Home](../README.md) | [Next: Security Checklist →](./security-checklist.md)

---

# Supply Chain Security

Supply chain attacks target the build process, dependencies, and artifacts rather than the running application. SolarWinds, XZ Utils, and Log4Shell demonstrated that a single compromised upstream component can affect thousands of organizations.

---

## Attack Surface

```
Source code   →   Build system   →   Artifacts   →   Deployment   →   Runtime
     │                 │                  │                │               │
  Typosquatting    Poisoned CI       Tampered image   Unverified      Vulnerable
  Malicious deps   OIDC token theft  Registry abuse   provenance      dependency
  Abandoned pkgs   Build server      Image tag         No SBOM        0-day
                   compromise        mutation
```

---

## SLSA Framework (Supply-chain Levels for Software Artifacts)

SLSA defines four levels of build integrity guarantees:

| Level | Requirements | Threat mitigated |
|-------|-------------|-----------------|
| **SLSA 1** | Build process documented; SBOM generated | Accidental mistakes |
| **SLSA 2** | Hosted build service; signed provenance | Tampered build steps |
| **SLSA 3** | Hardened build platform; isolated builds | Compromised build host |
| **SLSA 4** | Two-party review; hermetic builds | Insider threats |

---

## Image Signing with Cosign (Sigstore)

```bash
# Install cosign
brew install cosign

# Keyless signing (uses OIDC identity — no long-lived key needed)
# Works in GitHub Actions with GITHUB_TOKEN
cosign sign --yes \
    --rekor-url=https://rekor.sigstore.dev \
    ghcr.io/my-org/my-app@sha256:abc123def456

# Verify a signature
cosign verify \
    --certificate-identity=https://github.com/my-org/my-app/.github/workflows/release.yml@refs/heads/main \
    --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
    ghcr.io/my-org/my-app@sha256:abc123def456

# Attach SBOM to image
syft ghcr.io/my-org/my-app:latest -o cyclonedx-json > sbom.json
cosign attach sbom \
    --sbom sbom.json \
    ghcr.io/my-org/my-app@sha256:abc123def456

# Verify SBOM is attached
cosign download sbom ghcr.io/my-org/my-app@sha256:abc123def456

# Sign with a key pair (for air-gapped environments)
cosign generate-key-pair   # Creates cosign.key + cosign.pub
cosign sign --key cosign.key ghcr.io/my-org/my-app:latest
cosign verify --key cosign.pub ghcr.io/my-org/my-app:latest
```

### GitHub Actions: Sign on Push

```yaml
# .github/workflows/release.yml (relevant steps)
jobs:
  build-and-sign:
    runs-on: ubuntu-latest
    permissions:
      id-token: write    # Required for keyless signing
      packages: write
      contents: read

    steps:
      - uses: actions/checkout@v4

      - uses: docker/build-push-action@v5
        id: build
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          provenance: true    # Generates SLSA provenance attestation
          sbom: true          # Generates SBOM attestation

      - uses: sigstore/cosign-installer@v3

      - name: Sign image (keyless)
        run: |
          cosign sign --yes \
              --rekor-url=https://rekor.sigstore.dev \
              ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
        env:
          COSIGN_EXPERIMENTAL: "1"

      - name: Verify signature
        run: |
          cosign verify \
              --certificate-identity="${{ github.server_url }}/${{ github.repository }}/.github/workflows/release.yml@${{ github.ref }}" \
              --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
              ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
```

---

## Kubernetes: Enforce Image Signing (Policy)

```yaml
# Kyverno policy: require Cosign signature before deploying
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-signature
spec:
  validationFailureAction: Enforce
  background: false
  rules:
    - name: check-signature
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaces: [production, staging]
      verifyImages:
        - imageReferences:
            - "ghcr.io/my-org/*"
          attestors:
            - count: 1
              entries:
                - keyless:
                    subject: "https://github.com/my-org/my-app/.github/workflows/release.yml@refs/heads/main"
                    issuer: "https://token.actions.githubusercontent.com"
                    rekor:
                      url: https://rekor.sigstore.dev
```

---

## SBOM (Software Bill of Materials)

```bash
# Syft — generate SBOM from image or filesystem
brew install syft

# From a container image
syft ghcr.io/my-org/my-app:latest -o cyclonedx-json > sbom-cyclonedx.json
syft ghcr.io/my-org/my-app:latest -o spdx-json > sbom-spdx.json
syft ghcr.io/my-org/my-app:latest -o table          # Human-readable

# From filesystem (before build)
syft dir:. -o cyclonedx-json > sbom.json

# Scan SBOM for vulnerabilities with Grype
grype sbom:sbom-cyclonedx.json
grype sbom:sbom-cyclonedx.json --fail-on high

# Check SBOM completeness
# Key fields to verify:
# - All packages have version + license
# - Checksums present for all components
# - Supplier information included
jq '.components | length' sbom-cyclonedx.json
jq '[.components[] | select(.licenses == null)] | length' sbom-cyclonedx.json
```

---

## Dependency Pinning and Integrity

```bash
# Python — pin with hashes (prevents substitution attacks)
# Generate:
pip-compile --generate-hashes requirements.in -o requirements.txt

# Install with hash verification:
pip install --require-hashes -r requirements.txt

# Example locked requirement:
# django==4.2.7 \
#     --hash=sha256:89c8... \
#     --hash=sha256:1f3e...

# Node — package-lock.json enforces integrity
npm ci    # Strict: fails if package-lock.json and package.json are out of sync

# Check for typosquatting (packages with similar names to popular ones)
pip install pip-audit
pip-audit --requirement requirements.txt

# Detect abandoned packages (no updates > 2 years)
pip install pip-check-reqs
pip-check-reqs .

# Go — go.sum file verifies module checksums
go mod verify    # Verify all module checksums match go.sum
go mod tidy      # Remove unused deps
```

---

## Secure Build Practices

```dockerfile
# Dockerfile: reproducible, minimal, non-root
# Use digest pinning (not tags — tags can be mutated)
FROM python:3.12-slim@sha256:abc123def456...  # Pin to digest

WORKDIR /app

# Create non-root user before copying files
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Copy dependency files first (Docker layer cache)
COPY --chown=appuser:appgroup requirements.txt .

# Install with hash verification
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Copy application code
COPY --chown=appuser:appgroup src/ ./src/

# Drop to non-root
USER appuser

# Explicitly declare what the container does
ENTRYPOINT ["python", "-m", "uvicorn", "src.main:app"]
```

```bash
# Scan Dockerfile for security issues
trivy config Dockerfile
hadolint Dockerfile    # Dockerfile best-practices linter
docker run --rm -i hadolint/hadolint < Dockerfile
```

---

## Provenance Attestation (SLSA)

```bash
# GitHub Actions: slsa-github-generator (SLSA Level 3)
# .github/workflows/release.yml
```

```yaml
jobs:
  build:
    outputs:
      digests: ${{ steps.hash.outputs.digests }}
    steps:
      - name: Build artifact
        run: |
          make build
          sha256sum my-app-binary > checksums.txt

      - name: Output digest
        id: hash
        run: |
          DIGEST=$(sha256sum my-app-binary | base64 -w0)
          echo "digests=$DIGEST" >> $GITHUB_OUTPUT

  provenance:
    needs: [build]
    permissions:
      actions: read
      id-token: write
      contents: write
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v1.10.0
    with:
      base64-subjects: ${{ needs.build.outputs.digests }}
      upload-assets: true    # Uploads provenance to GitHub release

# Verify provenance
  verify:
    needs: [provenance]
    runs-on: ubuntu-latest
    steps:
      - uses: slsa-framework/slsa-verifier/actions/installer@v2.6.0
      - run: |
          slsa-verifier verify-artifact my-app-binary \
              --provenance-path my-app-binary.intoto.jsonl \
              --source-uri github.com/my-org/my-app \
              --source-tag ${{ github.ref_name }}
```

---

## References

- [SLSA Framework](https://slsa.dev/)
- [Sigstore / Cosign](https://docs.sigstore.dev/)
- [Syft (SBOM)](https://github.com/anchore/syft)
- [Grype (SBOM scanning)](https://github.com/anchore/grype)
- [CISA SBOM guidance](https://www.cisa.gov/sbom)
- [OpenSSF Scorecard](https://securityscorecards.dev/)

---

← [Previous: Incident Response](./incident-response.md) | [Home](../README.md) | [Next: Security Checklist →](./security-checklist.md)
