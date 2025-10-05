
#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <stdio.h>
#include <limits.h>
#include "cgr.h"
#include "heap.h"
#include "leo_metrics.h"

// ═══════════════════════════════════════════════════════════════════════════
// Constantes y macros
// ═══════════════════════════════════════════════════════════════════════════

#define EPS_TIME  1e-12   // Tolerancia temporal (femtosegundos)
#define EPS_BYTES 1e-9    // Tolerancia de capacidad (~1 byte)

// Debug opcional (compilar con -DDEBUG_VERBOSE)
#ifdef DEBUG_VERBOSE
#define DEBUG_PRINT(...) fprintf(stderr, "[DEBUG CGR] " __VA_ARGS__)
#else
#define DEBUG_PRINT(...) ((void)0)
#endif

static inline int max3(int a, int b, int c) {
    int m = a > b ? a : b;
    return m > c ? m : c;
}

// ═══════════════════════════════════════════════════════════════════════════
// Construcción del índice by_from
// ═══════════════════════════════════════════════════════════════════════════

NeighborIndex* build_neighbor_index(const Contact *C, int N) {
    if (!C || N <= 0) return NULL;
    
    // Encontrar nodo máximo para dimensionar el array
    int maxNode = 0;
    for (int i = 0; i < N; i++) {
        maxNode = max3(maxNode, C[i].from, C[i].to);
    }

    NeighborIndex *ni = (NeighborIndex*)calloc(1, sizeof(NeighborIndex));
    if (!ni) return NULL;
    
    ni->node_cap = maxNode + 1;
    ni->by_from = (IndexList*)calloc(ni->node_cap, sizeof(IndexList));
    if (!ni->by_from) {
        free(ni);
        return NULL;
    }

    // Agrupar contactos por nodo origen
    for (int i = 0; i < N; i++) {
        int from = C[i].from;
        if (from < 0 || from >= ni->node_cap) continue;
        
        IndexList *L = &ni->by_from[from];
        if (L->count >= L->cap) {
            L->cap = (L->cap == 0 ? 8 : L->cap * 2);
            int *new_idxs = (int*)realloc(L->idxs, sizeof(int) * L->cap);
            if (!new_idxs) continue; // Skip en caso de fallo de memoria
            L->idxs = new_idxs;
        }
        L->idxs[L->count++] = i;
    }
    
    DEBUG_PRINT("Índice construido: %d nodos, %d contactos\n", ni->node_cap, N);
    return ni;
}

void free_neighbor_index(NeighborIndex* ni) {
    if (!ni) return;
    if (ni->by_from) {
        for (int i = 0; i < ni->node_cap; i++) {
            free(ni->by_from[i].idxs);
        }
        free(ni->by_from);
    }
    free(ni);
}

// ═══════════════════════════════════════════════════════════════════════════
// Helpers de filtros / prefijo forzado
// ═══════════════════════════════════════════════════════════════════════════

static inline int is_banned_id(int id, const CgrFilters *F) {
    if (!F || !F->banned_ids || F->banned_count <= 0) return 0;
    
    for (int i = 0; i < F->banned_count; i++) {
        if (F->banned_ids[i] == id) return 1;
    }
    return 0;
}

static inline int forced_id_at(const CgrFilters *F, int k) {
    if (!F || !F->forced_prefix_ids || F->forced_count <= 0) return -1;
    if (k < 0 || k >= F->forced_count) return -1;
    return F->forced_prefix_ids[k];
}

/* Dado un contacto índice ci, calcula cuántos elementos del prefijo forzado
   ya se han satisfecho en la ruta actual (desde la raíz). */
static int compute_prefix_done(int ci, const Label *lab, const Contact *C, const CgrFilters *F) {
    if (!F || !F->forced_prefix_ids || F->forced_count <= 0) return 0;

    // Contar longitud de la cadena hasta la raíz
    int len = 0, walker = ci;
    while (walker != -1) {
        len++;
        walker = lab[walker].prev_idx;
        // Protección contra ciclos
        if (len > 10000) {
            DEBUG_PRINT("WARNING: Posible ciclo en backtracking\n");
            break;
        }
    }

    if (len == 0) return 0;

    // Volcamos los ids de contacto en orden desde raíz → actual
    int *seq = (int*)malloc(sizeof(int) * len);
    if (!seq) return 0;
    
    int idx = len - 1;
    walker = ci;
    while (walker != -1 && idx >= 0) {
        seq[idx--] = C[walker].id;
        walker = lab[walker].prev_idx;
    }

    // Comparamos con el prefijo forzado desde el inicio
    int matched = 0;
    while (matched < F->forced_count && matched < len) {
        if (seq[matched] != F->forced_prefix_ids[matched]) break;
        matched++;
    }
    
    free(seq);
    return matched;
}

// ═══════════════════════════════════════════════════════════════════════════
// Cálculos de capacidad y ETA
// ═══════════════════════════════════════════════════════════════════════════

static double available_bytes_window(const Contact *c, double t_in) {
    if (t_in > c->t_end + EPS_TIME) return 0.0;
    
    double start_tx = (t_in < c->t_start) ? c->t_start : t_in;
    double window = c->t_end - start_tx - c->setup_s;
    if (window <= EPS_TIME) return 0.0;
    
    double rate = (c->rate_bps > 1.0) ? c->rate_bps : 1.0;
    return window * rate;
}

// ✅ MEJORA: Pre-check rápido de viabilidad sin calcular ETA completo
static inline int contact_is_viable(const Contact *c, double t_arrival, double bundle_bytes) {
    // Check temporal básico
    if (t_arrival > c->t_end + EPS_TIME) return 0;
    
    double start_tx = (t_arrival < c->t_start) ? c->t_start : t_arrival;
    double window = c->t_end - start_tx - c->setup_s;
    if (window <= EPS_TIME) return 0;
    
    // Check de capacidad
    double rate = (c->rate_bps > 1.0) ? c->rate_bps : 1.0;
    double cap_window = window * rate;
    double cap_actual = (c->residual_bytes < cap_window) ? c->residual_bytes : cap_window;
    
    if (cap_actual + EPS_BYTES < bundle_bytes) return 0;
    
    // Check que la transmisión cabe en la ventana
    double tx_time = bundle_bytes / rate;
    double finish = start_tx + c->setup_s + tx_time;
    if (finish > c->t_end + EPS_TIME) return 0;
    
    return 1;
}

// ETA al final del contacto, dado t_in (tiempo de llegada al nodo de entrada del contacto)
static double eta_contact(const Contact *c, double t_in, double bundle_bytes, double expiry_abs) {
    if (t_in > c->t_end + EPS_TIME) return DBL_MAX;
    
    double avail = available_bytes_window(c, t_in);
    double cap = (c->residual_bytes < avail) ? c->residual_bytes : avail;
    
    if (cap + EPS_BYTES < bundle_bytes) return DBL_MAX;

    double start_tx = (t_in < c->t_start) ? c->t_start : t_in;
    double rate = (c->rate_bps > 1.0) ? c->rate_bps : 1.0;
    double tx_time = bundle_bytes / rate;
    double finish = start_tx + c->setup_s + tx_time;
    
    if (finish > c->t_end + EPS_TIME) return DBL_MAX;

    double eta = finish + c->owlt;
    
    // Check de expiración
    if (expiry_abs > 0.0 && eta > expiry_abs + EPS_TIME) return DBL_MAX;
    
    return eta;
}

// ✅ NUEVA: Métrica compuesta que considera LEO (DESPUÉS de eta_contact) NOT USED

// static double eta_contact_leo(const Contact *c, double t_in, double bundle_bytes, 
//                               double expiry_abs, int prefer_isl) {
//     double base_eta = eta_contact(c, t_in, bundle_bytes, expiry_abs);
    
//     if (base_eta == DBL_MAX || !prefer_isl) return base_eta;
    
//     // Aplicar penalización por tipo de enlace
//     LeoMetrics m = compute_leo_metrics(c, t_in);
//     double penalty = link_type_penalty(m.link_type);
    
//     // Añadir penalización temporal (favorece ISL sin cambiar ETA real)
//     return base_eta + penalty;
// }

// ═══════════════════════════════════════════════════════════════════════════
// Búsqueda k=1 (wrapper sin filtros)
// ═══════════════════════════════════════════════════════════════════════════

Route cgr_best_route(const Contact *C, int N, const CgrParams *P, const NeighborIndex *NI) {
    return cgr_best_route_filtered(C, N, P, NI, NULL);
}

// ═══════════════════════════════════════════════════════════════════════════
// Búsqueda k=1 con filtros (banned + forced prefix) — Core CGR
// ═══════════════════════════════════════════════════════════════════════════

Route cgr_best_route_filtered(const Contact *C, int N, const CgrParams *P,
                              const NeighborIndex *NI, const CgrFilters *F)
{
    Route R = {.contact_ids = NULL, .hops = 0, .eta = DBL_MAX, .found = false};
    
    // Validación de entrada
    if (!P || !NI || !C || N <= 0) {
        DEBUG_PRINT("ERROR: Parámetros inválidos\n");
        return R;
    }
    
    if (P->src_node < 0 || P->src_node >= NI->node_cap) {
        DEBUG_PRINT("ERROR: Nodo origen %d fuera de rango [0,%d)\n", P->src_node, NI->node_cap);
        return R;
    }
    
    if (P->dst_node < 0 || P->dst_node >= NI->node_cap) {
        DEBUG_PRINT("ERROR: Nodo destino %d fuera de rango [0,%d)\n", P->dst_node, NI->node_cap);
        return R;
    }

    DEBUG_PRINT("Búsqueda %d→%d, bytes=%.0f, t0=%.3f\n", 
                P->src_node, P->dst_node, P->bundle_bytes, P->t0);

    // Inicializar labels (uno por contacto)
    Label *lab = (Label*)malloc(sizeof(Label) * N);
    if (!lab) return R;
    
    for (int i = 0; i < N; i++) {
        lab[i].contact_idx = i;
        lab[i].eta = DBL_MAX;
        lab[i].prev_idx = -1;
    }

    MinHeap *pq = heap_new(64);
    if (!pq) {
        free(lab);
        return R;
    }
    
    double expiry_abs = (P->expiry > 0.0) ? (P->t0 + P->expiry) : 0.0;

    // ─────────────────────────────────────────────────────────────────────
    // Semilla: inicializar desde el nodo origen
    // ─────────────────────────────────────────────────────────────────────
    
    if (F && F->forced_prefix_ids && F->forced_count > 0) {
        // Modo prefijo forzado: buscar el primer contacto específico
        int first_id = forced_id_at(F, 0);
        DEBUG_PRINT("Buscando prefijo forzado, primer contacto=%d\n", first_id);
        
        for (int ci = 0; ci < N; ci++) {
            if (C[ci].id != first_id) continue;
            if (C[ci].from != P->src_node) continue;
            if (is_banned_id(C[ci].id, F)) continue;
            
            // Pre-check rápido
            if (!contact_is_viable(&C[ci], P->t0, P->bundle_bytes)) continue;
            
            double eta = eta_contact(&C[ci], P->t0, P->bundle_bytes, expiry_abs);
            if (eta == DBL_MAX) continue;

            lab[ci].eta = eta;
            lab[ci].prev_idx = -1;
            heap_push(pq, (Label){.contact_idx = ci, .eta = eta, .prev_idx = -1});
            DEBUG_PRINT("Semilla: contacto %d (id=%d), eta=%.3f\n", ci, C[ci].id, eta);
            break; // Solo uno
        }
    } else {
        // Modo normal: todos los contactos que salen del origen
        if (P->src_node >= 0 && P->src_node < NI->node_cap) {
            IndexList L = NI->by_from[P->src_node];
            DEBUG_PRINT("Semilla: %d contactos desde nodo %d\n", L.count, P->src_node);
            
            for (int k = 0; k < L.count; k++) {
                int ci = L.idxs[k];
                
                if (F && is_banned_id(C[ci].id, F)) continue;
                
                // Pre-check rápido
                if (!contact_is_viable(&C[ci], P->t0, P->bundle_bytes)) continue;
                
                double eta = eta_contact(&C[ci], P->t0, P->bundle_bytes, expiry_abs);
                if (eta == DBL_MAX) continue;
                
                if (eta < lab[ci].eta) {
                    lab[ci].eta = eta;
                    lab[ci].prev_idx = -1;
                    heap_push(pq, (Label){.contact_idx = ci, .eta = eta, .prev_idx = -1});
                    DEBUG_PRINT("  Semilla: contacto %d (id=%d), eta=%.3f\n", ci, C[ci].id, eta);
                }
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────
    // Dijkstra temporal
    // ─────────────────────────────────────────────────────────────────────
    
    int best_end = -1;
    double best_eta = DBL_MAX;
    int expansions = 0;

    while (!heap_empty(pq)) {
        Label cur = heap_pop(pq);
        int ci = cur.contact_idx;
        double eta_here = cur.eta;
        
        expansions++;

        // Label desactualizada (ya procesamos este contacto con mejor ETA)
        if (eta_here > lab[ci].eta + EPS_TIME) continue;

        // ¿Cuánto prefijo hemos cumplido en esta ruta?
        int prefix_done = compute_prefix_done(ci, lab, C, F);

        // ¿Llegamos al destino?
        if (C[ci].to == P->dst_node) {
            // Si hay prefijo, asegúrate de que está completo
            if (!(F && F->forced_prefix_ids && F->forced_count > 0) || 
                prefix_done >= F->forced_count) {
                best_end = ci;
                best_eta = eta_here;
                DEBUG_PRINT("✓ Destino alcanzado: contacto %d (id=%d), eta=%.3f, expansiones=%d\n",
                           ci, C[ci].id, eta_here, expansions);
                break; // Óptimo por Dijkstra
            }
        }

        // Expandir vecinos desde el nodo destino de este contacto
        int next_node = C[ci].to;
        if (next_node < 0 || next_node >= NI->node_cap) continue;

        IndexList L = NI->by_from[next_node];

        // ¿Aún falta un contacto específico del prefijo?
        int need_forced_next = -1;
        if (F && F->forced_prefix_ids && F->forced_count > 0 && prefix_done < F->forced_count) {
            need_forced_next = forced_id_at(F, prefix_done);
            DEBUG_PRINT("  Requiere contacto forzado #%d: id=%d\n", prefix_done, need_forced_next);
        }

        for (int kk = 0; kk < L.count; kk++) {
            int nj = L.idxs[kk];

            // Filtros
            if (need_forced_next != -1 && C[nj].id != need_forced_next) continue;
            if (F && is_banned_id(C[nj].id, F)) continue;
            
            // Pre-check rápido antes de calcular ETA completo
            if (!contact_is_viable(&C[nj], eta_here, P->bundle_bytes)) continue;

            double eta_n = eta_contact(&C[nj], eta_here, P->bundle_bytes, expiry_abs);
            if (eta_n == DBL_MAX) continue;

            // Actualizar si es mejor
            if (eta_n + EPS_TIME < lab[nj].eta) {
                lab[nj].eta = eta_n;
                lab[nj].prev_idx = ci;
                heap_push(pq, (Label){.contact_idx = nj, .eta = eta_n, .prev_idx = ci});
            }
        }
    }

    heap_free(pq);

    if (best_end == -1) {
        DEBUG_PRINT("✗ No se encontró ruta (expansiones=%d)\n", expansions);
        free(lab);
        return R; // No encontrada
    }

    // ─────────────────────────────────────────────────────────────────────
    // Reconstrucción de ruta (backtracking)
    // ─────────────────────────────────────────────────────────────────────
    
    int cap = 16, len = 0;
    int *rev = (int*)malloc(sizeof(int) * cap);
    if (!rev) {
        free(lab);
        return R;
    }
    
    int cur = best_end;
    while (cur != -1) {
        if (len >= cap) {
            cap *= 2;
            int *new_rev = (int*)realloc(rev, sizeof(int) * cap);
            if (!new_rev) {
                free(rev);
                free(lab);
                return R;
            }
            rev = new_rev;
        }
        rev[len++] = cur;
        cur = lab[cur].prev_idx;
    }
    
    // Invertir para obtener orden correcto
    R.contact_ids = (int*)malloc(sizeof(int) * len);
    if (!R.contact_ids) {
        free(rev);
        free(lab);
        return R;
    }
    
    for (int i = 0; i < len; i++) {
        R.contact_ids[i] = C[rev[len - 1 - i]].id;
    }
    R.hops = len;
    R.eta = best_eta;
    R.found = true;

    DEBUG_PRINT("✓ Ruta reconstruida: %d saltos, eta=%.3f\n", len, best_eta);

    free(rev);
    free(lab);
    return R;
}

void free_route(Route *r) {
    if (!r) return;
    free(r->contact_ids);
    r->contact_ids = NULL;
    r->hops = 0;
    r->eta = 0;
    r->found = false;
}

// ═══════════════════════════════════════════════════════════════════════════
// K rutas por CONSUMO (modo práctico)
// ═══════════════════════════════════════════════════════════════════════════

static void consume_capacity(Contact *C, int N, const Route *route, const CgrParams *P) {
    if (!route->found || route->hops <= 0) return;

    DEBUG_PRINT("Consumiendo capacidad para ruta con %d saltos\n", route->hops);

    for (int step = 0; step < route->hops; step++) {
        int id = route->contact_ids[step];
        for (int i = 0; i < N; i++) {
            if (C[i].id == id) {
                double bytes = P->bundle_bytes;
                
                if (C[i].residual_bytes >= bytes) {
                    C[i].residual_bytes -= bytes;
                } else {
                    C[i].residual_bytes = 0.0;
                }
                
                DEBUG_PRINT("  Contacto %d: %.0f → %.0f bytes\n", 
                           id, C[i].residual_bytes + bytes, C[i].residual_bytes);
                break;
            }
        }
    }
}

Routes cgr_k_routes(const Contact *C_in, int N, const CgrParams *P, const NeighborIndex *NI, int K) {
    Routes RS = {.items = NULL, .count = 0, .cap = 0};
    
    if (K <= 0 || !C_in || !P || !NI) return RS;

    DEBUG_PRINT("K rutas por consumo: K=%d\n", K);

    // Copia de trabajo (consumiremos capacidad)
    Contact *C = (Contact*)malloc(sizeof(Contact) * N);
    if (!C) return RS;
    
    memcpy(C, C_in, sizeof(Contact) * N);

    RS.cap = K;
    RS.items = (Route*)calloc(RS.cap, sizeof(Route));
    if (!RS.items) {
        free(C);
        return RS;
    }

    for (int k = 0; k < K; k++) {
        DEBUG_PRINT("Iteración K=%d/%d\n", k + 1, K);
        
        Route r = cgr_best_route(C, N, P, NI);
        if (!r.found) {
            DEBUG_PRINT("No hay más rutas disponibles\n");
            break;
        }
        
        RS.items[RS.count++] = r;
        consume_capacity(C, N, &r, P);
    }

    free(C);
    return RS;
}

// ═══════════════════════════════════════════════════════════════════════════
// K rutas Yen-lite (diversidad sin consumo) - ✅ FIX DUPLICADOS
// ═══════════════════════════════════════════════════════════════════════════

// ✅ Helper: verificar si una ruta ya existe en el resultado
static int route_already_exists(const Routes *rs, const Route *candidate) {
    for (int i = 0; i < rs->count; i++) {
        const Route *existing = &rs->items[i];
        
        // Mismo número de saltos
        if (existing->hops != candidate->hops) continue;
        
        // Comparar secuencia completa
        int same = 1;
        for (int j = 0; j < existing->hops; j++) {
            if (existing->contact_ids[j] != candidate->contact_ids[j]) {
                same = 0;
                break;
            }
        }
        
        if (same) return 1; // Duplicado encontrado
    }
    return 0;
}

Routes cgr_k_yen(const Contact *C, int N, const CgrParams *P, const NeighborIndex *NI, int K) {
    Routes out = {.items = NULL, .count = 0, .cap = 0};
    
    if (K <= 0 || !C || !P || !NI) return out;

    DEBUG_PRINT("K rutas Yen-lite: K=%d\n", K);

    out.cap = K;
    out.items = (Route*)calloc(K, sizeof(Route));
    if (!out.items) return out;

    // Ruta base (sin filtros)
    Route base = cgr_best_route_filtered(C, N, P, NI, NULL);
    if (!base.found) {
        DEBUG_PRINT("No existe ruta base\n");
        return out;
    }
    
    out.items[out.count++] = base;
    DEBUG_PRINT("Ruta base: %d saltos, eta=%.3f\n", base.hops, base.eta);

    // ✅ FIX: Búsqueda exhaustiva de alternativas con deduplicación global
    int max_attempts = K * 20; // Límite de intentos
    int attempts = 0;
    
    while (out.count < K && attempts < max_attempts) {
        attempts++;
        
        double best_eta = DBL_MAX;
        Route best = {.contact_ids = NULL, .hops = 0, .eta = DBL_MAX, .found = false};

        // Probar desvíos desde TODAS las rutas ya encontradas
        for (int route_idx = 0; route_idx < out.count; route_idx++) {
            const Route *ref = &out.items[route_idx];
            
            // Probar desvío en cada posición
            for (int i = 0; i < ref->hops; i++) {
                CgrFilters F;
                memset(&F, 0, sizeof(F));
                
                // Prefijo forzado: [0..i-1]
                F.forced_prefix_ids = ref->contact_ids;
                F.forced_count = i;

                // Contacto baneado: el i-ésimo
                int banned_one = ref->contact_ids[i];
                F.banned_ids = &banned_one;
                F.banned_count = 1;

                Route cand = cgr_best_route_filtered(C, N, P, NI, &F);
                if (!cand.found) continue;

                // ✅ FIX: Verificar contra TODAS las rutas existentes
                if (route_already_exists(&out, &cand)) {
                    free_route(&cand);
                    continue;
                }

                // Quedarnos con la mejor nueva alternativa
                if (cand.eta < best_eta) {
                    if (best.found) free_route(&best);
                    best = cand;
                    best_eta = cand.eta;
                } else {
                    free_route(&cand);
                }
            }
        }

        // Si no encontramos ninguna nueva, terminar
        if (!best.found) {
            DEBUG_PRINT("No hay más alternativas después de %d intentos\n", attempts);
            break;
        }
        
        out.items[out.count++] = best;
        DEBUG_PRINT("✓ Ruta alternativa #%d: %d saltos, eta=%.3f\n", 
                   out.count, best.hops, best.eta);
    }

    return out;
}

void free_routes(Routes *rs) {
    if (!rs || !rs->items) return;
    
    for (int i = 0; i < rs->count; i++) {
        free_route(&rs->items[i]);
    }
    
    free(rs->items);
    rs->items = NULL;
    rs->count = 0;
    rs->cap = 0;
}
