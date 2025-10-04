
# EcoStation CGR — Enrutamiento por Contact Graph para constelaciones LEO

## 1) De qué va esto (para qué sirve)

**EcoStation CGR** es un motor de **enrutamiento DTN** (Delay/Disruption Tolerant Networking) pensado para **constelaciones LEO**. En estas redes, los satélites y estaciones sólo pueden comunicarse durante **ventanas de contacto**. El sistema calcula **rutas viables en el tiempo** (no sólo topológicas) para entregar un “bundle” de datos desde un **origen** a un **destino**, minimizando el **tiempo estimado de llegada (ETA)** y respetando:

* Ventanas [inicio, fin] de cada enlace.
* Latencia de establecimiento (**setup**), tiempo de transmisión (**rate × bytes**) y **propagación** (OWLT).
* Opcionalmente, **capacidad residual**.

> ¿Para qué se usa? Para **planificar rutas de datos** en redes con enlaces intermitentes: satélite–satélite (ISL) o satélite–tierra (GS), donde la conectividad cambia con la órbita.

---

## 2) El problema en simple

En LEO, los enlaces aparecen y desaparecen. No basta con saber “quién se conecta con quién”: hay que asegurarse de que **cada salto** puede empezar **a tiempo**, terminar **antes de que cierre** su ventana, y enlazar con el **siguiente**. Eso define un **grafo de contactos**: cada **contacto** es un “nodo” temporal y dos contactos se encadenan si **respetan la causalidad** (tiempos y nodos).

---

## 3) ¿Cómo funciona el motor? (flujo lógico)

1. **Entrada**: un **plan de contactos** (CSV) con filas del tipo: `id, from, to, t_start, t_end, owlt_s, rate_bps, setup_s, residual_bytes`.
2. **Construcción del grafo temporal**: el motor indexa qué contactos pueden seguir a cuáles, respetando tiempos y continuidad de nodos.
3. **Ruta óptima (k=1)**: se ejecuta un **Dijkstra temporal** que minimiza **ETA** (desde `t0`), descartando contactos donde **no cabe** el bundle por ventana o capacidad.
4. **Rutas alternativas (K)**:

   * **K consumo**: tras hallar una ruta, **descuelga capacidad** en los contactos usados y recalcula (rutas “realistas” con congestión).
   * **K Yen-lite**: genera **rutas diversas** (sin consumir capacidad) aplicando desvíos/bans a prefijos del mejor camino.
5. **Salida**: rutas con su **ETA**, **latencia total** y **secuencia de contactos**.

> El objetivo por defecto es **minimizar ETA**. Se pueden añadir otras métricas (energía, número de saltos) como penalizaciones.

---

## 4) Modo “Live” (simulación en tiempo real)

El binario **`cgr_live`** ejecuta el ruteo en ciclos (p. ej., cada 10s de tiempo simulado) y muestra:

* **Ruta óptima** del ciclo (si existe), alternativas K, y **barra de progreso orbital**.
* **Contactos activos** (ventanas abiertas en ese instante).
* **Autoperiodificación** del plan: si el CSV representa sólo un tramo de tiempo, el sistema puede **repetir** ese tramo (como una órbita) para que **siempre** haya próximas ventanas.

### Autoperiodo (qué hace)

* Detecta el **span temporal** del CSV: `max(t_end) - min(t_start)`.
* Si **no** se pasa `--period`, usa ese **span** como **periodo**.
* Antes de cada ciclo, **clona** las ventanas en los bloques `k` y `k+1` alrededor del tiempo actual, asegurando que haya **contactos futuros**.

> Con esto, la simulación **no se “muere”** cuando `t0` supera la última ventana del CSV.

---

## 5) Modos de ruteo disponibles

* **Baseline (k=1)**: mejor ruta por ETA con poda temporal/capacidad.
* **K por consumo (`--k N`)**: tras cada camino elegido, **resta** `bundle_bytes` de `residual_bytes` en sus contactos y **recalcula**. Útil para simular uso de recursos.
* **K Yen-lite (`--k-yen N`)**: obtiene rutas **diversificadas** deshabilitando por turnos segmentos del mejor camino. No toca capacidades.

> En **Live**, por defecto se listan **K** alternativas con Yen-lite para ver variedad.

---

## 6) Datos y APIs que puede usar

* **CSV local**: la fuente principal durante el desarrollo. Ej.: `data/contacts_realistic.csv`.
* **API Socrata (data.nasa.gov)**: muchos datasets exponen endpoints SODA (JSON/CSV) que se podrían **mapear** al esquema de contactos. El módulo `nasa_api` está preparado para integrarse (stubs), y puede:

  * Intentar **fetch** de contactos por dataset-id.
  * Caer en **fallback** al CSV local si la API no responde.
* **api.nasa.gov**: opcional para enriquecer metadatos. No es imprescindible para el ruteo.

> En producción, lo normal es **generar** el plan de contactos a partir de **efemérides orbitales** (p. ej., TLEs) y geometría de visibilidad. El motor admite cualquier fuente si respetas el **formato**.

---

## 7) Formato de entrada (CSV)

Cada fila describe **una ventana de contacto dirigida**:

```
id, from, to, t_start, t_end, owlt_s, rate_bps, setup_s, residual_bytes
0,  100,  1,     0.0,   60.0,   0.020,  6000000,   0.1,     300000000
```

* **from/to**: nodos (satélites/GS) lógicos.
* **t_start/t_end**: segundos de tiempo simulado.
* **owlt_s**: latencia de propagación.
* **rate_bps**: capacidad instantánea (bits/s) usada para calcular tiempo de TX.
* **setup_s**: retardo de establecimiento por contacto.
* **residual_bytes**: capacidad restante (para el modo de consumo).

---

## 8) Métricas y decisiones

* **Factibilidad** de un salto: cabe si `start_tx = max(t_in, t_start)` y
  `start_tx + setup + (bytes/rate) ≤ t_end` **y** `residual_bytes ≥ bytes` (si se usa consumo).
* **ETA** de un salto: `finish + owlt`.
* **ETA de la ruta**: acumulación secuencial de los saltos.
* **Selección de alternativas**: varia prefijos y aplica **bans** para diversificar caminos (Yen-lite), o **consume** capacidad para simular congestión.

---

## 9) Flujo típico de uso

1. **Prepara** un CSV de contactos realista.
2. **Ejecuta** en modo línea de comandos (`cgr`) para obtener la mejor ruta o K rutas.
3. **Simula** en vivo con `cgr_live` para ver cómo cambia el camino óptimo con el tiempo:
   `./cgr_live --period 5400 --tick 10 --k 3 --bytes 5e7`
4. **Compara** estrategias (baseline vs consumo vs Yen-lite) con los testers: generan casos, validan encadenados temporales y revisan capacidad.

---

## 10) Qué aporta respecto a un “CGR simple”

* **Poda por capacidad/ventana** integrada (no sólo tiempos).
* **K rutas con consumo**: útiles para planificación realista donde el uso de un enlace afecta rutas futuras.
* **K rutas diversas** (Yen-lite) para evaluar **robustez** y **redundancia**.
* **Simulación Live con autoperiodo** y **progreso**, para visualizar el comportamiento durante la órbita.

---

## 11) Límites y siguientes pasos

* **Sin efemérides**: el CSV no se genera aún a partir de TLEs; se asume dado.
* **Capacidad continua**: el consumo es por-bundle; no se modela tráfico concurrente ni colas.
* **Reconvergencia**: si un salto falla en ejecución, replanificar desde el último punto viable es futuro trabajo.

**Roadmap**:

* **Disjoint routing** (edge/node-disjoint) como modo adicional.
* **Clases de servicio / TTL** y prioridades en coste.
* **Backlog por nodo** y múltiples bundles.
* **OWLT variable** y objetivos multi-criterio (ETA + energía).

---

## 12) Cómo defender el proyecto (sin código)

* **Problema real**: en LEO los enlaces son efímeros; el ruteo debe ser **temporal y oportunista**.
* **Solución**: modelar cada **contacto como evento** y encadenarlos con **causalidad temporal**, optimizando **ETA** con restricciones de **ventana** y **capacidad**.
* **Valor**:

  * mejor planificación de tráfico satelital y entrega a GS,
  * alternativas robustas (diversidad / consumo),
  * simulación en vivo para **operaciones** y **what-if**.
* **Extensibilidad**: entradas via CSV o API, periodificación orbital, y módulos listos para integrar datos reales.

