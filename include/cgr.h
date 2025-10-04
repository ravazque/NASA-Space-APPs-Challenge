
// include/cgr.h — Búsqueda de rutas CGR (k=1 y K-rutas por consumo)

#pragma once
#include "contact.h"

// Estructuras auxiliares para vecindad por nodo origen
typedef struct {
    int *idxs;   // índices de contactos que salen de un nodo
    int count;
    int cap;
} IndexList;

typedef struct {
    IndexList *by_from; // tamaño = node_cap
    int node_cap;
} NeighborIndex;

NeighborIndex* build_neighbor_index(const Contact *C, int N);
void free_neighbor_index(NeighborIndex* ni);

// Ruta óptima (k=1) minimizando ETA, con poda por capacidad y expiración
Route cgr_best_route(const Contact *C, int N, const CgrParams *P, const NeighborIndex *NI);

// K rutas por iteración: cada vez que se halla una ruta, se "consume" capacidad
// de los contactos usados y se busca la siguiente ruta. Modifica una COPIA local
// de los contactos para no afectar al array original.
Routes cgr_k_routes(const Contact *C_in, int N, const CgrParams *P, const NeighborIndex *NI, int K);

// Utilidades
void free_route(Route *r);
void free_routes(Routes *rs);

