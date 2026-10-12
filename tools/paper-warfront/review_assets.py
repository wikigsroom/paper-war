"""Record an explicit completed visual review; never claim runtime verification."""
import argparse
import json
from datetime import datetime, timezone
from export_library import LIB, ROOT, make_gallery, write_json


def main():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all-images",action="store_true")
    group.add_argument("--id",action="append")
    group.add_argument("--category",action="append")
    parser.add_argument("--note",required=True)
    args=parser.parse_args()
    registry=json.loads((LIB/"library-manifest.json").read_text(encoding="utf-8"))
    runtime=json.loads((LIB/"runtime-manifest.json").read_text(encoding="utf-8"))
    ids={record["id"] for record in registry["assets"]}
    if args.id and not set(args.id).issubset(ids):
        parser.error("Unknown asset ID")
    reviewed=[]
    for record in registry["assets"]:
        if record["category"]=="audio":
            continue
        selected=args.all_images or (args.id and record["id"] in args.id) or (args.category and record["category"] in args.category)
        if not selected:
            continue
        if not record.get("export_info"):
            parser.error("Asset has no export: "+record["id"])
        record["status"]="visual-reviewed"
        record["qa"].update({"visual_review":"passed","reviewed_by":"Codex","reviewed_at_utc":datetime.now(timezone.utc).isoformat(),"review_note":args.note,"runtime_review":"pending"})
        if record["qa"].get("cell_border_touch"):
            record["qa"]["cell_boundary_review"]="Exported silhouette visually confirmed complete; source-cell boundary warning reviewed."
        if record.get("portrait_path"):
            record["qa"]["portrait_visual_review"]="passed"
        runtime["assets"][record["id"]]["status"]=record["status"]
        reviewed.append(record["id"])
    write_json(LIB/"library-manifest.json",registry)
    write_json(LIB/"runtime-manifest.json",runtime)
    plan=json.loads((ROOT/"output/imagegen/paper-warfront/jobs.json").read_text(encoding="utf-8"))
    make_gallery(registry["assets"],plan["jobs"])
    write_json(LIB/"visual-review.json",{"reviewed_by":"Codex","reviewed_at_utc":datetime.now(timezone.utc).isoformat(),"asset_ids":reviewed,"note":args.note,"scope":"static images and derived portraits; gameplay verification pending"})
    print(f"Recorded static visual review for {len(reviewed)} image assets; runtime status remains pending.")


if __name__=="__main__":
    main()
