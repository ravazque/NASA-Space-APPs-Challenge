
#pragma once
#include "contact.h"

typedef enum
{
    LINK_ISL = 0,      // Inter-Satellite Link (SAT-SAT)
    LINK_UPLINK = 1,   // Ground Station -> Satellite
    LINK_DOWNLINK = 2  // Satellite -> Ground Station
} LinkType;

typedef struct
{
    double power_consumption_w;  // Consumo de potencia (Watts)
    double doppler_shift_hz;     // Desplazamiento Doppler
    double snr_db;               // Signal-to-Noise Ratio
    LinkType link_type;          // Tipo de enlace
    double elevation_angle_deg;  // Ángulo de elevación (para GS)
} LeoMetrics;

LinkType classify_link_type(int from, int to);

LeoMetrics compute_leo_metrics(const Contact *c, double t_arrival);

double link_type_penalty(LinkType lt);

