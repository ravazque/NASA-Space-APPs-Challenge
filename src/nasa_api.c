// src/nasa_api.c — Implementación de integración con NASA APIs
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include "nasa_api.h"

char	*ft_strdup(const char *s1)
{
	size_t	len;
	char	*dup_str;
	size_t	i;

	len = 0;
	while (s1[len] != '\0')
	{
		len++;
	}
	dup_str = (char *)malloc(len + 1);
	if (!dup_str)
	{
		return (NULL);
	}
	i = 0;
	while (i <= len)
	{
		dup_str[i] = s1[i];
		i++;
	}
	return (dup_str);
}

// Inicializar configuración
NasaApiConfig* nasa_api_init(const char *api_key, const char *dataset_id) {
    NasaApiConfig *cfg = (NasaApiConfig*)calloc(1, sizeof(NasaApiConfig));
    if (!cfg) return NULL;
    
    if (api_key) {
        cfg->api_key = ft_strdup(api_key);
    }
    
    if (dataset_id) {
        cfg->dataset_id = ft_strdup(dataset_id);
    }
    
    cfg->update_interval_s = 5; // Default: 5 minutos
    cfg->cache_file = ft_strdup("data/contacts_cache.csv");
    
    return cfg;
}

// Liberar configuración
void nasa_api_free(NasaApiConfig *cfg) {
    if (!cfg) return;
    
    free(cfg->api_key);
    free(cfg->soda_app_token);
    free(cfg->dataset_id);
    free(cfg->cache_file);
    free(cfg);
}

// Fetch real desde API SODA (usando curl)
int nasa_api_fetch_contacts(const NasaApiConfig *cfg, Contact **out_contacts) {
    if (!cfg || !cfg->dataset_id) return -1;
    
    // Construir comando curl
    char cmd[2048];
    snprintf(cmd, sizeof(cmd),
        "curl -s -G 'https://data.nasa.gov/resource/%s.json' "
        "--data-urlencode '$select=id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes' "
        "--data-urlencode '$limit=10000' "
        "%s%s "
        "-o /tmp/nasa_contacts.json",
        cfg->dataset_id,
        cfg->soda_app_token ? "-H 'X-App-Token: " : "",
        cfg->soda_app_token ? cfg->soda_app_token : ""
    );
    
    // Ejecutar curl
    int ret = system(cmd);
    if (ret != 0) {
        fprintf(stderr, "Error: curl failed (ret=%d)\n", ret);
        return -1;
    }
    
    // TODO: Parsear JSON y convertir a Contact[]
    // Por ahora, usar caché CSV como fallback
    fprintf(stderr, "WARNING: JSON parsing not implemented, using CSV cache\n");
    
    return 0;
}

// Actualizar si es necesario
int nasa_api_update_if_needed(const NasaApiConfig *cfg, UpdateState *state,
                               Contact **out_contacts, int *out_count) {
    if (!cfg || !state) return -1;
    
    time_t now = time(NULL);
    
    // ¿Necesitamos actualizar?
    if (state->last_update == 0 || 
        (now - state->last_update) >= cfg->update_interval_s) {
        
        fprintf(stderr, "[NASA API] Actualizando contactos desde API...\n");
        
        int n = nasa_api_fetch_contacts(cfg, out_contacts);
        
        if (n < 0) {
            state->error_count++;
            snprintf(state->last_error, sizeof(state->last_error),
                     "Failed to fetch from API");
            
            // Fallback a caché
            fprintf(stderr, "[NASA API] Usando caché: %s\n", cfg->cache_file);
            // Cargar desde caché
            return 0;
        }
        
        state->last_update = now;
        state->contact_count = n;
        state->update_counter++;
        
        fprintf(stderr, "[NASA API] ✓ Actualizado: %d contactos\n", n);
        return 1; // Actualizado
    }
    
    // Usar datos existentes
    return 0;
}

// Calcular contactos desde TLEs (placeholder para futuro)
int calculate_contacts_from_tles(const char *tle_file, double t_start, double t_end,
                                  Contact **out_contacts) {
    (void)tle_file;
    (void)t_start;
    (void)t_end;
    (void)out_contacts;
    
    // TODO: Implementar con libsgp4
    fprintf(stderr, "calculate_contacts_from_tles: NOT IMPLEMENTED\n");
    return -1;
}
