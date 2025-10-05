# EcoStation CGR — Contact‑Graph Routing for LEO‑LEO Meshes

## 0) TL;DR

A minimal DTN router for LEO constellations using Contact Graph Routing (CGR):

* **Store–carry–forward** model with precomputed **contact windows** between nodes.
* Builds a **temporal contact graph** and finds the **minimum‑ETA** path.
* **Improvement included:** optional **K alternative routes** by accounting for **residual capacity** after each found path.
* **Input:** a `contacts.csv` describing link windows and resources.

---

## 1) Context & Rationale: DTN + CGR

**Why DTN?** Space networks (LEO, cislunar, interplanetary) suffer intermittent connectivity and variable latency. Conventional IP breaks when a link isn’t available. DTN (Delay/Disruption Tolerant Networking) stores bundles and forwards them when a window opens.

**What is CGR?** Contact Graph Routing is **schedule‑aware**: if we know in advance when links exist, we can compute routes that respect **time** and **capacity** constraints. Each contact (a link available within `[t_start, t_end]`) becomes a vertex in a temporal graph. An edge exists if one contact can follow another in time. The path cost is **ETA** (Earliest Time of Arrival).

**Reality in LEO.** Windows are short, topology changes quickly, and both ISL (inter‑satellite links) and downlinks appear/disappear. CGR models this precisely because it reasons over a **contact plan**.

---

## 2) What this project provides (at a glance)

* A working **MVP** capable of: (a) computing the best path (K=1) minimizing ETA; (b) producing **K plausible routes** by consuming capacity on used contacts.
* **Inputs:** `contacts.csv` with `id, from, to, t_start, t_end, owlt_s, rate_bps, setup_s, residual_bytes`.
* **Outputs:** a structured summary indicating whether a route was found and, if so, the path’s ETA, latency, hop count, and the sequence of contacts (or a list of K routes).

> Goal of the MVP: enable rapid experiments to **measure ETA, hops, and congestion effects** in LEO meshes without modeling full queueing or MAC details.

---

## 3) How it fits LEO system simulations

* **Windows** come from a **contact plan** (derived from TLE/ephemerides and the planned ISLs/downlinks). The MVP reads it as CSV.
* **Physical latency** is captured by **OWLT** (one‑way light time), which can be precomputed or approximated per contact.
* **Capacity** is represented via `rate_bps` and `residual_bytes`.
* **Downlinks & ISL** are both just contacts: SAT–GS or SAT–SAT.
* **Expiry/TTL** can restrict routes that arrive too late.

This abstraction makes it easy to **plug** into broader simulations and to compare strategies fairly.

---

## 4) Included improvements & why they matter

1. **Capacity‑aware pruning.** Discards contacts that cannot carry the bundle in the remaining window. This reflects real LEO contention.
2. **K routes via capacity consumption.** After finding the best path, the used contacts’ residual capacity is **reduced**, revealing **alternative realistic routes** for the next iterations.

**Why this approach?**

* Reproduces congestion effects **without** full queue models.
* Incremental and simple to integrate into existing **simulation pipelines**.

---

## 5) Current status vs. what we’re aiming for

**Current status**

* CGR (K=1) using a temporal Dijkstra‑style expansion with checks for window, capacity, and optional expiry.
* **K>1** via residual‑capacity consumption to obtain diversified alternatives.
* CLI‑friendly I/O ready for demos and dashboards.

**What we’re seeking next (roadmap)**

* **True K‑shortest** (e.g., Yen) to complement the capacity‑consumption heuristic.
* **Service classes / priorities** aligned with the Bundle Protocol.
* **Partial‑window consumption** (fractional use of a contact’s duration).
* **Edge/Node‑disjoint options** and fast reconvergence with ban lists.
* **Backlog modeling** per node and per‑link remaining volume.
* **Benchmarking harness** to compare against a “vanilla CGR” baseline on identical contact plans.

---

## 6) Glossary — What each thing is

* **Contact:** A time‑bounded opportunity to transmit between two nodes (`from → to`) with given setup time, rate, and residual capacity.
* **Contact plan:** The full schedule of all contacts over the simulation horizon.
* **OWLT (one‑way light time):** Propagation delay for the contact (distance / c).
* **ETA (Earliest Time of Arrival):** Arrival time at the destination when following a given path.
* **Residual capacity (`residual_bytes`):** Remaining bytes that can still be transmitted on a contact.
* **Setup time (`setup_s`):** Per‑contact overhead before payload transmission can begin.
* **K routes:** A set of alternative feasible paths produced either by true K‑shortest algorithms or by iteratively consuming capacity.
* **TTL / Expiry:** Upper bound on how late a bundle may arrive.

---

## 7) Data model (CSV)

Minimal schema expected by the MVP:

```text
# id, from, to, t_start, t_end, owlt_s, rate_bps, setup_s, residual_bytes
```

> Any generator producing this schema (from TLEs, planners, or synthetic scenarios) can be used to feed the router.

---

## 8) Evaluation & success criteria

* **Baseline parity:** Match a standard CGR implementation on feasibility and minimum ETA for K=1 under identical contact plans.
* **Added value for K>1:** Provide **diverse** alternatives that reflect capacity contention and path competition.
* **Scalability:** Maintain acceptable performance on constellation‑scale contact plans.
* **Traceability:** Each route should be explainable via its contacts and per‑hop timing.

---

## 9) Responsible use & scope

This MVP is intended for **simulation and research**. It doesn’t model security, regulatory constraints, or lower‑layer behavior (MAC/PHY). For mission‑critical systems, additional validation and safety mechanisms are required.

---

## 10) CGR — Full feature breakdown (what it includes)

**Core:**

* **Temporal contact graph:** nodes are contacts (time‑bounded links), edges connect time‑compatible contacts.
* **ETA‑optimal path (K=1):** earliest‑arrival routing with OWLT + setup overhead.
* **Capacity awareness:** checks residual bytes and effective throughput within each window; prunes infeasible contacts.
* **TTL/expiry filtering:** discards paths arriving after the bundle deadline.
* **Bidirectional handling:** treats ISL and downlink/uplink uniformly as directed contacts.
* **Contact setup time:** modeled per hop before data transfer.

**Enhanced options (our add‑ons):**

* **K alternatives via residual‑capacity consumption:** after a found route, we reduce capacity on used contacts to surface realistic alternates.
* **(Planned) K‑shortest algorithms:** e.g., Yen/Eppstein for diversity with formal guarantees.
* **(Planned) Disjointness policies:** node‑disjoint / edge‑disjoint variants to improve robustness.
* **(Planned) Service classes:** priorities and pre‑emption consistent with DTN/Bundle Protocol profiles.
* **(Planned) Partial‑window usage:** proportional consumption of time/capacity when splitting across windows.

**Outputs and KPIs:**

* Per route: **ETA**, **total latency**, **hop count**, **contacts used**, **bottleneck rate**, **consumed capacity**.
* For K>1: diversity metrics (path overlap %), incremental ETA, and feasibility notes.

---

## 11) Collision/Conflict analysis — what we compute and what we show

**Goal:** ensure the planned transmissions don’t collide or over‑commit shared resources.

**Computed checks:**

* **Contact overlap conflicts:** two flows attempting to use the **same contact window** beyond residual capacity.
* **Node‑radio contention:** concurrent contacts exceeding a node’s **transceiver concurrency** (e.g., 1 link at a time).
* **Setup‑time clashes:** overlapping setup periods that delay or invalidate a hop.
* **TCA proximity flags (optional):** mark contacts occurring near **closest‑approach** events where pointing or safety constraints might throttled links.
* **Downlink ground‑station contention:** simultaneous downlinks competing for the same GS antenna.

**What the analysis shows:**

* A **conflict table** listing: window IDs, nodes involved, time span, type (capacity, radio, GS), and severity.
* **Timeline view** (Gantt‑like): windows as bars; conflicts highlighted; selected route overlaid.
* **Per‑node heatmap**: utilization vs. time to spot hot spots.
* **Capacity ledger**: before/after residual bytes for each contact used by the route.

**Why it matters:** it validates that a route is not only time‑feasible but also **resource‑feasible**, and it explains failures (e.g., "no route due to GS contention at 12:41–12:43").

---

## 12) The `.html` report — purpose and contents

**Objective:** offer a **single, shareable dashboard** to inspect a scenario, compare the **baseline CGR** with our **improved approach**, and understand **why** a path was (or wasn’t) found.

**The HTML shows:**

* **Scenario overview:** nodes, time horizon, number of contacts, policy toggles (TTL, K, disjointness, radio concurrency).
* **Contact plan explorer:** searchable table + timeline to filter by node, link type (ISL/downlink), and time.
* **Route visualizer:**

  * **Timeline overlay** of the chosen path with per‑hop OWLT, setup, and transfer intervals.
  * **Map panel** (if enabled) to display ground tracks / GS locations and hop sequence.
* **K‑routes comparator:** side‑by‑side cards with ETA, hops, bottleneck, overlap %, and a sparkline timeline.
* **Conflict audit:** tables/plots described above to reveal capacity/radio/GS contention and residual‑capacity changes.
* **Export buttons:** download JSON/CSV of selected routes and the conflict log for reproducible tests.

**Intended use:**

* Quickly **defend design choices** ("our variant reduces ETA by X% under contention") during reviews.
* **Debug** failed routes by inspecting constraint violations.
* **Benchmark** improvements on identical contact plans.

> If you want, I can wire the current CLI outputs to this HTML template so it renders automatically after each run (no code walkthrough needed in the README; just a `make report`).

