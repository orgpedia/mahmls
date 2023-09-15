from pathlib import Path
import json
import subprocess
import datetime
import sys
import os
import re

import yaml

from more_itertools import first

from docint.util import get_repo_path, get_repo_dir, find_date
from docint import pdfwrapper

from urllib.parse import quote



from dateutil import parser




def get_document_infos(pdf_repo_paths, start_num):
    sessions = {'Budget': ['budget', 'budjet', 'a1', 'c1', 'first'],
                'Monsoon': ['monsoon', 'rainy', 'a2'],
                'Winter': ['winter', 'a3', 'third', 'antim'],
                'Fourth': ['fourth'],
                }
                
    years = '2023-2022-2021-2020-2019-2018-2017-2016-2015-2014-2013-2012'.split('-')

    def has_val(pdf_path, vals):
        p = str(pdf_path).lower()
        return any(v in p for v in vals)

    
    def get_proceedings_info(pdf_path):
        session = first((s for s, vals in sessions.items() if has_val(pdf_path, vals)), None)
        year = first((y for y in years if y.lower() in str(pdf_path)), None)
        if not year:
            y = first((y for y in years if y[2:] in str(pdf_path)), None)
            year = f'20{y}'


        unmatched_dict = {'mls.org.in/pdf/karyawali_R16C.pdf': ('Monsoon', '2016'),
                          'mls.org.in/pdf/karyawali15C1.pdf': ('Budget', '2015'),
                          'mls.org.in/pdf/Final karyawaliconcil2012.pdf': ('Monsoon', '2012'),
                          'mls.org.in/pdf/karyawali14C1.pdf': ('Budget', '2014'),
                          'mls.org.in/pdf/final karyawali.pdf': ('Budget', '2012'),
                          'mls.org.in/newpdf2017/Temp KARYAVALI.pdf': ('Budget', '2017'),
                          'mls.org.in/pdf/karyawali_splA.pdf': ('Winter', '2014'),
                          'mls.org.in/pdf/Temporary Karyavali sabha.pdf': ('Budget', '2012'),
                          'mls.org.in/newpdf/tatpurati karyavali.pdf': ('Winter', '2016'),
                          }

        (s, y) = first((v for k, v in unmatched_dict.items() if k in str(pdf_path)), (None, None))

        session = s if not session else session
        year = y if not year else year

        assert session and year, 'Unknwn session/year for {pdf_path}'
        url = f'http://{quote("/".join(pdf_path.parts[5:]))}'        
        return session, year, url

    def rm_str(s, rm_list):
        for r in rm_list:
            s = s.replace(r, '')
        return s

    def get_date(pdf_path):
        file_name = pdf_path.name
        mr_dt_dict = {'९ मार्च, २०२१': '9 March 2021',
                      '१० मार्च, २०२१': '10 March 2021',
                      '२२ डिसेंबर, २०२१': '22 December 2021',
                      '२४ डिसेंबर, २०२१': '24 December 2021',                 
                      '२७ डिसेंबर, २०२१': '27 December 2021',
                      '07.08.2007': '7 Aug 2007',
                      '७ मार्च, २०१७': '7 March 2017',
                      }
        
        file_name = rm_str(file_name.lower(), ['final', 'yadi', 'yaadi', 'starred', 'question', 'a.pdf', '.pdf', '_', '-assembly'])
        file_name = file_name.replace('. ', '.').replace('.207 ', '.2007 ').strip()
        file_name = file_name[1:] if file_name[0] == 'y' else file_name

        mr_key = [k for k in mr_dt_dict if k in file_name]
        if mr_key:
            assert len(mr_key) == 1
            file_name = mr_dt_dict[mr_key[0]]


        if 'PDF2023' in pdf_path.parts:
            d, _ = pdf_path.name.split('-')
            dt = datetime.date(year=2023, month=3, day=int(d))
            if d == '28':
                dt = datetime.date(year=2023, month=2, day=28)
            return dt
        
        dt, dt_err = find_date(file_name)
        if dt_err:
            match = re.search('\d{8}', pdf_path.name)
            if match:
                dt_str = match.group()
                d, m, y = dt_str[:2],dt_str[2:4], dt_str[4:]
                dt = datetime.date(day=int(d), month=int(m), year=int(y))
                #print(f'{dt} {pdf_path}')
            else:
                print(f'{dt_err} {pdf_path} {file_name}')
                dt = None
        return dt
        

    def get_starred_info(pdf_path):
        
        dt = get_date(pdf_path)

        if not dt:
            return '', ''
        if dt.month in [2, 3, 4]:
            session = 'Budget'        
        elif dt.month in [6, 7, 8]:
            session = 'Monsoon'
        elif dt.month in [11, 12]:
            session = 'Winter'
        else:
            session = None

        assert session and dt
        url = f'http://mls.org.in/{quote("/".join(pdf_path.parts[5:]))}'
        print(url)
        return session, dt, url



    def get_unstarred_info(pdf_path):
        num_dict = {
            '2015': [ ('Budget', 1, 10), ('Monsoon', 11, 38), ('Winter', 39, 58)],
            '2016': [ ('Budget', 59, 109), ('Monsoon', 110, 200), ('Winter', 201, 259)],
            '2017': [ ('Budget', 260, 292), ('Monsoon', 293, 346), ('Winter', 347, 385)],
            '2018': [ ('Budget', 386, 418), ('Monsoon', 419, 456), ('Winter', 457, 512)],
            '2019': [ ('Budget', 513, 557), ('Monsoon', 558, 604) ],
            '2020': [('Monsoon', 1, 11), ('Winter', 12, 41)],
            '2021': [('Budget', 42, 56), ('Monsoon', 57, 61), ('Winter', 62, 75)],
            '2022': [('Budget', 76, 90), ('Monsoon', 91, 103), ('Winter', 104, 124)],
            '2023': [('Budget', 125, 151), ('Monsoon', 152, 187)]
        }

        def get_session(year, num):
            if year == '2015' and num > 58:
                return '2016', 'Winter'

            sessions = [v[0] for v in num_dict[year] if v[1] <= num <= v[2]]
            assert len(sessions) == 1
            return year, sessions[0]
        
        mr_dict = {
            'अतारांकित प्रश्नोत्तरांची दुसरी यादी- सन २०१६ चे पाचवे (हिवाळी) अधिवेशन.pdf': (2016, 2),
            'अतारांकित प्रश्नोत्तरांची आठवी यादी- सन २०१६ चे पाचवे (हिवाळी) अधिवेशन.pdf': (2016, 8),
            'अतारांकित प्रश्नोत्तराची सहावी यादी- सन २०१६ चे पाचवे (हिवाळी) अधिवेशन.pdf': (2016, 6),
            'अतारांकित प्रश्नोत्तराची सातवी यादी- सन २०१६ चे पाचवे (हिवाळी) अधिवेशन.pdf': (2016, 7),
            'सन २०१६ च्या पाचव्या (हिवाळी) अधिवेशनाकरिता तयार करण्यात आलेली अतारांकित प्रश्नोत्तराची पहिली यादी.pdf': (2016, 1),
            'अतारांकित प्रश्नोत्तरांची पाचवी यादी- सन २०१६ चे पाचवे (हिवाळी) अधिवेशन.pdf': (2016, 5),
            'अतारांकित प्रश्नोत्तराची नववी यादी-२०१६ चे पाचवे (हिवाळी) अधिवेशन.pdf': (2016, 9),
            'अतारांकित प्रश्नोत्तरांची चौथी यादी- सन २०१६ चे पाचवे (हिवाळी) अधिवेशन.pdf': (2016, 4),
        }

        url = f'http://mls.org.in/{quote("/".join(pdf_path.parts[5:]))}'
        
        if pdf_path.name in mr_dict:
            year, list_num  = mr_dict[pdf_path.name]
            return str(year), 'Winter', url

        session = first((s for s, vals in sessions.items() if has_val(pdf_path, vals)), None)
        if not session:
            file_name = rm_str(pdf_path.name.lower(), ['%20', ' ', 'unstarred_question_yaadi_', '.pdf', 'ul_'])
            num, year = file_name.split('of')
            year, session = get_session(year, int(num))
        else:
            year = first((y for y in years if y.lower() in str(pdf_path)), None)
        return year, session, url

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

    doc_infos = []
    for repo_path in pdf_repo_paths:
        doc_info = {'repo_path': repo_path}
        pdf_path = Path(repo_path[1:])

        doc_info['house'] = pdf_path.parts[3]
        doc_info['doc_type'] = pdf_path.parts[4]

        doc_info['num_pages'], doc_info['large_image_idxs'] = get_pdf_info(pdf_path)
        if not doc_info['num_pages']:
           continue

        if doc_info['doc_type'] == 'Proceedings':
            doc_info['session'], doc_info['year'], doc_info['url'] = get_proceedings_info(pdf_path)

        elif doc_info['doc_type'] in ('StarredQuestions'):
            doc_info['session'], dt, doc_info['url'] = get_starred_info(pdf_path)
            doc_info['year'] = dt.year
            doc_info['date'] = str(dt)
            
        elif doc_info['doc_type'] == 'UnstarredQuestions':
            doc_info['year'], doc_info['session'], doc_info['url'] = get_unstarred_info(pdf_path)
            
        elif doc_info['doc_type'] == 'BriefReport':
            continue

        else:
            raise NotImplementedError('Unable to find doc_type')

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

    website_dir = Path(sys.argv[1])
    documents_dir = Path(sys.argv[2])

    documents_file = documents_dir / "documents.json"
    documents_dict, document_infos = load_documents(documents_file)

    start_num = max(
        (get_doc_num(d["name"]) for d in documents_dict.values()), default=1
    )
    starting_start_num = start_num
    
    repo_dir = get_repo_dir()    
    all_pdf_files = [get_repo_path(d.absolute(), repo_dir) for d in website_dir.glob('**/*.pdf')]

    new_pdf_files = [f for f in all_pdf_files if f not in documents_dict]

    new_document_infos = get_document_infos(new_pdf_files, start_num)
    document_infos.extend(new_document_infos)

    documents_file.write_text(json.dumps(document_infos, indent=2, ensure_ascii=False))

    print("Creating sym links")
    os.chdir(documents_file.parent)

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

"""
"/import/websites/gr.maharashtra.gov.in/IT/02-Sep-2021/_pdfs/201801201843024511.pdf": {
    "url": "https://gr.maharashtra.gov.in/Site/Upload/Government%20Resolutions/English/201801201843024511.pdf",
    "dept": "Information Technology Department",
    "text": "State Level Implementation Committee on BharatNet Project-regarding",
    "code": "201801201843024511",
    "date": "20-01-2018",
    "size_kb": "363",
    "name": "mahit-1.pdf",
    "num_pages": 3,
    "large_image_idxs": [],
    "crawl_dir": "02-Sep-2021"
  },

"""    
