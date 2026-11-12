# Frontend and Network Optimization

Frontend performance is the user-visible result of server response, network
delivery, resource discovery, browser parsing, JavaScript execution, rendering,
and interaction handling. Measure both laboratory and real-user behavior.

## Core Web Vitals

The current Core Web Vitals are:

| Metric | What it represents | Good at the 75th percentile |
| --- | --- | ---: |
| Largest Contentful Paint (LCP) | Main-content loading | 2.5 seconds or less |
| Interaction to Next Paint (INP) | Interaction responsiveness | 200 ms or less |
| Cumulative Layout Shift (CLS) | Visual stability | 0.1 or less |

Lab tools provide reproducible diagnosis. Field data represents real devices,
networks, caches, sessions, and user interactions. Use both.

## Improve loading and LCP

- Reduce server time to first byte for the initial document.
- Make the LCP resource discoverable in initial HTML.
- Do not lazy-load the above-the-fold LCP image.
- Give critical resources appropriate priority.
- Compress and correctly size images; use responsive sources.
- Remove unnecessary redirects and serial request chains.
- Serve static assets close to users through a CDN when appropriate.
- Cache immutable versioned assets for a long duration.
- Inline only genuinely critical CSS and defer noncritical work.

Preloading everything creates contention. Preload only measured critical
resources.

## Improve responsiveness and INP

- Break long main-thread tasks into smaller work units.
- Reduce JavaScript shipped, parsed, and executed.
- Defer noncritical third-party scripts.
- Avoid expensive synchronous layout and layout thrashing.
- Render only visible or necessary interface regions.
- Move suitable CPU-heavy work to Web Workers.
- Keep event handlers focused and update the interface promptly.
- Prefer progressive rendering over blocking the entire result.

Track input delay, handler processing, and presentation delay separately when
diagnosing a slow interaction.

## Improve visual stability and CLS

- Set dimensions or aspect ratios for images, video, embeds, and advertisements.
- Reserve space for content loaded later.
- Avoid inserting content above existing visible content.
- Use transform animations instead of layout-changing properties when possible.
- Test fallback fonts and web-font metric differences.
- Keep skeleton and final layouts geometrically compatible.

## JavaScript and bundle strategy

- Remove unused dependencies and duplicate packages.
- Prefer platform features over large libraries for small needs.
- Split by meaningful routes or features, not into excessive tiny chunks.
- Lazy-load code that is not required for the initial experience.
- Analyze bundle composition and set size budgets in CI.
- Avoid hydrating static content that needs no client interaction.
- Consider server rendering or prerendering when it improves critical delivery.

Code splitting can move delay from startup to interaction. Preload a chunk when
user intent predicts it will soon be needed.

## Network and API delivery

- Minimize sequential client-server round trips.
- Use compression for suitable text payloads.
- Use HTTP caching validators for revalidation.
- Keep payload schemas focused and paginate large collections.
- Reuse connections and avoid unnecessary cross-origin handshakes.
- Design graceful behavior for slow, offline, and failed requests.

## Performance budgets

Useful frontend budgets include:

- JavaScript, CSS, image, and font bytes by route
- Number of critical-path requests
- LCP resource discovery delay
- Main-thread long-task time
- Core Web Vitals at the 75th percentile
- Third-party script cost
- Performance on representative low-end devices and networks

Review budgets in CI and field monitoring. A fast developer laptop on a local
network is not a representative user environment.

See the official [Web Vitals guidance](https://web.dev/articles/vitals) and
[LCP optimization guide](https://web.dev/articles/optimize-lcp).
