// src/cgr_live.c — CGR con actualización continua de datos desde NASA
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <time.h>
#include "csv.h"
#include "cgr.h"
#include "nasa_api.h"

static volatile int keep_running = 1;

void signal_handler(int signum) {
    (void)signum;
    keep_running = 0;
    printf("\n[SIGNAL] Deteniendo simulación...\n");
}

void print_status(const UpdateState *state, int cycle, double sim_time) {
    printf("\n╔════════════════════════════════════════════════════════╗\n");
    printf("║  CICLO #%-4d | Tiempo simulado: %.1f s              \n", cycle, sim_time);
    printf("╠════════════════════════════════════════════════════════╣\n");
    printf("║  Contactos activos: %-6d                             \n", state->contact_count);
    printf("║  Actualizaciones:   %-6d                             \n", state->update_counter);
    printf("║  Errores:           %-6d                             \n", state->error_count);
    if (state->last_update > 0) {
        char buf[64];
        strftime(buf, sizeof(buf), "%H:%M:%S", localtime(&state->last_update));
        printf("║  Última actualización: %s                           \n", buf);
    }
    printf("╚════════════════════════════════════════════════════════╝\n");
}

int main(int argc, char **argv) {
    // Configuración
    const char *dataset_id = (argc > 1) ? argv[1] : NULL;
    const char *api_key = getenv("NASA_API_KEY");
    
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    printf("╔══════════════════════════════════════════════════════════╗\n");
    printf("║     CGR LIVE - Simulación con Datos NASA en Tiempo Real  ║\n");
    printf("╚══════════════════════════════════════════════════════════╝\n\n");
    
    if (!dataset_id) {
        printf("MODO SIMULACIÓN: Usando datos locales (data/contacts_realistic.csv)\n");
        printf("Para usar API de NASA: %s <dataset-id>\n", argv[0]);
        printf("Ejemplo: %s abcd-1234\n\n", argv[0]);
    }
    
    // Inicializar API
    NasaApiConfig *api = nasa_api_init(api_key, dataset_id);
    if (!api) {
        fprintf(stderr, "Error: No se pudo inicializar API\n");
        return 1;
    }
    
    api->update_interval_s = 60; // Actualizar cada 60 segundos en simulación
    
    UpdateState state = {0};
    Contact *C = NULL;
    int N = 0;
    
    // Carga inicial
    if (dataset_id) {
        printf("[API] Intentando conectar con NASA data.gov...\n");
        nasa_api_update_if_needed(api, &state, &C, &N);
    }
    
    // Fallback a datos locales
    if (N == 0) {
        printf("[LOCAL] Cargando datos desde data/contacts_realistic.csv\n");
        N = load_contacts_csv("data/contacts_realistic.csv", &C);
        if (N <= 0) {
            fprintf(stderr, "Error: No se pudieron cargar contactos\n");
            nasa_api_free(api);
            return 1;
        }
        state.contact_count = N;
    }
    
    printf("✓ Cargados %d contactos\n\n", N);
    
    // Construir índice
    NeighborIndex *NI = build_neighbor_index(C, N);
    
    // Parámetros de simulación
    CgrParams P = {
        .src_node = 100,
        .dst_node = 200,
        .t0 = 0.0,
        .bundle_bytes = 50e6, // 50 MB
        .expiry = 0.0
    };
    
    int cycle = 0;
    double sim_time = 0.0;
    
    printf("🚀 Iniciando bucle de simulación (Ctrl+C para detener)...\n");
    sleep(2);
    
    // ═══════════════════════════════════════════════════════════
    // BUCLE PRINCIPAL: Actualización y enrutamiento continuo
    // ═══════════════════════════════════════════════════════════
    
    while (keep_running) {
        cycle++;
        
        // Actualizar timestamp de simulación
        P.t0 = sim_time;
        
        // Intentar actualizar contactos desde API (si aplica)
        if (dataset_id) {
            int updated = nasa_api_update_if_needed(api, &state, &C, &N);
            if (updated > 0) {
                printf("\n[API] ✓ Contactos actualizados desde NASA\n");
                // Reconstruir índice
                free_neighbor_index(NI);
                NI = build_neighbor_index(C, N);
            }
        }
        
        // Mostrar estado
        print_status(&state, cycle, sim_time);
        
        // Calcular mejor ruta (k=1)
        Route R = cgr_best_route(C, N, &P, NI);
        
        if (R.found) {
            printf("\n🛰️  RUTA ÓPTIMA ENCONTRADA:\n");
            printf("   • ETA:      %.3f s\n", R.eta);
            printf("   • Latencia: %.3f s\n", R.eta - P.t0);
            printf("   • Saltos:   %d\n", R.hops);
            printf("   • Path:     ");
            for (int i = 0; i < R.hops; i++) {
                if (i > 0) printf(" → ");
                printf("%d", R.contact_ids[i]);
            }
            printf("\n");
            
            free_route(&R);
        } else {
            printf("\n⚠️  NO HAY RUTA DISPONIBLE\n");
        }
        
        // Calcular K rutas alternativas (Yen)
        printf("\n📊 Rutas alternativas (K=3):\n");
        Routes RS = cgr_k_yen(C, N, &P, NI, 3);
        
        for (int i = 0; i < RS.count; i++) {
            printf("   #%d: ETA=%.3f s, %d saltos\n", 
                   i+1, RS.items[i].eta, RS.items[i].hops);
        }
        
        free_routes(&RS);
        
        // Avanzar tiempo de simulación
        sim_time += 10.0; // Avanzar 10 segundos por ciclo
        
        // Esperar antes del próximo ciclo
        printf("\n⏳ Próximo ciclo en 1 segundos...\n");
        sleep(1);
    }
    
    // Limpieza
    printf("\n\n[CLEANUP] Liberando recursos...\n");
    free_neighbor_index(NI);
    free(C);
    nasa_api_free(api);
    
    printf("✓ Simulación finalizada después de %d ciclos\n", cycle);
    
    return 0;
}
