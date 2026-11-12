# Roadmap

---

## Current State (v1.0)

- 164 labs across 23 categories
- Docker Compose profiles for all major tool categories
- React dashboard with progress tracking
- FastAPI backend with SQLite persistence
- Lab runner with automated grading
- LocalStack (AWS), Azurite (Azure), GCP emulators
- Full observability stack (Prometheus, Grafana, Loki, Jaeger)
- Security tooling (Vault, Keycloak)
- CI/CD platform (Gitea, Woodpecker CI)

---

## Near-Term (v1.1)

### Lab Improvements
- [ ] Add solution walkthroughs for all labs (opt-in spoiler reveal)
- [ ] Video links for complex labs
- [ ] Difficulty ratings based on real user completion data
- [ ] Estimated time calibration from actual run data

### Platform
- [ ] `make export-progress` — export progress to JSON/PDF certificate
- [ ] Lab prerequisites auto-check (offer to run prerequisite labs first)
- [ ] `make lab-stats` — show completion rate and avg score per lab
- [ ] Offline mode indicator (detect when Docker Hub is unreachable)

### New Labs
- [ ] `04-docker/distroless-images` — build minimal secure images
- [ ] `05-kubernetes/gateway-api` — Kubernetes Gateway API
- [ ] `11-security/falco-runtime` — Falco runtime threat detection
- [ ] `13-cicd/tekton-pipelines` — Tekton on Kubernetes CI
- [ ] `12-observability/continuous-profiling` — Pyroscope/pprof

---

## Medium-Term (v1.2)

### AI/ML Ops Labs
- [ ] `labs/23-mlops/` — model serving, feature stores
- [ ] Ollama integration for local LLM labs
- [ ] Vector database lab (Qdrant, Weaviate)

### Platform Features
- [ ] Multi-user support (SQLite → PostgreSQL backend)
- [ ] Lab leaderboard (for classroom use)
- [ ] Webhook to notify Slack/Discord on lab completion
- [ ] Automated lab freshness validation (CI checks validate.sh still passes)

### More Cloud Emulation
- [ ] Spanner emulator (GCP)
- [ ] Azure Event Hubs emulator
- [ ] AWS ECS local (Finch / act)

---

## Long-Term (v2.0)

### Collaborative Features
- [ ] Shared lab environments (multiple users on one instance)
- [ ] Instructor mode (view student progress, unlock hints)
- [ ] Lab authoring UI (create labs from the dashboard)

### Extended Platforms
- [ ] DigitalOcean API emulator labs
- [ ] Cloudflare Workers local (Miniflare)
- [ ] Nomad + Consul labs (HashiCorp stack alternative to K8s)

### Assessment
- [ ] Timed challenge mode (solve production incident in 30 min)
- [ ] Automated competency badges
- [ ] PDF report export with lab completion details

---

## Contributing New Labs

To propose a new lab:
1. Check [LAB_INDEX.md](LAB_INDEX.md) to avoid duplicates
2. Create `labs/<category>/<lab-slug>/lab.yaml` using the schema
3. Write `README.md`, `validate.sh`, `grade.sh`
4. Submit a PR with `make validate-labs` output showing pass

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for full guidelines.

---

## Version History

| Version | Date | Highlights |
|---------|------|-----------|
| 1.0 | 2026-05 | Initial release, 164 labs, full platform |
