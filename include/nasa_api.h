#ifndef NASA_API_H
#define NASA_API_H

#include "cgr.h"

typedef struct {
    const char *dataset_id;       // p.ej., "abcd-1234"
    const char *app_token;        // opcional: X-App-Token (Socrata)
    int         sod_limit;        // tamaño de página CSV
    int         update_interval_s;// reservado para refrescos
} NasaApiConfig;

int nasa_api_fetch_contacts(const NasaApiConfig *cfg, Contact **out_contacts);
int nasa_api_update_if_needed(const NasaApiConfig *cfg, double sim_time,
                              Contact **out_contacts, int *out_count);

#endif
