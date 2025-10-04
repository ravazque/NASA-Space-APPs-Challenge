#!/usr/bin/env python3
"""
Visualiza rutas CGR en formato gráfico
"""

import argparse
import json
import sys
from datetime import datetime

def load_contacts(path):
    contacts = {}
    with open(path, "r") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"): continue
            parts = [x.strip() for x in s.split(",")]
            cid = int(parts[0])
            from_n = int(parts[1])
            to_n = int(parts[2])
            t_start = float(parts[3])
            t_end = float(parts[4])
            contacts[cid] = {
                'id': cid, 'from': from_n, 'to': to_n,
                't_start': t_start, 't_end': t_end
            }
    return contacts

def classify_node(nid):
    """Clasificar nodo como SAT o GS"""
    if nid % 100 == 0 and nid >= 100 and nid < 1000:
        return "GS"
    return "SAT"

def visualize_route(contacts, route, t0):
    """Visualizar ruta en formato ASCII"""
    if not route['found']:
        print("❌ No route found")
        return
    
    print("\n" + "═" * 70)
    print(f"  VISUALIZACIÓN DE RUTA: ETA={route['eta']:.3f}s, Hops={route['hops']}")
    print("═" * 70 + "\n")
    
    t_current = t0
    
    for i, cid in enumerate(route['contacts']):
        c = contacts[cid]
        
        from_type = classify_node(c['from'])
        to_type = classify_node(c['to'])
        
        # Determinar tipo de enlace
        if from_type == "SAT" and to_type == "SAT":
            link = "ISL 🛰️ ←→ 🛰️"
        elif from_type == "GS":
            link = "UP  📡 ──→ 🛰️"
        else:
            link = "DOWN 🛰️ ──→ 📡"
        
        print(f"Hop #{i+1}: Contact {cid}")
        print(f"  ├─ {link}")
        print(f"  ├─ Nodes: {c['from']}({from_type}) → {c['to']}({to_type})")
        print(f"  ├─ Window: [{c['t_start']:.1f}, {c['t_end']:.1f}]s")
        print(f"  ├─ Start TX: {max(t_current, c['t_start']):.3f}s")
        print(f"  └─ Arrival: {t_current:.3f}s\n")
        
        # Actualizar tiempo para siguiente hop
        start_tx = max(t_current, c['t_start'])
        t_current = start_tx + 1.0  # Simplificado

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contacts", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--t0", type=float, default=0.0)
    args = ap.parse_args()
    
    contacts = load_contacts(args.contacts)
    
    with open(args.json, 'r') as f:
        data = json.load(f)
    
    if 'routes' in data:
        for i, route in enumerate(data['routes']):
            print(f"\n{'=' * 70}")
            print(f"RUTA #{i+1}")
            visualize_route(contacts, route, args.t0)
    else:
        visualize_route(contacts, data, args.t0)

if __name__ == "__main__":
    main()
