
# EcoStation — CGR API (LEO)

## Visión general

Este proyecto implementa **Contact Graph Routing (CGR)** para redes espaciales tipo **LEO–LEO / LEO–Tierra** usando **un único modo: API**. El binario `cgr_api` descarga un **plan de contactos** (ventanas de visibilidad, retardos, tasas y capacidad residual) desde un dataset SODA de **data.nasa.gov** y calcula la **ruta de mínima ETA** (Earliest Time of Arrival) para un bundle entre un **nodo origen** y un **nodo destino**.

Además, incorpora un **aprendizaje ligero opcional** (muy barato en CPU/RAM) que ajusta el coste de los enlaces en función de la espera observada y/o del consumo de capacidad, mejorando la estabilidad de las rutas frente a congestión o solapamiento de ventanas.

---

## ¿Qué problema resuelve?

En LEO, la topología cambia rápidamente: los enlaces entre satélites y estaciones existen sólo durante **ventanas** cortas y con **altas velocidades relativas**. En este contexto, CGR modela la red como un **grafo temporal de contactos** y selecciona una ruta **causal** (respetando disponibilidad temporal, *setup* y retardo OWLT) que minimiza la **ETA**.

---

## Cómo funciona (lógica, sin código)

1. **Ingesta por API**

   * Se selecciona un **proveedor** de datos mediante una **macro** de compilación. Por defecto: `NASA_PROVIDER_SODA` (Socrata SODA, CSV).
   * El módulo de API descarga un CSV con campos: `id, from, to, t_start, t_end, owlt, rate_bps, setup_s, residual_bytes`.

2. **Construcción del grafo de contactos**

   * Cada fila es un **contacto dirigido** con ventana `[t_start, t_end)`.
   * El coste efectivo por salto incluye **setup_s**, **retardo OWLT** y **tiempos de espera** si la transmisión debe aguantar hasta la apertura de la ventana.

3. **Búsqueda de ruta (CGR)**

   * Se ejecuta un **Dijkstra temporal** sobre el grafo de contactos: sólo se enlazan contactos compatibles en el tiempo y el destino.
   * Se devuelve la **ruta óptima** (mínima ETA) y, opcionalmente, **K alternativas** (variación tipo Yen, sin consumo de capacidad).

4. **Aprendizaje ligero (opcional)**

   * **Consume**: tras utilizar una ruta, se **descuenta** `bundle_bytes` del `residual_bytes` de cada contacto usado (simula uso/carga).
   * **EWMA**: se calcula una **penalización suave** por enlace con una media móvil exponencial sobre la **espera observada** en el primer salto; esta penalización se **inyecta** en el *setup* del enlace mediante un factor `lambda`.
   * Efecto: el sistema evita “enamorarse” de un único enlace y estabiliza latencias cuando hay ventanas competidas.

---

## Flujo de ejecución

1. **Inicio**: parseo de flags CLI (dataset, token, src/dst, `t0`, bytes, `k`, ciclos).
2. **Descarga**: el módulo API obtiene el CSV y lo parsea a memoria.
3. **Ciclo de planificación** (1 o varios ciclos):

   * Construye o actualiza el índice de vecinos por tiempo/nodo.
   * Ejecuta CGR y devuelve **ETA, latencia y path**.
   * (Opcional) Aplica **consume** y/o **EWMA** para el próximo ciclo.
   * Avanza el reloj simulado `tick` segundos y repite hasta `cycles`.

---

## Diferencias y mejoras frente a CGR “puro”

* **CGR clásico**: óptimo respecto al plan de contactos **estático**; tiende a repetir rutas idénticas cuando hay un enlace “muy bueno”, ignorando congestión.
* **Este proyecto** añade, sin apenas coste de recursos:

  * **Consumo de capacidad** *(opcional)* → rutas más diversas y realistas.
  * **Penalización EWMA** *(opcional)* → reduce esperas recurrentes y estabiliza la latencia media.

**Resultado**: con **sobrecoste mínimo (O(hops) + O(E) por ciclo)**, se obtiene un rendimiento **más robusto** en escenarios con ventanas competidas, manteniendo la simplicidad del CGR.

---

## Macro del proveedor de API

La selección del proveedor se hace en `include/nasa_api.h`:

```c
#define NASA_PROVIDER NASA_PROVIDER_SODA   // por defecto: SODA (data.nasa.gov)
// #define NASA_PROVIDER NASA_PROVIDER_CUSTOM // plantilla para tu propia API
```

Si cambias a `NASA_PROVIDER_CUSTOM`, implementa los *stubs* en `src/nasa_api.c` para tu backend.

---

## Uso rápido (CLI)

```bash
# Compilar
make

# Una planificación (sin aprendizaje)
./cgr_api \
  --dataset abcd-1234 --app-token TU_TOKEN \
  --src 100 --dst 200 --t0 0 --bytes 5e7 --k 3 --cycles 1

# Varios ciclos con aprendizaje ligero
./cgr_api \
  --dataset abcd-1234 --app-token TU_TOKEN \
  --src 100 --dst 200 --t0 0 --bytes 5e7 --k 3 \
  --cycles 30 --tick 10 --consume --learn-ewma --alpha 0.2 --lambda 1.0
```

**Flags clave**

* `--dataset`, `--app-token`: identifican el dataset SODA y token.
* `--src`, `--dst`, `--t0`, `--bytes`: definen la consulta.
* `--k`: número de rutas alternativas.
* `--cycles`, `--tick`: iteraciones y avance del reloj (para aprendizaje).
* `--consume`: resta capacidad a los contactos usados.
* `--learn-ewma --alpha A --lambda L`: penalización suave por enlace.

---

## Estructura mínima

* `src/api_main.c` → punto de entrada (API + aprendizaje ligero).
* `src/nasa_api.c` / `include/nasa_api.h` → proveedor SODA + macro de cambio.
* `src/cgr.c`, `src/heap.c`, `src/csv.c`, `src/leo_metrics.c`, `include/cgr.h` → núcleo CGR y utilidades.
* `Makefile` → build mínimo (sin tests), enlaza `-lcurl -lm`.

---

## Límites conocidos

* El aprendizaje es **ligero** (no simula colas ni *multi-commodity flow*).
* La calidad depende de la **fidelidad del plan de contactos** publicado en el dataset.
* Si el dataset no incluye `residual_bytes`, el consumo sólo afectará rutas subsecuentes dentro de la ejecución, no el dataset remoto.

---

## Defensa durante el Hackathon

* Mantiene la **corrección temporal** del CGR, imprescindible en LEO.
* Añade **dos heurísticas** simples pero efectivas que reducen la **miopía** del modelo estático con un **coste despreciable**.
* Es **modular**: cambiar de API es un `#define`; ampliar el aprendizaje o desactivarlo es cuestión de flags.

---

## Créditos

Desarrollado para EcoStation Europa — módulo de planificación y exploración de rutas CGR sobre datos públicos.

---

# CGR - Contact Graph Routing for Space Networks

**Real-time satellite network routing simulator with DTN (Delay-Tolerant Networking) capabilities.**

## 🚀 Quick Start

```bash
# Build and run real-time simulation
make run

# That's it! The simulator will:
# - Generate a realistic 12-satellite network
# - Compute optimal routes every 15 seconds
# - Show alternative paths with K=5 diversity
# - Display progress in real-time (Ctrl+C to stop)
```

## 📁 Project Structure

```
├── src/
│   ├── cgr.c           # Core CGR algorithm (Dijkstra + Yen's K-shortest)
│   ├── cgr_live.c      # Real-time simulation (main executable)
│   ├── csv.c           # CSV parser for contact plans
│   ├── heap.c          # Min-heap for Dijkstra
│   ├── leo_metrics.c   # LEO satellite link metrics
│   └── nasa_api.c      # NASA SODA API integration
├── include/            # Header files
├── data/               # Example contact plans (OPTIONAL - for testing only)
└── Makefile
```

## 🛰️ Is the `data/` folder necessary?

**No**, the `data/` folder is **optional**. It contains example CSV files for testing:

- **With API mode** (`--source api`): Fetches real-time data from NASA
- **With synthetic mode** (`--source synth`): Generates realistic contact plans on-the-fly
- **With local mode** (`--source local`): Uses CSV files from `data/`

**Recommendation**: Keep `data/contacts_realistic.csv` as a fallback for offline testing.

## 🌐 NASA API Integration

### Current Configuration

The code uses **NASA's SODA API** structure expecting:
```csv
id,from,to,t_start,t_end,owlt,rate_bps,setup_s,residual_bytes
```

### How to Use with Real NASA Data

1. **Find a compatible dataset** at https://data.nasa.gov/dataset/
   - Look for datasets with satellite contact/telemetry data
   - Recommended: ISS tracking, satellite conjunction data

2. **Adapt the data schema** (if needed):
   - Modify `nasa_api.c` to transform NASA data to the expected format
   - Or use the **synthetic generator** (recommended for demos)

3. **Run with API**:
```bash
./cgr_live <dataset-id> --source api --app-token YOUR_TOKEN
```

### Why Synthetic Mode is Better for Demos

The synthetic generator (`--source synth`) creates realistic satellite networks with:
- ✅ Realistic orbital periods (~90 min)
- ✅ Inter-Satellite Links (ISLs)
- ✅ Ground station contact windows
- ✅ Variable data rates and capacities
- ✅ Randomized topology (configurable seed)

## 🎮 Usage Examples

### Default Real-Time Demo
```bash
make run
# Uses: 12 satellites, 15s time step, 50MB bundles, K=5 routes
```

### Custom Parameters
```bash
./cgr_live --source synth --synth-n 20 --tick 10 --k 3 --bytes 100e6
# 20 satellites, 10s steps, 3 alternative routes, 100MB bundles
```

### With NASA API (when available)
```bash
./cgr_live abcd-1234 --source api --app-token YOUR_TOKEN --tick 20 --k 5
```

### Local CSV Testing
```bash
./cgr_live --source local --contacts data/contacts_realistic.csv
```

## 📊 Output Explanation

```
╔════════════════════════════════════════════════════════╗
║  CYCLE #1    | Simulation time: 0.0 s                  
╠════════════════════════════════════════════════════════╣
║  Active contacts:   8                                  
║  Data source:       SYNTHETIC                          
║  Errors:            0                                  
╚════════════════════════════════════════════════════════╝

🛰️  OPTIMAL ROUTE FOUND:
   • ETA:      92.456 s       ← Earliest arrival time
   • Latency:  92.456 s       ← Total delivery time
   • Hops:     5              ← Number of satellite links
   • Path:     0 → 3 → 7 → 11 → 14

📊 Alternative routes (K=5):
   #1: ETA=92.456 s, 5 hops (+0.0% overhead)    ← Best route
   #2: ETA=95.123 s, 6 hops (+2.9% overhead)    ← Backup
   #3: ETA=98.772 s, 5 hops (+6.8% overhead)    ← Alternative
   ...
```

## 🔧 Build Options

```bash
make          # Standard build
make debug    # Debug build with sanitizers
make clean    # Remove objects
make fclean   # Remove everything
make re       # Rebuild from scratch
```

## 🧪 Advanced Features

### K-Shortest Paths
- **Yen-lite algorithm**: Finds diverse alternative routes without consuming

