import os, json, argparse, datetime, pathlib, sys, traceback

ROOT = pathlib.Path(".").resolve()
OUT_DIR = ROOT / "outputs"
LOG_DIR = ROOT / "logs"
STATE_DIR = ROOT / "state"
for p in (OUT_DIR, LOG_DIR, STATE_DIR):
    p.mkdir(parents=True, exist_ok=True)

def log(msg):
    ts = datetime.datetime.utcnow().isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_DIR / "runner.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")

def save_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def run_stub_v3(profile, query):
    from stubs.active_rag_stub_v3 import run as run_stub
    return run_stub(profile=profile, query=query or "Qual é a política de fretes e prazo?")

def run_papers(profile, query):
    from tasks.papers_arxiv import run as run_papers
    q = query or "autonomous agents memory tool use"
    return run_papers(query=q, max_results=5)

def run_demo(profile, query):
    return {"demo": "ok", "profile": profile, "query": query}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default=os.getenv("TASK", "stub_v3"))
    parser.add_argument("--profile", default=os.getenv("PROFILE", "default"))
    parser.add_argument("--query", default=os.getenv("QUERY", ""))
    args = parser.parse_args()

    log(f"starting task={args.task} profile={args.profile}")

    try:
        if args.task == "stub_v3":
            res = run_stub_v3(args.profile, args.query)
        elif args.task == "papers":
            res = run_papers(args.profile, args.query)
        else:
            res = run_demo(args.profile, args.query)

        stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        outpath = OUT_DIR / f"result-{args.task}-{stamp}.json"
        save_json(res, outpath)
        log(f"wrote {outpath}")
    except Exception as e:
        err = {"error": str(e), "traceback": traceback.format_exc()}
        save_json(err, OUT_DIR / "error.json")
        log(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()