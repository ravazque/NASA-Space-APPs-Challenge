
// src/cgr.c — Implementación CGR (k=1) y K-rutas por consumo de capacidad

#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <stdio.h>
#include "cgr.h"
#include "heap.h"

static inline int max3(int a,int b,int c){ int m=a>b?a:b; return m>c?m:c; }

NeighborIndex* build_neighbor_index(const Contact *C, int N){
    int maxNode = 0;
    for(int i=0;i<N;i++) maxNode = max3(maxNode, C[i].from, C[i].to);

    NeighborIndex *ni = (NeighborIndex*)calloc(1, sizeof(NeighborIndex));
    ni->node_cap = maxNode + 1;
    ni->by_from = (IndexList*)calloc(ni->node_cap, sizeof(IndexList));

    for(int i=0;i<N;i++){
        int from = C[i].from;
        if(from < 0 || from >= ni->node_cap) continue;
        IndexList *L = &ni->by_from[from];
        if(L->count >= L->cap){
            L->cap = (L->cap==0?4:L->cap*2);
            L->idxs = (int*)realloc(L->idxs, sizeof(int)*L->cap);
        }
        L->idxs[L->count++] = i;
    }
    return ni;
}

void free_neighbor_index(NeighborIndex* ni){
    if(!ni) return;
    for(int i=0;i<ni->node_cap;i++) free(ni->by_from[i].idxs);
    free(ni->by_from);
    free(ni);
}

// ETA al final del contacto, dado que "llego" al nodo origen del contacto en t_in.
static double eta_contact(const Contact *c, double t_in, double bundle_bytes){
    if(t_in > c->t_end) return DBL_MAX; // llego tarde
    if(c->residual_bytes + 1e-9 < bundle_bytes) return DBL_MAX; // no cabe

    double start_tx = (t_in < c->t_start) ? c->t_start : t_in;
    double rate = (c->rate_bps > 1.0) ? c->rate_bps : 1.0; // evita /0
    double tx_time = bundle_bytes / rate;
    double finish_tx = start_tx + c->setup_s + tx_time;

    if(finish_tx > c->t_end + 1e-12) return DBL_MAX; // no cabe en ventana

    return finish_tx + c->owlt;
}

// k=1 — Dijkstra temporal sobre grafo de contactos (vértices = contactos)
Route cgr_best_route(const Contact *C, int N, const CgrParams *P, const NeighborIndex *NI){
    Route R = {.contact_ids=NULL, .hops=0, .eta=DBL_MAX, .found=false};

    Label *lab = (Label*)malloc(sizeof(Label)*N);
    for(int i=0;i<N;i++){ lab[i].contact_idx=i; lab[i].eta=DBL_MAX; lab[i].prev_idx=-1; }

    MinHeap *pq = heap_new(64);

    // Semilla: todos los contactos que SALEN de src y son viables desde t0
    if(P->src_node >= 0 && P->src_node < NI->node_cap){
        IndexList L = NI->by_from[P->src_node];
        for(int k=0;k<L.count;k++){
            int ci = L.idxs[k];
            double eta = eta_contact(&C[ci], P->t0, P->bundle_bytes);
            if(eta==DBL_MAX) continue;
            if(P->expiry>0 && eta > P->t0 + P->expiry) continue;

            if(eta < lab[ci].eta){
                lab[ci].eta = eta;
                lab[ci].prev_idx = -1;
                heap_push(pq, (Label){ .contact_idx=ci, .eta=eta, .prev_idx=-1 });
            }
        }
    }

    // Dijkstra: expandir por menor ETA
    int best_end = -1;
    double best_eta = DBL_MAX;

    while(!heap_empty(pq)){
        Label cur = heap_pop(pq);
        int ci = cur.contact_idx;
        double eta_here = cur.eta;

        // label desactualizada
        if(eta_here > lab[ci].eta + 1e-12) continue;

        // ¿Destino alcanzado?
        if(C[ci].to == P->dst_node){
            best_end = ci;
            best_eta = eta_here;
            break; // primeras llegada por Dijkstra es óptima
        }

        // Vecinos: contactos que salen del nodo "to" actual
        int next_node = C[ci].to;
        if(next_node < 0 || next_node >= NI->node_cap) continue;

        IndexList L = NI->by_from[next_node];
        for(int kk=0; kk<L.count; kk++){
            int nj = L.idxs[kk];
            double eta_n = eta_contact(&C[nj], eta_here, P->bundle_bytes);
            if(eta_n==DBL_MAX) continue;
            if(P->expiry>0 && eta_n > P->t0 + P->expiry) continue;

            if(eta_n + 1e-12 < lab[nj].eta){
                lab[nj].eta = eta_n;
                lab[nj].prev_idx = ci;
                heap_push(pq, (Label){ .contact_idx=nj, .eta=eta_n, .prev_idx=ci });
            }
        }
    }

    heap_free(pq);

    if(best_end == -1){
        free(lab);
        return R; // sin ruta
    }

    // Reconstrucción de la ruta (IDs de contacto en orden)
    int cap = 16, len = 0;
    int *rev = (int*)malloc(sizeof(int)*cap);
    int cur = best_end;
    while(cur != -1){
        if(len>=cap){ cap*=2; rev = (int*)realloc(rev, sizeof(int)*cap); }
        rev[len++] = cur;
        cur = lab[cur].prev_idx;
    }

    R.contact_ids = (int*)malloc(sizeof(int)*len);
    for(int i=0;i<len;i++){
        R.contact_ids[i] = C[rev[len-1-i]].id;
    }
    R.hops = len;
    R.eta  = best_eta;
    R.found = true;

    free(rev);
    free(lab);
    return R;
}

void free_route(Route *r){
    if(!r) return;
    free(r->contact_ids);
    r->contact_ids = NULL;
    r->hops = 0;
    r->eta = 0;
    r->found = false;
}

// Utilidad interna: reduce residual_bytes de los contactos usados en 'route'.
// Trabaja sobre un array de contactos MODIFICABLE (una copia local para K rutas).
static void consume_capacity(Contact *C, int N, const Route *route, const CgrParams *P){
    if(!route->found || route->hops<=0) return;

    // Para mapear id -> índice (O(N)). Para N pequeño es suficiente; si no, construye hash.
    for(int step=0; step<route->hops; step++){
        int id = route->contact_ids[step];
        for(int i=0;i<N;i++){
            if(C[i].id == id){
                double bytes = P->bundle_bytes;
                if(C[i].residual_bytes >= bytes) C[i].residual_bytes -= bytes;
                else C[i].residual_bytes = 0.0; // agota
                break;
            }
        }
    }
}

// K rutas: copia los contactos de entrada, itera k veces (o hasta que falle)
Routes cgr_k_routes(const Contact *C_in, int N, const CgrParams *P, const NeighborIndex *NI, int K){
    Routes RS = {.items=NULL, .count=0, .cap=0};
    if(K <= 0) return RS;

    // Copia local sobre la que consumimos capacidad
    Contact *C = (Contact*)malloc(sizeof(Contact)*N);
    memcpy(C, C_in, sizeof(Contact)*N);

    // Reserva inicial para K rutas
    RS.cap = K;
    RS.items = (Route*)calloc(RS.cap, sizeof(Route));

    for(int k=0; k<K; k++){
        Route r = cgr_best_route(C, N, P, NI);
        if(!r.found){
            break; // no hay más rutas
        }
        // Guarda la ruta
        RS.items[RS.count++] = r;
        // Consume capacidad en la copia local
        consume_capacity(C, N, &r, P);
    }

    free(C);
    return RS;
}

void free_routes(Routes *rs){
    if(!rs || !rs->items) return;
    for(int i=0;i<rs->count;i++) free_route(&rs->items[i]);
    free(rs->items);
    rs->items=NULL; rs->count=0; rs->cap=0;
}

