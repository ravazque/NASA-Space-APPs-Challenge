// include/nasa_api.h — Integración con APIs de NASA para datos satelitales en tiempo real
#pragma once
#include "contact.h"
#include <time.h>

// Configuración de API
typedef struct {
    char *api_key;           // API key de NASA (opcional para algunos endpoints)
    char *soda_app_token;    // App token de Socrata/SODA (opcional)
    char *dataset_id;        // ID del dataset en data.nasa.gov (e.g., "abcd-1234")
    int update_interval_s;   // Intervalo de actualización en segundos (e.g., 300 = 5 min)
    char *cache_file;        // Archivo de caché local
} NasaApiConfig;

// Estado de actualización
typedef struct {
    time_t last_update;      // Timestamp de última actualización
    int contact_count;       // Número de contactos actuales
    int update_counter;      // Contador de actualizaciones exitosas
    int error_count;         // Contador de errores
    char last_error[256];    // Último mensaje de error
} UpdateState;

// Inicializar configuración de API
NasaApiConfig* nasa_api_init(const char *api_key, const char *dataset_id);

// Liberar configuración
void nasa_api_free(NasaApiConfig *cfg);

// Obtener contactos desde API de NASA (SODA)
// Retorna número de contactos obtenidos, <0 en error
int nasa_api_fetch_contacts(const NasaApiConfig *cfg, Contact **out_contacts);

// Actualizar contactos si es necesario (respeta update_interval)
// Retorna 1 si actualizó, 0 si usa caché, <0 en error
int nasa_api_update_if_needed(const NasaApiConfig *cfg, UpdateState *state, 
                               Contact **out_contacts, int *out_count);

// Función helper: calcular ventanas de contacto desde TLEs (futuro)
// Esta función usaría SGP4 para propagar órbitas
int calculate_contacts_from_tles(const char *tle_file, double t_start, double t_end,
                                  Contact **out_contacts);
								  