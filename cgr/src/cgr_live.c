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
#include "csv.h"
#include "nasa_api.h"

static volatile sig_atomic_t g_stop = 0;
static void on_sigint(int s){ (void)s; g_stop = 1; }

typedef enum { SRC_LOCAL=0, SRC_API=1, SRC_SYNTH=2 } DataSource;

typedef struct {
    DataSource source;
    double period;        // orbital period (s); 0 = no periodization
    double tick;          // simulation time step (s)
    int    k_alt;         // K for alternative routes (Yen-lite)
    int    src, dst;
    double bundle_bytes;
    const char *contacts_path; // local CSV (fallback)
    bool   auto_period;   // auto-calculate period from CSV if not specified
    // API config
    const char *dataset_id;
    const char *app_token;
    // Synthetic generator control
    int    synth_n;       // number of intermediate satellites
    unsigned int seed;    // random seed (0 = time(NULL))
} LiveCfg;

static void banner(void){
    printf("\n╔══════════════════════════════════════════════════════════╗\n");
    printf("║   CGR LIVE - Real-Time Space Network Route Simulation    ║\n");
    printf("╚══════════════════════════════════════════════════════════╝\n\n");
}

static void usage(const char *p){
    fprintf(stderr,
    "Usage:\n"
    "  %s [<nasa-dataset-id>] [--source local|api|synth] [--contacts <csv>]\n"
    "     [--src N --dst N] [--bytes B] [--tick s] [--period s] [--auto-period]\n"
    "     [--k N] [--app-token <token>] [--synth-n N] [--seed S] [--help]\n\n"
    "Examples:\n"
    "  %s --source local --contacts data/contacts_realistic.csv\n"
    "  %s abcd-1234 --source api --app-token YOUR_TOKEN --tick 10 --k 3\n"
    "  %s --source synth --period 5400 --tick 10 --k 3 --bytes 5e7 --synth-n 10\n",
    p,p,p,p);
}

static void sleep_ms(int ms){
    struct timespec ts; ts.tv_sec = ms/1000; ts.tv_nsec = (ms%1000)*1000000L;
    nanosleep(&ts, NULL);
}

static void print_progress(double now, double period){
    if(period <= 0){ printf("\n"); return; }
    double f = fmod(now, period) / period;
    int width = 30;
    int filled = (int)(f * width);
    printf("   Orbit: [");
    for(int i=0;i<width;i++) putchar(i<filled? '#':'.');
    printf("]  φ=%.1f%%\n", f*100.0);
}

// Duplicate contact windows around t0 for orbital periodicity
static Contact* periodize_contacts(const Contact *base, int N, double t0, double period, int *outM){
    if(period <= 0.0){
        Contact *C = (Contact*)malloc(sizeof(Contact)*N);
        memcpy(C, base, sizeof(Contact)*N);
        *outM = N;
        return C;
    }
    long k = (long)(t0 / period);
    int M = N*2;
    Contact *C = (Contact*)malloc(sizeof(Contact)*M);
    for(int i=0;i<N;i++){
        C[i]   = base[i];
        C[i].t_start += k*period;
        C[i].t_end   += k*period;
        C[i+N] = base[i];
        C[i+N].t_start += (k+1)*period;
        C[i+N].t_end   += (k+1)*period;
    }
    *outM = M;
    return C;
}

/* ===========================
 * Realistic Synthetic Generator
 * ===========================
 * - Ring topology with Nsats satellites
 * - Directed ISLs (Inter-Satellite Links)
 * - Multiple ground station (GS) contact windows throughout orbit
 * - Continuous coverage with overlapping windows
 * - Each run randomized (configurable seed)
 */
static int synth_generate(Contact **out, int *src, int *dst, double *period_out,
                          int Nsats, unsigned int seed) {
    if(!out) return -1;
    if(seed == 0) seed = (unsigned)time(NULL);
    srand(seed);

    int SRC = 100;                 // source node (GS)
    int DST = 200;                 // destination node (GS)
    double P = 180.0;              // shorter orbital period: 3 minutes for demo

    double owlt = 0.02;            // one-way light time: 20 ms
    double setup = 0.1;            // setup delay: 100 ms

    int M = 0;
    int cap = 128;
    Contact *C = (Contact*)malloc(sizeof(Contact)*cap);

    // Safe macro for adding contacts
    #define PUSH(_from,_to,_t0,_t1,_rate,_resid) do{                               \
        if(M>=cap){ cap*=2; C=(Contact*)realloc(C,sizeof(Contact)*cap);}           \
        C[M].id = M;                                                               \
        C[M].from = (_from);                                                       \
        C[M].to   = (_to);                                                         \
        C[M].t_start = (_t0);                                                      \
        C[M].t_end   = (_t1);                                                      \
        C[M].owlt    = (owlt);                                                     \
        C[M].rate_bps= (_rate);                                                    \
        C[M].setup_s = (setup);                                                    \
        C[M].residual_bytes = (_resid);                                            \
        M++;                                                                        \
    }while(0)

    // Create contacts distributed throughout the orbital period
    // Multiple passes to ensure continuous coverage
    
    for(int pass=0; pass<3; pass++){  // 3 passes per orbit
        double pass_start = pass * (P / 3.0);
        
        // SRC → first satellites (2 options per pass)
        for(int i=0;i<2;i++){
            double t0   = pass_start + (rand()%10);     // Stagger starts
            double dur  = 25 + (rand()%15);             // 25..39s duration
            double rate = (6 + rand()%4)*1e6;           // 6..9 Mbps
            double resid= (2 + rand()%5)*1e8;           // 200..600 MB
            int sat = 1+i;
            PUSH(SRC, sat, t0, t0+dur, rate, resid);
        }

        // ISLs in ring (directed): always available with long windows
        double isl_start = pass_start;
        for(int i=1;i<Nsats;i++){
            double t0   = isl_start + (i-1)*3;          // Staggered by 3s
            double dur  = P / 3.0 + 10;                 // Long overlapping windows
            double rate = (8 + rand()%5)*1e6;           // 8..12 Mbps (ISL faster)
            double resid= (5 + rand()%10)*1e8;          // 500MB..1.4GB
            PUSH(i, i+1, t0, t0+dur, rate, resid);
        }

        // Final hop to DST (2 windows per pass)
        for(int k=0;k<2;k++){
            double t0   = pass_start + 30 + k*15 + (rand()%5);
            double dur  = 20 + (rand()%15);
            double rate = (7 + rand()%6)*1e6;           // 7..12 Mbps
            double resid= (3 + rand()%8)*1e8;           // 300..1000 MB
            PUSH(Nsats, DST, t0, t0+dur, rate, resid);
        }
    }

    #undef PUSH

    *out = C;
    if(src) *src = SRC;
    if(dst) *dst = DST;
    if(period_out) *period_out = P;
    return M;
}

int main(int argc, char **argv){
    signal(SIGINT, on_sigint);

    banner();

    LiveCfg L = {
        .source = SRC_SYNTH,  // Default to synthetic for demo
        .period = 0.0,
        .tick = 15.0,
        .k_alt = 5,
        .src = 100, .dst = 200,
        .bundle_bytes = 50e6,  // 50 MB default
        .contacts_path = "data/contacts_realistic.csv",
        .auto_period = true,
        .dataset_id = NULL,
        .app_token  = NULL,
        .synth_n = 12,
        .seed = 0
    };

    // First non-flag argument = dataset-id (if using API mode)
    for(int i=1;i<argc;i++){
        if(!strcmp(argv[i], "--help")) { usage(argv[0]); return 0; }
        else if(argv[i][0] != '-') L.dataset_id = argv[i];
        else if(!strcmp(argv[i],"--source") && i+1<argc){
            i++;
            if(!strcmp(argv[i],"local")) L.source=SRC_LOCAL;
            else if(!strcmp(argv[i],"api")) L.source=SRC_API;
            else if(!strcmp(argv[i],"synth")) L.source=SRC_SYNTH;
            else { fprintf(stderr,"--source must be local|api|synth\n"); return 2; }
        }
        else if(!strcmp(argv[i],"--contacts") && i+1<argc) L.contacts_path = argv[++i];
        else if(!strcmp(argv[i],"--src") && i+1<argc) L.src = (int)strtol(argv[++i],NULL,10);
        else if(!strcmp(argv[i],"--dst") && i+1<argc) L.dst = (int)strtol(argv[++i],NULL,10);
        else if(!strcmp(argv[i],"--bytes") && i+1<argc) L.bundle_bytes = strtod(argv[++i],NULL);
        else if(!strcmp(argv[i],"--tick") && i+1<argc) L.tick = strtod(argv[++i],NULL);
        else if(!strcmp(argv[i],"--period") && i+1<argc) { L.period = strtod(argv[++i],NULL); L.auto_period=false; }
        else if(!strcmp(argv[i],"--auto-period")) L.auto_period = true;
        else if(!strcmp(argv[i],"--k") && i+1<argc) L.k_alt = (int)strtol(argv[++i],NULL,10);
        else if(!strcmp(argv[i],"--app-token") && i+1<argc) L.app_token = argv[++i];
        else if(!strcmp(argv[i],"--synth-n") && i+1<argc) L.synth_n = (int)strtol(argv[++i],NULL,10);
        else if(!strcmp(argv[i],"--seed") && i+1<argc) { L.seed = (unsigned int)strtoul(argv[++i],NULL,10); }
        else {
            fprintf(stderr, "Unrecognized parameter: %s\n", argv[i]);
            usage(argv[0]);
            return 2;
        }
    }

    // Display mode information
    if(L.source == SRC_API){
        printf("MODE: NASA API (SODA) — dataset %s (CSV fallback if unavailable)\n",
               L.dataset_id ? L.dataset_id : "(not specified)");
    } else if(L.source == SRC_SYNTH){
        printf("MODE: SYNTHETIC — Realistic contact generator (seed=%u)\n", 
               L.seed ? L.seed : (unsigned)time(NULL));
    } else {
        printf("MODE: LOCAL SIMULATION — Using local data (%s)\n", L.contacts_path);
        printf("To use NASA API: %s <dataset-id> --source api [--app-token XXX]\n", argv[0]);
    }
    printf("\n");

    // ====== Load contacts based on source ======
    Contact *C0 = NULL; int N0 = 0;

    if(L.source == SRC_API){
        if(!L.dataset_id){
            fprintf(stderr,"Error: must provide <dataset-id> as first argument with --source api\n");
            return 2;
        }
        NasaApiConfig cfg = {
            .dataset_id = L.dataset_id,
            .app_token = L.app_token,
            .sod_limit = 50000,
            .update_interval_s = 0
        };
        int n = nasa_api_fetch_contacts(&cfg, &C0);
        if(n > 0){ N0 = n; }
        else {
            printf("[API] No data available; falling back to local: %s\n", L.contacts_path);
            N0 = load_contacts_csv(L.contacts_path, &C0);
            if(N0 <= 0){ fprintf(stderr,"Error: could not load contacts.\n"); return 1; }
        }
    }
    else if(L.source == SRC_SYNTH){
        double Pgen=0.0; int s=0,d=0;
        N0 = synth_generate(&C0, &s, &d, &Pgen, L.synth_n, L.seed);
        if(N0 <= 0){ fprintf(stderr,"Error: synthetic generator failed.\n"); return 1; }
        if(L.src==100 && L.dst==200){ L.src=s; L.dst=d; }
        if(L.period<=0.0){ L.period=Pgen; }
        printf("✓ Generated %d synthetic contacts (period=%.1f s)\n\n", N0, L.period);
    }
    else { // SRC_LOCAL
        N0 = load_contacts_csv(L.contacts_path, &C0);
        if(N0 <= 0){ fprintf(stderr,"Error: could not load contacts.\n"); return 1; }
        printf("✓ Loaded %d contacts\n\n", N0);
    }

    // AUTO-PERIOD if applicable
    if(L.auto_period && L.period <= 0.0){
        double tmin = 1e300, tmax = -1e300;
        for(int i=0;i<N0;i++){
            if(C0[i].t_start < tmin) tmin = C0[i].t_start;
            if(C0[i].t_end   > tmax) tmax = C0[i].t_end;
        }
        double span = (tmax > tmin) ? (tmax - tmin) : 0.0;
        if(span > 0.0){
            L.period = span;
            printf("ℹ️  Auto-period enabled: period=%.3f s (contact time span)\n\n", L.period);
        }
    }

    // ====== Real-time simulation loop ======
    printf("🚀 Starting real-time simulation loop (Ctrl+C to stop)...\n\n");
    double sim_time = 0.0;
    int cycle = 0;

    while(!g_stop){
        cycle++;
        printf("╔════════════════════════════════════════════════════════╗\n");
        printf("║  CYCLE #%-4d | Simulation time: %.1f s              \n", cycle, sim_time);
        printf("╠════════════════════════════════════════════════════════╣\n");

        int Nc = 0;
        Contact *C = periodize_contacts(C0, N0, sim_time, L.period, &Nc);
        NeighborIndex *NI = build_neighbor_index(C, Nc);

        int active = 0;
        for(int i=0;i<Nc;i++){
            if(sim_time >= C[i].t_start && sim_time < C[i].t_end) active++;
        }
        printf("║  Active contacts:   %-4d                               \n", active);
        printf("║  Data source:       %-30s  \n",
               (L.source==SRC_API?"NASA API (SODA)":(L.source==SRC_SYNTH?"SYNTHETIC":"LOCAL CSV")));
        printf("║  Errors:            0                                  \n");
        printf("╚════════════════════════════════════════════════════════╝\n\n");

        // Compute optimal route
        CgrParams P = { .src_node=L.src, .dst_node=L.dst, .t0=sim_time, .bundle_bytes=L.bundle_bytes, .expiry=0.0 };
        Route best = cgr_best_route(C, Nc, &P, NI);

        if(best.found){
            // Calculate wait time for first hop
            double wait_s = 0.0;
            if(best.hops>0){
                int first_id = best.contact_ids[0];
                for(int i=0;i<Nc;i++){
                    if(C[i].id == first_id){
                        double start_tx = fmax(sim_time, C[i].t_start);
                        wait_s = fmax(0.0, start_tx - sim_time);
                        break;
                    }
                }
            }
            printf("🛰️  OPTIMAL ROUTE FOUND:\n");
            printf("   • ETA:      %.3f s\n", best.eta);
            printf("   • Latency:  %.3f s (includes initial wait: %.3f s)\n", best.eta - sim_time, wait_s);
            printf("   • Hops:     %d\n", best.hops);
            printf("   • Path:     ");
            for(int i=0;i<best.hops;i++){ if(i) printf(" → "); printf("%d", best.contact_ids[i]); }
            printf("\n\n");
        } else {
            printf("⚠️  NO ROUTE AVAILABLE\n\n");
        }

        // Alternative routes (Yen-lite)
        if(L.k_alt > 0 && best.found){
            Routes RS = cgr_k_yen(C, Nc, &P, NI, L.k_alt);
            printf("📊 Alternative routes (K=%d):\n", L.k_alt);
            if(RS.count==0) printf("   (none)\n");
            for(int r=0;r<RS.count;r++){
                const Route *R = &RS.items[r];
                double overhead = ((R->eta - best.eta) / best.eta) * 100.0;
                printf("   #%d: ETA=%.3f s, %d hops (+%.1f%% overhead)\n", 
                       r+1, R->eta, R->hops, overhead);
            }
            printf("\n");
            free_routes(&RS);
        }

        print_progress(sim_time, L.period);

        free_route(&best);
        free_neighbor_index(NI);
        free(C);

        printf("⏳ Next cycle in 1 second...\n\n");
        sleep_ms(1000);
        sim_time += L.tick;
    }

    printf("\n[SIGNAL] Stopping simulation...\n\n");
    printf("[CLEANUP] Freeing resources...\n");
    free(C0);
    printf("✓ Simulation completed after %d cycles\n", cycle);
    return 0;
}
