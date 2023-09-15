import os
import sys
from pathlib import Path

from docint.util import get_repo_dir, get_repo_path


def get_num(pdf_file):
    stub, ext = pdf_file.name.split(".")
    name, num = stub.split("-")
    return int(num)


def get_max_num(src_dir):
    pdf_files = src_dir.glob("*.pdf")
    return max((get_num(pdf_file) for pdf_file in pdf_files), default=0)


def link_files(src_dir, tgt_dir, start_num, end_num):
    os.chdir(tgt_dir)
    src_files = [p for p in src_dir.glob("*.pdf") if get_num(p) >= start_num]
    for src_file in src_files:
        repo_dir = get_repo_dir()
        src_repo_path = get_repo_path(src_file, repo_dir)
        src_relative_path = f"../../..{src_repo_path}"
        print(src_relative_path, src_file.name)
        os.symlink(src_relative_path, src_file.name)


def main():
    src_dir = Path(sys.argv[1])
    tgt_dir = Path(sys.argv[2])

    src_max_num = get_max_num(src_dir)
    tgt_max_num = get_max_num(tgt_dir)
    print(f"src_max_num: {src_max_num} tgt_max_num: {tgt_max_num}")

    if src_max_num > tgt_max_num:
        link_files(src_dir.resolve(), tgt_dir, tgt_max_num + 1, src_max_num)


if __name__ == "__main__":
    main()
