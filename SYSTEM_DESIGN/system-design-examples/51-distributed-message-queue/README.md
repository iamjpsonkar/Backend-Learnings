# Distributed Message Queue

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Append ordered records to partitions, replicate them, let consumer groups track offsets, and retain/replay data.

Quantify peak load, latency, availability, retention, accuracy, and consistency before choosing components.

## Data and interfaces

Topic, Partition, Record(offset,key,value,time), Replica, ConsumerGroupOffset(group,partition,offset,epoch).

Use idempotent writes, cursor-based reads, explicit versions, and schema-controlled events.

## Architecture

```text
producer -> partition leader -> replica quorum -> log; consumers -> fetch -> process -> commit offset
```

Partition by key, batch/compress writes, use sequential logs and sparse indexes, elect leaders with consensus metadata, and rebalance consumers with epochs.

## Failure, security, and observability

Acknowledge by durability policy, fence old producers/leaders, use idempotent producer sequences, protect ACLs, and monitor under-replication, lag, disk, and rebalance time.

Use least privilege, encryption, tenant isolation, audit logs, capacity limits, dashboards, and actionable alerts.

## Key trade-off

More partitions increase parallelism but cost metadata, open files, and rebalance overhead; ordering exists only within a partition.
