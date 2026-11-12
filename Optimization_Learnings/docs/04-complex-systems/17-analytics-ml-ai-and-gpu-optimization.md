# Analytics, ML, AI, and GPU Optimization

Data and ML systems combine storage, preprocessing, communication, accelerator
memory, kernels, synchronization, and model quality. Optimize the pipeline, not
GPU utilization in isolation.

## Data pipeline

- Profile loading independently from model compute.
- Shard early and keep enough parallel readers to feed devices.
- Use compact, sequential, splittable formats.
- Prefetch and overlap input, host-to-device transfer, and compute.
- Pin host memory only when it improves transfer and fits memory budgets.
- Cache transformed data at the cheapest reusable stage.
- Move supported transformations into vectorized or device execution.
- Use synthetic input to prove whether input is the bottleneck.

## Training compute

- Increase batch size until utilization improves without violating convergence,
  memory, or latency goals.
- Use mixed precision with loss scaling and numerical validation.
- Fuse operators and compile stable graphs where supported.
- Use efficient tensor layouts and dimensions suited to accelerator kernels.
- Remove unnecessary gradient computation and synchronization.
- Accumulate gradients to reduce communication frequency when valid.
- Recompute activations to trade compute for memory when memory-bound.
- Profile kernels, launch gaps, memory bandwidth, and host stalls.

## Distributed training

- Optimize one device before scaling out.
- Prefer data parallelism until model size requires model or pipeline parallelism.
- Overlap collective communication with computation.
- Bucket small gradients and avoid unnecessary all-reduce operations.
- Keep workers balanced; one slow rank delays synchronous steps.
- Place workers and accelerators on high-bandwidth topology.
- Checkpoint asynchronously and test restart time.
- Measure scaling efficiency, not only total throughput.

## Inference optimization

- Batch dynamically with maximum queue delay.
- Quantize weights and activations with task-level quality evaluation.
- Distill, prune, or choose smaller models when quality budgets allow.
- Cache deterministic embeddings, prefixes, features, and responses with privacy
  and freshness controls.
- Compile and fuse stable serving graphs.
- Route requests by model, context size, latency class, and hardware capability.
- Use speculative or early-exit techniques only with measured quality and cost.
- Bound input, output, context, and generation lengths.

## Retrieval and recommendation

- Precompute embeddings and incremental features.
- Use approximate nearest-neighbor indexes with an explicit recall budget.
- Apply cheap candidate generation before expensive ranking.
- Limit feature fan-out and batch online feature reads.
- Separate freshness-critical features from slower stable features.
- Monitor popularity skew, cold items, and cache concentration.

## Analytics engines

- Partition and cluster around selective filters.
- Use column pruning, predicate pushdown, vectorization, and compression.
- Maintain statistics for cost-based optimization.
- Broadcast small dimensions and handle skewed joins adaptively.
- Incrementally process changed partitions rather than full history.
- Materialize frequent expensive aggregates with freshness objectives.

## Quality and economics

Report accuracy, recall, convergence, freshness, and safety beside throughput,
latency, accelerator hours, energy, and cost per training or inference unit.

## Sources

- [PyTorch performance tuning](https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide.html)
- [TensorFlow GPU performance analysis](https://www.tensorflow.org/guide/gpu_performance_analysis)
- [Spark SQL performance tuning](https://spark.apache.org/docs/latest/sql-performance-tuning)
- [CUDA C++ best practices](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
