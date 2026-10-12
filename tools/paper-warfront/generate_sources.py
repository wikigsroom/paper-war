"""Use the user-selected skill, sequentially, without containers or browser tabs."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=Path(r"C:\Users\carzy\.codex\skills\sub2-image-gen\scripts\sub2_image_gen.py")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser()
    parser.add_argument("--job", action="append",help="Generate only the named job; repeatable.")
    parser.add_argument("--force",action="store_true",help="Replace existing selected source images.")
    args=parser.parse_args()
    plan=json.loads((ROOT/"output/imagegen/paper-warfront/jobs.json").read_text(encoding="utf-8"))
    if args.job:
        unknown=set(args.job)-{j["id"] for j in plan["jobs"]}
        if unknown:
            parser.error("Unknown jobs: "+", ".join(sorted(unknown)))
    failures=[]
    for job in plan["jobs"]:
        if args.job and job["id"] not in args.job:
            continue
        destination=ROOT/job["source_path"]
        if destination.is_file() and not args.force:
            print(job["id"]+": preserved",flush=True)
            continue
        destination.parent.mkdir(parents=True,exist_ok=True)
        command=[sys.executable,str(SCRIPT),"generate","--prompt-file",str(ROOT/job["prompt_path"]),"--model",plan["model"],"--quality","high","--size",job["requested_size"],"--output-format","png","--out",str(destination)]
        if args.force:
            command.append("--force")
        result=None
        for attempt in range(3):
            print(job["id"]+f": generating (attempt {attempt+1})",flush=True)
            result=subprocess.run(command,capture_output=True,text=True,encoding="utf-8",errors="replace",env={**os.environ,"PYTHONIOENCODING":"utf-8"})
            log=result.stdout+result.stderr
            if result.returncode==0:
                print(job["id"]+": saved",flush=True)
                break
            print(log[-1400:],flush=True)
            if "429" not in log and "502" not in log and "503" not in log:
                break
            if attempt<2:
                time.sleep(8*(attempt+1))
        if result.returncode:
            failures.append(job["id"])
    print("Finished. Failed jobs: "+(", ".join(failures) or "none"),flush=True)
    sys.exit(1 if failures else 0)


if __name__=="__main__":
    main()
