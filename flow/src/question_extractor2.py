import os
import re
import sys
from pathlib import Path
import pprint
from collections import Counter

from docint.vision import Vision

NumDashes = 3
Sections = ['title', 'header', 'question', 'answer']
Saluts = ('श्री', 'श्रीमती', 'डॉ', 'प्रा.', 'अॅड', 'ॲड', 'ॲङ')

@Vision.factory(
    "question_extractor2",
    default_config={
        "stub": "question_extractor"
    },
)
class QuestionExtractor:
    def __init__(self, stub):
        self.stub = stub

    def parse_header(self, lines):
        orig_text = text =' '.join(l.text_with_break() for l in lines)
        
        num, text = text.strip().split(' ', 1)
        num = num.strip('()')

        names_start_idx = min([text.index(s) for s in Saluts if s in text], default=0)
        
        long_num = text[:names_start_idx].strip()
        
        text = text[names_start_idx:]
        names_end_idx = text.index(':')
        names = text[:names_end_idx].strip().split(',')
        names = [n.strip() for n in names]

        text = text[names_end_idx+1:].strip()
        role_end_idx = text.index('पुढील') if 'पुढील' in text else len(text)
        role = text[:role_end_idx].strip()
        role = role.replace('पुढील गोष्टींचा खुलासा करतील काय', '').replace('सन्माननीय', '').strip(':-').strip()
        return {'header': orig_text, 'question_num': num, 'names': names, 'role': role}

    def parse_question(self, lines):
        orig_text =' '.join(l.text_with_break() for l in lines)

        points = re.split(r'(\(\d+\))', orig_text)
        if len(points) == 1:
            # try searching for 1)...2)
            points = re.split(r'(\d+\))', orig_text)

        sub_questions = []
        for i in range(1, len(points), 2):
            sub_questions.append(f"{points[i]} {points[i+1].strip()}".strip())

        return {'question': orig_text, 'sub_questions': sub_questions}

    def parse_answer(self, lines):
        orig_text = ' '.join(l.text_with_break() for l in lines)
        no_answer = True if 'उत्तर आले नाही' in orig_text else False
        if no_answer:
            return {'answer': orig_text, 'minister_name': '', 'sub_answers': []}

        minister_name, text  = orig_text.split(':', 1)
        minister_name = minister_name.strip()

        points = re.split(r'(\(\d+\))', orig_text)
        sub_answers = []
        for i in range(1, len(points), 2):
            sub_answers.append(f"{points[i]} {points[i+1].strip()}".strip())

        return {'answer': orig_text, 'minister_name': minister_name, 'sub_answers': sub_answers}


    def build_question(self, page_idx, line_idx, question_lines, question_num, doc_type):
        def is_header_start(line):
            line_text = line.text_with_break().strip()
            # import pdb
            # pdb.set_trace()
            if doc_type == 'StarredQuestions':
                #pattern = r"^\(\s*(\d+)\s*\)\s+([\d\s]*)\s+"
                pattern = r"^\(\s*(\d+)\s*\)\s*([\*])*\s*([\d\s]*)\s+"
                return bool(re.match(pattern, line_text))
            else:
                pattern = r"^\(\s*(\d+)\s*\)\s+(\s*\d+\s*)\s*\(\s*(\d+-\d+-\d+)\s*\)"
                return bool(re.match(pattern, line_text))

        def is_question_start(line):
            line_text = line.text_with_break().strip().strip('◌़')

            if not line_text:
                return False

            m = re.match(r'^\(\s*(\d+)\s*\)|^(\d+)\)', line_text)
            if not m:
                return False

            match_num = m.group(1) if m.group(1) else m.group(2)
            return int(match_num) == 1

        def is_answer_start(line):
            no_answer = True if 'उत्तर आले नाही' in line.text_with_break() else False
            if no_answer:
                return True
            else:
                line_text = line.text_with_break().strip().strip('◌़')
                if line_text:
                    if line_text.startswith(Saluts):
                        return True
                    elif re.match(r'^: \(\s*(\d+)\s*\)', line_text):
                        # no name given
                        return True
                    else:
                        return False
                else:
                    return False
                #return line_text and line_text.startswith(Saluts)

        print_line = True
        # if question_num == 1:
        #     print_line = True
        #     import pdb
        #     pdb.set_trace()

        question = {}
        section, section_lines = 'title', []
        for idx, line in enumerate(question_lines):
            if print_line:
                print(f'{idx}) {section}[{len(section_lines)}]: {line.text_with_break()}')

            if section == 'title' and is_header_start(line):
                question['title'] = ' '.join(l.text_with_break() for l in section_lines).strip('*')
                section, section_lines = 'header', []

            elif section == 'header' and is_question_start(line):
                header_info = self.parse_header(section_lines)
                question = {**question, **header_info}

                section, section_lines = 'question', []
            elif section == 'question' and is_answer_start(line):
                question_info = self.parse_question(section_lines)
                question = {**question, **question_info}

                section, section_lines = 'answer', []

            if line.words:
                section_lines.append(line)

        answer_info = self.parse_answer(section_lines)
        question = {**question, **answer_info}
        return question

    def question_iter(self, doc):
        def is_dashed(line, page):
            if line.words and page.dash_edges and dash_edges_idx < len(page.dash_edges):
                return line.ymin > page.dash_edges[dash_edges_idx].ymin
            else:
                return False


        page_idx, first_line_idx, question_lines = 0, 0, []
        for page in doc.pages:
            #assert len(page.words) == len(page.word_infos), f'{doc.pdf_name}-{page.page_idx} mismatch'

            dash_edges_idx = 0
            for (line_idx, line) in enumerate(page.lines):

                #if page.page_idx == 0:
                #print(f'{line_idx}) {line.text_with_break()} # words {len(line.words)}')

                if is_dashed(line, page):
                    yield (page_idx, first_line_idx, question_lines)
                    page_idx, first_line_idx = page.page_idx, line_idx
                    question_lines = [ line ]
                    dash_edges_idx += 1

                elif (line_idx == 0) and (page_idx > 0) and len(line.words) < 5:
                    # ignore first line
                    continue
                else:
                    if line.words:
                        question_lines.append(line)
        yield (page_idx, line_idx, question_lines)

    def check(self, question):
        errs = []

        if len(question.get('sub_questions', [])) == 0:
            errs.append('subq_zero')

        # Ignoring
        # if len(question.get('sub_answers', [])) != len(question.get('sub_questions', [])):
        #     errs.append('sub_mismatch')

        min_name = question.get('minister_name', '')
        if not min_name or len(min_name) < 10:
            no_answer = True if 'उत्तर आले नाही' in question.get('answer', '') else False
            if not no_answer:
                errs.append('incorrect_min')

        role = question.get('role', '')
        errs += ['role_missing'] if not role or len(role) < 10 else []
        errs += ['role_incorrect'] if not role.endswith('मंत्री') else []


        names = question.get('names', [])
        errs += ['no_names'] if not names else []

        return errs


    def __call__(self, doc):
        def get_question_signature(question):
            return '-'.join([f'{s[0]}{len(question.get(s,"").split())}' for s in Sections])

        print(f'> question_extractor: {doc.pdf_name} {doc.info["doc_type"]}')

        if doc.info['doc_type'] not in ('StarredQuestions', 'UnstarredQuestions'):
            print('Ignoring doc_type: '+ doc.info['doc_type'])
            doc.questions = []
            return doc


        for w in [w for p in doc.pages for w in p.words]:
            if w.text.strip() == 'ः':
                print(f"  - replaceStr pa{w.page_idx}.wo{w.word_idx} <all> ':'")



        doc.add_extra_field("questions", ("noparse", "", ""))
        doc.questions, question_num = [], 1
        for (page_idx, line_idx, question_lines) in self.question_iter(doc):
            if (page_idx == 0 and len(question_lines) < 12) or (page_idx != 0 and len(question_lines) < 10):
                print(f"Skipping lines: {doc.pdf_name}-{page_idx} #lines{len(question_lines)}")
                continue

            if 'तारांकित प्रश्नोत्तरांची यादी' in question_lines[0].text_with_break():
                print(f"Skipping lines: {doc.pdf_name}-{page_idx} #lines{len(question_lines)}")
                continue

            try:
                question = self.build_question(page_idx, line_idx, question_lines, question_num, doc.info['doc_type'])
            except ValueError as e:
                print(f'ValuError: {page_idx} {line_idx}')
                raise e

            question['page_idx'] = page_idx
            question['start_line_idx'] = line_idx
            question['info'] = doc.info
            errors = self.check(question)


            err_str = ", ".join(errors)
            sig = get_question_signature(question)
            print(f'Qsig: {doc.pdf_name}={page_idx}-{line_idx}[{question_num}]: {sig} {err_str}')
            question_num += 1


            # if 'no_names' in err_str:
            #     print('***** Header *****')
            #     print(question['header'])
            #     print()

            if len(errors) < 4:
                doc.questions.append(question)

        print(f'< question_extractor: {doc.pdf_name} {len(doc.questions)} Qs extracted')
        if len(doc.questions) == 0:
            print('**** NO questions extracted **')
        return doc
