#!/usr/bin/env bash
# test/run_all.sh — genera casos, ejecuta el binario en varios modos y valida

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/cgr"
GEN="$ROOT/test/gen_cases.py"
VAL="$ROOT/test/validate.py"
OUT="$ROOT/test/out"
CASES="$ROOT/test/cases"

mkdir -p "$OUT" "$CASES"

if [ ! -x "$BIN" ]; then
  echo "Compilando binario..."
  make -C "$ROOT"
fi

echo "Generando casos deterministas y aleatorios..."
python3 "$GEN" --small --medium --large --random 25 --out "$CASES" > "$OUT/gen.log"

RESULTS="$OUT/results.csv"
echo "case,mode,k,src,dst,bytes,found,eta,latency,hops,valid,msg" > "$RESULTS"

run_case () {
  local case="$1"; shift
  local mode="$1"; shift
  local k="$1"; shift
  local src="$1"; shift
  local dst="$1"; shift
  local t0="$1"; shift
  local bytes="$1"; shift

  local cmd=("$BIN" --contacts "$case" --src "$src" --dst "$dst" --t0 "$t0" --bytes "$bytes")
  if [ "$mode" = "yen" ]; then
    cmd+=("--k-yen" "$k")
  else
    [ "$k" -gt 1 ] && cmd+=("--k" "$k")
  fi
  # salida JSON compacta (por defecto)
  local out_json
  if ! out_json="$("${cmd[@]}")"; then
    echo "$(basename "$case"),$mode,$k,$src,$dst,$bytes,false,0,0,0,false,exec_error" >> "$RESULTS"
    return
  fi

  # Valida y vuelca línea CSV
  local val
  if ! val="$(python3 "$VAL" --contacts "$case" --json "$out_json" --bytes "$bytes" --mode "$mode")"; then
    echo "$(basename "$case"),$mode,$k,$src,$dst,$bytes,false,0,0,0,false,validator_error" >> "$RESULTS"
    return
  fi
  # el validador imprime múltiples líneas CSV (una por ruta)
  while IFS= read -r line; do
    echo "$(basename "$case"),$mode,$k,$src,$dst,$bytes,$line" >> "$RESULTS"
  done <<< "$val"
}

echo "Ejecutando battery de tests..."
# parámetros genéricos (¡sin espacios!)
BYTES_SMALL=20000000
BYTES_MED=60000000
BYTES_LARGE=150000000

for c in "$CASES"/*.csv; do
  base="$(basename "$c")"

  # src/dst anotados en la línea META del CSV
  src="$(awk -F'[,_]' '/^# META/{print $4}' "$c")"
  dst="$(awk -F'[,_]' '/^# META/{print $6}' "$c")"
  [ -z "${src:-}" ] && src=100
  [ -z "${dst:-}" ] && dst=200

  case "$base" in
    small_*) bytes=$BYTES_SMALL ;;
    medium_*) bytes=$BYTES_MED ;;
    large_*) bytes=$BYTES_LARGE ;;
    rand_*)  bytes=$BYTES_MED ;;
    *)       bytes=$BYTES_SMALL ;;
  esac

  # k=1
  run_case "$c" "consume" 1 "$src" "$dst" 0 "$bytes"
  # K por consumo
  run_case "$c" "consume" 3 "$src" "$dst" 0 "$bytes"
  # K Yen-lite
  run_case "$c" "yen" 3 "$src" "$dst" 0 "$bytes"
done

# Resumen simple al final (stdout + fichero)
pass=$(awk -F, 'NR>1 && $11=="true"{ok++} END{print ok+0}' "$RESULTS")
fail=$(awk -F, 'NR>1 && $11=="false"{ko++} END{print ko+0}' "$RESULTS")
total=$((pass+fail))
{
  echo "Resumen:"
  echo "  Total rutas validadas: $total"
  echo "  ✅ OK: $pass"
  echo "  ❌ KO: $fail"
  echo "Detalles: $RESULTS"
} | tee "$OUT/summary.txt"

