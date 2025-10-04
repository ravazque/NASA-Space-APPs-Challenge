
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

