# Frontend, Mobile, and Client Performance

Client performance spans loading, parsing, execution, rendering, interaction,
memory, battery, network variability, and backend latency. Optimize for real
devices and real sessions at the 75th percentile and beyond, not only a fast
developer machine.

## Delivery and loading

- Set a route-level budget for HTML, CSS, JavaScript, fonts, images, and data.
- Send useful HTML early and stream when the framework supports it safely.
- Inline only truly critical CSS and defer noncritical styles.
- Code-split by route and capability, not into excessive tiny requests.
- Tree-shake and remove duplicate libraries, polyfills, locales, and source
  artifacts from production bundles.
- Preload only resources certainly needed soon; excessive hints compete with
  critical downloads.
- Use immutable hashed assets and correct shared-cache policy.

## Images, video, and fonts

- Select modern formats from measured quality and compatibility.
- Resize and provide responsive variants instead of sending display-independent
  originals.
- Do not lazy-load the above-the-fold largest content element.
- Reserve dimensions to prevent layout shift.
- Subset fonts, reduce families and weights, and choose display behavior.
- Adapt video bitrate and resolution to network and viewport.

## JavaScript and interaction

- Ship less JavaScript; execution and memory matter after download.
- Break long main-thread tasks and yield to high-priority interactions.
- Move suitable CPU work to workers without excessive cloning.
- Virtualize large lists and incrementally render results.
- Batch DOM reads and writes to avoid forced layout.
- Prefer compositor-friendly animations.
- Debounce or throttle high-frequency work based on product semantics.
- Remove listeners, timers, observers, and retained trees when views unmount.

## Rendering strategy

Choose static generation, server rendering, streaming, client rendering, or
islands per route. Server rendering can improve initial content but adds server
cost and hydration work. Measure time to useful content and interaction, not
only first bytes.

## Client data

- Deduplicate in-flight requests and cache with explicit freshness.
- Prefetch likely next actions under network and data-use budgets.
- Use optimistic updates only with reconciliation and failure UX.
- Paginate and incrementally synchronize large datasets.
- Avoid retry storms when many installed clients reconnect.
- Version offline state and migrate it incrementally.

## Mobile-specific strategies

- Measure startup, frame time, jank, memory, battery, thermal state, and network.
- Defer nonessential SDK initialization.
- Reduce bridge and serialization crossings in hybrid applications.
- Batch background sync and respect platform scheduling.
- Store appropriately sized media and clear bounded caches.
- Test low-memory termination, offline behavior, and slow radio transitions.

## Real-user monitoring

Segment by device class, application version, geography, connection, route, and
experience while protecting privacy and cardinality. Compare lab and field data;
lab tests diagnose reproducibly, while field data captures real variability.

## Sources

- [Web Vitals](https://web.dev/articles/vitals)
- [Optimizing long tasks](https://web.dev/articles/optimize-long-tasks)
- [HTTP caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching)
