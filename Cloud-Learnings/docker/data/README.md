# Data Directory

Sample datasets, seed data, and backups for the Cloud-Learnings Lab Platform.

## Structure

```
data/
├── seed/            Sample seed data files (JSON, CSV, SQL)
├── sample-bills/    Fake cloud billing CSV datasets for FinOps labs
├── sample-logs/     Sample application log files for log analysis
├── sample-events/   Sample event payloads (JSON) for messaging labs
└── backups/         Database backup output directory (gitignored)
```

## Seed Data

Used by `./run.sh seed` to populate databases with sample records.

## Sample Bills

Fake cloud bill CSVs for FinOps simulation labs. These contain synthetic cost data modeled after real cloud billing exports.

See `sample-bills/README.md` for field descriptions.

## Sample Logs

Example application and access logs for log analysis practice.

## Sample Events

Example JSON event payloads for messaging and event-driven labs.

## Backups

The `backups/` directory stores database dumps created by `./run.sh backup`. These are excluded from git.
