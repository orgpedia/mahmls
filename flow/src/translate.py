import json
import os
import sys
from itertools import tee, zip_longest
from pathlib import Path


def pairwise(iterable):
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def grouper(iterable, n, *, incomplete="fill", fillvalue=None):
    "Collect data into non-overlapping fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, fillvalue='x') --> ABC DEF Gxx
    # grouper('ABCDEFG', 3, incomplete='strict') --> ABC DEF ValueError
    # grouper('ABCDEFG', 3, incomplete='ignore') --> ABC DEF
    args = [iter(iterable)] * n
    if incomplete == "fill":
        return zip_longest(*args, fillvalue=fillvalue)
    if incomplete == "strict":
        return zip(*args, strict=True)
    if incomplete == "ignore":
        return zip(*args)
    else:
        raise ValueError("Expected fill, strict, or ignore")


ModelDir = os.environ.get(
    "MODEL_DIR", "../../../import/models/ai4bharat/IndicTrans2-en/ct2_int8_model"
)


class Translator:
    def __init__(self, translations_file, todo_file, src_lang, tgt_lang):
        self.translations_file = Path(translations_file)
        self.todo_file = Path(todo_file)

        if self.todo_file.exists() and self.todo_file.stat().st_size > 0:
            todo_dict = json.loads(self.todo_file.read_text())
        else:
            todo_dict = {}

        self.para_todos = todo_dict.get("paras", [])
        self.cell_todos = todo_dict.get("cells", [])

        self.todo_file = todo_file
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang

        self.model = None
        self.indic2en_trans = None

    def load_model(self):
        from docint.models.indictrans.engine import Model

        print(ModelDir)
        return Model(str(ModelDir), device="cpu")

    def load_translations(self):
        indic2en_trans = {}
        if self.translations_file.exists() and self.translations_file.stat().st_size > 0:
            json_list = json.loads(self.translations_file.read_text())
            for trans_dict in json_list:
                m, e = trans_dict["mr"], trans_dict["en"]
                indic2en_trans[m] = e
        return indic2en_trans

    def save_translations(self):
        save_trans = sorted(
            [{"mr": k, "en": v} for (k, v) in self.indic2en_trans.items()],
            key=lambda d: d["mr"],
        )
        self.translations_file.write_text(
            json.dumps(save_trans, indent=2, ensure_ascii=False)
        )

    def para_translate(self, para_texts):
        para_texts = list(para_texts)

        partitions = self.model.group_paragraphs(
            para_texts, self.src_lang, self.tgt_lang
        )
        print(f"#paragraphs: {len(para_texts)} #partitions: {len(partitions)}")

        for (s, e) in pairwise(partitions):
            batch_paras = para_texts[s:e]
            batch_trans = self.model.translate_paragraphs(
                batch_paras, self.src_lang, self.tgt_lang
            )

            assert len(batch_trans) == len(batch_paras)

            for (p, t) in zip(batch_paras, batch_trans):
                self.indic2en_trans[p] = t

            if batch_trans:
                self.save_translations()

    def sentences_translate(self, sents):
        sents = list(sents)
        partitions = self.model.group_paragraphs(sents, self.src_lang, self.tgt_lang)

        for (s, e) in pairwise(partitions):
            batch_sents = sents[s:e]
            batch_trans = self.model.batch_translate(
                batch_sents, self.src_lang, self.tgt_lang
            )
            assert len(batch_sents) == len(batch_trans)

            for (s, t) in zip(batch_sents, batch_trans):
                self.indic2en_trans[s] = t

            if batch_trans:
                self.save_translations()

    def translate(self):
        if not self.para_todos and not self.cell_todos:
            return

        self.model = self.load_model()
        self.indic2en_trans = self.load_translations()

        para_texts = [p for p in self.para_todos if p not in self.indic2en_trans]
        cell_texts = [c for c in self.cell_todos if c not in self.indic2en_trans]

        print("******** PARAGRAPHS ***********")
        self.para_translate(para_texts)

        print("******** CELLS ***********")

        self.sentences_translate(cell_texts)
        print("******** DONE ***********")


def main():
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if len(sys.argv) != 3:
        print("Usage: {sys.argv[0]} <input_dir> <output_dir>")
        print("\tinput_dir contains doc_translations_todo.json")
        sys.exit(1)

    todo_file = input_dir / "doc_translations_todo.json"
    translations_file = output_dir / "doc_translations.json"

    translator = Translator(translations_file, todo_file, "mar_Deva", "eng_Latn")

    translator.translate()


if __name__ == "__main__":
    main()
