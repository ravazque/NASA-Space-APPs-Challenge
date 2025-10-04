// src/cgr.c — CGR: Dijkstra temporal (k=1), K por consumo y K Yen-lite (con filtros) — C puro
#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <stdio.h>
#include "cgr.h"
#include "heap.h"

static inline int max3(int a,int b,int c){ int m=a>b?a:b; return m>c?m:c; }

/*-----------------------------------------------------------------------------
  Construcción del índice by_from
-----------------------------------------------------------------------------*/
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

/*-----------------------------------------------------------------------------
  Helpers de filtros / prefijo forzado
-----------------------------------------------------------------------------*/
static inline int is_banned_id(int id, const CgrFilters *F){
    if(!F || !F->banned_ids || F->banned_count<=0) return 0;
    for(int i=0;i<F->banned_count;i++){
        if(F->banned_ids[i] == id) return 1;
    }
    return 0;
}

static inline int forced_id_at(const CgrFilters *F, int k){
    if(!F || !F->forced_prefix_ids || F->forced_count<=0) return -1;
    if(k < 0 || k >= F->forced_count) return -1;
    return F->forced_prefix_ids[k];
}

/* Dado un contacto índice ci, calcula cuántos elementos del prefijo forzado
   ya se han satisfecho en la ruta actual (desde la raíz). Para ello reconstruye
   la ruta (prev_idx) y compara con forced_prefix_ids desde el inicio. */
static int compute_prefix_done(int ci, const Label *lab, const Contact *C, const CgrFilters *F){
    if(!F || !F->forced_prefix_ids || F->forced_count<=0) return 0;

    // Primero contamos longitud de la cadena hasta la raíz
    int len = 0, walker = ci;
    while(walker != -1){ len++; walker = lab[walker].prev_idx; }

    // Volcamos los ids de contacto en orden desde raíz -> actual
    int *seq = (int*)malloc(sizeof(int)*len);
    int idx = len - 1; walker = ci;
    while(walker != -1){
        seq[idx--] = C[walker].id;
        walker = lab[walker].prev_idx;
    }

    // Comparamos con el prefijo forzado desde el inicio
    int matched = 0;
    while(matched < F->forced_count && matched < len){
        if(seq[matched] != F->forced_prefix_ids[matched]) break;
        matched++;
    }
    free(seq);
    return matched;
}

/*-----------------------------------------------------------------------------
  Capacidad por ventana y ETA de contacto
-----------------------------------------------------------------------------*/
static double available_bytes_window(const Contact *c, double t_in){
    if(t_in > c->t_end) return 0.0;
    double start_tx = (t_in < c->t_start) ? c->t_start : t_in;
    double window = c->t_end - start_tx - c->setup_s;
    if(window <= 1e-12) return 0.0;
    double rate = (c->rate_bps > 1.0) ? c->rate_bps : 1.0;
    return window * rate;
}

// ETA al final del contacto, dado t_in (tiempo de llegada al nodo de entrada del contacto)
static double eta_contact(const Contact *c, double t_in, double bundle_bytes, double expiry_abs){
    if(t_in > c->t_end) return DBL_MAX;
    double avail = available_bytes_window(c, t_in);
    double cap = (c->residual_bytes < avail) ? c->residual_bytes : avail;
    if(cap + 1e-9 < bundle_bytes) return DBL_MAX;

    double start_tx = (t_in < c->t_start) ? c->t_start : t_in;
    double rate = (c->rate_bps > 1.0) ? c->rate_bps : 1.0;
    double tx_time = bundle_bytes / rate;
    double finish = start_tx + c->setup_s + tx_time;
    if(finish > c->t_end + 1e-12) return DBL_MAX;

    double eta = finish + c->owlt;
    if(expiry_abs > 0.0 && eta > expiry_abs) return DBL_MAX;
    return eta;
}

/*-----------------------------------------------------------------------------
  Búsqueda k=1 (sin filtros) = envoltorio
-----------------------------------------------------------------------------*/
Route cgr_best_route(const Contact *C, int N, const CgrParams *P, const NeighborIndex *NI){
    return cgr_best_route_filtered(C, N, P, NI, NULL);
}

/*-----------------------------------------------------------------------------
  Búsqueda k=1 con filtros (banned + forced prefix)
-----------------------------------------------------------------------------*/
Route cgr_best_route_filtered(const Contact *C, int N, const CgrParams *P,
                              const NeighborIndex *NI, const CgrFilters *F)
{
    Route R = {.contact_ids=NULL, .hops=0, .eta=DBL_MAX, .found=false};
    if(!P || !NI) return R;

    // Labels
    Label *lab = (Label*)malloc(sizeof(Label)*N);
    for(int i=0;i<N;i++){ lab[i].contact_idx=i; lab[i].eta=DBL_MAX; lab[i].prev_idx=-1; }

    MinHeap *pq = heap_new(64);
    double expiry_abs = (P->expiry > 0.0) ? (P->t0 + P->expiry) : 0.0;

    // Semilla
    if(F && F->forced_prefix_ids && F->forced_count > 0){
        int first_id = forced_id_at(F, 0);
        // Ese primer contacto debe salir de src
        for(int ci=0; ci<N; ci++){
            if(C[ci].id != first_id) continue;
            if(C[ci].from != P->src_node) continue;
            if(is_banned_id(C[ci].id, F)) continue;

            double eta = eta_contact(&C[ci], P->t0, P->bundle_bytes, expiry_abs);
            if(eta == DBL_MAX) continue;

            lab[ci].eta = eta;
            lab[ci].prev_idx = -1;
            heap_push(pq, (Label){ .contact_idx=ci, .eta=eta, .prev_idx=-1 });
            break; // solo ese
        }
    } else {
        if(P->src_node >= 0 && P->src_node < NI->node_cap){
            IndexList L = NI->by_from[P->src_node];
            for(int k=0;k<L.count;k++){
                int ci = L.idxs[k];
                if(F && is_banned_id(C[ci].id, F)) continue;
                double eta = eta_contact(&C[ci], P->t0, P->bundle_bytes, expiry_abs);
                if(eta==DBL_MAX) continue;
                if(eta < lab[ci].eta){
                    lab[ci].eta = eta;
                    lab[ci].prev_idx = -1;
                    heap_push(pq, (Label){ .contact_idx=ci, .eta=eta, .prev_idx=-1 });
                }
            }
        }
    }

    // Dijkstra temporal
    int best_end = -1;
    double best_eta = DBL_MAX;

    while(!heap_empty(pq)){
        Label cur = heap_pop(pq);
        int ci = cur.contact_idx;
        double eta_here = cur.eta;

        if(eta_here > lab[ci].eta + 1e-12) continue; // label desactualizada

        // ¿Cuánto prefijo hemos cumplido en esta ruta?
        int prefix_done = compute_prefix_done(ci, lab, C, F);

        // ¿Destino?
        if(C[ci].to == P->dst_node){
            // Si hay prefijo, asegúrate de que está completo
            if(!(F && F->forced_prefix_ids && F->forced_count>0) || prefix_done >= F->forced_count){
                best_end = ci;
                best_eta = eta_here;
                break; // óptimo por Dijkstra
            }
        }

        // Expandir vecinos
        int next_node = C[ci].to;
        if(next_node < 0 || next_node >= NI->node_cap) continue;

        IndexList L = NI->by_from[next_node];

        // ¿Aún falta un contacto específico del prefijo?
        int need_forced_next = -1;
        if(F && F->forced_prefix_ids && F->forced_count>0 && prefix_done < F->forced_count){
            need_forced_next = forced_id_at(F, prefix_done);
        }

        for(int kk=0; kk<L.count; kk++){
            int nj = L.idxs[kk];

            if(need_forced_next != -1 && C[nj].id != need_forced_next) continue; // exige el siguiente del prefijo
            if(F && is_banned_id(C[nj].id, F)) continue;

            double eta_n = eta_contact(&C[nj], eta_here, P->bundle_bytes, expiry_abs);
            if(eta_n == DBL_MAX) continue;

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
        return R; // no encontrada
    }

    // Reconstrucción de ruta
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

/*-----------------------------------------------------------------------------
  K rutas por CONSUMO (modo práctico)
-----------------------------------------------------------------------------*/
static void consume_capacity(Contact *C, int N, const Route *route, const CgrParams *P){
    if(!route->found || route->hops<=0) return;

    for(int step=0; step<route->hops; step++){
        int id = route->contact_ids[step];
        for(int i=0;i<N;i++){
            if(C[i].id == id){
                double bytes = P->bundle_bytes;
                if(C[i].residual_bytes >= bytes) C[i].residual_bytes -= bytes;
                else C[i].residual_bytes = 0.0;
                break;
            }
        }
    }
}

Routes cgr_k_routes(const Contact *C_in, int N, const CgrParams *P, const NeighborIndex *NI, int K){
    Routes RS = {.items=NULL, .count=0, .cap=0};
    if(K <= 0) return RS;

    Contact *C = (Contact*)malloc(sizeof(Contact)*N);
    memcpy(C, C_in, sizeof(Contact)*N);

    RS.cap = K;
    RS.items = (Route*)calloc(RS.cap, sizeof(Route));

    for(int k=0; k<K; k++){
        Route r = cgr_best_route(C, N, P, NI);
        if(!r.found){
            break;
        }
        RS.items[RS.count++] = r;
        consume_capacity(C, N, &r, P);
    }

    free(C);
    return RS;
}

/*-----------------------------------------------------------------------------
  K rutas Yen-lite (diversidad sin consumo)
-----------------------------------------------------------------------------*/
Routes cgr_k_yen(const Contact *C, int N, const CgrParams *P, const NeighborIndex *NI, int K){
    Routes out = {.items=NULL, .count=0, .cap=0};
    if(K <= 0) return out;

    out.cap = K;
    out.items = (Route*)calloc(K, sizeof(Route));

    // Ruta base
    Route base = cgr_best_route_filtered(C, N, P, NI, NULL);
    if(!base.found){
        return out;
    }
    out.items[out.count++] = base;

    for(int k=1; k<K; k++){
        double best_eta = 1e300;
        Route best = (Route){0};

        const Route *prev = &out.items[k-1];
        // probamos desvío en cada posición
        for(int i=0; i<prev->hops; i++){
            // Prefijo forzado: [0..i-1]
            CgrFilters F;
            memset(&F, 0, sizeof(F));
            F.forced_prefix_ids = prev->contact_ids; // apunta al array de la ruta previa
            F.forced_count = i;

            // Contacto baneado: el i-ésimo de la ruta previa
            int banned_one = prev->contact_ids[i];
            F.banned_ids = &banned_one;
            F.banned_count = 1;

            Route cand = cgr_best_route_filtered(C, N, P, NI, &F);
            if(!cand.found) continue;

            // Evitar duplicado exacto con la anterior
            int same = (cand.hops == prev->hops);
            if(same){
                for(int t=0; t<cand.hops; t++){
                    if(cand.contact_ids[t] != prev->contact_ids[t]) { same=0; break; }
                }
            }
            if(same){ free_route(&cand); continue; }

            if(cand.eta < best_eta){
                if(best.found) free_route(&best);
                best = cand;
                best_eta = cand.eta;
            } else {
                free_route(&cand);
            }
        }

        if(!best.found) break;
        out.items[out.count++] = best;
    }

    return out;
}

void free_routes(Routes *rs){
    if(!rs || !rs->items) return;
    for(int i=0;i<rs->count;i++) free_route(&rs->items[i]);
    free(rs->items);
    rs->items=NULL; rs->count=0; rs->cap=0;
}
