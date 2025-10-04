#!/usr/bin/env python3
"""
Analiza resultados de tests y genera reporte
"""

import csv
import sys
from collections import defaultdict

def analyze_results(csv_path):
    stats = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'by_mode': defaultdict(lambda: {'pass': 0, 'fail': 0}),
        'by_case': defaultdict(lambda: {'pass': 0, 'fail': 0}),
    }
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats['total'] += 1
            
            valid = row['valid'] == 'true'
            if valid:
                stats['passed'] += 1
                stats['by_mode'][row['mode']]['pass'] += 1
                stats['by_case'][row['case']]['pass'] += 1
            else:
                stats['failed'] += 1
                stats['by_mode'][row['mode']]['fail'] += 1
                stats['by_case'][row['case']]['fail'] += 1
    
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              ANÁLISIS DE RESULTADOS CGR                   ║")
    print("╚══════════════════════════════════════════════════════════╝\n")
    
    success_rate = 100.0 * stats['passed'] / stats['total'] if stats['total'] > 0 else 0
    
    print(f"📊 Resumen Global:")
    print(f"   • Total tests:  {stats['total']}")
    print(f"   • ✅ Pasados:    {stats['passed']} ({success_rate:.1f}%)")
    print(f"   • ❌ Fallidos:   {stats['failed']}\n")
    
    print("📈 Por Modo:")
    for mode, data in sorted(stats['by_mode'].items()):
        total = data['pass'] + data['fail']
        rate = 100.0 * data['pass'] / total if total > 0 else 0
        print(f"   • {mode:8s}: {data['pass']:3d}/{total:3d} ({rate:5.1f}%)")
    
    print("\n🔍 Casos con mayor tasa de fallo:")
    failures = [(case, data['fail'], data['pass'] + data['fail']) 
                for case, data in stats['by_case'].items() 
                if data['fail'] > 0]
    failures.sort(key=lambda x: x[1], reverse=True)
    
    for case, fails, total in failures[:10]:
        print(f"   • {case:30s}: {fails}/{total} fallos")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: analyze_results.py <results.csv>")
        sys.exit(1)
    
    analyze_results(sys.argv[1])