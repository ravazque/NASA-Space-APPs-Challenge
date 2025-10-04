#!/usr/bin/env python3
"""
Genera casos de contactos para probar CGR:

- small_*: grafos pequeños (línea, diamante, estrella, anillo)
- medium_*: añade cuellos de botella y variantes temporales
- large_*: mallas más densas
- rand_*: grafos aleatorios reproducibles

Formato CSV con cabecera comentada + línea META con src/dst:
# META,src,100,dst,200
# id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes
"""

import argparse, os, random

def w(f, rows):
    for r in rows:
        f.write(r + "\n")

def line_case(src=100, dst=200, hops=3, start=0, wlen=40, gap=10, rate=6e6, setup=0.1, owlt=0.02, bytes_cap=3e8):
    rows = [f"# META,src,{src},dst,{dst}"]
    rows.append("# id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes")
    cur = src
    t = start
    for i in range(hops-1):
        nxt = i+1
        rows.append(f"{i},{cur},{nxt},{t},{t+wlen},{owlt:.3f},{rate:.0f},{setup:.2f},{bytes_cap:.0f}")
        cur = nxt
        t += wlen - gap
    rows.append(f"{hops-1},{cur},{dst},{t},{t+wlen},{owlt:.3f},{rate:.0f},{setup:.2f},{bytes_cap:.0f}")
    return rows

def diamond_case(src=100, dst=200):
    rows = [f"# META,src,{src},dst,{dst}"]
    rows.append("# id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes")
    # 100->1,100->2 ; 1->200,2->200
    rows.append("0,100,1,0,60,0.020,8000000,0.1,300000000")
    rows.append("1,100,2,0,60,0.020,8000000,0.1,300000000")
    rows.append("2,1,200,30,100,0.020,9000000,0.1,300000000")
    rows.append("3,2,200,25,90,0.020,6000000,0.1,300000000")
    return rows

def star_case(src=100, dst=200):
    rows = [f"# META,src,{src},dst,{dst}"]
    rows.append("# id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes")
    # src->a,b,c ; a/b/c -> hub -> dst
    rows.append("0,100,1,0,40,0.020,7000000,0.1,200000000")
    rows.append("1,100,2,5,50,0.020,7000000,0.1,200000000")
    rows.append("2,100,3,10,60,0.020,7000000,0.1,200000000")
    rows.append("3,1,4,30,80,0.020,5000000,0.1,150000000")
    rows.append("4,2,4,45,90,0.020,5000000,0.1,150000000")
    rows.append("5,3,4,55,100,0.020,5000000,0.1,150000000")
    rows.append("6,4,200,85,140,0.020,9000000,0.1,400000000")
    return rows

def ring_case(src=100, dst=200):
    rows = [f"# META,src,{src},dst,{dst}"]
    rows.append("# id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes")
    # dos caminos alrededor del anillo (100-1-2-200 y 100-3-4-200)
    rows.append("0,100,1,0,40,0.020,6000000,0.1,200000000")
    rows.append("1,1,2,20,70,0.020,6000000,0.1,200000000")
    rows.append("2,2,200,60,110,0.020,7000000,0.1,200000000")
    rows.append("3,100,3,0,45,0.020,6000000,0.1,200000000")
    rows.append("4,3,4,25,80,0.020,6000000,0.1,200000000")
    rows.append("5,4,200,65,120,0.020,7000000,0.1,200000000")
    return rows

def bottleneck_variant(rows, factor=0.25):
    out = []
    for r in rows:
        if r.startswith("#") or r.strip()=="":
            out.append(r); continue
        parts = [x.strip() for x in r.split(",")]
        rate = float(parts[6])
        resid = float(parts[8])
        # reduce capacidad en el primer y último salto (ejemplo simple)
        if parts[0] in ("0","1"):
            rate = rate * factor
            resid = resid * factor
        parts[6] = str(int(rate))
        parts[8] = str(int(resid))
        out.append(",".join(parts))
    return out

def rand_case(name, src=100, dst=200, n_mid=10, density=0.35, seed=42):
    rnd = random.Random(seed)
    rows = [f"# META,src,{src},dst,{dst}"]
    rows.append("# id,from,to,t_start,t_end,owlt_s,rate_bps,setup_s,residual_bytes")
    cid = 0
    times = {}
    levels = [[],[]]
    for i in range(1, n_mid+1):
        levels[rnd.randint(0,1)].append(i)
    for i in levels[0]:
        t0 = rnd.randint(0,20); te = t0 + rnd.randint(30,60)
        rate = rnd.randint(4,10)*1e6; setup = 0.1; owlt=0.02
        resid = rnd.randint(2,8)*1e8
        rows.append(f"{cid},{src},{i},{t0},{te},{owlt:.3f},{int(rate)},{setup:.1f},{int(resid)}"); cid+=1
        times[i] = te-5
    for i in range(1,n_mid+1):
        for j in range(1,n_mid+1):
            if i==j: continue
            if rnd.random() < density:
                base = times.get(i, rnd.randint(20,40))
                t0 = base - rnd.randint(10,15)
                te = base + rnd.randint(15,35)
                rate = rnd.randint(4,10)*1e6; setup = 0.1; owlt=0.02
                resid = rnd.randint(2,8)*1e8
                rows.append(f"{cid},{i},{j},{t0},{te},{owlt:.3f},{int(rate)},{setup:.1f},{int(resid)}"); cid+=1
                times[j] = max(times.get(j,0), te-5)
    for i in range(1,n_mid+1):
        if rnd.random() < 0.7:
            base = times.get(i, rnd.randint(50,80))
            t0 = base; te = base + rnd.randint(25,45)
            rate = rnd.randint(6,12)*1e6; setup=0.1; owlt=0.02
            resid = rnd.randint(3,10)*1e8
            rows.append(f"{cid},{i},{dst},{t0},{te},{owlt:.3f},{int(rate)},{setup:.1f},{int(resid)}"); cid+=1
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--small", action="store_true")
    ap.add_argument("--medium", action="store_true")
    ap.add_argument("--large", action="store_true")
    ap.add_argument("--random", type=int, default=0, help="nº de casos aleatorios")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    idx = 0

    if args.small:
        cases = [
            ("small_line.csv", line_case()),
            ("small_diamond.csv", diamond_case()),
            ("small_star.csv", star_case()),
            ("small_ring.csv", ring_case()),
        ]
        for name, rows in cases:
            with open(os.path.join(args.out, name), "w") as f: w(f, rows); idx+=1

    if args.medium:
        drows = diamond_case()
        with open(os.path.join(args.out, "medium_diamond_bneck.csv"), "w") as f: w(f, bottleneck_variant(drows, 0.3)); idx+=1
        lrows = line_case(hops=5, wlen=45, gap=8, rate=7e6)
        with open(os.path.join(args.out, "medium_line5.csv"), "w") as f: w(f, lrows); idx+=1

    if args.large:
        lrows = line_case(hops=8, wlen=50, gap=5, rate=8e6, bytes_cap=7e8)
        with open(os.path.join(args.out, "large_line8.csv"), "w") as f: w(f, lrows); idx+=1
        rrows = rand_case("large_rand", n_mid=25, density=0.28, seed=77)
        with open(os.path.join(args.out, "large_rand.csv"), "w") as f: w(f, rrows); idx+=1

    for r in range(args.random):
        name = f"rand_{r:02d}.csv"
        rows = rand_case(name, n_mid=random.randint(6,14), density=random.uniform(0.22,0.4), seed=100+r)
        with open(os.path.join(args.out, name), "w") as f: w(f, rows); idx+=1

    print(f"Generados {idx} casos en {args.out}")

if __name__ == "__main__":
    main()
