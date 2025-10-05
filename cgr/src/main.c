
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <stdbool.h>
#include <limits.h>
#include <errno.h>
#include <ctype.h>
#include "csv.h"
#include "cgr.h"

typedef enum { FMT_JSON=0, FMT_TEXT=1 } OutputFmt;

static void usage(const char* prog){
    fprintf(stderr,
    "Usage:\n"
    "  %s --contacts <file> --src <node> --dst <node> --t0 <sec> --bytes <B>\n"
    "     [--expiry <sec>] [--k <num>] [--k-yen <num>] [--pretty] [--format text|json]\n"
    "\n"
    "Notas:\n"
    "  --k      : K rutas iterando por CONSUMO de capacidad (heurístico práctico).\n"
    "  --k-yen  : K rutas diversas estilo Yen (SIN consumir capacidad). Si ambos, prioriza --k-yen.\n"
    "  --pretty : JSON con identado y saltos de línea.\n"
    "  --format : 'json' (por defecto) o 'text' para salida legible en consola.\n",
    prog);
}

// ✅ FIX: Validación robusta de enteros
static int parse_int_safe(const char *s, int *out){
    char *endptr;
    errno = 0;
    long val = strtol(s, &endptr, 10);
    
    // Validar: no vacío, sin basura al final, rango válido
    if (endptr == s || *endptr != '\0' || errno == ERANGE || val < 0 || val > INT_MAX) {
        return -1;
    }
    *out = (int)val;
    return 0;
}

// ✅ FIX: Validación robusta de doubles
static int parse_double_safe(const char *s, double *out){
    char *endptr;
    errno = 0;
    double val = strtod(s, &endptr);
    
    if (endptr == s || *endptr != '\0' || errno == ERANGE || val < 0.0) {
        return -1;
    }
    *out = val;
    return 0;
}

/* ----------------------- Helpers de impresión JSON ----------------------- */

static void print_json_route_compact(const Route *R, double t0){
    printf("{\"eta\":%.6f,\"latency\":%.6f,\"hops\":%d,\"contacts\":[",
           R->eta, R->eta - t0, R->hops);
    for(int i=0;i<R->hops;i++){
        printf("%s%d", (i? ",":""), R->contact_ids[i]);
    }
    printf("]}");
}

static void print_json_route_pretty(const Route *R, double t0, int indent){
    const char *sp = "                                                                ";
    int pad = indent < 64 ? indent : 64;
    printf("%.*s{\n", pad, sp);
    printf("%.*s  \"eta\": %.6f,\n", pad, sp, R->eta);
    printf("%.*s  \"latency\": %.6f,\n", pad, sp, R->eta - t0);
    printf("%.*s  \"hops\": %d,\n", pad, sp, R->hops);
    printf("%.*s  \"contacts\": [", pad, sp);
    for(int i=0;i<R->hops;i++){
        printf("%s%d", (i? ", ": ""), R->contact_ids[i]);
    }
    printf("]\n%.*s}", pad, sp);
}

static void print_json_single(const Route *R, double t0, int pretty){
    if(!R->found){
        if(pretty) {
            printf("{\n  \"found\": false\n}\n");
        } else {
            printf("{\"found\":false}\n");
        }
        return;
    }
    if(pretty){
        printf("{\n  \"found\": true,\n  \"eta\": %.6f,\n  \"latency\": %.6f,\n  \"hops\": %d,\n  \"contacts\": [",
               R->eta, R->eta - t0, R->hops);
        for(int i=0;i<R->hops;i++){
            printf("%s%d", (i? ", ": ""), R->contact_ids[i]);
        }
        printf("]\n}\n");
    } else {
        printf("{\"found\":true,\"eta\":%.6f,\"latency\":%.6f,\"hops\":%d,\"contacts\":[",
               R->eta, R->eta - t0, R->hops);
        for(int i=0;i<R->hops;i++){
            printf("%s%d", (i? ",":""), R->contact_ids[i]);
        }
        printf("]}\n");
    }
}

static void print_json_multi(const Routes *RS, double t0, int pretty){
    if(RS->count == 0){
        if(pretty) {
            printf("{\n  \"found\": false,\n  \"routes\": []\n}\n");
        } else {
            printf("{\"found\":false,\"routes\":[]}\n");
        }
        return;
    }
    if(pretty){
        printf("{\n  \"found\": true,\n  \"routes\": [\n");
        for(int r=0; r<RS->count; r++){
            print_json_route_pretty(&RS->items[r], t0, 4);
            printf("%s\n", (r+1<RS->count? ",": ""));
        }
        printf("  ]\n}\n");
    } else {
        printf("{\"found\":true,\"routes\":[");
        for(int r=0; r<RS->count; r++){
            print_json_route_compact(&RS->items[r], t0);
            printf("%s", (r+1<RS->count? ",":""));
        }
        printf("]}\n");
    }
}

/* ----------------------- Helpers de impresión TEXTO ----------------------- */

static void print_text_single(const Route *R, double t0){
    if(!R->found){
        printf("No se encontró ruta.\n");
        return;
    }
    printf("Ruta óptima (k=1)\n");
    printf("• ETA: %.3f s   • Latencia: %.3f s   • Saltos: %d\n", R->eta, R->eta - t0, R->hops);
    printf("• Secuencia de contactos: ");
    for(int i=0;i<R->hops;i++){
        if(i) printf(" → ");
        printf("%d", R->contact_ids[i]);
    }
    printf("\n");
}

// ✅ NUEVA: Versión mejorada con estadísticas y mejor formato
static void print_text_multi_enhanced(const Routes *RS, double t0, const char *title){
    if(RS->count == 0){
        printf("No se encontraron rutas.\n");
        return;
    }
    
    if(title && *title) printf("%s\n", title);
    
    // ✅ Calcular estadísticas
    double min_eta = DBL_MAX, max_eta = 0, sum_eta = 0;
    int min_hops = INT_MAX, max_hops = 0;
    
    for(int r=0; r<RS->count; r++){
        const Route *R = &RS->items[r];
        if(R->eta < min_eta) min_eta = R->eta;
        if(R->eta > max_eta) max_eta = R->eta;
        sum_eta += R->eta;
        if(R->hops < min_hops) min_hops = R->hops;
        if(R->hops > max_hops) max_hops = R->hops;
    }
    double avg_eta = sum_eta / RS->count;
    
    printf("┌─────────────────────────────────────────────────────────┐\n");
    printf("│ 📊 Estadísticas de %d ruta(s):                          \n", RS->count);
    printf("│   • ETA mínimo:   %.3f s                                \n", min_eta);
    printf("│   • ETA máximo:   %.3f s                                \n", max_eta);
    printf("│   • ETA promedio: %.3f s                                \n", avg_eta);
    printf("│   • Diversidad:   %.3f s (Δmax-min)                    \n", max_eta - min_eta);
    printf("│   • Saltos:       [%d, %d]                              \n", min_hops, max_hops);
    printf("└─────────────────────────────────────────────────────────┘\n\n");
    
    for(int r=0; r<RS->count; r++){
        const Route *R = &RS->items[r];
        double latency = R->eta - t0;
        
        // Indicador visual de calidad (relativo al mejor)
        double quality = (max_eta > min_eta) ? (R->eta - min_eta) / (max_eta - min_eta) : 0.0;
        const char *indicator;
        if(quality < 0.1) indicator = "🟢"; // Óptima
        else if(quality < 0.3) indicator = "🟡"; // Buena
        else indicator = "🟠"; // Alternativa
        
        printf("%s Ruta #%d\n", indicator, r+1);
        printf("  ├─ ETA:      %.3f s\n", R->eta);
        printf("  ├─ Latencia: %.3f s\n", latency);
        printf("  ├─ Saltos:   %d\n", R->hops);
        printf("  ├─ Overhead: +%.1f%% vs óptima\n", 
               100.0 * (R->eta - min_eta) / (min_eta + 1e-9));
        printf("  └─ Path:     ");
        for(int i=0; i<R->hops; i++){
            if(i) printf(" → ");
            printf("%d", R->contact_ids[i]);
        }
        printf("\n");
        
        if(r+1 < RS->count){
            printf("\n");
        }
    }
}

/* ------------------------------------------------------------------- */

int main(int argc, char **argv){
    const char *contacts_path = NULL;
    CgrParams P = { .src_node=-1, .dst_node=-1, .t0=0.0, .bundle_bytes=0.0, .expiry=0.0 };
    int K_consume = 1;
    int K_yen = 0;
    int pretty = 0;
    OutputFmt fmt = FMT_JSON;

    // ✅ FIX: Parsing con validación
    for(int i=1;i<argc;i++){
        if(!strcmp(argv[i],"--contacts") && i+1<argc) {
            contacts_path = argv[++i];
        }
        else if(!strcmp(argv[i],"--src") && i+1<argc) {
            if(parse_int_safe(argv[i+1], &P.src_node) != 0){
                fprintf(stderr, "Error: --src debe ser un entero válido ≥0 (recibido: '%s')\n", argv[i+1]);
                return 2;
            }
            i++;
        }
        else if(!strcmp(argv[i],"--dst") && i+1<argc) {
            if(parse_int_safe(argv[i+1], &P.dst_node) != 0){
                fprintf(stderr, "Error: --dst debe ser un entero válido ≥0 (recibido: '%s')\n", argv[i+1]);
                return 2;
            }
            i++;
        }
        else if(!strcmp(argv[i],"--t0")  && i+1<argc) {
            if(parse_double_safe(argv[i+1], &P.t0) != 0){
                fprintf(stderr, "Error: --t0 debe ser un número ≥0 (recibido: '%s')\n", argv[i+1]);
                return 2;
            }
            i++;
        }
        else if(!strcmp(argv[i],"--bytes") && i+1<argc) {
            if(parse_double_safe(argv[i+1], &P.bundle_bytes) != 0){
                fprintf(stderr, "Error: --bytes debe ser un número ≥0 (recibido: '%s')\n", argv[i+1]);
                return 2;
            }
            i++;
        }
        else if(!strcmp(argv[i],"--expiry") && i+1<argc) {
            if(parse_double_safe(argv[i+1], &P.expiry) != 0){
                fprintf(stderr, "Error: --expiry debe ser un número ≥0 (recibido: '%s')\n", argv[i+1]);
                return 2;
            }
            i++;
        }
        else if(!strcmp(argv[i],"--k") && i+1<argc) {
            if(parse_int_safe(argv[i+1], &K_consume) != 0 || K_consume < 1){
                fprintf(stderr, "Error: --k debe ser un entero ≥1 (recibido: '%s')\n", argv[i+1]);
                return 2;
            }
            i++;
        }
        else if(!strcmp(argv[i],"--k-yen") && i+1<argc) {
            if(parse_int_safe(argv[i+1], &K_yen) != 0){
                fprintf(stderr, "Error: --k-yen debe ser un entero ≥0 (recibido: '%s')\n", argv[i+1]);
                return 2;
            }
            i++;
        }
        else if(!strcmp(argv[i],"--pretty")) {
            pretty = 1;
        }
        else if(!strcmp(argv[i],"--format") && i+1<argc){
            const char *v = argv[++i];
            if(!strcmp(v,"text")) fmt = FMT_TEXT;
            else if(!strcmp(v,"json")) fmt = FMT_JSON;
            else {
                fprintf(stderr, "Error: --format debe ser 'text' o 'json' (recibido: '%s')\n", v);
                return 2;
            }
        }
        else { 
            fprintf(stderr, "Error: argumento desconocido o faltante: %s\n", argv[i]);
            usage(argv[0]); 
            return 2; 
        }
    }

    // ✅ FIX: Validación mejorada
    if(!contacts_path){
        fprintf(stderr, "Error: falta --contacts <archivo>\n");
        usage(argv[0]); 
        return 2;
    }
    if(P.src_node < 0){
        fprintf(stderr, "Error: falta --src <nodo> o valor inválido\n");
        usage(argv[0]); 
        return 2;
    }
    if(P.dst_node < 0){
        fprintf(stderr, "Error: falta --dst <nodo> o valor inválido\n");
        usage(argv[0]); 
        return 2;
    }
    if(P.bundle_bytes <= 0.0){
        fprintf(stderr, "Error: --bytes debe ser > 0 (recibido: %.0f)\n", P.bundle_bytes);
        usage(argv[0]); 
        return 2;
    }
    if(K_consume < 1) K_consume = 1;
    if(K_yen < 0) K_yen = 0;

    Contact *C=NULL; 
    int N = load_contacts_csv(contacts_path, &C);
    if(N<=0){ 
        fprintf(stderr,"Error: no se pudieron cargar contactos desde %s\n", contacts_path); 
        return 1; 
    }

    NeighborIndex *NI = build_neighbor_index(C, N);

    // Prioriza --k-yen si se indica
    if(K_yen > 0){
        Routes RS = cgr_k_yen(C, N, &P, NI, K_yen);
        if(fmt == FMT_JSON) {
            print_json_multi(&RS, P.t0, pretty);
        } else {
            print_text_multi_enhanced(&RS, P.t0, "Rutas K (Yen-lite, sin consumo)");
        }
        free_routes(&RS);
        free_neighbor_index(NI);
        free(C);
        return 0;
    }

    // Modo consumo
    if(K_consume == 1){
        Route R = cgr_best_route(C, N, &P, NI);
        if(fmt == FMT_JSON) {
            print_json_single(&R, P.t0, pretty);
        } else {
            print_text_single(&R, P.t0);
        }
        free_route(&R);
    } else {
        Routes RS = cgr_k_routes(C, N, &P, NI, K_consume);
        if(fmt == FMT_JSON) {
            print_json_multi(&RS, P.t0, pretty);
        } else {
            print_text_multi_enhanced(&RS, P.t0, "Rutas K (consumo de capacidad)");
        }
        free_routes(&RS);
    }

    free_neighbor_index(NI);
    free(C);
    return 0;
}
