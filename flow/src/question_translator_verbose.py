import json
from pathlib import Path

from docint.util import get_full_path, get_model_path, is_readable_nonempty, is_repo_path
from docint.vision import Vision

MarathiNums = "१२३४५६७८९०.() "

def is_number(cell):
    cell = cell.strip(".) ")
    return all(c in MarathiNums for c in cell)


EnglishNums = "1234567890.() "
MarthiEnglishNumDict = dict((m, e) for (m, e) in zip(MarathiNums, EnglishNums))


def trans_number(cell):
    return "".join(MarthiEnglishNumDict[c] for c in cell)


def get_row_texts(row):
    return [c.text_with_break() for c in row.cells]


BatchSize = 100


@Vision.factory(
    "question_translator",
    depends=[
        "docker:python:3.7-slim",
        "apt:git",
        "git+https://github.com/orgpedia/indic_nlp_library-deva.git",
        "ctranslate2==3.9.0",
        "sentencepiece",
    ],
    default_config={
        "stub": "question_translator",
        "mode": "write_todos",
        "model_dir": "/import/models",
        "model_name": "ai4bharat:IndicTrans2-en/ct2_int8_model",
        "translations_dir": "conf/trans",
        "todo_dir": "conf/todos",
        "output_dir": "output",
        "write_output": False,
        "src_lang": "hindi",
        "tgt_lang": "",
    },
)
class QuestionTranslator:
    def __init__(
        self,
        stub,
        mode,
        model_dir,
        model_name,
        translations_dir,
        todo_dir,
        output_dir,
        write_output,
        src_lang,
        tgt_lang,
    ):
        self.conf_dir = Path("conf")
        self.stub = stub
        self.mode = mode

        self.model_dir = Path(model_dir)
        self.model_name = model_name

        if is_repo_path(self.model_dir):
            self.model_dir = get_full_path(self.model_dir)
        else:
            self.model_dir = Path(self.model_dir)

        self.output_dir = Path(output_dir)
        self.translations_dir = Path(translations_dir)
        self.todos_dir = Path(todo_dir)

        self.translations_file = None
        self.todos_file = None

        self.para_todos = set()
        self.sent_todos = set()

        self.write_output = write_output
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.model = None
        self.num_docs = 100

    def load_model(self):
        from ..models.indictrans.engine import Model

        print(f"[QuestionTranslator] Loading translation model...")
        print(f"[QuestionTranslator] Model directory: {self.model_dir}")
        trans_model_dir = get_model_path(self.model_name, self.model_dir)
        print(f"[QuestionTranslator] Translation model path: {trans_model_dir}")
        print(f"[QuestionTranslator] Initializing model on CPU...")
        return Model(str(trans_model_dir), device="cpu")

    def get_range_str(self, doc_num):
        # 423 -> '401-500'
        base_num = doc_num - (doc_num % self.num_docs)
        return f'{base_num+1}-{base_num+100}'

    def load_translations(self, doc):
        print(f"[QuestionTranslator] Loading translations for document: {doc.pdf_name}")
        doc_num, _ = doc.pdf_name.split('-')[1].split('.')
        range_str = self.get_range_str(int(doc_num))
        print(f"[QuestionTranslator] Document number: {doc_num}, Range: {range_str}")

        # file does not exist or there is a mismatch
        if not self.translations_file or self.translations_file.name != f'trans-{range_str}.json':
            self.translations_file = self.translations_dir / f'trans-{range_str}.json'
            print(f"[QuestionTranslator] Translations file: {self.translations_file}")

        self.translations = {}
        if is_readable_nonempty(self.translations_file):
            json_list = json.loads(self.translations_file.read_text())
            print(f"[QuestionTranslator] Loaded {len(json_list)} translation entries from {self.translations_file}")
            for trans_dict in json_list:
                m, e = trans_dict["mr"], trans_dict["en"]
                self.translations[m] = e
        else:
            print(f"[QuestionTranslator] No existing translations file found at {self.translations_file}")

    def save_translations(self):
        save_trans = sorted(
            [{"mr": k, "en": v} for (k, v) in self.translations.items()],
            key=lambda d: d["mr"],
        )
        print(f"[QuestionTranslator] Saving {len(save_trans)} translations to {self.translations_file}")
        self.translations_file.write_text(json.dumps(save_trans, indent=2, ensure_ascii=False))
        print(f"[QuestionTranslator] Translations saved successfully")

    def load_todos(self, doc):
        print(f"[QuestionTranslator] Loading todos for document: {doc.pdf_name}")
        doc_num, _ = doc.pdf_name.split('-')[1].split('.')
        range_str = self.get_range_str(int(doc_num))

        # file does not exist or there is a mismatch
        if not self.todos_file or self.todos_file.name != f'todos-{range_str}.json':
            self.todos_file = self.todos_dir / f'todos-{range_str}.json'
            print(f"[QuestionTranslator] Todos file: {self.todos_file}")

        if is_readable_nonempty(self.todos_file):
            json_dict = json.loads(self.todos_file.read_text())
            self.para_todos = set(json_dict.get('paras',[]))
            self.sent_todos = set(json_dict.get('sents',[]))
            print(f"[QuestionTranslator] Loaded {len(self.para_todos)} paragraph todos and {len(self.sent_todos)} sentence todos")
        else:
            self.para_todos = set()
            self.sent_todos = set()
            print(f"[QuestionTranslator] No existing todos file found at {self.todos_file}")

    def save_todos(self):
        if self.para_todos or self.sent_todos:
            todo = {"paras": sorted(self.para_todos), "sents": sorted(self.sent_todos)}
            print(f"[QuestionTranslator] Saving todos: {len(self.para_todos)} paragraphs, {len(self.sent_todos)} sentences to {self.todos_file}")
            self.todos_file.write_text(json.dumps(todo, indent=2, ensure_ascii=False))
            print(f"[QuestionTranslator] Todos saved successfully")
        else:
            print(f"[QuestionTranslator] No todos to save")

    def para_translate(self, para_texts):
        print(f"[QuestionTranslator] Translating {len(para_texts)} paragraphs from {self.src_lang} to {self.tgt_lang}")
        para_trans = [
            self.model.translate_paragraph(p, self.src_lang, self.tgt_lang) for p in para_texts
        ]
        print(f"[QuestionTranslator] Paragraph translation completed")
        for (p, t) in zip(para_texts, para_trans):
            self.indic2en_trans[p] = t
        self.save_translations()

    def sentences_translate(self, sents):
        print(f"[QuestionTranslator] Translating {len(sents)} sentences from {self.src_lang} to {self.tgt_lang}")
        sents_trans = self.model.batch_translate(sents, self.src_lang, self.tgt_lang)
        print(f"[QuestionTranslator] Sentence translation completed")
        for (s, t) in zip(sents, sents_trans):
            self.indic2en_trans[s] = t
        self.save_translations()

    def get_trans(self, text):
        if text.isascii():
            return text
        else:
            t = self.translations.get(text, None)
            if t is None:
                print(f'[QuestionTranslator] **TRANSLATE_ERROR: Translation not found for: {text[:100]}{"..." if len(text) > 100 else ""}')
            return t
        #return None if text.isascii() else self.translations.get(text, None)

    def translate_question(self, question):
        def mk_list(lst):
            return lst if isinstance(lst, list) else [lst]

        def mk_zip_list(field):
            return zip(mk_list(question.get(field, [])), mk_list(en_question.get(field, [])))

        def get_num(num_str):
            try:
                return int(num_str)
            except ValueError as e:
                return num_str

        q_num = question.get('question_num', 'unknown')
        print(f"[QuestionTranslator] Translating question #{q_num}")

        en_question = {}
        en_question['title'] = self.get_trans(question['title'])
        en_question['names'] = [self.get_trans(n) for n in question['names']]
        en_question['role'] = self.get_trans(question['role'])
        en_question['minister_name'] = self.get_trans(question['minister_name'])

        en_question['sub_questions'] = [self.get_trans(s) for s in question.get('sub_questions',[])]
        en_question['sub_answers'] = [self.get_trans(s) for s in question.get('sub_answers', [])]

        en_question['question'] = '\n'.join(q for q in en_question['sub_questions'] if q)
        en_question['answer'] = '\n'.join(a for a in en_question['sub_answers'] if a)
        en_question['question_num'] = get_num(question.get('question_num', ''))

        para_fields = ['title', 'sub_questions', 'sub_answers']
        sent_fields = ['names', 'role', 'minister_name']

        todo_paras = [ m for f in para_fields for (m, e) in mk_zip_list(f) if e is None ]
        todo_sents = [ m for f in sent_fields for (m, e) in mk_zip_list(f) if e is None ]

        if todo_paras or todo_sents:
            print(f"[QuestionTranslator] Question #{q_num}: Found {len(todo_paras)} paragraph todos, {len(todo_sents)} sentence todos")

        return en_question, todo_paras, todo_sents

    def __call__(self, doc):
        print(f"\n[QuestionTranslator] ===== Processing document: {doc.pdf_name} =====")
        doc.add_extra_page_field("en_questions", ("noparse", "", ""))

        if not doc.questions:
            print(f"[QuestionTranslator] No questions found in document {doc.pdf_name}")
            doc.en_questions = []
            return doc

        print(f"[QuestionTranslator] Found {len(doc.questions)} questions in document")

        if self.mode == 'write_todos':
            print(f"[QuestionTranslator] Mode: write_todos")
            self.load_translations(doc)
            self.load_todos(doc)

            write_todos = False

            doc.en_questions = []
            translated_count = 0

            for idx, question in enumerate(doc.questions, 1):
                print(f"[QuestionTranslator] Processing question {idx}/{len(doc.questions)}")
                en_question, q_unk_paras, q_unk_sents  = self.translate_question(question)

                q_todo_paras = [ p for p in q_unk_paras if p not in self.para_todos ]
                q_todo_sents = [ s for s in q_unk_sents if s not in self.sent_todos ]

                if q_todo_paras or q_todo_sents:
                    print(f"[QuestionTranslator] Question {idx}: Adding {len(q_todo_paras)} new paragraph todos, {len(q_todo_sents)} new sentence todos")
                    self.para_todos.update(q_todo_paras)
                    self.sent_todos.update(q_todo_sents)
                    write_todos = True
                else:
                    print(f"[QuestionTranslator] Question {idx}: Fully translated, adding to output")
                    doc.en_questions.append(en_question)
                    translated_count += 1
            #end for

            print(f"[QuestionTranslator] Checking header lines for translation")
            h_todo_sents = [ s for s in doc.header_lines if s not in self.sent_todos ]
            if h_todo_sents:
                print(f"[QuestionTranslator] Adding {len(h_todo_sents)} header line todos")
                self.sent_todos.update(h_todo_sents)
                write_todos = True

            if write_todos:
                print(f"[QuestionTranslator] *** Document NOT fully translated ***")
                print(f"[QuestionTranslator] Translated: {translated_count}/{len(doc.questions)} questions")
                print(f"[QuestionTranslator] Writing todos for remaining translations")
                self.save_todos()
            else:
                print(f"[QuestionTranslator] *** Document FULLY translated ***")
                print(f"[QuestionTranslator] All {len(doc.questions)} questions translated successfully")
        else:
            print(f"[QuestionTranslator] Mode: {self.mode}")
            pass

        print(f"[QuestionTranslator] ===== Finished processing {doc.pdf_name} =====\n")
        return doc
