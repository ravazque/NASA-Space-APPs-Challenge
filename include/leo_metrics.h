// include/leo_metrics.h — Métricas específicas para redes LEO
#pragma once
#include "contact.h"

// Tipo de enlace en constelación LEO
typedef enum {
    LINK_ISL = 0,      // Inter-Satellite Link (SAT-SAT)
    LINK_UPLINK = 1,   // Ground Station -> Satellite
    LINK_DOWNLINK = 2  // Satellite -> Ground Station
} LinkType;

// Métricas extendidas para LEO
typedef struct {
    double power_consumption_w;  // Consumo de potencia (Watts)
    double doppler_shift_hz;     // Desplazamiento Doppler
    double snr_db;               // Signal-to-Noise Ratio
    LinkType link_type;          // Tipo de enlace
    double elevation_angle_deg;  // Ángulo de elevación (para GS)
} LeoMetrics;

// Clasificar tipo de enlace basado en IDs de nodos
// Convención: nodos 1-999 son SAT, 100,200,300... son GS
LinkType classify_link_type(int from, int to);

// Calcular métricas LEO para un contacto
LeoMetrics compute_leo_metrics(const Contact *c, double t_arrival);

// Penalización por tipo de enlace (ISL preferido sobre GS)
double link_type_penalty(LinkType lt);
