
// include/csv.h — Carga de contactos desde CSV

#pragma once
#include "contact.h"

// Devuelve el número de contactos leídos, o <0 en error.
// Asigna el array en *out_contacts (liberar con free()).
int load_contacts_csv(const char *path, Contact **out_contacts);

