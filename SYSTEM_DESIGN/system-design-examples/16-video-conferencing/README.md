# Video Conferencing

[Back to the 60-example catalog](../README.md)

**[Read the complete worked solution](SOLUTION.md)**

## Scope and requirements

Create rooms, connect participants, exchange audio/video/screen media, and support recording and moderation.

Set measurable availability and latency targets, estimate peak load and retained
data, and state the ordering and consistency guarantees explicitly.

## APIs and data model

HTTPS creates room tokens; WebSocket signaling negotiates transports; media uses WebRTC with short-lived credentials.

Room(id, policy, region); Participant(room, user, role, joined_at); recordings and chat are separate durable artifacts.

## High-level design

```text
client -> signaling -> regional SFU mesh -> participants; SFU -> recorder/object storage
```

Choose a nearby SFU, forward selected layers using simulcast/SVC, cap subscriptions by device capacity, and cascade SFUs for large or cross-region rooms.

## Reliability, security, and operations

Use ICE/TURN fallback, reconnect to a replacement SFU, rotate room keys, authorize every publish/subscribe action, and isolate media processes.

Track join success/time, RTT, jitter, packet loss, bitrate, freezes, SFU CPU/egress, reconnects, and recording gaps.

## Key trade-off

Mesh is simple for tiny calls; SFUs scale participants and preserve quality but add infrastructure cost and a media trust boundary.
