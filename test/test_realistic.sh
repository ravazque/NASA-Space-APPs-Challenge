#!/bin/bash
# test_realistic.sh - Pruebas con escenario realista

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Test CGR con Escenario Realista LEO                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

CONTACTS="data/contacts_realistic.csv"

# Crear archivo si no existe
if [ ! -f "$CONTACTS" ]; then
    echo "⚠️  Creando $CONTACTS..."
    cat > "$CONTACTS" << 'EOF'
# contacts_realistic.csv — Escenario LEO más realista
# id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes
0, 100, 1,   0,  40, 0.020, 10000000, 0.2, 100000000
1,   1,  2,  25,  65, 0.015, 12000000, 0.1, 120000000
2,   2, 200, 55, 100, 0.025,  8000000, 0.1,  80000000
3,   1,  3,  30,  80, 0.020,  6000000, 0.2,  90000000
4,   3, 200, 70, 130, 0.030,  5000000, 0.1,  70000000
5, 100, 4,  20,  55, 0.025,  9000000, 0.2,  85000000
6,   4,  2,  50,  90, 0.018, 11000000, 0.1, 110000000
7, 100, 5,   5,  45, 0.022,  7000000, 0.2,  95000000
8,   5,  6,  40,  85, 0.016, 13000000, 0.1, 140000000
9,   6, 200, 75, 125, 0.020, 10000000, 0.1, 100000000
EOF
    echo "✓ Archivo de contactos realistas creado"
    echo ""
fi

make -s

echo "━━━ Prueba 1: t0=0 (salida inmediata) ━━━"
./cgr --contacts "$CONTACTS" --src 100 --dst 200 --t0 0 --bytes 5e7 --k-yen 5 --format text
echo ""

echo "━━━ Prueba 2: t0=10 (salida retrasada) ━━━"
echo "(Observa cómo latencia ≠ ETA)"
./cgr --contacts "$CONTACTS" --src 100 --dst 200 --t0 10 --bytes 5e7 --k-yen 5 --format text
echo ""

echo "━━━ Prueba 3: Bundle grande (agota capacidad) ━━━"
./cgr --contacts "$CONTACTS" --src 100 --dst 200 --t0 0 --bytes 9e7 --k 3 --format text
echo ""

echo "━━━ Prueba 4: TTL estricto ━━━"
./cgr --contacts "$CONTACTS" --src 100 --dst 200 --t0 0 --bytes 5e7 --expiry 80 --k-yen 5 --format text
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ Tests completados                                       ║"
echo "╚════════════════════════════════════════════════════════════╝"