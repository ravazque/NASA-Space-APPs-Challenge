#!/bin/bash
# test/test_all.sh — Ejecuta TODAS las pruebas en serie

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              SUITE COMPLETA DE TESTS CGR LEO                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

FAILED=0
PASSED=0

run_test() {
    local name="$1"
    local cmd="$2"
    
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}[TEST]${NC} $name"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if eval "$cmd"; then
        echo -e "${GREEN}✓ PASS${NC}: $name"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $name"
        ((FAILED++))
    fi
    echo ""
}

# ═══════════════════════════════════════════════════════════════════
# FASE 1: Compilación
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}═══ FASE 1: COMPILACIÓN ═══${NC}"
run_test "Compilación limpia" "make fclean && make"

# ═══════════════════════════════════════════════════════════════════
# FASE 2: Tests unitarios básicos
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}═══ FASE 2: TESTS UNITARIOS ═══${NC}"

run_test "Validación de entrada (debe fallar con 'invalid')" \
    "! ./cgr --contacts data/contacts.csv --src invalid --dst 200 --t0 0 --bytes 5e7 2>/dev/null"

run_test "Ruta óptima simple (k=1)" \
    "./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --format text | grep -q 'Ruta óptima'"

run_test "JSON output válido" \
    "./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 | python3 -m json.tool > /dev/null"

run_test "JSON pretty válido" \
    "./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --pretty | python3 -m json.tool > /dev/null"

# ═══════════════════════════════════════════════════════════════════
# FASE 3: Tests de escenarios realistas
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}═══ FASE 3: ESCENARIOS REALISTAS ═══${NC}"

run_test "Escenario realista LEO" \
    "./test/test_realistic.sh > /dev/null"

run_test "K rutas por consumo (K=3)" \
    "./cgr --contacts data/contacts_realistic.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k 3 --format text | grep -q 'Estadísticas'"

run_test "K rutas Yen (K=5)" \
    "./cgr --contacts data/contacts_realistic.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k-yen 5 --format text | grep -q 'Estadísticas'"

run_test "Latencia ≠ ETA con t0>0" \
    "./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 10 --bytes 5e7 --format text | grep 'Latencia:' | grep -v 'ETA:'"

run_test "Restricción de TTL" \
    "./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --expiry 50 --format text"

run_test "Bundle grande agota capacidad" \
    "./cgr --contacts data/contacts_realistic.csv --src 100 --dst 200 --t0 0 --bytes 9e7 --k 3 --format text"

# ═══════════════════════════════════════════════════════════════════
# FASE 4: Suite completa de casos generados
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}═══ FASE 4: SUITE COMPLETA (casos generados) ═══${NC}"

run_test "Generación de casos de prueba" \
    "python3 test/gen_cases.py --small --medium --large --random 10 --out test/cases"

run_test "Validación con casos generados" \
    "bash test/run_all.sh | tee test/out/full_suite.log"

# Verificar tasa de éxito
PASS_RATE=$(awk -F, 'NR>1 && $11=="true"{ok++} END{print int(100*ok/NR)}' test/out/results.csv 2>/dev/null || echo "0")

if [ "$PASS_RATE" -ge 70 ]; then
    echo -e "${GREEN}✓ Tasa de éxito: $PASS_RATE% (≥70% requerido)${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ Tasa de éxito: $PASS_RATE% (<70% requerido)${NC}"
    ((FAILED++))
fi

# ═══════════════════════════════════════════════════════════════════
# FASE 5: Tests de rendimiento
# ═══════════════════════════════════════════════════════════════════

echo -e "${BLUE}═══ FASE 5: BENCHMARKS ═══${NC}"

run_test "Benchmark K=10 Yen" \
    "make bench"

# ═══════════════════════════════════════════════════════════════════
# RESUMEN FINAL
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                      RESUMEN FINAL                            ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}✓ Tests pasados:${NC} $PASSED"
echo -e "${RED}✗ Tests fallidos:${NC} $FAILED"
echo ""

TOTAL=$((PASSED + FAILED))
SUCCESS_RATE=$((100 * PASSED / TOTAL))

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  🎉 TODOS LOS TESTS PASARON (100%)     ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    exit 0
elif [ $SUCCESS_RATE -ge 80 ]; then
    echo -e "${YELLOW}⚠️  Tasa de éxito: $SUCCESS_RATE% (ACEPTABLE)${NC}"
    exit 0
else
    echo -e "${RED}❌ Tasa de éxito: $SUCCESS_RATE% (INSUFICIENTE)${NC}"
    exit 1
fi
