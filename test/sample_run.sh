
#!/usr/bin/env bash
# tests/sample_run.sh — ejecución de ejemplo
set -e
cd "$(dirname "$0")/.."
make
echo "== Ruta óptima (k=1):"
./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 50000000
echo
echo "== Tres rutas (k=3) con consumo de capacidad:"
./cgr --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 50000000 --k 3
echo

