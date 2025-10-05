
#pragma once
#include "contact.h"

typedef struct {
    Label *items;
    int size;
    int cap;
} MinHeap;

MinHeap* heap_new(int cap);
void heap_free(MinHeap* h);
void heap_push(MinHeap* h, Label v);
Label heap_pop(MinHeap* h);
int heap_empty(MinHeap* h);

