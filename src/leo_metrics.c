
#include <math.h>
#include "leo_metrics.h"

#define PI 3.14159265358979323846

// Clasificar tipo de enlace
LinkType classify_link_type(int from, int to) {
    // Convención: 1-999 = SAT, múltiplos de 100 = GS
    int from_is_gs = (from % 100 == 0 && from >= 100 && from < 1000);
    int to_is_gs = (to % 100 == 0 && to >= 100 && to < 1000);
    
    if (!from_is_gs && !to_is_gs) return LINK_ISL;        // SAT→SAT
    if (from_is_gs && !to_is_gs) return LINK_UPLINK;      // GS→SAT
    if (!from_is_gs && to_is_gs) return LINK_DOWNLINK;    // SAT→GS
    
    return LINK_ISL; // Default
}

// Calcular métricas LEO
LeoMetrics compute_leo_metrics(const Contact *c, double t_arrival) {
    LeoMetrics m;
    (void)t_arrival; // Marcado como intencional para uso futuro
    
    m.link_type = classify_link_type(c->from, c->to);
    
    // Potencia: ISL consume menos que enlaces GS
    switch (m.link_type) {
        case LINK_ISL:
            m.power_consumption_w = 5.0 + c->rate_bps / 1e6 * 0.5; // 5W base + ~0.5W/Mbps
            break;
        case LINK_UPLINK:
            m.power_consumption_w = 50.0 + c->rate_bps / 1e6 * 2.0; // Mayor potencia para uplink
            break;
        case LINK_DOWNLINK:
            m.power_consumption_w = 20.0 + c->rate_bps / 1e6 * 1.0;
            break;
    }
    
    // Doppler shift simplificado (LEO ~7.5 km/s, Ka-band 32 GHz)
    double velocity_kms = 7.5; // Velocidad orbital LEO típica
    double frequency_ghz = 32.0; // Ka-band
    m.doppler_shift_hz = (velocity_kms * 1000.0 / 299792458.0) * frequency_ghz * 1e9;
    
    // SNR simplificado (mejor para ISL)
    if (m.link_type == LINK_ISL) {
        m.snr_db = 25.0 - c->owlt * 100; // Mejor SNR, menor distancia
    } else {
        m.snr_db = 20.0 - c->owlt * 150; // Peor SNR para enlaces GS
    }
    
    // Ángulo de elevación (solo para enlaces GS)
    if (m.link_type != LINK_ISL) {
        // Simplificado: basado en OWLT (mayor OWLT = menor elevación)
        double earth_radius = 6371.0;
        double sat_altitude = 550.0; // LEO típico
        m.elevation_angle_deg = asin(earth_radius / (earth_radius + sat_altitude)) * 180.0 / PI;
    } else {
        m.elevation_angle_deg = 0.0;
    }
    
    return m;
}

// Penalización por tipo de enlace (favorecer ISL)
double link_type_penalty(LinkType lt) {
    switch (lt) {
        case LINK_ISL:      return 0.0;   // Sin penalización
        case LINK_DOWNLINK: return 0.5;   // Pequeña penalización
        case LINK_UPLINK:   return 1.0;   // Mayor penalización
        default:            return 0.0;
    }
}
