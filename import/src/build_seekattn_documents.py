import json
import os
import sys
from pathlib import Path

from docint import pdfwrapper
from docint.util import get_repo_dir, get_repo_path
from more_itertools import first

"""
  {
    "repo_path": "",
    "house": "Assembly",
    "doc_type": "StarredQuestions",
    "session": "Monsoon",
    "url": "http://mls.org.in/pdf%20monsoon%202017/yaadi%2011-8-2017.pdf",
    "year": 2017,
    "date": "2017-08-11",
    "name": "mahmls-1656.pdf"
  },

"""

def rm_str(s, rm_list):
    for r in rm_list:
        s = s.replace(r, '')
    return s


def get_document_infos(pdf_repo_paths, start_num):
    sessions = {'Budget': ['budget', 'budjet', 'a1', 'c1', 'first'],
                'Monsoon': ['monsoon', 'rainy', 'a2'],
                'Winter': ['winter', 'a3', 'third', 'antim'],
                'Fourth': ['fourth'],
                }

    def get_pdf_info(doc_path):
        try:
            pdf = pdfwrapper.open(doc_path)
        except:  # noqa pdfwrapper should raise exceptions
            print(f"Unable to load: {doc_path}")
            return 0, []

        large_image_idxs = [p.page_idx for p in pdf.pages if p.has_large_image]
        return len(pdf.pages), large_image_idxs
                
    years = '2023-2022-2021-2020-2019-2018-2017-2016-2015-2014-2013-2012'.split('-')

    def has_val(pdf_path, vals):
        p = str(pdf_path).lower()
        return any(v in p for v in vals)

    def get_seekingattention_info(pdf_path):
        session = first((s for s, vals in sessions.items() if has_val(pdf_path, vals)), None)
        year = first((y for y in years if y.lower() in str(pdf_path)), None)
        num = rm_str(pdf_path.stem.lower(), ['assembly', 'patrak_bhag_', '_', '-',
                                             'patrak bhag 2  no', 'patrak bhag 2  23 oct 2017'])
        url = f'http://mls.org.in/{str(pdf_path).replace("import/websites/mls.org.in/PatrakBhag/","")}'
        print(session, year, num, url)
        return session, year, url, num


    doc_infos = []
    for repo_path in pdf_repo_paths:
        doc_info = {'repo_path': repo_path}
        pdf_path = Path(repo_path[1:])

        doc_info['house'] = 'Assembly'
        doc_info['doc_type'] = 'SeekingAttentionQuestion'


        doc_info['num_pages'], doc_info['large_image_idxs'] = get_pdf_info(pdf_path)
        if not doc_info['num_pages']:
           continue
       
        di = doc_info
        di['session'], di['year'], di['url'], di['doc_num'] = get_seekingattention_info(pdf_path)
        doc_info['name'] = f'mahmls-{start_num}.pdf'
        start_num += 1
        doc_infos.append(doc_info)
    return doc_infos

def load_documents(documents_json):
    if not documents_json.exists() or documents_json.stat().st_size <= 0:
        return {}, []
    doc_infos = json.loads(documents_json.read_text())
    documents_dict = dict((d["repo_path"], d) for d in doc_infos)
    return documents_dict, doc_infos

def main():
    def get_doc_num(doc_name):
        num = int(doc_name.replace(".", "-").split("-")[1])
        return num
    
    def is_seeking_attention(file_path):
        stub = str(file_path).replace('/import/websites/mls.org.in/PatrakBhag/', '')
        return any(stub in sf for sf in seekingattn_files)

    website_dir = Path(sys.argv[1])
    documents_dir = Path(sys.argv[2])

    documents_file = documents_dir / "documents_seekattn.json"
    documents_dict, document_infos = load_documents(documents_file)

    start_num = max(
        (get_doc_num(d["name"]) for d in documents_dict.values()), default=1
    )

    # start numbering from 
    starting_start_num = start_num if start_num != 1 else 4000
    
    repo_dir = get_repo_dir()    
    all_pdf_files = [get_repo_path(d.absolute(), repo_dir) for d in website_dir.glob('**/*.pdf')]

    new_pdf_files = [f for f in all_pdf_files if f not in documents_dict]

    seekingattn_files = Path(website_dir / 'seeking_attention.lst.txt').read_text().split('\n')
    new_pdf_files = [f for f in all_pdf_files if is_seeking_attention(f)]

    print(f'Processing new files: # {len(new_pdf_files)}')

    new_document_infos = get_document_infos(new_pdf_files, starting_start_num)
    document_infos.extend(new_document_infos)
    documents_file.write_text(json.dumps(document_infos, indent=2, ensure_ascii=False))

    print("Creating sym links")
    os.chdir(documents_file.parent)

    import pdb
    pdb.set_trace()

    for doc_info in document_infos:
        repo_path = doc_info['repo_path']
        relative_path = Path(f"../..{repo_path}")
        assert relative_path.exists()

        dst_path = doc_info["name"]
        if not Path(dst_path).exists():
            print(f"\tSymlinking {relative_path} -> {dst_path}")
            os.symlink(relative_path, dst_path)


if __name__ == "__main__":
    main()
