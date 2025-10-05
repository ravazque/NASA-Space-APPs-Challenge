# EcoStation CGR — Collision Prediction & CGR Routing in LEO Constellations

---

> ⚠️ **Important notice**
>
> * The **collision prediction service that is not embedded in `index.html`** relies on an **external API** to operate.
> * The **CGR component** runs on a **realistic simulated scenario**. Inside its folder you can start it by running: `make run`.
>
> **Quick demo / visualization:** open `index.html` (at the repo root) directly in your browser. You can also publish the repo with **GitHub Pages** and access it via URL.
>
> **Program viewer from Github:** [Our interface](https://ravazque.github.io/NASA-Space-APPs-Challenge/)

---

> ⚙️ **NOTE**
> 
> In some cases, when the number of satellites is reduced, the interface (in beta phase) may lose the route even if the simulation only has one. The transmitter and receiver must be reassigned so that the interface can reconnect all the information.

---

## 1) What is this project?

A functional prototype for **simulation and visualization** of LEO networks that integrates:

* **Collision prediction** (detection of satellite close approaches with risk metrics and time-to-closest-approach).
* **CGR (Contact Graph Routing)** with enhancements to **maximize the chance of finding a route** and to propose **K alternative routes** when possible.
* An **interactive 3D interface** (CesiumJS) with control panels to tune parameters, view RF/optical links, active routes, and alerts.

The goal is to enable **rapid experiments** and exploration of routing decisions under different **contact window** and **capacity** conditions.

---

## 2) How to run and view the visualization

**Option A: Local (fastest)**

1. Download or clone the repository.
2. Open **`index.html`** in your browser (double‑click or `File → Open`). No backend is required for the basic visualization.

**Option B: GitHub Pages (optional)**

1. In GitHub, go to **Settings → Pages**.
2. Publish branch `main` (root folder).
3. Access the visualization through the generated GitHub Pages URL.

**CGR & Prediction services (simulated/remote):**

* Inside the corresponding folder, run **`make run`** to start the CGR scenario and related services. The standalone collision predictor that is **not** part of `index.html` uses an **external API**.

---

## 3) Repository layout

* **`index.html`** — 3D UI, control panels, live links and route visualization.
* **`cgr/`** — **Contact Graph Routing** logic (CGR), K alternatives, and capacity/window handling.
* **`orbitalAnalysis/`** — utilities and data for **contact windows** and orbital analysis.

---

## 4) Collision prediction (how it works, no code)

The prediction module evaluates **satellite pairs** to detect **hazardous approaches** within a configurable threshold (**Minimum Safe Distance**):

* **Detection:** computes **instant distance** and projects the **Distance at Closest Approach (DCA)** over a short horizon.
* **Displayed metrics:**

  * **Risk probability** (a heuristic combining how close they will be, whether they are converging, and how long until the closest point).
  * **Relative speed** (km/s) between satellites.
  * **TCA** (*Time to Closest Approach*): time estimated until the minimum distance.
  * **DCA** (*Distance at Closest Approach*): predicted minimum separation.
* **Objective:** provide **situational awareness** and context for evaluating routes/links. This is a **simulation‑oriented** approach and is **not** a replacement for operational **Conjunction Assessment** (CDMs).
* **Note:** when used outside the web visualization, the predictor **relies on an external API** (see the notice at the top).

---

## 5) Enhanced CGR routing (functional view)

**CGR** (Contact Graph Routing) models the network with **temporal contacts**: each viable link has a window `[t_start, t_end]`, latency (OWLT), setup time, and **capacity**. The router computes the path that minimizes **ETA** (Earliest Time of Arrival).

**Key improvements in this project:**

1. **Capacity‑aware pruning:** discards contacts that cannot carry the **bundle** within the effective window, avoiding infeasible routes.
2. **K alternative routes:** after the best path is found, compute **K** feasible alternatives for resilience and load balancing.
3. **Smart fallback:** if the enhanced mode cannot find a path, **extend the planning horizon** and/or fall back to **classic CGR** to maximize success probability.

**K Routes (quick explainer)**

* **What:** compute not only the best route, but the **top‑K** next best candidates.
* **Why:** improves **resilience**; if the main route degrades, alternatives are available.
* **Impact:** larger **K** costs more **compute**, but raises **robustness** and choice diversity.

---

## 6) How the visualization (`index.html`) works

Opening `index.html` presents a 3D globe with the constellation and three functional areas:

### Left panel — Configuration

* **Number of Satellites:** constellation size.
* **Orbital Altitude (km):** LEO range (160–2000 km).
* **Simulation Speed:** accelerates the simulation clock.
* **Routing Mode:** *CGR Enhanced*, *Classic*, or *Auto*.
* **Recalculation Frequency (s):** how often (sim seconds) links and routes are recomputed.
* **Planning Horizon (min):** how far into the future to build the contact graph.
* **Bundle Size (MB):** DTN bundle volume; affects **contact viability** (setup/capacity/window).
* **K Routes:** number of alternative routes to compute.
* **Legend & Actions:** quick source/destination shuffle, pause/resume, reset camera.

### Right panel — Metrics

* **Active Algorithm:** current CGR mode.
* **Active Links / Calculation Time:** dynamic link count and compute cost.
* **Simulation Time:** current simulated time (moved here from the top bar).
* **Collision Prevention:** safety threshold and **collision alerts** with probability, relative speed, TCA, and DCA.
* **Active Route:** end‑to‑end latency (**E2E**) and **hop count**.
* **Alternative K‑Yen Routes:** compact summary of additional candidates.

### Bottom panel — System information

* **Contact Windows:** upcoming/active windows for relevant node pairs.
* **Collision Alerts:** detailed alerts with risk levels and supporting metrics.

**Link colors:**

* **RF (radiofrequency):** orange.
* **Optical (non‑RF):** blue (subject to LEO conditions and realistic distance thresholds for intra/inter‑plane links).

---

## 7) Goal & scope

* **Goal:** enable **interactive experiments** and route comparisons in LEO networks with realistic windows/latencies and collision‑risk awareness.
* **Scope (MVP):** **educational/experimental** focus. Not a replacement for operational systems or space‑traffic CDMs.

---

## 8) Strengths & introduced improvements

**Strengths**

* **No backend** needed for visualization: open and use.
* CGR with **capacity awareness** and **K routes**: more realism for congestion and alternatives.
* Clear panels and **live‑tunable** parameters.

**Notable improvements**

* **Fallback** to “always try to find” a viable route (if it exists within the horizon).
* Integrated **collision alerts** with operationally meaningful metrics.
* In‑UI explanations for **K routes**, **bundle**, **horizon**, and **recalculation**.

---

## 9) Why the contact plan matters (minimal data)

CGR is powered by a **contact plan** (e.g., CSV) with minimal fields: `from`, `to`, `t_start`, `t_end`, `owlt_s`, `rate_bps`, `setup_s`, `residual_bytes`. With this, one can reproduce useful LEO temporal behavior for routing **without** dropping to PHY/MAC details.

---

## 10) Suggested roadmap

* Formal **K‑shortest paths** (Yen/Eppstein) with complexity control.
* **Disjoint routing** (node/edge) and fast **reconvergence** on failures.
* **Service classes/priorities** (Bundle Protocol) and QoS policies.
* Validation with parametric scenarios and time‑series.

---

## 11) Credits & responsible use

Educational prototype based on **DTN/CGR** ideas applied to LEO. Usage is **experimental** and **does not** replace operational **Conjunction Assessment** or mission tools.

---

### Links

* **Repository:** [https://github.com/ravazque/NASA-Space-APPs-Challenge](https://github.com/ravazque/NASA-Space-APPs-Challenge)
* **Visualization:** open `index.html` (repo root) or publish with GitHub Pages to access via URL.
