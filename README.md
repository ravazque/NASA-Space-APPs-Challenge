# README.md

# EcoStation CGR — Routing con Contact Graphs para mallas LEO-LEO

## 0) Qué es esto

Enrutador **DTN** minimalista para constelaciones **LEO**, basado en **Contact Graph Routing (CGR)**. Calcula rutas usando un **plan de contactos** (ventanas [t_start, t_end]) y minimiza **ETA** con un **Dijkstra temporal**.

**Modos disponibles**

* **k=1**: mejor ruta (ETA mínima).
* **K por consumo**: `--k N` — tras cada ruta, se **descuelga capacidad** (`residual_bytes`) en los contactos usados; busca rutas alternativas **realistas**.
* **K Yen-lite**: `--k-yen N` — rutas **diversas** (sin consumir capacidad) a partir de **prefijos forzados** y **bans** (aprox. Yen K-shortest para grafos de contactos).

## 1) ¿Por qué CGR en LEO?

* Ventanas **cortas** y topología **rápida** (ISL / pases a GS).
* DTN `store–carry–forward` con **agenda** de enlaces.
* **Vértices = contactos**, aristas si se respeta causalidad temporal.
* **Coste**: ETA = `setup + tx_time + owlt` acumulados.

**Capacidad** (MVP+): cada contacto tiene `residual_bytes`. Un bundle cabe si:

```
usable_window = (min(t_end, ...) - max(t_start, t_in) - setup_s)
available = min(residual_bytes, usable_window * rate_bps)
available >= bundle_bytes
```

## 2) Estado actual del algoritmo

* **CGR básico (k=1)** con poda por ventana, **capacidad** y **expiry**.
* **K por consumo** (heurístico práctico).
* **K Yen-lite** (diversidad real por prefijos/bans, sin consumir).

## 3) Roadmap inmediato

* **Disjoint**: `--disjoint-contacts | --disjoint-nodes` (bans acumulados).
* **TTL/Prioridades**: coste y poda por clase de servicio.
* **Volumen por tramo** y **backlog** por nodo (múltiples bundles).
* **Reconvergencia**: replan desde el último contacto válido si “cae” un enlace.
* **OWLT variable** (efemérides) y métrica multi-objetivo ETA+energía.

## 4) Build y uso rápido

```bash
make
./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --pretty
./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k 3 --format text
./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k-yen 3 --pretty
```

### Flags útiles

* `--expiry <s>`: TTL; descarta rutas con `eta > t0+expiry`.
* `--pretty`: JSON identado; `--format text`: salida humana.

## 5) Modelo de datos (CSV)

```
# id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes
0, 100, 1, 0, 60, 0.020, 5000000, 0.2, 300000000
```

* `from/to`: nodos (SAT/GS), `t_*` en segundos sim.
* `owlt_s`: one-way light time.
* `rate_bps`: bps; `setup_s`: latencia de establecimiento.
* `residual_bytes`: capacidad disponible.

## 6) Testing (nuevo)

Hemos añadido un **tester** que:

* Genera **casos deterministas** (línea, diamante, estrella, anillo), con/ sin cuellos de botella.
* Genera **casos aleatorios** (conectividad y tiempos controlados).
* Ejecuta el binario en **distintos modos** y valida:

  * que la ruta encadena contactos temporalmente,
  * que **cabe** en ventanas y capacidad,
  * que en **modo consumo** no se sobrepasa capacidad al encadenar K rutas.
* Reporta **resumen** (pases/fallos) y CSV con resultados.

### Ejecutar

```bash
make test     # smoke + scenarios
make fuzz     # aleatorios medianos/grandes
make bench    # micro-benchmark escalado
```

Resultados en `test/out/`:

* `summary.txt` y `results.csv`
* los contactos generados en `test/cases/`

## 7) Estructura

```
include/        # headers
src/            # implementación (CGR, CSV, heap, CLI)
data/           # ejemplo pequeño
test/           # NUEVO tester (generador, validador, runner)
```

## 8) Licencia y alcance

MVP educativo para validar ideas de ruteo en constelaciones LEO. No pretende reemplazar implementaciones completas de CGR/BPv7 en misiones reales.
