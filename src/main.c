// src/main.c — CLI: salida estética (--pretty) y formato texto (--format text)
// Soporta: k por consumo (--k) y K Yen-lite (--k-yen)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <stdbool.h>
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

static int parse_int(const char *s){ return (int)strtol(s, NULL, 10); }
static double parse_double(const char *s){ return strtod(s, NULL); }

/* ----------------------- Helpers de impresión ----------------------- */

static void print_json_route_compact(const Route *R, double t0){
    printf("{\"eta\":%.6f,\"latency\":%.6f,\"hops\":%d,\"contacts\":[",
           R->eta, R->eta - t0, R->hops);
    for(int i=0;i<R->hops;i++){
        printf("%s%d", (i? ",":""), R->contact_ids[i]);
    }
    printf("]}");
}

static void print_json_route_pretty(const Route *R, double t0, int indent){
    // indent es número de espacios previos
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

static void print_text_multi(const Routes *RS, double t0, const char *title){
    if(RS->count == 0){
        printf("No se encontraron rutas.\n");
        return;
    }
    if(title && *title) printf("%s\n", title);
    for(int r=0; r<RS->count; r++){
        const Route *R = &RS->items[r];
        printf("Ruta #%d  |  ETA: %.3f s  |  Latencia: %.3f s  |  Saltos: %d\n", r+1, R->eta, R->eta - t0, R->hops);
        printf("  contactos: ");
        for(int i=0;i<R->hops;i++){
            if(i) printf(" → ");
            printf("%d", R->contact_ids[i]);
        }
        printf("\n");
        if(r+1<RS->count) printf("— — — — — — — — — — — — — —\n");
    }
}

/* ------------------------------------------------------------------- */

int main(int argc, char **argv){
    const char *contacts_path = NULL;
    CgrParams P = { .src_node=-1, .dst_node=-1, .t0=0.0, .bundle_bytes=0.0, .expiry=0.0 };
    int K_consume = 1;
    int K_yen = 0; // si >0, usamos yen
    int pretty = 0;
    OutputFmt fmt = FMT_JSON;

    for(int i=1;i<argc;i++){
        if(!strcmp(argv[i],"--contacts") && i+1<argc) contacts_path = argv[++i];
        else if(!strcmp(argv[i],"--src") && i+1<argc) P.src_node = parse_int(argv[++i]);
        else if(!strcmp(argv[i],"--dst") && i+1<argc) P.dst_node = parse_int(argv[++i]);
        else if(!strcmp(argv[i],"--t0")  && i+1<argc) P.t0 = parse_double(argv[++i]);
        else if(!strcmp(argv[i],"--bytes") && i+1<argc) P.bundle_bytes = parse_double(argv[++i]);
        else if(!strcmp(argv[i],"--expiry") && i+1<argc) P.expiry = parse_double(argv[++i]);
        else if(!strcmp(argv[i],"--k") && i+1<argc) K_consume = parse_int(argv[++i]);
        else if(!strcmp(argv[i],"--k-yen") && i+1<argc) K_yen = parse_int(argv[++i]);
        else if(!strcmp(argv[i],"--pretty")) pretty = 1;
        else if(!strcmp(argv[i],"--format") && i+1<argc){
            const char *v = argv[++i];
            if(!strcmp(v,"text")) fmt = FMT_TEXT;
            else fmt = FMT_JSON;
        }
        else { usage(argv[0]); return 2; }
    }

    if(!contacts_path || P.src_node<0 || P.dst_node<0 || P.bundle_bytes<=0.0){
        usage(argv[0]); return 2;
    }
    if(K_consume < 1) K_consume = 1;
    if(K_yen < 0) K_yen = 0;

    Contact *C=NULL; int N = load_contacts_csv(contacts_path, &C);
    if(N<=0){ fprintf(stderr,"Error: no contacts loaded from %s\n", contacts_path); return 1; }

    NeighborIndex *NI = build_neighbor_index(C, N);

    // Prioriza --k-yen si se indica
    if(K_yen > 0){
        Routes RS = cgr_k_yen(C, N, &P, NI, K_yen);
        if(fmt == FMT_JSON)  print_json_multi(&RS, P.t0, pretty);
        else                 print_text_multi(&RS, P.t0, "Rutas K (Yen-lite, sin consumo)");
        free_routes(&RS);
        free_neighbor_index(NI);
        free(C);
        return 0;
    }

    // Modo consumo
    if(K_consume == 1){
        Route R = cgr_best_route(C, N, &P, NI);
        if(fmt == FMT_JSON)  print_json_single(&R, P.t0, pretty);
        else                 print_text_single(&R, P.t0);
        free_route(&R);
    } else {
        Routes RS = cgr_k_routes(C, N, &P, NI, K_consume);
        if(fmt == FMT_JSON)  print_json_multi(&RS, P.t0, pretty);
        else                 print_text_multi(&RS, P.t0, "Rutas K (consumo de capacidad)");
        free_routes(&RS);
    }

    free_neighbor_index(NI);
    free(C);
    return 0;
}
