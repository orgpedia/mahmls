import csv
import gzip
import json
import shutil
import sys
from operator import itemgetter
from itertools import groupby

from pathlib import Path

Fields = ['session', 'year', 'house', 'doc_type', 'date', 'list_num']

def get_info(qna_en_file):
    qnas = []
    with gzip.open(qna_en_file, "rb") as f:
        qnas = json.loads(f.read())
        if qnas:
            return [qnas[0].get(f, None) for f in Fields]
        else:
            return [None for f in Fields]


ExportDir = Path('/Users/mukund/orgpedia/mahmls/export/orgpedia_mahmls/')

def export_document(mr_txt_file):
    doc_name = mr_txt_file.name.replace('.mr.txt.gz', '')
    
    qna_en_file = mr_txt_file.parent / f'{doc_name}.qna.en.json.gz'    
    qna_mr_file = mr_txt_file.parent / f'{doc_name}.qna.mr.json.gz'

    en_field_vals = get_info(qna_en_file)
    session, year, house, doc_type, doc_date, list_num = en_field_vals

    if doc_type not in ('StarredQuestions', 'UnstarredQuestions'):
        return [], []

    with gzip.open(qna_en_file, "rb") as f:
        en_questions = json.loads(f.read())
        for question in en_questions:
            for (f, v) in zip(Fields, en_field_vals):
                question.setdefault(f, v)
            question['year'] = int(question['year'])
            question['names'] = '-'.join(question['names'])
        

    mr_field_vals = get_info(qna_mr_file)
    with gzip.open(qna_mr_file, "rb") as f:
        mr_questions = json.loads(f.read())
        for question in mr_questions:
            for (f, v) in zip(Fields, mr_field_vals):
                question.setdefault(f, v)
            question['year'] = int(question['year'])
            question['names'] = '-'.join(question['names'])            
    
    stub = ''
    if doc_type in ('StarredQuestions', 'UnstarredQuestions'):
        stub = f'-{str(doc_date).replace("-","")}' if doc_type == 'StarredQuestions' else f'-{list_num}'

    doc_name = f'{year}-{session}-{house}-{doc_type}{stub}.mr.txt.gz'
    ex_mr_file = ExportDir / Path(f'{doc_type}-docs') / doc_name
    
    ex_mr_file.parent.mkdir(exist_ok=True)

    print(f'Copying to {ex_mr_file.name}')

    shutil.copyfile(mr_txt_file, ex_mr_file)

    # Get questions
    return en_questions, mr_questions

def write_csv_file(csv_file_name, questions, schema, fields):
    with gzip.open((ExportDir / Path('Questions') / csv_file_name), 'wt') as questions_csv:
        csv_writer = csv.DictWriter(questions_csv, fieldnames=schema)
        csv_writer.writeheader()
        rows = [dict((s, q.get(k, '')) for (s, k) in zip(schema, fields)) for q in questions]
        csv_writer.writerows(rows)

def write_json_file(json_file_name, questions):
    with gzip.open((ExportDir / Path('Questions') / json_file_name), 'wb') as f:
        f.write(bytes(json.dumps(questions), encoding='utf-8'))

def main():
    en_all_questions, mr_all_questions = [], []
    for doc_dir in sys.argv[1:]:
        doc_dir = Path(doc_dir)
        output_dir = doc_dir / "output"

        doc_files = output_dir.glob('*.mr.txt.gz')
        for doc_file in doc_files:
            #doc_file = Path(output_dir / 'mahmls-252.pdf.mr.txt.gz')
            (en_questions, mr_questions) = export_document(doc_file)
            en_all_questions += en_questions
            mr_all_questions += mr_questions
    #end

    en_fields = ['title', 'question_num', 'long_num', 'names', 'role', 'question_date', 'question',
                 'minister_name', 'answer_date', 'answer', 'house', 'doc_type', 'session', 'year',
                 'url', 'name', 'date', 'list_num' ]

    mr_fields = ['शीर्षक', 'प्रश्न_क्रमांक', 'लांब संख्या', 'नावे', 'मंत्रीपद', 'प्रश्न तारीख', 'प्रश्न',
                 'मंत्री नाव', 'उत्तर तारीख', 'उत्तर', 'सभागृह', 'दस्तऐवज_प्रकार',
                 'सत्र', 'वर्ष', 'संकेत स्थळ', 'नाव', 'तारीख', 'यादी_क्रमांक']

    
    en_all_questions.sort(key=itemgetter('year'))
    for (year, year_questions) in groupby(en_all_questions, key=itemgetter('year')):
        year_questions = list(year_questions)
        write_csv_file(f'{year}-question_answer_en.csv.gz', year_questions, en_fields, en_fields)
        write_json_file(f'{year}-question_answer_en.json.gz', year_questions)
        
    mr_all_questions.sort(key=itemgetter('year'))
    for (year, year_questions) in groupby(mr_all_questions, key=itemgetter('year')):
        year_questions = list(year_questions)        
        write_csv_file(f'{year}-question_answer_mr.csv.gz', year_questions, mr_fields, en_fields)
        write_json_file(f'{year}-question_answer_mr.json.gz', year_questions)

main()
