
#pragma once
#include <stdbool.h>

// Un "contacto" es una ventana de enlace programada entre dos nodos (from -> to).
typedef struct
{
    int id;               // identificador único del contacto (para reportar la ruta)
    int from;             // id del nodo origen (SAT/GS)
    int to;               // id del nodo destino (SAT/GS)
    double t_start;       // inicio de la ventana (s)
    double t_end;         // fin de la ventana (s)
    double owlt;          // one-way light time (s)
    double rate_bps;      // capacidad (bps)
    double setup_s;       // retardo de establecimiento (s)
    double residual_bytes;// capacidad aún disponible (bytes) para el bundle
} Contact;

// Etiqueta de estado para Dijkstra temporal (una por contacto).
typedef struct
{
    int contact_idx;   // índice del contacto (posición en el array C[])
    double eta;        // earliest arrival time al FINAL del contacto
    int prev_idx;      // backpointer: índice del contacto previo, -1 si raíz
} Label;

// Resultado de UNA ruta
typedef struct
{
    int *contact_ids;  // ids de los contactos en orden (no índices)
    int hops;          // número de saltos (contactos)
    double eta;        // ETA final (s)
    bool found;        // true si hay ruta
} Route;

// Parámetros de un enrutamiento (para un bundle)
typedef struct
{
    int src_node;       // nodo origen (SAT/GS)
    int dst_node;       // nodo destino (SAT/GS)
    double t0;          // tiempo de salida/creación del bundle (s)
    double bundle_bytes;// tamaño del bundle (bytes)
    double expiry;      // tiempo de expiración relativo (s); 0 = sin restricción
} CgrParams;

// Conjunto de rutas (K rutas)
typedef struct
{
    Route *items;       // array de rutas
    int count;          // cuántas rutas válidas se obtuvieron
    int cap;            // capacidad del array
} Routes;

