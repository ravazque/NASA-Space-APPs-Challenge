#!/bin/bash
# analisis_leo.sh - Simula análisis de conectividad LEO→GS

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Análisis de Conectividad LEO: Satélite → Ground Station ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

CONTACTS="data/contacts.csv"

echo "📡 Escenario: Downlink de telemetría (50 MB)"
echo "   • Origen:  Nodo 100 (Ground Station)"
echo "   • Destino: Nodo 200 (Ground Station)"
echo "   • Payload: 50,000,000 bytes"
echo "   • Tiempo:  t0 = 0 s"
echo ""
echo "────────────────────────────────────────────────────────────"

# Ruta primaria
echo "🔹 RUTA PRIMARIA (óptima)"
echo ""
./cgr --contacts "$CONTACTS" \
      --src 100 --dst 200 \
      --t0 0 --bytes 5e7 \
      --format text
echo ""

# Backup routes
echo "────────────────────────────────────────────────────────────"
echo "🔹 RUTAS DE RESPALDO (Top 3 con consumo)"
echo ""
./cgr --contacts "$CONTACTS" \
      --src 100 --dst 200 \
      --t0 0 --bytes 5e7 \
      --k 3 \
      --format text
echo ""

# Análisis de diversidad
echo "────────────────────────────────────────────────────────────"
echo "🔹 ANÁLISIS DE DIVERSIDAD (Yen K-shortest paths)"
echo "   (Rutas independientes sin agotar recursos)"
echo ""
./cgr --contacts "$CONTACTS" \
      --src 100 --dst 200 \
      --t0 0 --bytes 5e7 \
      --k-yen 5 \
      --format text
echo ""

# Caso con restricción temporal
echo "────────────────────────────────────────────────────────────"
echo "🔹 CASO CRÍTICO: TTL = 100s (ventana limitada)"
echo ""
./cgr --contacts "$CONTACTS" \
      --src 100 --dst 200 \
      --t0 0 --bytes 5e7 \
      --expiry 100 \
      --k-yen 3 \
      --format text
echo ""

echo "════════════════════════════════════════════════════════════"
echo "Análisis completado. Ver gráficas de conectividad temporal."
echo "════════════════════════════════════════════════════════════"
