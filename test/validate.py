#!/usr/bin/env python3
"""
Valida rutas devueltas por el binario cgr para un contacts.csv dado.

Entrada:
  --contacts <csv>
  --json '<salida_json_de_cgr>'
  --bytes <bundle_bytes>
  --mode consume|yen

Salida:
  Una o varias líneas CSV (una por ruta):
    found,eta,latency,hops,valid,msg
Dónde:
  - valid=true si la secuencia de contactos es temporalmente encadenable,
    respeta tasa/ventana/owlt y capacidad.
  - En modo 'consume', acumula consumo sobre las K rutas.
"""

import argparse, json, math

def load_contacts(path):
    contacts = {}
    order = []
    with open(path,"r") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"): continue
            parts = [x.strip() for x in s.split(",")]
            cid = int(parts[0]); from_n = int(parts[1]); to_n=int(parts[2])
            t_start=float(parts[3]); t_end=float(parts[4]); owlt=float(parts[5])
            rate=float(parts[6]); setup=float(parts[7]); resid=float(parts[8])
            contacts[cid] = dict(id=cid, from_n=from_n, to_n=to_n, t_start=t_start, t_end=t_end,
                                 owlt=owlt, rate=rate, setup=setup, resid=resid)
            order.append(cid)
    return contacts, order

def available_bytes_window(c, t_in):
    if t_in > c["t_end"]: return 0.0
    start_tx = max(t_in, c["t_start"])
    window = c["t_end"] - start_tx - c["setup"]
    if window <= 1e-12: return 0.0
    rate = max(1.0, c["rate"])
    return window * rate

def eta_contact(c, t_in, bundle_bytes, expiry_abs=None, resid_override=None):
    if t_in > c["t_end"]: return math.inf
    avail = available_bytes_window(c, t_in)
    cap_resid = c["resid"] if resid_override is None else resid_override
    cap = min(cap_resid, avail)
    if cap + 1e-9 < bundle_bytes: return math.inf
    start_tx = max(t_in, c["t_start"])
    tx_time = bundle_bytes / max(1.0, c["rate"])
    finish = start_tx + c["setup"] + tx_time
    if finish > c["t_end"] + 1e-12: return math.inf
    eta = finish + c["owlt"]
    if expiry_abs is not None and eta > expiry_abs: return math.inf
    return eta

def validate_sequence(contacts, seq, t0, bundle_bytes, expiry_abs=None, residual_state=None):
    """ residual_state: dict cid -> resid actual (para modo consumo) """
    t_in = t0
    last_to = None
    used = []
    for idx, cid in enumerate(seq):
        if cid not in contacts:
            return False, f"contact_id {cid} no existe"
        c = contacts[cid]
        if idx==0 and last_to is None:
            pass
        else:
            # encadenado por nodo: el from debe ser el 'to' anterior
            if c["from_n"] != last_to:
                return False, f"encadenado inválido: {last_to} -> {c['from_n']}"
        resid = residual_state.get(cid, c["resid"]) if residual_state is not None else c["resid"]
        eta = eta_contact(c, t_in, bundle_bytes, expiry_abs, resid_override=resid)
        if not math.isfinite(eta):
            return False, f"no cabe en ventana/capacidad (cid={cid})"
        # consumir capacidad de este contacto (para modo consumo)
        if residual_state is not None:
            residual_state[cid] = max(0.0, resid - bundle_bytes)
        # avanzar
        start_tx = max(t_in, c["t_start"])
        tx_time = bundle_bytes / max(1.0, c["rate"])
        finish = start_tx + c["setup"] + tx_time
        t_in = finish + c["owlt"]
        last_to = c["to_n"]
        used.append(cid)
    return True, "ok"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contacts", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--bytes", type=float, required=True)
    ap.add_argument("--mode", choices=["consume","yen"], default="consume")
    args = ap.parse_args()

    C, order = load_contacts(args.contacts)
    doc = json.loads(args.json)
    t0 = 0.0

    if not doc.get("found", False):
        print("false,0,0,0,false,not_found")
        return

    # normalizamos a lista de rutas
    routes = []
    if "routes" in doc:
        routes = doc["routes"]
    else:
        routes = [dict(eta=doc.get("eta",0.0), hops=doc.get("hops",0), contacts=doc.get("contacts",[]))]

    # residual state para modo consumo
    resid_state = {cid: C[cid]["resid"] for cid in C} if args.mode=="consume" else None

    for r in routes:
        seq = r.get("contacts", [])
        if not seq:
            print(f"true,{r.get('eta',0)},{r.get('latency',0)},{r.get('hops',0)},false,empty_route")
            continue
        ok, msg = validate_sequence(C, seq, t0, args.bytes, None, resid_state)
        valid = "true" if ok else "false"
        eta = r.get("eta", 0.0)
        lat = r.get("latency", 0.0)
        hops = r.get("hops", len(seq))
        print(f"true,{eta},{lat},{hops},{valid},{msg}")

if __name__ == "__main__":
    main()
