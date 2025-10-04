# EcoStation CGR — Routing con Contact Graphs para mallas LEO-LEO

## 0) TL;DR

Este repo implementa un enrutador DTN minimalista para constelaciones **LEO** basado en **Contact Graph Routing (CGR)**:

* Modelo **store–carry–forward** con **ventanas de visibilidad** (contactos) entre nodos.
* Construimos un **grafo temporal de contactos** y buscamos la **ruta de menor ETA** (tiempo de llegada) con **Dijkstra temporal**.
* **Mejora incluida**: `--k N` rutas por **consumo de capacidad** (`residual_bytes`) tras cada ruta encontrada → alternativas realistas en mallas LEO.
* Datos de entrada: `data/contacts.csv` (id, from, to, t_start, t_end, owlt, rate, setup, residual_bytes).

---

## 1) Origen y fundamento: DTN + CGR

**¿Por qué DTN?** En redes espaciales (LEO, cislunar, interplanetario) la conectividad es **intermitente** y la latencia variable. IP clásico falla cuando el enlace no está disponible. **DTN** (Delay/Disruption Tolerant Networking) usa **bundles** que se almacenan y reenvían cuando hay ventana de enlace.

**¿Qué es CGR?** **Contact Graph Routing** es un algoritmo **schedule-aware**: asume que conocemos por adelantado un **plan de contactos** (qué enlaces existirán y **cuándo**). Con esa agenda, calcula rutas que **respetan tiempo y capacidad**:

* Cada **contacto** (enlace disponible dentro de [t_start, t_end]) se trata como un **vértice** en un grafo temporal.
* Existe una arista A→B si **temporalmente encadenan** (el bundle llega al nodo de B **antes** de que acabe su ventana de transmisión).
* El coste es la **ETA** (Earliest Time of Arrival) acumulada: establecimiento + transmisión + **OWLT** (one-way light time).

**Realidad LEO-LEO.** En LEO las ventanas son **cortas**, la topología **cambia rápido** y los ISL (enlaces intersatélite) y downlinks aparecen/desaparecen. CGR modela esto con precisión porque opera sobre un **calendario** de enlaces.

---

## 2) ¿Qué implementa este proyecto?

**Objetivo:** disponer de un **MVP funcional** para: (a) calcular **la mejor ruta** (k=1) minimizando ETA y (b) obtener **K rutas** plausibles aplicando **consumo de capacidad**.

### 2.1. Entradas

* `contacts.csv` con filas: `id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes`.
* Parámetros CLI: `--src`, `--dst`, `--t0` (epoch sim), `--bytes` (tamaño del bundle), `--expiry` (TTL opcional) y `--k` (número de rutas deseadas).

### 2.2. Salidas

* JSON con: `found`, y **o** bien una ruta (`eta`, `latency`, `hops`, `contacts`) **o** una lista `routes` para K>1.

### 2.3. Núcleo algorítmico

1. **ETA por contacto**: si el bundle llega al nodo origen del contacto en `t_in`:

   * `start_tx = max(t_in, t_start)`
   * `tx_time = bundle_bytes / rate_bps`
   * `finish = start_tx + setup_s + tx_time`
   * **Descarta** si `finish > t_end` o `residual_bytes < bundle_bytes`.
   * `ETA = finish + owlt`.
2. **Dijkstra temporal (k=1)**: vértices=contactos; se expande por **ETA mínima** hasta alcanzar `dst`.
3. **K rutas (consumo)**: tras cada ruta, se **reduce** `residual_bytes` de los contactos usados y se recomputa. Esto fuerza rutas alternativas realistas cuando un enlace se “satura”.

---

## 3) Relación con la simulación de sistemas LEO

* **Ventanas**: provienen de un **contact plan** (derivado de TLE/efemérides y de la planificación de ISL y pases a estaciones). Aquí se inyecta como CSV.
* **Latencia física**: **OWLT** ≈ distancia/c. En CSV ya llega pre-calculado o aproximado.
* **Capacidad**: tasa × duración efectiva (menos overhead). El MVP la modela como `residual_bytes` por contacto.
* **Downlinks/ISL**: ambos son contactos SAT–GS o SAT–SAT.
* **Expiración**: `--expiry` opcional restringe rutas que superen `t0 + expiry`.

Esta abstracción permite **probar rápidamente** estrategias de enrutado, medir **latencia**, **nº de saltos** y el efecto de **congestión** por consumo.

---

## 4) Mejoras incluidas y por qué

1. **Poda por capacidad.** En LEO, el solape de ventanas + múltiples flujos puede saturar enlaces; descartamos contactos donde el bundle **no cabe**.
2. **K rutas por consumo.** Tras hallar la mejor ruta, **consumimos** capacidad de sus contactos → la **siguiente** búsqueda revela **caminos alternativos** de forma estable y simple.

**Ventajas de esta aproximación** (para un MVP):

* Reproduce efectos de **congestión** sin modelar colas complejas.
* Es incremental y fácil de integrar en pipelines de simulación.

---

## 5) Estado actual vs. meta de mejora

**Estado actual**

* CGR (k=1) con **Dijkstra temporal** + validaciones de ventana/capacidad/expiración.
* `--k N` con **consumo de capacidad** para obtener múltiples rutas.
* CLI y salida JSON listas para demos y tableros.

**Meta de mejora**

* **Yen K-shortest** (rutas genuinamente alternativas sin depender de consumo).
* **Prioridades/TTL** conforme a Bundle Protocol (clases de servicio).
* **Consumo parcial** en ventanas (cuando el bundle usa una fracción del tiempo).
* **Edge/Node-disjoint** con listas de **bans** y reconvergencia rápida.
* **Backlog/colas** por nodo y volumen residual por tramo.

---

## 6) Tour del código

* `include/contact.h` — Estructuras: `Contact`, `Label`, `Route`, `CgrParams`, `Routes`.
* `include/cgr.h` — APIs: índices de vecindad, `cgr_best_route` (k=1), `cgr_k_routes` (K con consumo).
* `include/csv.h` — Carga de contactos desde CSV.
* `include/heap.h` — Min-heap de etiquetas por ETA.
* `src/csv.c` — Parser CSV robusto a espacios/comentarios.
* `src/heap.c` — Min-heap O(log n) para Dijkstra.
* `src/cgr.c` — Cálculo de ETA por contacto, Dijkstra temporal, consumo de capacidad y K rutas.
* `src/main.c` — CLI: parsea flags, invoca algoritmo, imprime JSON.
* `data/contacts.csv` — Escenario de ejemplo con varias ramas 100→…→200.

---

## 7) Data model (CSV)

```
# id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes
0, 100, 1, 0, 60, 0.020, 5000000, 0.2, 300000000
```

**Campos**

* `id`: identificador del contacto.
* `from`/`to`: IDs de nodos (SAT/GS).
* `t_start`/`t_end`: ventana en segundos.
* `owlt_s`: one-way light time.
* `rate_bps`: tasa de transmisión.
* `setup_s`: retardo de establecimiento.
* `residual_bytes`: capacidad aún disponible para el bundle.

---

## 8) Build y ejecución

```
make            # compila
make run        # demo (k=3) sobre data/contacts.csv
./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k 3
```

**Salida** (ejemplo):

```json
{"found":true,"routes":[
  {"eta":123.456789,"latency":123.456789,"hops":3,"contacts":[0,1,2]},
  {"eta":132.110000,"latency":132.110000,"hops":3,"contacts":[3,4,5]},
  {"eta":140.900000,"latency":140.900000,"hops":3,"contacts":[6,7,8]}
]}
```

---

## 9) Validación y pruebas rápidas

* **Sanidad temporal**: ninguna transmisión termina tras `t_end`.
* **Consumo**: la 2ª/3ª ruta debe cambiar si la 1ª agotó un enlace.
* **Sensibilidad**: reduce `rate_bps` o `residual_bytes` para observar rutas más largas y latencia mayor.
* **Realismo**: genera `contacts.csv` desde un plan de contactos real (simulador) y vuelve a ejecutar.

---

## 10) Limitaciones y supuestos

* Capacidad modelada como `residual_bytes` por contacto (sin colas intermedias).
* Sin prioridad/clase de servicio.
* OWLT dada; no se recalcula dinámicamente.
* No hay solapado de bundles ni fragmentación.

---

## 11) Glosario mínimo

* **DTN**: arquitectura tolerante a retrasos/cortes; opera con **bundles**.
* **CGR**: enrutado consciente de **agendas de contacto**; minimiza ETA.
* **OWLT**: latencia unidireccional por distancia/c.
* **ISL**: enlace intersatélite (SAT–SAT).
* **ETA**: tiempo de llegada estimado.

---

## 12) Roadmap técnico (próximos pasos)

* Añadir `yen.{h,c}` con K-shortest real (spurs + bans) manteniendo causalidad temporal.
* Introducir **prioridades** y **TTL** en el coste y en la poda.
* Modelar **consumo parcial** por tramo y **backlog** por nodo.
* Exportar **trazas** para análisis (CSV) y hooks para tablero web.
