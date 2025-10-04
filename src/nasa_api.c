
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <curl/curl.h>

#include "nasa_api.h"
#include "csv.h"
#include "cgr.h"

#if NASA_PROVIDER == NASA_PROVIDER_SODA

typedef struct { FILE *fp; } CurlFileSink;
static size_t curl_write_to_file(void *ptr, size_t size, size_t nmemb, void *userdata)
{
    CurlFileSink *s = (CurlFileSink*)userdata;
    return fwrite(ptr, size, nmemb, s->fp) * size;
}

static int build_soda_url(char *dst, size_t cap, const NasaApiConfig *cfg)
{
    if(!cfg || !cfg->dataset_id) return -1;
    int limit = cfg->sod_limit > 0 ? cfg->sod_limit : 50000;
    return snprintf(
        dst, cap,
        "https://data.nasa.gov/resource/%s.csv"
        "?$select=id,from,to,t_start,t_end,owlt,rate_bps,setup_s,residual_bytes"
        "&$limit=%d",
        cfg->dataset_id, limit
    );
}

int nasa_api_fetch_contacts(const NasaApiConfig *cfg, Contact **out_contacts)
{
    if(!cfg || !cfg->dataset_id || !out_contacts) return -1;
    *out_contacts = NULL;

    char url[1024];
    if(build_soda_url(url, sizeof(url), cfg) <= 0) return -1;

    char tmp_path[256];
    snprintf(tmp_path, sizeof(tmp_path), "/tmp/nasa_contacts_%ld.csv", (long)getpid());

    CURL *curl = curl_easy_init();
    if(!curl) return -1;

    FILE *fp = fopen(tmp_path, "wb");
    if(!fp){ curl_easy_cleanup(curl); return -1; }

    CurlFileSink sink = {.fp = fp};
    curl_easy_setopt(curl, CURLOPT_URL, url);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_to_file);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &sink);
    curl_easy_setopt(curl, CURLOPT_USERAGENT, "EcoStation-CGR/1.0");

    struct curl_slist *headers = NULL;
    if(cfg->app_token && cfg->app_token[0]){
        char h[256];
        snprintf(h, sizeof(h), "X-App-Token: %s", cfg->app_token);
        headers = curl_slist_append(headers, h);
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    }

    CURLcode rc = curl_easy_perform(curl);
    fclose(fp);

    long http_code = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);

    if(headers) curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    if(rc != CURLE_OK || http_code < 200 || http_code >= 300)
	{
        remove(tmp_path);
        return 0;
    }

    Contact *C = NULL;
    int N = load_contacts_csv(tmp_path, &C);
    remove(tmp_path);

    if(N <= 0) return 0;
    *out_contacts = C;
    return N;
}

int nasa_api_update_if_needed(const NasaApiConfig *cfg, double sim_time, Contact **out_contacts, int *out_count)
{
    (void)cfg; (void)sim_time; (void)out_contacts; (void)out_count;
    return 0;
}

#elif NASA_PROVIDER == NASA_PROVIDER_CUSTOM

int nasa_api_fetch_contacts(const NasaApiConfig *cfg, Contact **out_contacts)
{
    (void)cfg; (void)out_contacts;
    fprintf(stderr, "[CUSTOM] Implementa tu proveedor en nasa_api.c\n");
    return -1;
}

int nasa_api_update_if_needed(const NasaApiConfig *cfg, double sim_time, Contact **out_contacts, int *out_count)
{
    (void)cfg; (void)sim_time; (void)out_contacts; (void)out_count;
    return 0;
}
#else
#error "NASA_PROVIDER inválido — usa NASA_PROVIDER_SODA o NASA_PROVIDER_CUSTOM"

#endif

