import os
import re
import sys
from pathlib import Path
import pprint
from collections import Counter

from more_itertools import partition

from docint.vision import Vision
NumDashes = 3
Sections = ['title', 'header', 'question', 'answer']
Saluts = ('श्री', 'श्रीमती', 'डॉ', 'प्रा.', 'अॅड', 'ॲड', 'ॲङ', 'कुमारी')
@Vision.factory(
    "question_extractor",
    default_config={
        "output_dir": "output",
        "ignore_bold": False,
    },
)
class QuestionExtractor:
    def __init__(self, output_dir, ignore_bold):
        self.output_dir = Path(output_dir)
        self.ignore_bold = ignore_bold

    def parse_header(self, lines):
        orig_text = text =' '.join(l.raw_text() for l in lines)
        num, text = text.split(' ', 1)
        num = num.strip('()')
        
        names_start_idx = min([text.index(s) for s in Saluts if s in text], default=0)
        
        long_num = text[:names_start_idx].strip()
        question_date = ''        
        if '(' in long_num:
            long_num, question_date = long_num.split('(', 1)
            question_date = question_date.strip('() .*')
        else:
            long_num = long_num.strip('*')
            

        #print(f'\t\t{long_num} {question_date}')

        text = text[names_start_idx:]
        names_end_idx = text.index(':')
        if len(text[names_end_idx:]) < 5:
            names_end_idx = text.index('सन्माननीय')
        
        names = text[:names_end_idx].strip().split(',')
        names = [n.strip() for n in names]

        text = text[names_end_idx+1:].strip()
        if 'तारांकित प्रश्न' in text or 'अतारांकित' in text:
            names_end_idx = text.index(':')
            if len(text[names_end_idx:]) < 5:
                #print('')
                names_end_idx = text.index('सन्माननीय')
            text = text[names_end_idx+1:].strip()
            
        role_end_idx = text.index('पुढील') if 'पुढील' in text else len(text)
        role = text[:role_end_idx].strip()
        role = role.replace('पुढील गोष्टींचा खुलासा करतील काय', '').replace('सन्माननीय', '').strip(':-').strip()
        return {'header': orig_text, 'question_num': num, 'names': names, 'role': role,
                'long_num': long_num, 'question_date': question_date}

    def parse_question(self, lines):
        orig_text =' '.join(l.raw_text() for l in lines)
        sub_questions = re.findall(r'\(\d+\)\s[^\(]+', orig_text)
        sub_questions = [s.strip() for s in sub_questions]
        return {'question': orig_text, 'sub_questions': sub_questions}

    def parse_answer(self, lines):
        def majority(vals):
            ctr = Counter(bool(v) for v in vals)
            return max(ctr, key=ctr.get)
        
        def is_bold_word(word):
            word_info = word.page.word_infos[word.word_idx]
            return majority('bold' in f.lower() for f in word_info.fonts) or majority(lw != 0.0 for lw in word_info.line_widths)

        
        orig_text = ' '.join(l.raw_text() for l in lines)
        no_answer = True if 'उत्तर आले नाही' in orig_text else False
        if no_answer:
            return {'answer': orig_text, 'minister_name': '', 'sub_answers': []}

        if ':' not in orig_text:
            # Forgot to add ':' in text pick up text that is bold
            non_minister_ws, minister_ws = partition(is_bold_word, lines[0].words)
            minister_name = ' '.join(w.text for w in minister_ws).strip()
            text = ' '.join(w.text for w in non_minister_ws) + ' '
            text += ' '.join(l.raw_text() for l in lines[1:])
        else:
            minister_name, text  = orig_text.split(':', 1)
            minister_name = minister_name.strip()

        answer_date = ''
        if '(' in minister_name and lines[0].page.doc.info['doc_type'] == 'UnstarredQuestions':
            paren_index = minister_name.rindex('(')
            minister_name, answer_date = minister_name[:paren_index],minister_name[paren_index:]
            answer_date = answer_date.strip('(). ')
            minister_name = minister_name.strip()
            
        sub_answers = re.findall(r'\(\d+\)[^\(]*', orig_text)
        sub_answers = [s.strip() for s in sub_answers]
        
        # print(minister_name, answer_date)
        
        return {'answer': orig_text, 'minister_name': minister_name, 'sub_answers': sub_answers,
                'answer_date': answer_date}
        
    def build_question(self, page_idx, line_idx, question_lines, question_num):
        def majority(vals):
            ctr = Counter(bool(v) for v in vals)
            return max(ctr, key=ctr.get)
        
        def has_number_at_start(line):
            # Todo write a regex'
            line_text = line.raw_text().strip().strip('◌़').strip('*')
            # second regex added for mahmls-354
            return line_text and (bool(re.match(r'^\(\d+\)', line_text[:10])) or bool(re.match(r'^\d+\)', line_text[:10])))

        def matches_number_at_start(num_at_start, line):
            # Todo write a regex'
            line_text = line.raw_text().strip().strip('◌़')
            if not line_text:
                return False

            m = re.match(r'\((\d+)\)|(\d+)\)', line_text)
            if not m:
                return False
            
            match_num = m.group(1) if m.group(1) else m.group(2)
            return int(match_num) == num_at_start 

        def has_name_at_start(line):
            no_answer = True if 'उत्तर आले नाही' in line.raw_text() else False
            if no_answer:
                return True
            else:
                line_text = line.text_with_break()
                return line.words and line_text.strip().startswith(Saluts)

        def is_bold_word(word):
            word_info = word.page.word_infos[word.word_idx]
            return majority('bold' in f.lower() for f in word_info.fonts) or majority(lw != 0.0 for lw in word_info.line_widths)
        
        def is_bold(line, only_start=False):
            if self.ignore_bold:
                return True

            
            if not only_start:
                return all(is_bold_word(w) for w in line.words)
            else:
                return is_bold_word(line.words[0])

        print_line = False
        # if page_idx == 16 and line_idx == 47:        
        # if question_num == 32:
        #     print_line = True
        #     import pdb
        #     pdb.set_trace()
        
        question = {}
        section, section_lines = 'title', []
        for idx, line in enumerate(question_lines):
            if print_line:
                print(f'{idx}) {section}[{len(section_lines)}]: {line.raw_text()}')
            
            if section == 'title' and has_number_at_start(line) and is_bold(line, only_start=True):
                question['title'] = ' '.join(l.raw_text() for l in section_lines).strip('*')
                section, section_lines = 'header', []
                
            elif section == 'header' and has_number_at_start(line) and not is_bold(line):
                header_info = self.parse_header(section_lines)
                question = {**question, **header_info}
                
                section, section_lines = 'question', []
            elif section == 'question' and has_name_at_start(line) and is_bold(line, only_start=True):
                question_info = self.parse_question(section_lines)
                question = {**question, **question_info}                
                
                section, section_lines = 'answer', []

            if line.words:
                section_lines.append(line)

        if section == 'answer':
            answer_info = self.parse_answer(section_lines)
            question = {**question, **answer_info}                            
        elif section == 'question':
            # Answer marker not found
            question_info = self.parse_question(section_lines)
            question = {**question, **question_info}
            question['answer'] = ''
            question['minister_name'] = ''            

        return question

    def question_iter(self, doc):
        def is_dashed(line):
            line_text = line.raw_text().strip()
            dash_str, under_str = '-' * NumDashes, '_' * NumDashes
            has_dashes = line_text.startswith(dash_str) or line_text.startswith(under_str)
            # if has_dashes and not all(c in '-_' for c in set(list(line_text))):
            #     print(f'WRONG LINE: {line_text}')
            #return has_dashes

            # if has_dashes and all(c in '-_' for c in set(list(line_text))) and \
            #    :
            #     print(f'WRONG LINE: {line_text}')
            
            # Not doing center aligned as not all separators are center aligned.
            
            return has_dashes and all(c in '-_' for c in set(list(line_text))) 


        page_idx, first_line_idx, question_lines = 0, 0, []
        for page in doc.pages:
            assert len(page.words) == len(page.word_infos), f'{doc.pdf_name}-{page.page_idx} mismatch'
            
            for (line_idx, line) in enumerate(page.lines):
                
                # if page.page_idx == 0:
                # print(f'{line_idx}) {line.raw_text()} # words {len(line.words)}')
                
                if is_dashed(line):
                    yield (page_idx, first_line_idx, question_lines)
                    page_idx, first_line_idx = page.page_idx, line_idx
                    question_lines = []
                elif (line_idx == 0) and (page.page_idx > 0) and len(line.words) < 5:
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

        # ignoring
        # if len(question.get('sub_answers', [])) != len(question.get('sub_questions', [])):
        #     errs.append('sub_mismatch')

        min_name = question.get('minister_name', '')
        if not min_name or len(min_name) < 10:
            no_answer = True if 'उत्तर आले नाही' in question.get('answer', '') else False
            if not no_answer:
                errs.append(f'incorrect_min >{min_name}<')

        role = question.get('role', '')
        errs += [f'role_missing{role}'] if not role or len(role) < 10 else []
        errs += [f'role_incorrect{role}'] if not role.endswith('मंत्री') else []

        errs += [f'no_answer'] if not question.get('answer', '') else []

        names = question.get('names', [])
        errs += ['no_names'] if not names else []
        
        return errs
        

    def __call__(self, doc):
        def get_question_signature(question):
            return '-'.join([f'{s[0]}{len(question.get(s,"").split())}' for s in Sections])
        
        print(f'> question_extractor: {doc.pdf_name}')
        if doc.info['doc_type'] not in ('StarredQuestions', 'UnstarredQuestions'):
            print('Ignoring doc_type: '+ doc.info['doc_type'])
            doc.questions = []
            return doc

        
        doc.add_extra_field("questions", ("noparse", "", ""))
        doc.add_extra_field("header_lines", ("noparse", "", ""))

        
        doc.questions, doc.header_lines, question_num = [], [], 1
        for (page_idx, line_idx, question_lines) in self.question_iter(doc):

            if (page_idx == 0 and len(question_lines) < 12) or (page_idx != 0 and len(question_lines) < 8):
                if page_idx == 0:
                    doc.header_lines.extend(ln.raw_text() for ln in question_lines)

                if page_idx != 0 and page_idx < len(doc.pages) - 2:
                    # only print if it is a middle page
                    print(f"Skipping lines: {doc.pdf_name}-{page_idx} #lines{len(question_lines)}")
                continue

            if 'तारांकित प्रश्नोत्तरांची यादी' in question_lines[0].raw_text() or 'तारांकित प्रश्र्नोत्तरांची यादी' in question_lines[0].raw_text():
                if page_idx == 0:
                    doc.header_lines.extend(ln.raw_text() for ln in question_lines)
                else:
                    print(f"Skipping lines: {doc.pdf_name}-{page_idx} *#lines{len(question_lines)}")                    
                continue
            
            try:
                question = self.build_question(page_idx, line_idx, question_lines, question_num)
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
        

