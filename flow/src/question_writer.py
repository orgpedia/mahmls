import gzip
import json
from pathlib import Path

from docint.vision import Vision


@Vision.factory(
    "question_writer",
    default_config={
        "stub": "question_writer",
        "output_dir": "output",
        #"formats": ["json", "csv"],
    },
)
class QuestionWriter:
    def __init__(self, stub, output_dir):
        self.stub = stub
        self.output_path = Path(output_dir)

        self.trans_dict = {
            'Council': 'विधानपरिषद',
            'Assembly': 'विधानसभा',
            'Proceedings': 'कार्यवाही',
            'UnstarredQuestions': 'अतारांकित प्रश्न',
            'StarredQuestions': 'तारांकित प्रश्न',
            'Monsoon': 'पावसाळी',
            'Budget': 'अर्थसंकल्पीय',
            'Winter': 'हिवाळी',
            'Fourth': 'चौथे',
        }        
        
    def clone_question(self, question, lang, doc):
        attributes = ['title', 'question_num', 'long_num', 'names', 'role', 'question_date',
                      'question', 'minister_name', 'answer_date', 'answer']
        
        new_question = dict((k, question.get(k, '')) for k in attributes)

        info_attributes = ['house', 'doc_type', 'session', 'year', 'url', 'name', 'date', 'list_num']
        trans_attributes = ['house', 'doc_type', 'session']
        
        for info_attrib in info_attributes:
            if lang == 'mr' and info_attrib in trans_attributes:
                new_question[info_attrib] = self.trans_dict[doc.info[info_attrib]]
            else:
                new_question[info_attrib] = doc.info.get(info_attrib, None)

        return new_question

    def build_document(self, doc):
        def build_question(question):
            return '\n'.join(question[a] for a in ['title', 'header', 'question', 'answer'])

        if doc.info['doc_type'] in ('StarredQuestions', 'UnstarredQuestions'):
            doc_header = '\n'.join(doc.header_lines) + '\n-----\n'
            return doc_header + '\n      -----\n'.join(build_question(q) for q in doc.questions)
        else:
            lines_txt = [ln.text_with_break() for p in doc.pages for ln in p.lines]
            return '\n'.join(lines_txt)

    def __call__(self, doc):
        mr_questions = getattr(doc,'questions', [])
        en_questions = getattr(doc,'en_questions', [])

        mr_towrite = [ self.clone_question(q, 'mr', doc) for q in mr_questions]
        en_towrite = [ self.clone_question(q, 'en', doc) for q in en_questions]

        mr_qna_file = self.output_path / f'{doc.pdf_name}.qna.mr.json.gz'
        en_qna_file = self.output_path / f'{doc.pdf_name}.qna.en.json.gz'

        with gzip.open(mr_qna_file, "wb") as f:
            f.write(bytes(json.dumps(mr_towrite, separators=(',', ':'), ensure_ascii=False), encoding='utf-8'))
        
        with gzip.open(en_qna_file, "wb") as f:
            f.write(bytes(json.dumps(en_towrite, separators=(',', ':'), ensure_ascii=False), encoding='utf-8'))

        mr_doc_path = (self.output_path / f'{doc.pdf_name}.mr.txt.gz')
        with gzip.open(mr_doc_path, "wb") as f:
            f.write(bytes(self.build_document(doc), encoding='utf-8'))

        #(self.output_path / f'{doc.pdf_name}.en.txt').write_text(self.build_document(doc))

        return doc

        
            
            

        
        
