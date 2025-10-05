
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "csv.h"

static char* trim(char *s){
    while(isspace((unsigned char)*s)) s++;
    if(!*s) return s;
    char *e = s + strlen(s) - 1;
    while(e>s && isspace((unsigned char)*e)) *e-- = 0;
    return s;
}

int load_contacts_csv(const char *path, Contact **out_contacts){
    FILE *f = fopen(path, "r");
    if(!f) return -1;

    int cap = 128, n = 0;
    Contact *arr = (Contact*)malloc(sizeof(Contact)*cap);
    char line[1024];

    while(fgets(line, sizeof(line), f)){
        char *p = trim(line);
        if(*p=='#' || *p==0) continue;

        Contact c;
        // id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes
        int ok = sscanf(p, " %d , %d , %d , %lf , %lf , %lf , %lf , %lf , %lf ",
            &c.id, &c.from, &c.to, &c.t_start, &c.t_end, &c.owlt, &c.rate_bps, &c.setup_s, &c.residual_bytes);
        if(ok != 9) continue; // ignora líneas corruptas

        if(n >= cap){
            cap *= 2;
            arr = (Contact*)realloc(arr, sizeof(Contact)*cap);
        }
        arr[n++] = c;
    }

    fclose(f);
    *out_contacts = arr;
    return n;
}

