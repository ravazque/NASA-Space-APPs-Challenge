
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <stdbool.h>
#include <time.h>
#include <unistd.h>
#include <math.h>

#include "cgr.h"
#include "nasa_api.h"

static volatile sig_atomic_t g_stop = 0;
static void on_sigint(int s){ (void)s; g_stop = 1; }

typedef struct
{
    const char *dataset_id;
    const char *app_token;
    int    src, dst;
    double t0;
    double bundle_bytes;
    int    k_alt;
    int    cycles;
    double tick_s;
    bool   consume;       // resta capacidad usada
    bool   learn_ewma;    // penalización suave por enlace
    double alpha;         // coeficiente EWMA [0..1]
    double lambda_;       // peso de penalización en segundos
} Cfg;

typedef struct
{
    double penalty_s;
} EdgeState;

static void usage(const char *p)
{
    fprintf(stderr,
    "Uso (API SODA):\n"
    "  %s --dataset <id> [--app-token TOKEN] --src N --dst N --t0 s --bytes B [--k N]\n"
    "     [--cycles M] [--tick s] [--consume] [--learn-ewma --alpha A --lambda L]\n\n"
    "Ejemplo:\n"
    "  %s --dataset abcd-1234 --app-token TU_TOKEN --src 100 --dst 200 --t0 0 --bytes 5e7 --k 3 --cycles 30 --tick 10 --consume --learn-ewma --alpha 0.2 --lambda 1.0\n",
    p,p);
}

int main(int argc, char **argv)
{
    signal(SIGINT, on_sigint);

    Cfg cfg = {
        .dataset_id=NULL, .app_token=NULL,
        .src=100, .dst=200, .t0=0.0, .bundle_bytes=5e7,
        .k_alt=3, .cycles=1, .tick_s=10.0,
        .consume=false, .learn_ewma=false, .alpha=0.2, .lambda_=1.0
    };

    for(int i=1;i<argc;i++){
        if(!strcmp(argv[i],"--help")){ usage(argv[0]); return 0; }
        else if(!strcmp(argv[i],"--dataset") && i+1<argc) cfg.dataset_id = argv[++i];
        else if(!strcmp(argv[i],"--app-token") && i+1<argc) cfg.app_token = argv[++i];
        else if(!strcmp(argv[i],"--src") && i+1<argc) cfg.src = (int)strtol(argv[++i],NULL,10);
        else if(!strcmp(argv[i],"--dst") && i+1<argc) cfg.dst = (int)strtol(argv[++i],NULL,10);
        else if(!strcmp(argv[i],"--t0") && i+1<argc) cfg.t0 = strtod(argv[++i],NULL);
        else if(!strcmp(argv[i],"--bytes") && i+1<argc) cfg.bundle_bytes = strtod(argv[++i],NULL);
        else if(!strcmp(argv[i],"--k") && i+1<argc) cfg.k_alt = (int)strtol(argv[++i],NULL,10);
        else if(!strcmp(argv[i],"--cycles") && i+1<argc) cfg.cycles = (int)strtol(argv[++i],NULL,10);
        else if(!strcmp(argv[i],"--tick") && i+1<argc) cfg.tick_s = strtod(argv[++i],NULL);
        else if(!strcmp(argv[i],"--consume")) cfg.consume = true;
        else if(!strcmp(argv[i],"--learn-ewma")) cfg.learn_ewma = true;
        else if(!strcmp(argv[i],"--alpha") && i+1<argc) cfg.alpha = strtod(argv[++i],NULL);
        else if(!strcmp(argv[i],"--lambda") && i+1<argc) cfg.lambda_ = strtod(argv[++i],NULL);
        else { fprintf(stderr,"Flag no reconocido: %s\n", argv[i]); usage(argv[0]); return 2; }
    }
    if(!cfg.dataset_id){ fprintf(stderr,"Error: --dataset es obligatorio\n"); usage(argv[0]); return 2; }

    printf("\n╔══════════════════════════════════════════════════════════╗\n");
    printf(  "║            CGR API — data.nasa.gov (SODA CSV)            ║\n");
    printf(  "╚══════════════════════════════════════════════════════════╝\n\n");

    NasaApiConfig acfg = {
        .dataset_id = cfg.dataset_id,
        .app_token  = cfg.app_token,
        .sod_limit  = 50000,
        .update_interval_s = 0
    };

    Contact *C = NULL; int N = nasa_api_fetch_contacts(&acfg, &C);
    if(N <= 0){
        fprintf(stderr,"No llegaron contactos desde API (dataset=%s)\n", cfg.dataset_id);
        return 1;
    }
    printf("✓ API OK — contactos: %d\n\n", N);

    EdgeState *E = (EdgeState*)calloc(N, sizeof(EdgeState));

    double now = cfg.t0;
    for(int cycle=1; cycle<=cfg.cycles && !g_stop; cycle++){
        printf("── Ciclo %d | t=%.1f s ─────────────────────────────────\n", cycle, now);

        Contact *W = (Contact*)malloc(sizeof(Contact)*N);
        memcpy(W, C, sizeof(Contact)*N);
        if(cfg.learn_ewma){
            for(int i=0;i<N;i++)
			{
                W[i].setup_s += cfg.lambda_ * E[i].penalty_s;
            }
        }

        NeighborIndex *NI = build_neighbor_index(W, N);

        CgrParams P = { .src_node=cfg.src, .dst_node=cfg.dst, .t0=now, .bundle_bytes=cfg.bundle_bytes, .expiry=0.0 };
        Route best = cgr_best_route(W, N, &P, NI);

        if(best.found)
		{
            double wait_s = 0.0;
            if(best.hops>0){
                int cid = best.contact_ids[0];
                for(int i=0;i<N;i++){
                    if(W[i].id==cid){
                        double start_tx = fmax(now, W[i].t_start);
                        wait_s = fmax(0.0, start_tx - now);
                        break;
                    }
                }
            }

            printf("  Ruta óptima:\n");
            printf("    • ETA:      %.3f s\n", best.eta);
            printf("    • Latencia: %.3f s (incluye espera inicial %.3f s)\n", best.eta - now, wait_s);
            printf("    • Saltos:   %d\n    • Path:     ", best.hops);
            for(int i=0;i<best.hops;i++){ if(i) printf(" → "); printf("%d", best.contact_ids[i]); }
            printf("\n");

            if(cfg.k_alt>0){
                Routes RS = cgr_k_yen(W, N, &P, NI, cfg.k_alt);
                printf("  Alternativas (K=%d):\n", RS.count);
                for(int r=0;r<RS.count;r++){
                    printf("    #%d: ETA=%.3f s, hops=%d\n", r+1, RS.items[r].eta, RS.items[r].hops);
                }
                free_routes(&RS);
            }

            if(cfg.consume){
                for(int i=0;i<best.hops;i++){
                    int cid = best.contact_ids[i];
                    for(int j=0;j<N;j++){
                        if(C[j].id==cid){
                            double before = C[j].residual_bytes;
                            if(C[j].residual_bytes > cfg.bundle_bytes)
                                C[j].residual_bytes -= cfg.bundle_bytes;
                            else
                                C[j].residual_bytes = 0;
                            printf("    consume: contacto %d  residual %.0f → %.0f\n",
                                   cid, before, C[j].residual_bytes);
                            break;
                        }
                    }
                }
            }
            if(cfg.learn_ewma && best.hops>0){
                int cid0 = best.contact_ids[0];
                for(int i=0;i<N;i++){
                    if(C[i].id==cid0){
                        E[i].penalty_s = (1.0 - cfg.alpha)*E[i].penalty_s + cfg.alpha*wait_s;
                        printf("    learn: contacto %d  penalty:= %.3f s\n", cid0, E[i].penalty_s);
                        break;
                    }
                }
            }
        } else {
            printf("  ⚠️  No hay ruta disponible\n");
        }

        free_route(&best);
        free_neighbor_index(NI);
        free(W);

        now += cfg.tick_s;
        if(cycle < cfg.cycles) {
            struct timespec ts = {.tv_sec=0,.tv_nsec=200*1000000L};
            nanosleep(&ts,NULL);
        }
    }

    free(E);
    free(C);
    printf("\n✓ Finalizado.\n");
    return 0;
}
