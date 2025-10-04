
#include <stdlib.h>
#include "heap.h"

static int cmp(const Label *a, const Label *b){
    if(a->eta < b->eta) return -1;
    if(a->eta > b->eta) return 1;
    return 0;
}

typedef struct { Label tmp; } _swap_t;
static void swap(Label *a, Label *b){ _swap_t t={*a}; *a=*b; *b=t.tmp; }

static void ensure(MinHeap *h){
    if(h->size >= h->cap){
        h->cap = h->cap ? h->cap*2 : 16;
        h->items = (Label*)realloc(h->items, sizeof(Label)*h->cap);
    }
}

MinHeap* heap_new(int cap){
    MinHeap *h = (MinHeap*)malloc(sizeof(MinHeap));
    h->size = 0;
    h->cap  = (cap>0?cap:16);
    h->items = (Label*)malloc(sizeof(Label)*h->cap);
    return h;
}
void heap_free(MinHeap* h){
    if(!h) return;
    free(h->items);
    free(h);
}
void heap_push(MinHeap* h, Label v){
    ensure(h);
    int i = h->size++;
    h->items[i] = v;
    // up-heap
    while(i>0){
        int p = (i-1)/2;
        if(cmp(&h->items[i], &h->items[p]) >= 0) break;
        swap(&h->items[i], &h->items[p]);
        i = p;
    }
}
Label heap_pop(MinHeap* h){
    Label ret = { .contact_idx=-1, .eta=1e300, .prev_idx=-1 };
    if(h->size==0) return ret;
    ret = h->items[0];
    h->items[0] = h->items[--h->size];
    // down-heap
    int i=0;
    for(;;){
        int l=2*i+1, r=2*i+2, m=i;
        if(l<h->size && cmp(&h->items[l], &h->items[m])<0) m=l;
        if(r<h->size && cmp(&h->items[r], &h->items[m])<0) m=r;
        if(m==i) break;
        swap(&h->items[i], &h->items[m]);
        i=m;
    }
    return ret;
}
int heap_empty(MinHeap* h){ return h->size==0; }

