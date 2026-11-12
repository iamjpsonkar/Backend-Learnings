# Assets

Static assets for the Docker practice platform.

---

## Directory Structure

```
assets/
├── diagrams/          # Architecture diagrams (PNG, SVG, draw.io)
├── screenshots/       # Lab screenshots and expected output images
└── icons/             # Service icons for documentation
```

---

## Diagrams

Place architecture diagrams here. Recommended tools:
- [draw.io](https://app.diagrams.net/) — free, exports to SVG/PNG
- [Excalidraw](https://excalidraw.com/) — hand-drawn style
- Mermaid (inline in Markdown) — version-controlled diagrams

### Naming convention
```
diagrams/
  platform-overview.png         # Full platform architecture
  network-topology.svg          # Docker network diagram
  lab-aws-localstack.png        # Per-lab diagrams
  observability-stack.png       # LGTM stack
```

---

## Screenshots

Document expected lab outputs for reference:
```
screenshots/
  lab-aws-localstack/
    s3-bucket-list.png
    dynamodb-scan.png
  grafana-dashboard.png
  traefik-dashboard.png
```

---

## Icons

Service icons in 64x64 PNG format for use in documentation and dashboards.

Source: Official vendor icon packs (check license before use).
