
// src/main.c — CLI para calcular 1 o K rutas y devolver JSON

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <float.h>
#include <stdbool.h>
#include "csv.h"
#include "cgr.h"

static void usage(const char* prog){
    fprintf(stderr,
    "Usage:\n"
    "  %s --contacts <file> --src <node> --dst <node> --t0 <sec> --bytes <B> [--expiry <sec>] [--k <num>]\n",
    prog);
}

static int parse_int(const char *s){ return (int)strtol(s, NULL, 10); }
static double parse_double(const char *s){ return strtod(s, NULL); }

int main(int argc, char **argv){
    const char *contacts_path = NULL;
    CgrParams P = { .src_node=-1, .dst_node=-1, .t0=0.0, .bundle_bytes=0.0, .expiry=0.0 };
    int K = 1;

    for(int i=1;i<argc;i++){
        if(!strcmp(argv[i],"--contacts") && i+1<argc) contacts_path = argv[++i];
        else if(!strcmp(argv[i],"--src") && i+1<argc) P.src_node = parse_int(argv[++i]);
        else if(!strcmp(argv[i],"--dst") && i+1<argc) P.dst_node = parse_int(argv[++i]);
        else if(!strcmp(argv[i],"--t0")  && i+1<argc) P.t0 = parse_double(argv[++i]);
        else if(!strcmp(argv[i],"--bytes") && i+1<argc) P.bundle_bytes = parse_double(argv[++i]);
        else if(!strcmp(argv[i],"--expiry") && i+1<argc) P.expiry = parse_double(argv[++i]);
        else if(!strcmp(argv[i],"--k") && i+1<argc) K = parse_int(argv[++i]);
        else { usage(argv[0]); return 2; }
    }

    if(!contacts_path || P.src_node<0 || P.dst_node<0 || P.bundle_bytes<=0.0){
        usage(argv[0]); return 2;
    }
    if(K < 1) K = 1;

    Contact *C=NULL; int N = load_contacts_csv(contacts_path, &C);
    if(N<=0){ fprintf(stderr,"Error: no contacts loaded from %s\n", contacts_path); return 1; }

    NeighborIndex *NI = build_neighbor_index(C, N);

    if(K == 1){
        Route R = cgr_best_route(C, N, &P, NI);
        if(!R.found){
            printf("{\"found\":false}\n");
        } else {
            printf("{\"found\":true,\"eta\":%.6f,\"latency\":%.6f,\"hops\":%d,\"contacts\":[",
                   R.eta, R.eta - P.t0, R.hops);
            for(int i=0;i<R.hops;i++){
                printf("%s%d", (i? ",":""), R.contact_ids[i]);
            }
            printf("]}\n");
        }
        free_route(&R);
    } else {
        Routes RS = cgr_k_routes(C, N, &P, NI, K);
        if(RS.count == 0){
            printf("{\"found\":false,\"routes\":[]}\n");
        } else {
            printf("{\"found\":true,\"routes\":[");
            for(int r=0; r<RS.count; r++){
                Route *R = &RS.items[r];
                printf("%s{\"eta\":%.6f,\"latency\":%.6f,\"hops\":%d,\"contacts\":[",
                       (r? ",":""), R->eta, R->eta - P.t0, R->hops);
                for(int i=0;i<R->hops;i++){
                    printf("%s%d", (i? ",":""), R->contact_ids[i]);
                }
                printf("]}");
            }
            printf("]}\n");
        }
        free_routes(&RS);
    }

    free_neighbor_index(NI);
    free(C);
    return 0;
}
