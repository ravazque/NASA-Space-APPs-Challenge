#ifndef NASA_API_H
#define NASA_API_H

#include "cgr.h"

#define NASA_PROVIDER_SODA   1
#define NASA_PROVIDER_CUSTOM 2

#ifndef NASA_PROVIDER
#define NASA_PROVIDER NASA_PROVIDER_SODA
#endif

typedef struct
{
    const char *dataset_id;
    const char *app_token;
    int         sod_limit;
    int         update_interval_s;
} NasaApiConfig;

int nasa_api_fetch_contacts(const NasaApiConfig *cfg, Contact **out_contacts);

int nasa_api_update_if_needed(const NasaApiConfig *cfg, double sim_time, Contact **out_contacts, int *out_count);

#endif

