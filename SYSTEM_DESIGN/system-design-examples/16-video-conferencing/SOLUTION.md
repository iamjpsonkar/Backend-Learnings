# Complete Solution: Video Conferencing

[Problem brief](README.md) | [All examples](../README.md)

## 1. Requirements

Create/join rooms, publish microphone/camera/screen, subscribe to participants,
mute/kick/moderate, adapt quality to network/device conditions, reconnect after
failure, and optionally record. Support browsers/mobile through WebRTC.

Targets: 1 million concurrent participants, typical room size 6, join p99 below 5
seconds, media availability 99.99%, interactive round-trip latency below 300 ms,
and graceful degradation before disconnection.

This design uses an SFU (Selective Forwarding Unit), not MCU composition. PSTN,
webinar transcoding, and end-to-end encrypted recording are separate extensions.

## 2. Capacity estimation

Assume each participant publishes 1.5 Mbps average and receives five 1 Mbps streams:

```text
global SFU ingress = 1M * 1.5 Mbps = 1.5 Tbps
global SFU egress  = 1M * 5 Mbps   = 5 Tbps
rooms              = 1M / 6       ~= 167K
```

Egress, packet processing, encryption, and concurrent transports dominate.
Provision each SFU below 60-70% network/CPU so it can absorb layer switches and
node evacuation. TURN relay can double network traversal for affected users.

## 3. Control-plane model and APIs

```text
Room(id, tenant, region, policy, state, created_at)
Participant(room_id, user_id, session_id, role, state, joined_at)
MediaTrack(track_id, session_id, kind, source, codec, layers)
Recording(id, room_id, state, object_prefix, consent_version)
```

```text
POST /v1/rooms                         -> room
POST /v1/rooms/{id}/join               -> signed join token + signaling endpoint
POST /v1/rooms/{id}/recordings         -> recording state
WebSocket signaling: join, offer/answer, ICE candidate, publish, subscribe,
                     layer update, mute, leave, reconnect
```

Join token includes room, participant, role, allowed publish/subscribe actions,
region, expiry, nonce, and signature.

## 4. Architecture

```text
client -> global edge -> regional signaling/room service
   |                         |
   | WebRTC/DTLS-SRTP        +-> SFU allocator -> SFU cluster
   |        \                      |       |
 STUN      TURN relay -------------+       +-> recorder bot -> object storage
                                             |
                                     cascaded SFU in other region

control: identity, room policy, moderation, topology, recording
media: encrypted RTP/RTCP packets through SFU/TURN
```

Keep signaling/control separate from media. Signaling outage should not interrupt
already established RTP, though it blocks topology changes/reconnect.

## 5. Step-by-step workflow

### Join

1. Client authenticates and requests join.
2. Room service checks policy/capacity and returns short-lived signed token plus
   regional signaling/STUN/TURN information.
3. Signaling validates token nonce and registers participant session.
4. Allocator selects SFU by region, zone, codec capability, CPU, bandwidth, room
   affinity, and evacuation state.
5. Client and SFU exchange WebRTC offer/answer and ICE candidates.
6. ICE tries direct UDP to SFU, then TCP/TLS TURN fallback if required.
7. DTLS establishes keys; SRTP media starts and participant state becomes joined.

### Publish and subscribe

1. Publisher negotiates codecs and sends simulcast/SVC layers for camera.
2. SFU validates track permission and indexes RTP SSRC/track/layers.
3. Subscribers express visible participants and device/network constraints.
4. SFU selects one suitable layer per subscriber/track and forwards packets.
5. RTCP feedback drives retransmission, keyframe requests, and congestion control.
6. Active-speaker/layout changes alter subscriptions without republishing source.

## 6. SFU allocation logic

```text
function chooseSfu(room, participant):
    candidates = sfus.filter(
        region=participant.preferredRegion,
        healthy=true, acceptingRooms=true,
        codecs contains participant.requiredCodec)

    if room.assignedSfu exists and room.assignedSfu in candidates:
        if room.assignedSfu.hasHeadroom(participant): return room.assignedSfu

    candidates = candidates.filter(hasNetworkAndCpuHeadroom)
    require not empty else CapacityUnavailable
    return minBy(candidates, sfu ->
        localityPenalty(sfu, participant) +
        normalizedCpu(sfu) + normalizedEgress(sfu) + roomSplitPenalty(sfu, room))
```

Keep a small room on one SFU for low latency. Large rooms use multiple SFUs and a
forwarding/cascade topology rather than exceeding one node's capacity.

## 7. Subscription and layer logic

```text
function updateSubscription(subscriber, track, estimate):
    budget = min(estimate.availableBitrate,
                 subscriber.deviceDecodeBudget,
                 subscriber.policyBudget)
    priority = layout.priority(track)      // screen > active speaker > thumbnails
    layer = highestLayerWithin(track.layers, budgetFor(priority))

    current = subscriber.layerFor(track)
    if layer > current and estimate.stableFor(UPGRADE_HYSTERESIS):
        requestKeyframeIfNeeded(track, layer)
        switchAtDecodableBoundary(subscriber, track, layer)
    else if layer < current:
        switchDownImmediately(subscriber, track, layer)
```

Upgrade slowly and downgrade quickly to avoid oscillation/rebuffer. Pause offscreen
video before sacrificing audio or screen share.

## 8. Packet forwarding core

```text
function onRtpPacket(publisher, packet):
    track = trackIndex.lookup(publisher.session, packet.ssrc)
    if missing or not authorized(publisher, track): drop

    updateIngressStats(track, packet)
    for subscriber in track.subscribers:
        if packet.layer != subscriber.selectedLayer: continue
        rewritten = rewriteSequenceTimestampAndSsrc(packet,
                                                     subscriber.translationState)
        if subscriber.pacer.canEnqueue(rewritten):
            subscriber.pacer.enqueue(rewritten)
        else:
            dropAccordingToMediaPriority(rewritten)
```

Each outbound stream needs sequence/timestamp translation when layers switch.
Pacing prevents bursts; bounded queues drop video packets instead of growing delay.

## 9. Reconnect and migration

Client stores room/session resume token and last topology version. On network change
or gateway loss it reconnects, obtains new ICE transport, and republishes tracks.
SFU failure usually requires media renegotiation; room service assigns replacement
and clients rejoin. Preserve participant identity but create new transport epoch so
late packets/signaling from old connection are ignored.

Planned draining stops new rooms, migrates/reconnects rooms gradually, then closes
remaining sessions after grace period.

## 10. Large rooms and multi-region

- One regional ingress SFU per publisher group.
- Cascade selected tracks once between regions, not one copy per remote subscriber.
- Forward active speakers/screen globally; thumbnails may use lower layers.
- For webinars, presenters publish while audience receives via cascaded SFU or
  low-latency streaming/CDN path.
- Room topology version prevents loops and stale cascade connections.

## 11. Recording

A recorder joins as authorized bot, subscribes to tracks, writes segmented media
plus timeline metadata, and uploads to object storage. Composition/transcoding runs
asynchronously. Recording state and participant consent are visible; recording
failure never interrupts live media.

## 12. Failure handling

| Failure | Behavior |
| --- | --- |
| Signaling instance fails | Existing media continues; clients reconnect for control changes |
| SFU fails | Room assigns replacement; clients reconnect with new transport epoch |
| TURN unavailable | Direct clients continue; affected restricted networks retry another TURN |
| Packet loss/congestion | NACK/FEC where configured, layer downgrade, pause low-priority video |
| Region impairment | New joins use other region; existing rooms migrate only when necessary |
| Recorder fails | Restart recorder from segment boundary and mark gap; live room continues |
| Bad codec/device | Negotiate common codec or transcode only at explicit expensive boundary |
| Control database unavailable | Existing room/media continue; new room/admin changes degrade |

## 13. Security and privacy

- Short-lived signed single-use join tokens and role-based media permissions.
- DTLS-SRTP media, TLS signaling, authenticated TURN credentials, mTLS services.
- Prevent participant from spoofing another track/SSRC or subscribing outside room.
- Rate-limit joins/signaling, cap tracks/bitrates, and isolate tenants/rooms.
- Recording requires policy/consent, encryption, retention, access audit, and purge.
- SFU normally sees decryptable media. Insertable-stream E2EE hides content from
  SFU but complicates recording, moderation, and key management.
- Avoid sensitive SDP/token/media data in logs.

## 14. Observability

Measure join success/time by phase, ICE candidate path, TURN usage, signaling
latency, active rooms/participants/tracks, SFU CPU/packet rate/ingress/egress,
RTT/jitter/loss, audio concealment, freezes, bitrate/layer switches, keyframe/NACK,
reconnects, room migrations, cascade health, and recording gaps.

Use client quality telemetry plus SFU metrics; server packet delivery alone cannot
prove the user heard/seen usable media. Load tests must generate real RTP behavior,
not only signaling requests.

## 15. Implementation path

1. **MVP:** small regional rooms, signaling, WebRTC SFU, STUN/TURN, audio/video,
   basic mute and quality metrics.
2. **Reliability:** redundant signaling/SFU, reconnect epochs, drain, recording,
   moderation, capacity-aware allocation, and fault injection.
3. **Quality/scale:** simulcast/SVC, congestion/layer policy, active speaker,
   large-room SFU topology, cascades, and automated capacity.
4. **Global/privacy:** regional placement/failover, consent/retention, optional
   E2EE model, abuse controls, chaos and disaster drills.

## 16. Final design

Use separate stateless signaling/control services and regional WebRTC SFUs. Publish
simulcast/SVC once, select and forward layers per subscriber with bounded pacing,
and cascade only needed tracks across regions. The central invariant is that every
media/control action is bound to the current authenticated participant and
transport/topology epoch; stale sessions cannot publish or alter a recovered room.
