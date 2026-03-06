#!/usr/bin/env python3
"""
MORPHOS CLI — Command-line interface for the Reasoning OS

Usage:
    morphos domains                     List all domains
    morphos import <file.csv>           Import CSV triples
    morphos import --dataset <name>     Import curated dataset
    morphos datasets                    List available curated datasets
    morphos info <domain>               Show domain details
    morphos search <src> <tgt>          Find structural analogy
    morphos query <concept>             Query knowledge about a concept
    morphos evidence <morph_id> ...     Add evidence to a morphism
    morphos programs                    List registered programs
    morphos tasks                       List task history
    morphos snapshot <domain>           Snapshot a domain
    morphos stats                       Show store statistics
    morphos repl                        Interactive REPL
"""
import sys, os, argparse, json, csv, time, readline

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import create_category
from engine.kernel import ReasoningStore, TaskScheduler
from engine.scale import find_analogies_csp, embedding_assisted_search, KnowledgeStore
from engine.learning import AnalogyMemory, learn_and_search, suggest_explorations
from engine.adapters import from_triples_csv


DB_PATH = os.environ.get("MORPHOS_DB", "morphos.db")


def get_store():
    return ReasoningStore(DB_PATH)


def cmd_domains(args):
    store = get_store()
    domains = store.list_domains()
    if not domains:
        print("  No domains. Use 'morphos import' to add data.")
        return
    print(f"  {'Name':<30s} {'Version':>7s}  {'ID'}")
    print(f"  {'─'*30} {'─'*7}  {'─'*36}")
    for d in domains:
        print(f"  {d['name']:<30s} v{d['version']:<6d}  {d['id'][:12]}...")
    print(f"\n  {len(domains)} domain(s)")
    store.close()


def cmd_datasets(args):
    from engine.datasets import ALL_DATASETS
    from engine.knowledge_base import ALL_EXTENDED_DATASETS
    from engine.linguistic_kb import ALL_LINGUISTIC_DATASETS
    all_ds = {**ALL_DATASETS, **ALL_EXTENDED_DATASETS, **ALL_LINGUISTIC_DATASETS}
    print(f"  {'Dataset':<30s} {'Objects':>7s} {'Morphisms':>9s}")
    print(f"  {'─'*30} {'─'*7} {'─'*9}")
    for name, fn in sorted(all_ds.items()):
        d = fn()
        print(f"  {name:<30s} {len(d['objects']):>7d} {len(d['morphisms']):>9d}")
    print(f"\n  {len(all_ds)} datasets available. Import with: morphos import --dataset <name>")


def cmd_import(args):
    store = get_store()
    if args.dataset:
        from engine.datasets import ALL_DATASETS
        from engine.knowledge_base import ALL_EXTENDED_DATASETS
        from engine.linguistic_kb import ALL_LINGUISTIC_DATASETS
        all_ds = {**ALL_DATASETS, **ALL_EXTENDED_DATASETS, **ALL_LINGUISTIC_DATASETS}
        if args.dataset == "all":
            for name, fn in all_ds.items():
                data = fn()
                cat = create_category(data["name"], data["objects"], data["morphisms"], auto_close=False)
                did = store.import_category(cat, domain_name=name)
                print(f"  Imported {name}: {len(data['objects'])} obj, {len(data['morphisms'])} morph")
            print(f"\n  {len(all_ds)} datasets imported.")
        elif args.dataset in all_ds:
            data = all_ds[args.dataset]()
            cat = create_category(data["name"], data["objects"], data["morphisms"], auto_close=False)
            did = store.import_category(cat, domain_name=args.dataset)
            print(f"  Imported {args.dataset}: {len(data['objects'])} obj, {len(data['morphisms'])} morph → {did[:12]}...")
        else:
            print(f"  Unknown dataset: {args.dataset}")
            print(f"  Available: {', '.join(sorted(all_ds.keys()))}")
    elif args.file:
        name = args.name or os.path.splitext(os.path.basename(args.file))[0]
        delimiter = "\t" if args.file.endswith(".tsv") else ","
        cat = from_triples_csv(args.file, name=name, delimiter=delimiter,
                               skip_header=not args.no_header)
        did = store.import_category(cat)
        print(f"  Imported {name}: {len(cat.objects)} obj, {len(cat.user_morphisms())} morph → {did[:12]}...")
    elif args.json:
        with open(args.json) as f:
            data = json.load(f)
        name = args.name or os.path.splitext(os.path.basename(args.json))[0]
        morphs = [(m[0], m[1], m[2], m[3] if len(m)>3 else "") for m in data["morphisms"]]
        cat = create_category(name, data["objects"], morphs, auto_close=False)
        did = store.import_category(cat)
        print(f"  Imported {name}: {len(cat.objects)} obj, {len(cat.user_morphisms())} morph → {did[:12]}...")
    else:
        print("  Usage: morphos import --dataset <name>")
        print("         morphos import --file <path.csv> [--name <domain_name>]")
        print("         morphos import --json <path.json> [--name <domain_name>]")
    store.close()


def cmd_info(args):
    store = get_store()
    d = store.get_domain(args.domain)
    if not d:
        print(f"  Domain '{args.domain}' not found.")
        store.close()
        return
    concepts = store.get_concepts(d["id"])
    morphisms = store.get_morphisms(d["id"])
    rel_types = set(m["rel_type"] for m in morphisms if m["rel_type"])
    inferred = sum(1 for m in morphisms if m["is_inferred"])
    evidenced = sum(1 for m in morphisms if m["evidence_ids"] != "[]")

    print(f"  Domain: {d['name']} (v{d['version']})")
    print(f"  ID: {d['id']}")
    print(f"  Objects: {len(concepts)}")
    print(f"  Morphisms: {len(morphisms)} ({inferred} inferred, {evidenced} with evidence)")
    print(f"  Relation types: {', '.join(sorted(rel_types)) if rel_types else '(none)'}")
    print()
    if morphisms:
        print(f"  {'Label':<20s} {'Source':<15s} {'Target':<15s} {'Type':<12s} {'Truth':>10s}")
        print(f"  {'─'*20} {'─'*15} {'─'*15} {'─'*12} {'─'*10}")
        for m in morphisms[:20]:
            flag = " *" if m["is_inferred"] else ""
            truth = f"{m['truth_modality'][:4]}({m['truth_degree']:.2f})"
            print(f"  {m['label']:<20s} {m['source_label']:<15s} {m['target_label']:<15s} {m['rel_type']:<12s} {truth:>10s}{flag}")
        if len(morphisms) > 20:
            print(f"  ... and {len(morphisms) - 20} more")
    store.close()


def cmd_search(args):
    store = get_store()
    src = store.get_domain(args.source)
    tgt = store.get_domain(args.target)
    if not src:
        print(f"  Domain '{args.source}' not found.")
        store.close(); return
    if not tgt:
        print(f"  Domain '{args.target}' not found.")
        store.close(); return

    sc = store.export_category(src["id"])
    tc = store.export_category(tgt["id"])

    method = args.method or "csp"
    print(f"  Searching: {args.source} → {args.target} (method={method})...")

    t0 = time.time()
    if method == "csp":
        results = find_analogies_csp(sc, tc, max_results=5)
    elif method == "embedding":
        results = embedding_assisted_search(sc, tc)
    else:
        from engine import find_functors_scalable
        ms = find_functors_scalable(sc, tc, min_score=0.0)
        results = [{"object_map": m.object_map, "score": m.overall_score} for m in ms]
    dt = time.time() - t0

    if results and results[0].get("score", 0) > 0:
        best = results[0]
        print(f"\n  Analogy found (score: {best['score']:.3f}) in {dt*1000:.0f}ms")
        print()
        print(f"  {'Source':<25s} {'Target':<25s}")
        print(f"  {'─'*25} {'─'*25}")
        for s, t in best["object_map"].items():
            print(f"  {s:<25s} ↦ {t}")

        # Auto-register
        pid = store.register_program(
            f"{args.source}→{args.target}", args.source, args.target,
            best["object_map"], score=best["score"])
        print(f"\n  Registered as program: {pid[:12]}...")
    else:
        print(f"\n  No structural analogy found ({dt*1000:.0f}ms)")

    store.close()


def cmd_query(args):
    ks = KnowledgeStore()
    ks.load_all_datasets()
    concept = args.concept

    # Query by subject
    results = ks.query(subject=concept, limit=20)
    if results:
        print(f"\n  '{concept}' as subject:")
        for rel, src, tgt, domain in results:
            print(f"    [{domain}] {rel}: {src} → {tgt}")

    # Query by object
    results_obj = ks.query(obj=concept, limit=10)
    if results_obj:
        print(f"\n  '{concept}' as object:")
        for rel, src, tgt, domain in results_obj:
            print(f"    [{domain}] {rel}: {src} → {tgt}")

    if not results and not results_obj:
        print(f"  No knowledge about '{concept}' in curated datasets.")


def cmd_evidence(args):
    store = get_store()
    mid = args.morphism_id
    if args.add:
        direction = "supports" if args.supports else "contradicts" if args.contradicts else "supports"
        eid = store.add_evidence(mid, args.add, direction, args.strength or 0.8, args.source or "")
        print(f"  Added evidence: {eid[:12]}...")
        m = store.conn.execute("SELECT truth_degree, truth_modality FROM morphisms WHERE id=?", (mid,)).fetchone()
        if m:
            print(f"  Updated truth: {m['truth_modality']}({m['truth_degree']:.3f})")
    else:
        evidence = store.get_evidence(mid)
        if evidence:
            for e in evidence:
                dir_sym = "+" if e["direction"] == "supports" else "−"
                print(f"  [{dir_sym}] {e['label']} (str={e['strength']:.1f}) from {e['source']}")
        else:
            print("  No evidence recorded.")
    store.close()


def cmd_programs(args):
    store = get_store()
    programs = store.list_programs()
    if not programs:
        print("  No programs. Run 'morphos search' to discover analogies.")
        store.close(); return
    print(f"  {'Name':<35s} {'v':>2s} {'Score':>6s} {'Conf':>4s}")
    print(f"  {'─'*35} {'─'*2} {'─'*6} {'─'*4}")
    for p in programs:
        print(f"  {p['name']:<35s} v{p['version']:<1d} {p['score']:>6.3f} {p['confirmations']:>4d}")
    print(f"\n  {len(programs)} program(s)")
    store.close()


def cmd_tasks(args):
    store = get_store()
    sched = TaskScheduler(store)
    tasks = sched.list_tasks()
    if not tasks:
        print("  No tasks."); store.close(); return
    for t in tasks[:20]:
        dur = f" {t['duration_ms']:.0f}ms" if t['duration_ms'] else ""
        print(f"  [{t['status']}] {t['task_type']}{dur}  {t['id'][:12]}...")
    store.close()


def cmd_snapshot(args):
    store = get_store()
    d = store.get_domain(args.domain)
    if not d:
        print(f"  Domain '{args.domain}' not found."); store.close(); return
    new_id = store.snapshot_domain(d["id"])
    print(f"  Snapshot created: {new_id[:12]}... (v{d['version'] + 1})")
    store.close()


def cmd_stats(args):
    store = get_store()
    s = store.stats
    print(f"  Database: {DB_PATH}")
    print(f"  Domains:     {s['domains']}")
    print(f"  Concepts:    {s['concepts']}")
    print(f"  Morphisms:   {s['morphisms']}")
    print(f"  Evidence:    {s['evidence']}")
    print(f"  Derivations: {s['derivations']}")
    print(f"  Programs:    {s['programs']}")
    print(f"  Tasks:       {s['tasks']}")
    store.close()


# ── REPL Helpers ──────────────────────────────────────

def _print_explanation(node: dict, indent: int = 0):
    """Recursively print a proof explanation tree."""
    pad = "  " * indent
    rule = f" [{node.get('rule', 'axiom')}]" if node.get("rule") else " [axiom]"
    print(f"{pad}  {node['label']}: {node['source']} → {node['target']}")
    print(f"{pad}    truth: {node['truth']}{rule}")
    if node.get("proof_term"):
        print(f"{pad}    proof: {node['proof_term'][:60]}")
    for ev in node.get("evidence", []):
        sym = "+" if ev["direction"] == "supports" else "−"
        print(f"{pad}    evidence [{sym}] {ev['label']} (str={ev['strength']:.2f})")
    for child in node.get("premises", []):
        if child:
            _print_explanation(child, indent + 1)


def _run_pipeline_repl(store, sched, mem, src_name: str, tgt_name: str):
    """Execute the 7-step canonical reasoning pipeline and print a full report."""
    import time
    steps = []

    def step(n: int, label: str):
        print(f"  [{n}/7] {label}...")
        return time.time()

    # 1. Import check
    t = step(1, f"Import check: {src_name}, {tgt_name}")
    src = store.get_domain(src_name)
    tgt = store.get_domain(tgt_name)
    if not src:
        print(f"       ✗ Source domain '{src_name}' not found. Import it first.")
        return
    if not tgt:
        print(f"       ✗ Target domain '{tgt_name}' not found. Import it first.")
        return
    src_c = store.get_concepts(src["id"])
    tgt_c = store.get_concepts(tgt["id"])
    print(f"       ✓ {src_name} ({len(src_c)} obj), {tgt_name} ({len(tgt_c)} obj)")
    steps.append(("import", True))

    # 2. Evidence summary
    t = step(2, "Evidence audit")
    src_m = store.get_morphisms(src["id"])
    tgt_m = store.get_morphisms(tgt["id"])
    evidenced_src = sum(1 for m in src_m if m["evidence_ids"] != "[]")
    evidenced_tgt = sum(1 for m in tgt_m if m["evidence_ids"] != "[]")
    print(f"       ✓ Source: {evidenced_src}/{len(src_m)} morphisms have evidence")
    print(f"       ✓ Target: {evidenced_tgt}/{len(tgt_m)} morphisms have evidence")
    steps.append(("evidence", True))

    # 3. Composition
    t = step(3, f"Auto-compose: {src_name}")
    tid = sched.submit("compose", {"domain_name": src_name})
    r = sched.execute(tid)
    print(f"       ✓ {r.get('new_compositions', 0)} new compositions, {r.get('stored_to_kernel', 0)} stored")
    steps.append(("compose", True))

    # 4. Analogy search
    t = step(4, f"CSP analogy search: {src_name} → {tgt_name}")
    t0 = time.time()
    from engine.scale import find_analogies_csp
    sc = store.export_category(src["id"])
    tc = store.export_category(tgt["id"])
    results = find_analogies_csp(sc, tc, max_results=3)
    dt = (time.time() - t0) * 1000
    if results and results[0]["score"] > 0:
        best = results[0]
        partial = " (partial)" if best.get("partial") else ""
        struct = f"  structural={best.get('structural_score', best['score']):.3f}"
        sem = f"  semantic={best.get('semantic_score', 0.0):.3f}" if best.get("semantic_score") is not None else ""
        print(f"       ✓ Found{partial} (score={best['score']:.3f},{struct},{sem} {dt:.0f}ms):")
        for s, tv in list(best["object_map"].items())[:5]:
            print(f"         {s:<20s} ↦ {tv}")
        if len(best["object_map"]) > 5:
            print(f"         ... +{len(best['object_map'])-5} more mappings")
        steps.append(("search", best["score"]))
    else:
        print(f"       ✗ No analogy found ({dt:.0f}ms)")
        steps.append(("search", 0.0))
        results = []

    # 5. Store mapping as program
    t = step(5, "Store mapping as program")
    if results and results[0]["score"] > 0:
        best = results[0]
        prog_name = f"{src_name}→{tgt_name}"
        pid = store.register_program(prog_name, src_name, tgt_name,
                                     best["object_map"], score=best["score"])
        print(f"       ✓ Program '{prog_name}' registered ({pid[:12]}...)")
        steps.append(("program", pid))
    else:
        print(f"       — Skipped (no mapping to store)")
        steps.append(("program", None))
        pid = None

    # 6. Program tests
    t = step(6, "Run program tests")
    if pid:
        test_result = store.run_program_tests(pid)
        passed = test_result.get("passed", 0)
        failed = test_result.get("failed", 0)
        total = passed + failed
        if total == 0:
            print(f"       — No tests registered (add tests via: POST /api/programs/<id>/test)")
        else:
            status = "✓" if failed == 0 else "✗"
            print(f"       {status} {passed}/{total} tests passed")
        steps.append(("tests", test_result))
    else:
        print(f"       — Skipped")
        steps.append(("tests", None))

    # 7. Derivation inspection
    t = step(7, "Inspect derivations")
    all_m = store.get_morphisms(src["id"]) + store.get_morphisms(tgt["id"])
    inferred = [m for m in all_m if m["is_inferred"]]
    weak = [m for m in all_m if m["truth_degree"] < 0.7]
    print(f"       ✓ {len(inferred)} inferred morphisms across both domains")
    if weak:
        print(f"       ⚠ {len(weak)} morphisms with truth < 0.7 (may need evidence)")
        for m in weak[:3]:
            print(f"         {m['label']}: {m['source_label']}→{m['target_label']} truth={m['truth_degree']:.3f}")
    steps.append(("derivations", len(inferred)))

    # Summary
    print(f"\n  ═══ Pipeline Complete ═══")
    passed_steps = sum(1 for _, v in steps if v and v is not False)
    print(f"  {passed_steps}/{len(steps)} steps succeeded")
    score = next((v for name, v in steps if name == "search" and isinstance(v, float)), 0.0)
    if score > 0.5:
        print(f"  ★ Strong analogy found (score={score:.3f}) — consider 'speculate on {src_name}'")
    elif score > 0.2:
        print(f"  ◈ Partial analogy found (score={score:.3f}) — try 'infer {src_name}' for more morphisms")
    else:
        print(f"  ○ Weak/no analogy — try larger domains or 'embedding' method")
    print()


# ── REPL ──────────────────────────────────────────────

def cmd_repl(args):
    """Interactive REPL with command compilation."""
    store = get_store()
    sched = TaskScheduler(store)
    mem = AnalogyMemory()
    ks = KnowledgeStore()
    try:
        ks.load_all_datasets()
    except Exception:
        pass

    print("  MORPHOS Reasoning OS — Interactive REPL")
    print("  Natural language queries compile to kernel tasks.")
    print("  Examples: 'find analogies between Irish mutations and type-system variance'")
    print("            'pipeline celtic math'  'compose grammar'  'infer grammar'")
    print("            'explain <morphism_id>'  'memory'  'suggest'")
    print("  Type 'help' for commands, 'quit' to exit.\n")

    from engine.query_lang import compile_query

    while True:
        try:
            line = input("λ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting.")
            break

        if not line:
            continue

        if line.lower() in ("quit", "exit", "q"):
            break

        # Compile the natural language query
        known = set()
        for d in store.list_domains():
            known.add(d["name"])

        cmd = compile_query(line, known_domains=known)

        try:
            if cmd.action == "help":
                print("""  ── Search & Analogy ──
    search music → math           find analogies (csp/embedding/scalable)
    pipeline music math           run full 7-step reasoning workflow
    compare celtic grammar        search + show scores

  ── Inference & Reasoning ──
    compose grammar               auto-compose morphisms
    infer grammar                 transitive closure (rule=transitivity)
    speculate on grammar          generate candidate morphisms

  ── Explain & Audit ──
    explain <morphism_id>         proof trace for a morphism
    explain path x → y in grammar  all morphisms connecting x→y
    evidence <morphism_id>        show evidence for a morphism

  ── Programs ──
    programs                      list registered programs
    test program <n>              run tests for a program
    reinforce program <n>         confirm a program
    save program <n> music math   register a named program

  ── Data ──
    import all                    import all curated datasets
    import grammar                import a specific dataset
    info grammar                  show domain details
    domains / datasets / stats

  ── Knowledge ──
    query <concept>               look up a concept
    memory / beliefs              show learned analogies
    suggest                       suggest unexplored pairs""")


            elif cmd.action == "domains":
                for d in store.list_domains():
                    print(f"    {d['name']} (v{d['version']})")

            elif cmd.action == "datasets":
                from engine.datasets import ALL_DATASETS
                from engine.knowledge_base import ALL_EXTENDED_DATASETS
                from engine.linguistic_kb import ALL_LINGUISTIC_DATASETS
                for n in sorted({**ALL_DATASETS, **ALL_EXTENDED_DATASETS, **ALL_LINGUISTIC_DATASETS}.keys()):
                    print(f"    {n}")

            elif cmd.action == "import":
                name = cmd.params.get("dataset", "")
                from engine.datasets import ALL_DATASETS
                from engine.knowledge_base import ALL_EXTENDED_DATASETS
                from engine.linguistic_kb import ALL_LINGUISTIC_DATASETS
                all_ds = {**ALL_DATASETS, **ALL_EXTENDED_DATASETS, **ALL_LINGUISTIC_DATASETS}
                if name == "all":
                    for n, fn in all_ds.items():
                        data = fn()
                        cat = create_category(data["name"], data["objects"], data["morphisms"], auto_close=False)
                        store.import_category(cat, domain_name=n)
                    print(f"  Imported {len(all_ds)} datasets")
                elif name in all_ds:
                    data = all_ds[name]()
                    cat = create_category(data["name"], data["objects"], data["morphisms"], auto_close=False)
                    store.import_category(cat, domain_name=name)
                    print(f"  Imported {name}: {len(data['objects'])} obj, {len(data['morphisms'])} morph")
                else:
                    print(f"  Unknown dataset: {name}")

            elif cmd.action == "info":
                name = cmd.params.get("domain", "")
                d = store.get_domain(name)
                if not d:
                    print(f"  Not found: {name}")
                else:
                    morphisms = store.get_morphisms(d["id"])
                    concepts = store.get_concepts(d["id"])
                    print(f"  {d['name']} v{d['version']}: {len(concepts)} obj, {len(morphisms)} morph")
                    for m in morphisms[:10]:
                        print(f"    {m['label']}: {m['source_label']} → {m['target_label']} [{m['rel_type']}]")
                    if len(morphisms) > 10:
                        print(f"    ... {len(morphisms) - 10} more")

            elif cmd.action == "search":
                src_name = cmd.params["source"]
                tgt_name = cmd.params["target"]
                method = cmd.params.get("method", "csp")
                src = store.get_domain(src_name)
                tgt = store.get_domain(tgt_name)
                if not src:
                    print(f"  Domain not found: {src_name}"); continue
                if not tgt:
                    print(f"  Domain not found: {tgt_name}"); continue
                sc = store.export_category(src["id"])
                tc = store.export_category(tgt["id"])
                t0 = time.time()
                if method == "embedding":
                    from engine.scale import embedding_assisted_search
                    results = embedding_assisted_search(sc, tc)
                else:
                    from engine.scale import find_analogies_csp
                    results = find_analogies_csp(sc, tc, max_results=3)
                dt = time.time() - t0
                if results and results[0]["score"] > 0:
                    r = results[0]
                    partial = " (partial)" if r.get("partial") else ""
                    struct = f", structural={r['structural_score']:.3f}" if r.get("structural_score") is not None else ""
                    sem = f", semantic={r['semantic_score']:.3f}" if r.get("semantic_score") is not None else ""
                    print(f"  Analogy{partial} (score: {r['score']:.3f}{struct}{sem}, {dt*1000:.0f}ms, {method}):")
                    for s, t in r["object_map"].items():
                        print(f"    {s:<25s} ↦ {t}")
                    pid = store.register_program(f"{src_name}→{tgt_name}", src_name, tgt_name, r["object_map"], score=r["score"])
                    print(f"  → Saved as program {pid[:12]}...")
                else:
                    print(f"  No analogy found ({dt*1000:.0f}ms)")

            elif cmd.action == "compose":
                name = cmd.params.get("domain", "")
                d = store.get_domain(name)
                if not d:
                    print(f"  Domain not found: {name}"); continue
                tid = sched.submit("compose", {"domain_name": name})
                result = sched.execute(tid)
                print(f"  Composed: {result.get('new_compositions', 0)} new, {result.get('stored_to_kernel', 0)} stored")

            elif cmd.action == "infer":
                name = cmd.params.get("domain", "")
                rule = cmd.params.get("rule", "transitivity")
                d = store.get_domain(name)
                if not d:
                    print(f"  Domain not found: {name}"); continue
                tid = sched.submit("infer", {"domain_name": name, "rule": rule})
                result = sched.execute(tid)
                print(f"  Inferred {result.get('new_inferences', 0)} new morphisms via {rule}")

            elif cmd.action == "explain":
                mid = cmd.params.get("morphism_id", "")
                node = store.explain_morphism(mid)
                if "error" in node:
                    print(f"  {node['error']}")
                else:
                    _print_explanation(node)

            elif cmd.action == "explain_path":
                src = cmd.params.get("source", "")
                tgt = cmd.params.get("target", "")
                dom_name = cmd.params.get("domain", "")
                d = store.get_domain(dom_name) if dom_name else None
                if not d:
                    print(f"  Domain not found: {dom_name}"); continue
                nodes = store.explain_path(src, tgt, d["id"])
                if not nodes:
                    print(f"  No morphism found: {src} → {tgt}")
                else:
                    for node in nodes:
                        _print_explanation(node)

            elif cmd.action == "pipeline":
                src_name = cmd.params["source"]
                tgt_name = cmd.params["target"]
                print(f"\n  ═══ Pipeline: {src_name} → {tgt_name} ═══\n")
                _run_pipeline_repl(store, sched, mem, src_name, tgt_name)

            elif cmd.action == "save_program":
                name = cmd.params.get("name", "")
                src_name = cmd.params.get("source")
                tgt_name = cmd.params.get("target")
                if not src_name or not tgt_name:
                    print(f"  Usage: save program <name> <source> <target}"); continue
                print(f"  Registering program '{name}': {src_name} → {tgt_name}")
                # Try to use most recent search result for the pair
                programs = store.list_programs()
                existing = next((p for p in programs if p["source_domain"] == src_name and p["target_domain"] == tgt_name), None)
                if existing:
                    print(f"  Found existing mapping (score={existing['score']:.3f}). Saved as '{name}'.")
                    store.register_program(name, src_name, tgt_name, {}, score=existing["score"])
                else:
                    print(f"  No mapping found for {src_name}→{tgt_name}. Run a search first.")

            elif cmd.action == "test_program":
                prog_name = cmd.params.get("program_name", "")
                p = store.get_program(prog_name)
                if not p:
                    print(f"  Program not found: {prog_name}"); continue
                result = store.run_program_tests(p["id"])
                print(f"  Tests: {result.get('passed', 0)} passed, {result.get('failed', 0)} failed")

            elif cmd.action == "reinforce_program":
                prog_name = cmd.params.get("program_name", "")
                p = store.get_program(prog_name)
                if not p:
                    print(f"  Program not found: {prog_name}"); continue
                store.reinforce_program(p["id"])
                print(f"  Reinforced program '{prog_name}'")

            elif cmd.action == "memory":
                analogies = list(mem.all_analogies())
                stats = mem.stats
                print(f"  Memory: {stats['total_analogies']} analogies, {stats['registered_categories']} categories")
                for a in analogies[:5]:
                    print(f"    {a.source_name} ↔ {a.target_name}: score={a.score:.3f}")
                if len(analogies) > 5:
                    print(f"    ... and {len(analogies) - 5} more")

            elif cmd.action == "query":
                concept = cmd.params.get("concept", "")
                results = ks.query(subject=concept, limit=15)
                results_obj = ks.query(obj=concept, limit=5)
                for rel, src, tgt, domain in results:
                    print(f"    [{domain}] {rel}: {src} → {tgt}")
                for rel, src, tgt, domain in results_obj:
                    print(f"    [{domain}] {rel}: {src} → {tgt}")
                if not results and not results_obj:
                    print(f"  Nothing found for '{concept}'")

            elif cmd.action == "evidence":
                mid = cmd.params.get("morphism_id", "")
                evidence = store.get_evidence(mid)
                for e in evidence:
                    d = "+" if e["direction"] == "supports" else "−"
                    print(f"    [{d}] {e['label']} (str={e['strength']:.1f}) from {e['source']}")
                if not evidence:
                    print("  No evidence")

            elif cmd.action == "programs":
                for p in store.list_programs():
                    print(f"    {p['name']} v{p['version']} (score={p['score']:.3f}) {p['source_domain']}→{p['target_domain']}")
                if not store.list_programs():
                    print("  No programs. Run a search first.")

            elif cmd.action == "suggest":
                cats = {}
                for d in store.list_domains():
                    try: cats[d["name"]] = store.export_category(d["id"])
                    except: pass
                for s, t, sc, r in suggest_explorations(mem, cats, max_suggestions=5):
                    print(f"    {s} ↔ {t}: {sc:.3f} ({r})")

            elif cmd.action == "stats":
                for k, v in store.stats.items():
                    print(f"    {k}: {v}")

            elif cmd.action == "speculate":
                name = cmd.params.get("domain", "")
                d = store.get_domain(name)
                if d:
                    from engine import speculate_morphisms, speculation_report
                    cat = store.export_category(d["id"])
                    print(speculation_report(cat))
                else:
                    print(f"  Not found: {name}")

            elif cmd.action == "snapshot":
                name = cmd.params.get("domain", "")
                d = store.get_domain(name)
                if d:
                    sid = store.snapshot_domain(d["id"])
                    print(f"  Snapshot: {sid[:12]}...")
                else:
                    print(f"  Not found: {name}")

            elif cmd.action == "tasks":
                for t in sched.list_tasks()[:10]:
                    print(f"    [{t['status']}] {t['task_type']} {t.get('params','')[:40]}")

            elif cmd.action == "derive":
                p = cmd.params
                print(f"  Derive: {p.get('label')} {p.get('source')} → {p.get('target')} via {p.get('rule')}")

            elif cmd.action == "unknown":
                if cmd.confidence == 0:
                    print(f"  Could not parse: \"{line}\". Type 'help' for examples.")
                else:
                    print(f"  Partially understood (confidence={cmd.confidence:.1f}): {cmd.params}")
            else:
                print(f"  Unhandled action: {cmd.action}")

        except Exception as e:
            print(f"  Error: {e}")

    store.close()


# ── Main ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="morphos",
        description="MORPHOS Reasoning OS — CLI",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("domains", help="List domains")
    sub.add_parser("datasets", help="List curated datasets")
    sub.add_parser("stats", help="Store statistics")
    sub.add_parser("programs", help="List programs")
    sub.add_parser("tasks", help="List tasks")
    sub.add_parser("repl", help="Interactive REPL")

    p_import = sub.add_parser("import", help="Import data")
    p_import.add_argument("--dataset", help="Curated dataset name (or 'all')")
    p_import.add_argument("--file", help="CSV/TSV file path")
    p_import.add_argument("--json", help="JSON file path")
    p_import.add_argument("--name", help="Domain name")
    p_import.add_argument("--no-header", action="store_true")

    p_info = sub.add_parser("info", help="Domain details")
    p_info.add_argument("domain")

    p_search = sub.add_parser("search", help="Find analogy")
    p_search.add_argument("source")
    p_search.add_argument("target")
    p_search.add_argument("--method", choices=["csp", "embedding", "scalable"], default="csp")

    p_query = sub.add_parser("query", help="Query knowledge")
    p_query.add_argument("concept")

    p_evidence = sub.add_parser("evidence", help="Manage evidence")
    p_evidence.add_argument("morphism_id")
    p_evidence.add_argument("--add", help="Evidence label")
    p_evidence.add_argument("--supports", action="store_true")
    p_evidence.add_argument("--contradicts", action="store_true")
    p_evidence.add_argument("--strength", type=float)
    p_evidence.add_argument("--source", default="")

    p_snap = sub.add_parser("snapshot", help="Snapshot domain")
    p_snap.add_argument("domain")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    handlers = {
        "domains": cmd_domains, "datasets": cmd_datasets, "import": cmd_import,
        "info": cmd_info, "search": cmd_search, "query": cmd_query,
        "evidence": cmd_evidence, "programs": cmd_programs, "tasks": cmd_tasks,
        "snapshot": cmd_snapshot, "stats": cmd_stats, "repl": cmd_repl,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
