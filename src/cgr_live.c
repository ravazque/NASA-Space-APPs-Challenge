
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
    double period;        // s; 0 = sin periodificar (se puede activar autoperiodo)
    double tick;          // paso del reloj simulado (s)
    int    k_alt;         // K para alternativas (Yen-lite)
    int    src, dst;
    double bundle_bytes;
    const char *contacts_path; // CSV local (fallback)
    bool   auto_period;   // si no se pasa --period, autocalcula del CSV
    // API
    const char *dataset_id;
    const char *app_token;
    // Synth control
    int    synth_n;       // número de satélites intermedios
    unsigned int seed;    // semilla (0 = time(NULL))
} LiveCfg;

static void banner(void){
    printf("\n╔══════════════════════════════════════════════════════════╗\n");
    printf("║     CGR LIVE - Simulación con Datos NASA en Tiempo Real  ║\n");
    printf("╚══════════════════════════════════════════════════════════╝\n\n");
}

static void usage(const char *p){
    fprintf(stderr,
    "Uso:\n"
    "  %s [<dataset-id NASA>] [--source local|api|synth] [--contacts <csv>]\n"
    "     [--src N --dst N] [--bytes B] [--tick s] [--period s] [--auto-period]\n"
    "     [--k N] [--app-token <token>] [--synth-n N] [--seed S] [--help]\n\n"
    "Ejemplos:\n"
    "  %s --source local --contacts data/contacts_realistic.csv\n"
    "  %s abcd-1234 --source api --app-token TU_TOKEN --tick 10 --k 3\n"
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
    printf("   órbita: [");
    for(int i=0;i<width;i++) putchar(i<filled? '#':'.');
    printf("]  φ=%.1f%%\n", f*100.0);
}

// Duplicamos ventanas alrededor de t0: segmento k y k+1 para asegurar cobertura
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
 * Generador sintético realista
 * ===========================
 * - Anillo de Nsats con ISLs dirigidos y 2 ventanas a GS (dst).
 * - Ventanas cortas con solape y rates plausibles.
 * - Cada ejecución cambia (seed configurable).
 *
 * Nota: este proyecto usa Contact con campos:
 *   owlt  (sin sufijo) y setup_s (con sufijo)
 */
static int synth_generate(Contact **out, int *src, int *dst, double *period_out,
                          int Nsats, unsigned int seed) {
    if(!out) return -1;
    if(seed == 0) seed = (unsigned)time(NULL);
    srand(seed);

    int SRC = 100;                 // origen lógico
    int DST = 200;                 // destino lógico (GS)
    double P = 5400.0;             // periodo orbital ~90 min

    double owlt = 0.02;            // 20 ms
    double setup = 0.1;

    int M = 0;
    int cap = 64;
    Contact *C = (Contact*)malloc(sizeof(Contact)*cap);

    // Macro segura (parámetros con prefijo para no colisionar con nombres de campos)
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

    // SRC -> algunos sats al inicio (dos opciones)
    for(int i=0;i<2;i++){
        double t0   = (rand()%15);              // 0..14s
        double dur  = 40 + (rand()%20);         // 40..59s
        double rate = (6 + rand()%4)*1e6;       // 6..9 Mbps
        double resid= (2 + rand()%5)*1e8;       // 200..600 MB
        int sat = 1+i;
        PUSH(SRC, sat, t0, t0+dur, rate, resid);
    }

    // ISLs en anillo (dirigidos): 1->2, 2->3, ..., Nsats-1 -> Nsats
    double tcur = 20.0;
    for(int i=1;i<Nsats;i++){
        double jitter = rand()%10;              // 0..9s
        double t0   = tcur + jitter;
        double dur  = 35 + (rand()%25);         // 35..59s
        double rate = (5 + rand()%6)*1e6;       // 5..10 Mbps
        double resid= (2 + rand()%7)*1e8;       // 200..800 MB
        PUSH(i, i+1, t0, t0+dur, rate, resid);
        tcur += 10.0;
    }

    // Último salto a DST (dos “ventanas” con solape)
    for(int k=0;k<2;k++){
        double t0   = 60 + k*15 + (rand()%6);
        double dur  = 35 + (rand()%25);
        double rate = (7 + rand()%6)*1e6;       // 7..12 Mbps
        double resid= (3 + rand()%8)*1e8;       // 300..1,000 MB
        PUSH(Nsats, DST, t0, t0+dur, rate, resid);
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
        .source = SRC_LOCAL,
        .period = 0.0,
        .tick = 10.0,
        .k_alt = 3,
        .src = 100, .dst = 200,
        .bundle_bytes = 5e7,
        .contacts_path = "data/contacts_realistic.csv",
        .auto_period = true,
        .dataset_id = NULL,
        .app_token  = NULL,
        .synth_n = 8,
        .seed = 0
    };

    // Primer argumento sin '-' = dataset-id si --source api
    for(int i=1;i<argc;i++){
        if(!strcmp(argv[i], "--help")) { usage(argv[0]); return 0; }
        else if(argv[i][0] != '-') L.dataset_id = argv[i];
        else if(!strcmp(argv[i],"--source") && i+1<argc){
            i++;
            if(!strcmp(argv[i],"local")) L.source=SRC_LOCAL;
            else if(!strcmp(argv[i],"api")) L.source=SRC_API;
            else if(!strcmp(argv[i],"synth")) L.source=SRC_SYNTH;
            else { fprintf(stderr,"--source debe ser local|api|synth\n"); return 2; }
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
            fprintf(stderr, "Parámetro no reconocido: %s\n", argv[i]);
            usage(argv[0]);
            return 2;
        }
    }

    // Mensaje de modo
    if(L.source == SRC_API){
        printf("MODO API (SODA): dataset %s — fallback CSV si no hay datos\n",
               L.dataset_id ? L.dataset_id : "(no especificado)");
    } else if(L.source == SRC_SYNTH){
        printf("MODO SINTÉTICO: generador de contactos realistas (seed=%u)\n", L.seed ? L.seed : (unsigned)time(NULL));
    } else {
        printf("MODO SIMULACIÓN: Usando datos locales (%s)\n", L.contacts_path);
        printf("Para usar API de NASA: %s <dataset-id> --source api [--app-token XXX]\n", argv[0]);
    }
    printf("\n");

    // ====== Carga de contactos según fuente ======
    Contact *C0 = NULL; int N0 = 0;

    if(L.source == SRC_API){
        if(!L.dataset_id){
            fprintf(stderr,"Error: debes pasar <dataset-id> como primer argumento con --source api\n");
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
            printf("[API] sin datos; fallback local: %s\n", L.contacts_path);
            N0 = load_contacts_csv(L.contacts_path, &C0);
            if(N0 <= 0){ fprintf(stderr,"Error: no se pudieron cargar contactos.\n"); return 1; }
        }
    }
    else if(L.source == SRC_SYNTH){
        double Pgen=0.0; int s=0,d=0;
        N0 = synth_generate(&C0, &s, &d, &Pgen, L.synth_n, L.seed);
        if(N0 <= 0){ fprintf(stderr,"Error: generador sintético falló.\n"); return 1; }
        if(L.src==100 && L.dst==200){ L.src=s; L.dst=d; } // usar src/dst generados si ibas con defaults
        if(L.period<=0.0){ L.period=Pgen; }
        printf("✓ Generados %d contactos sintéticos (period=%.1f s)\n\n", N0, L.period);
    }
    else { // SRC_LOCAL
        N0 = load_contacts_csv(L.contacts_path, &C0);
        if(N0 <= 0){ fprintf(stderr,"Error: no se pudieron cargar contactos.\n"); return 1; }
        printf("✓ Cargados %d contactos\n\n", N0);
    }

    // AUTOPERIODO si procede
    if(L.auto_period && L.period <= 0.0){
        double tmin = 1e300, tmax = -1e300;
        for(int i=0;i<N0;i++){
            if(C0[i].t_start < tmin) tmin = C0[i].t_start;
            if(C0[i].t_end   > tmax) tmax = C0[i].t_end;
        }
        double span = (tmax > tmin) ? (tmax - tmin) : 0.0;
        if(span > 0.0){
            L.period = span;
            printf("ℹ️  Auto-period activado: period=%.3f s (span origen)\n\n", L.period);
        }
    }

    // ====== Bucle live ======
    printf("🚀 Iniciando bucle de simulación (Ctrl+C para detener)...\n\n");
    double sim_time = 0.0;
    int cycle = 0;

    while(!g_stop){
        cycle++;
        printf("╔════════════════════════════════════════════════════════╗\n");
        printf("║  CICLO #%d    | Tiempo simulado: %.1f s              \n", cycle, sim_time);
        printf("╠════════════════════════════════════════════════════════╣\n");

        int Nc = 0;
        Contact *C = periodize_contacts(C0, N0, sim_time, L.period, &Nc);
        NeighborIndex *NI = build_neighbor_index(C, Nc);

        int active = 0;
        for(int i=0;i<Nc;i++){
            if(sim_time >= C[i].t_start && sim_time < C[i].t_end) active++;
        }
        printf("║  Contactos activos: %d                                 \n", active);
        printf("║  Fuente de datos:   %s                                 \n",
               (L.source==SRC_API?"API (SODA)":(L.source==SRC_SYNTH?"SINTETICO":"LOCAL CSV")));
        printf("║  Errores:           0                                  \n");
        printf("╚════════════════════════════════════════════════════════╝\n\n");

        // Routing
        CgrParams P = { .src_node=L.src, .dst_node=L.dst, .t0=sim_time, .bundle_bytes=L.bundle_bytes, .expiry=0.0 };
        Route best = cgr_best_route(C, Nc, &P, NI);

        if(best.found){
            // Espera al primer salto (explica saltos de ETA al bloque k+1)
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
            printf("🛰️  RUTA ÓPTIMA ENCONTRADA:\n");
            printf("   • ETA:      %.3f s\n", best.eta);
            printf("   • Latencia: %.3f s (incluye espera inicial %.3f s)\n", best.eta - sim_time, wait_s);
            printf("   • Saltos:   %d\n", best.hops);
            printf("   • Path:     ");
            for(int i=0;i<best.hops;i++){ if(i) printf(" → "); printf("%d", best.contact_ids[i]); }
            printf("\n\n");
        } else {
            printf("⚠️  NO HAY RUTA DISPONIBLE\n\n");
        }

        if(L.k_alt > 0){
            Routes RS = cgr_k_yen(C, Nc, &P, NI, L.k_alt);
            printf("📊 Rutas alternativas (K=%d):\n", L.k_alt);
            if(RS.count==0) printf("   (ninguna)\n");
            for(int r=0;r<RS.count;r++){
                const Route *R = &RS.items[r];
                printf("   #%d: ETA=%.3f s, %d saltos\n", r+1, R->eta, R->hops);
            }
            printf("\n");
            free_routes(&RS);
        }

        print_progress(sim_time, L.period);

        free_route(&best);
        free_neighbor_index(NI);
        free(C);

        printf("⏳ Próximo ciclo en 1 segundos...\n\n");
        sleep_ms(1000);
        sim_time += L.tick;
    }

    printf("[SIGNAL] Deteniendo simulación...\n\n");
    printf("[CLEANUP] Liberando recursos...\n");
    free(C0);
    printf("✓ Simulación finalizada después de %d ciclos\n", cycle);
    return 0;
}
