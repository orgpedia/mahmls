from pathlib import Path
import json
import subprocess
import datetime
import sys
import os

import yaml

from docint.util import get_repo_path, get_repo_dir
from docint import pdfwrapper

BaseURL = "https://gr.maharashtra.gov.in"
org_code = "mahmls"


def make_url(url_stub):
    if url_stub.startswith(BaseURL):
        return url_stub
    else:
        return f"{BaseURL}/{url_stub[3:]}"


def get_crawl_date(date_str):
    return datetime.datetime.strptime(date_str.name, "%d-%b-%Y")


def get_url_infos(crawl_dir):
    def get_code(pdf_file):
        assert pdf_file.name[-4:].lower() == ".pdf", f"Not a pdf file: {pdf_file.name}"
        return pdf_file.name.split(".")[0]

    def build_code_file_dict():
        pdf_files = crawl_dir.glob("**/*.pdf")
        pdf_files = [p for p in pdf_files if p.name[:4].isdigit()]
        return dict((get_code(pf), pf) for pf in pdf_files)

    code_file_dict = build_code_file_dict()
    url_file = crawl_dir / "urls.yml"
    file_url_infos = yaml.load(url_file.read_text(), Loader=yaml.FullLoader)
    url_infos = []
    for url_info in file_url_infos:
        file_code = url_info["code"]
        if file_code in code_file_dict:
            url_info["file_path"] = code_file_dict[file_code]
            url_infos.append(url_info)
    return url_infos


def fix_code(url_info):
    url_info["code"] = url_info["code"].strip(" .")
    return url_info


def load_documents(documents_json):
    if not documents_json.exists() or documents_json.stat().st_size <= 0:
        return {}, {}
    doc_infos = json.loads(documents_json.read_text())
    documents_dict = dict((d["code"], d) for d in doc_infos.values())
    return documents_dict, doc_infos


def main():
    def get_doc_num(doc_name):
        num = int(doc_name.replace(".", "-").split("-")[1])
        return num

    def get_num_pages(doc_path):
        output = subprocess.check_output(
            ["mdls", "-name", "kMDItemNumberOfPages", "-raw", doc_path]
        )
        return int(output.strip())

    def get_pdf_info(doc_path):
        try:
            pdf = pdfwrapper.open(doc_path)
        except:  # noqa pdfwrapper should raise exceptions
            print(f"Unable to load: {doc_path}")
            return 0, []

        large_image_idxs = [p.page_idx for p in pdf.pages if p.has_large_image]
        return len(pdf.pages), large_image_idxs

    if len(sys.argv) != 3:
        print("Usage: {sys.argv[0]} <department-GR-dir> <documents-dir>")
        sys.exit(1)

    dept_dir = Path(sys.argv[1])
    documents_dir = Path(sys.argv[2])

    print(f"Processing department directory: {dept_dir}")

    # load documents
    documents_file = documents_dir / "documents.json"
    documents_dict, doc_infos = load_documents(documents_file)

    start_num = max(
        (get_doc_num(d["name"]) for d in documents_dict.values()), default=0
    )

    starting_start_num = start_num

    crawl_dirs = [d for d in dept_dir.glob("*") if d.is_dir()]
    crawl_dirs.sort(key=get_crawl_date)

    for crawl_dir in crawl_dirs:
        print(f"\tcrawl_dir: {str(crawl_dir)}", end=" ")
        url_infos = get_url_infos(crawl_dir)

        url_infos = [fix_code(u) for u in url_infos]
        # year-4, day-month-4 hrmmss 6
        url_infos.sort(key=lambda u: int(u["code"][:14]))
        print(f"#url_infos: {len(url_infos)}")

        for url_info in url_infos:
            if url_info["code"] in documents_dict:
                continue

            file_path = url_info.pop("file_path")
            full_path = Path.cwd() / file_path
            repo_dir = get_repo_dir()
            repo_path_str = get_repo_path(full_path, repo_dir)

            start_num += 1
            url_info["name"] = f"{org_code}-{start_num}.pdf"
            url_info["url"] = make_url(url_info["url"])

            num_pages, large_image_idxs = get_pdf_info(file_path)
            if not num_pages:
                continue

            url_info["num_pages"] = num_pages
            url_info["large_image_idxs"] = large_image_idxs

            url_info["crawl_dir"] = crawl_dir.name

            doc_infos[repo_path_str] = url_info
            documents_dict[url_info["code"]] = url_info

    print(f"Total #doc_infos: {len(doc_infos)} #new: {start_num - starting_start_num}")
    if doc_infos and start_num > starting_start_num:
        print(f"\tWriting: {str(documents_file)}")
        documents_file.write_text(json.dumps(doc_infos, indent=2))

    print("Creating sym links")
    if documents_file.exists():
        documents_file_dict = yaml.load(
            documents_file.read_text(), Loader=yaml.FullLoader
        )
        os.chdir(documents_file.parent)

        for repo_path, doc_info in documents_file_dict.items():
            relative_path = Path(f"../..{repo_path}")
            assert relative_path.exists()

            dst_path = doc_info["name"]
            if not Path(dst_path).exists():
                print(f"\tSymlinking {relative_path} -> {dst_path}")
                os.symlink(relative_path, dst_path)


if __name__ == "__main__":
    main()
