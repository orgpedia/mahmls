#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path


def slug(value):
    s = "" if value is None else str(value)
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "na"


def mahmls_id(name):
    m = re.fullmatch(r"mahmls-(\d+)\.pdf", str(name or "").strip())
    return m.group(1) if m else None


def suffix_for(doc):
    doc_type = doc.get("doc_type")
    if doc_type in ("Proceedings", "Members"):
        return None
    if doc_type == "UnstarredQuestions":
        value = doc.get("list_num")
        if value in (None, ""):
            value = doc.get("date")
        return slug(value)
    value = doc.get("date")
    if value in (None, ""):
        value = doc.get("list_num")
    return slug(value)


def ensure_parent(path):
    path.parent.mkdir(parents=True, exist_ok=True)


def rel_target(link_path, target_path):
    return os.path.relpath(target_path, start=link_path.parent)


def set_symlink(link_path, target_path, apply):
    relative = rel_target(link_path, target_path)
    if link_path.is_symlink() and os.readlink(link_path) == relative:
        return "unchanged"

    if not apply:
        return "would_update"

    ensure_parent(link_path)
    if link_path.is_symlink() or link_path.exists():
        link_path.unlink()
    link_path.symlink_to(relative)
    return "updated"


def resolve_source(repo_path, doc_link):
    src = None
    if repo_path.exists() or repo_path.is_symlink():
        try:
            src = repo_path.resolve(strict=True)
        except FileNotFoundError:
            src = None
    if src is None and (doc_link.exists() or doc_link.is_symlink()):
        try:
            src = doc_link.resolve(strict=True)
        except FileNotFoundError:
            src = None
    return src


def parse_args():
    parser = argparse.ArgumentParser(
        description="Migrate mahmls PDFs into LFS/mahmls/pdfs and rewrite symlinks."
    )
    parser.add_argument(
        "--documents-json",
        default="import/documents/documents.json",
        help="Path to documents.json",
    )
    parser.add_argument(
        "--documents-dir",
        default="import/documents",
        help="Directory containing mahmls-*.pdf symlinks",
    )
    parser.add_argument(
        "--lfs-root",
        default="LFS/mahmls/pdfs",
        help="Destination root for migrated PDFs",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes. Without this flag the script runs in dry-run mode.",
    )
    parser.add_argument(
        "--stage",
        choices=("stage1", "stage2", "both"),
        default="both",
        help=(
            "stage1: copy to LFS + relink import/documents/mahmls-*.pdf; "
            "stage2: relink repo_path files under import/websites/... to LFS; "
            "both: run stage1 and stage2 together."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process at most N records (0 means all).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    root = Path.cwd().resolve()
    documents_json = (root / args.documents_json).resolve()
    documents_dir = (root / args.documents_dir).resolve()
    lfs_root = (root / args.lfs_root).resolve()

    with open(documents_json, encoding="utf-8") as f:
        records = json.load(f)

    counts = Counter()
    prepared = []

    for record in records:
        name = record.get("name")
        mid = mahmls_id(name)
        if not mid:
            prepared.append((record, None, None, None, None, None, None, "invalid_name"))
            continue

        house = slug(record.get("house"))
        year = slug(record.get("year"))
        session = slug(record.get("session"))
        doc_type = slug(record.get("doc_type"))

        out_dir = lfs_root / house / f"{year}-{session}"
        base_name = f"{house}-{year}-{session}-{doc_type}"
        suffix = suffix_for(record)
        if suffix:
            base_name = f"{base_name}-{suffix}"

        base_pdf = f"{base_name}.pdf"
        key = str(out_dir / base_pdf)
        counts[key] += 1

        repo_rel = str(record.get("repo_path", "")).lstrip("/")
        repo_path = root / repo_rel
        doc_link = documents_dir / name
        prepared.append((record, mid, out_dir, base_name, base_pdf, repo_path, doc_link, None))

    stats = Counter()
    skipped = []
    samples = []
    unchanged_doc_files = []
    unchanged_repo_files = []

    to_process = prepared if args.limit <= 0 else prepared[: args.limit]

    for item in to_process:
        record, mid, out_dir, base_name, base_pdf, repo_path, doc_link, err = item
        name = record.get("name")

        if err == "invalid_name":
            stats["invalid_name"] += 1
            skipped.append((name, "invalid_name"))
            continue

        key = str(out_dir / base_pdf)
        if counts[key] > 1:
            final_pdf = f"{base_name}-mahmls-{mid}.pdf"
            stats["collision_renamed"] += 1
        else:
            final_pdf = base_pdf

        dest = out_dir / final_pdf

        if args.stage in ("stage1", "both"):
            src = resolve_source(repo_path, doc_link)
            if src is None or not src.exists():
                stats["missing_source_stage1"] += 1
                skipped.append((name, "missing_source_stage1"))
                continue

            if not args.apply:
                if not dest.exists():
                    stats["would_copy_new"] += 1
                elif src.resolve() != dest.resolve():
                    stats["would_copy_overwrite"] += 1
                else:
                    stats["copy_already_pointing"] += 1
            else:
                ensure_parent(dest)
                if not dest.exists():
                    shutil.copy2(src, dest)
                    stats["copied_new"] += 1
                elif src.resolve() != dest.resolve():
                    shutil.copy2(src, dest)
                    stats["copied_overwrite"] += 1
                else:
                    stats["copy_already_pointing"] += 1

            doc_status = set_symlink(doc_link, dest, args.apply)
            stats[f"doc_link_{doc_status}"] += 1
            if doc_status == "unchanged":
                unchanged_doc_files.append(name)
        else:
            doc_status = "skipped"
            stats["doc_link_skipped"] += 1

        if args.stage in ("stage2", "both"):
            if not dest.exists():
                stats["missing_lfs_stage2"] += 1
                skipped.append((name, "missing_lfs_stage2"))
                continue
            repo_status = set_symlink(repo_path, dest, args.apply)
            stats[f"repo_link_{repo_status}"] += 1
            if repo_status == "unchanged":
                unchanged_repo_files.append(name)
        else:
            repo_status = "skipped"
            stats["repo_link_skipped"] += 1

        stats["processed"] += 1

        if len(samples) < 12:
            samples.append((name, str(dest.relative_to(root)), doc_status, repo_status))

    mode = "APPLY" if args.apply else "DRY_RUN"
    print(f"MODE={mode}")
    print(f"STAGE={args.stage}")
    print(f"TOTAL_RECORDS={len(records)}")
    print(f"PROCESSED_SCOPE={len(to_process)}")
    for key in sorted(stats):
        print(f"{key}={stats[key]}")

    print(f"SKIPPED_COUNT={len(skipped)}")
    for name, reason in skipped[:20]:
        print(f"SKIPPED {name}: {reason}")

    print("SAMPLES")
    for name, target, doc_status, repo_status in samples:
        print(f"{name} -> {target} | doc:{doc_status} repo:{repo_status}")

    print(f"DOC_LINK_UNCHANGED_FILES_COUNT={len(unchanged_doc_files)}")
    for name in unchanged_doc_files:
        print(f"DOC_LINK_UNCHANGED {name}")

    print(f"REPO_LINK_UNCHANGED_FILES_COUNT={len(unchanged_repo_files)}")
    for name in unchanged_repo_files:
        print(f"REPO_LINK_UNCHANGED {name}")


if __name__ == "__main__":
    main()
