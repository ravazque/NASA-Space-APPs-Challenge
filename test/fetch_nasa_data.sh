#!/bin/bash
# scripts/fetch_nasa_data.sh - Obtener datos reales de NASA

DATASET_ID="${1:-gvk9-iz74}"  # Ejemplo: ISS TLEs dataset
API_KEY="${NASA_API_KEY}"

echo "Descargando datos de NASA data.nasa.gov..."
echo "Dataset: $DATASET_ID"

# Obtener datos via SODA API
curl -G "https://data.nasa.gov/resource/${DATASET_ID}.json" \
     --data-urlencode '$limit=1000' \
     -H "X-App-Token: ${SODA_APP_TOKEN:-}" \
     -o data/nasa_raw.json

echo "✓ Datos descargados en data/nasa_raw.json"

# Convertir a CSV (requiere jq)
if command -v jq &> /dev/null; then
    echo "Convirtiendo a CSV..."
    jq -r '(.[0] | keys_unsorted) as $keys | $keys, map([.[ $keys[] ]]) | @csv' \
       data/nasa_raw.json > data/nasa_contacts.csv
    echo "✓ CSV generado en data/nasa_contacts.csv"
else
    echo "⚠️  Instala 'jq' para convertir automáticamente a CSV"
fi