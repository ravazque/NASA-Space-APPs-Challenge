
#pragma once
#include "contact.h"

typedef struct
{
    int *idxs;   // índices de contactos que salen de un nodo
    int count;
    int cap;
} IndexList;

typedef struct
{
    IndexList *by_from; // tamaño = node_cap
    int node_cap;
} NeighborIndex;

NeighborIndex* build_neighbor_index(const Contact *C, int N);
void free_neighbor_index(NeighborIndex* ni);

typedef struct
{
    const int *banned_ids;        // array de contact.id prohibidos (puede ser NULL)
    int banned_count;             // tamaño de banned_ids
    const int *forced_prefix_ids; // contactos que DEBEN usarse al principio (puede ser NULL)
    int forced_count;             // longitud del prefijo forzado
} CgrFilters;

Route cgr_best_route(const Contact *C, int N, const CgrParams *P, const NeighborIndex *NI);

Route cgr_best_route_filtered(const Contact *C, int N, const CgrParams *P,const NeighborIndex *NI, const CgrFilters *F);

Routes cgr_k_routes(const Contact *C_in, int N, const CgrParams *P, const NeighborIndex *NI, int K);

Routes cgr_k_yen(const Contact *C, int N, const CgrParams *P, const NeighborIndex *NI, int K);


void free_route(Route *r);
void free_routes(Routes *rs);
