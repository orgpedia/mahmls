import gzip
import json
import multiprocessing
import os
import re
import sys
from itertools import tee
from pathlib import Path

import pysbd
import sentencepiece as spm
from indicnlp.normalize import indic_normalize
from indicnlp.tokenize import indic_tokenize


def pairwise(iterable):
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

ModelDir = os.environ.get(
    "MODEL_DIR", "../../../import/models/ai4bharat/IndicTrans2-en/ct2_int8_model"
)

class Translator:
    def __init__(self, trans_file, todo_file, src_lang, tgt_lang, ckpt_dir=ModelDir):
        
        self.trans_file = Path(trans_file)
        self.todo_file = Path(todo_file)

        if not self.trans_file.exists():
            self.trans = {}
        elif self.trans_file.name.endswith('gz'):
            with gzip.open(self.trans_file, "rb") as f:
                trans_list = json.loads(f.read())
            self.trans = dict( (ln['mr'], ln['en']) for ln in trans_list)
        else:
            trans_list = json.loads(self.trans_file.read_text())
            self.trans = dict( (ln['mr'], ln['en']) for ln in trans_list)


        if self.todo_file.name.endswith('gz'):
            with gzip.open(todo_file, "rb") as f:
                self.todos = json.loads(f.read())
        else:
            self.todos = json.loads(self.todo_file.read_text())
            
        
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang


        self.queue_len = 4
        self.max_batch_size = 1024 * self.queue_len
        self.num_threads = multiprocessing.cpu_count() // 2

        self.file_batch_size = 5000

        device = "cpu"
        # import ctranslate2
        # self.ckpt_dir = ckpt_dir
        # self.device = device
        # self.translator = ctranslate2.Translator(
        #     self.ckpt_dir,
        #     device=self.device,
        #     device_index=0,
        #     #inter_threads=self.num_threads,
        #     #intra_threads=4,
        #     compute_type="default")

        self.sp_src = spm.SentencePieceProcessor(
            model_file=os.path.join(ckpt_dir, "vocab", "model.SRC")
        )
        self.sp_tgt = spm.SentencePieceProcessor(
            model_file=os.path.join(ckpt_dir, "vocab", "model.TGT")
        )

        normfactory = indic_normalize.IndicNormalizerFactory()
        self.normalizer = normfactory.get_normalizer('mr')# self.src_lang)

        self.seg = pysbd.Segmenter(language="mr", clean=False)

    def save_translations(self):
        save_trans = [{"mr": k, "en": v} for (k, v) in self.translations.items()]

        with gzip.open(self.trans_file, "wb") as f:
            f.write(bytes(json.dumps(save_trans, ensure_ascii=False), encoding='utf-8'))

    def preprocess_sents(self, sents):
        def process(sent):
            processed_sent = " ".join(
                indic_tokenize.trivial_tokenize(self.normalizer.normalize(sent.strip()), self.src_lang)
            )
            return processed_sent
        
        def apply_spm(sents):
            return [" ".join(self.sp_src.encode(sent, out_type=str)) for sent in sents]

        def add_token(sent, delimiter=" "):
            return self.src_lang + delimiter + self.tgt_lang + delimiter + sent

        def apply_lang_tags(sents):
            tagged_sents = []
            for sent in sents:
                tagged_sent = add_token(sent.strip())
                tagged_sents.append(tagged_sent)
            return tagged_sents


        def truncate_long_sentences(sents):
            MAX_SEQ_LEN = 256
            new_sents = []
            
            for sent in sents:
                words = sent.split()
                num_words = len(words)
                if num_words > MAX_SEQ_LEN:
                    print_str = " ".join(words[:5]) + " .... " + " ".join(words[-5:])
                    sent = " ".join(words[:MAX_SEQ_LEN])
                    print(
                        f"WARNING: Sentence {print_str} truncated to 256 tokens as it exceeds maximum length limit"
                    )
                    
                new_sents.append(sent)
            return new_sents

        
            
        preprocessed_sents = [process(s) for s in sents]
        tokenized_sents = apply_spm(preprocessed_sents)
        tagged_sents = apply_lang_tags(tokenized_sents)
        tagged_sents = truncate_long_sentences(tagged_sents)

        return tagged_sents

    def postprocess_sents(self, sents):
        def detokenize(text):
            # Remove space before punctuation characters
            text = re.sub(r"\s+([^\w\s\(\[\{])", r"\1", text)
            # Remove space after ( [ {
            text = re.sub(r"([\(\[\{])\s+", r"\1", text)
            return text
        
        sents = [self.sp_tgt.decode(x.split(" ")) for x in sents]
        postprocessed_sents = [ detokenize(sent) for sent in sents]
        return postprocessed_sents

    def model_translate_sents(self, sents):
        pass


    def translate_sents(self, sents):
        pre_sents = self.preprocess_sents(sents)

        num_tokens, batch_sents, translations, total_tokens = 0, [], [], 0
        for sent in pre_sents:
            num_sent_tokens = len(sent.strip().split(' '))
            if num_tokens + num_sent_tokens >= self.max_batch_size-10:
                translations += self.model_translate_sents(batch_sents)
                batch_sents.clear()
                total_tokens += num_tokens
                num_tokens = 0
            batch_sents.append(sent)
            num_tokens += num_sent_tokens

        if batch_sents:
            total_tokens += num_tokens
            translations += self.model_translate_sents(batch_sents)
        

        trans_sents = self.gpu_translate(sents)

        trans_sents = self.postprocess_sents(sents)
        return trans_sents

    def translate_paras(self, paras):
        paras = list(paras)

        sents, partitions = [], [0]
        for para in paras:
            sents.extend(s.strip() for s in self.seg.segment(para))
            partitions.append(len(sents))

        trans_sents = self.translate_sents(sents)

        trans_paras = []
        for (s, e)in pairwise(partitions):
            trans_para = " ".join(trans_sents[s:e])
        trans_paras.append(trans_para)
        return trans_paras
        
    def translate(self):
        print("******** PARAGRAPHS ***********")
        paras = [p for p in self.todos['paras'] if p not in self.trans]

        for start_idx in range(0, len(paras), self.file_batch_size):
            end_idx = start_idx + self.file_batch_size
            trans_paras = self.translate_paras(paras[start_idx:end_idx])
            assert len(paras) == len(trans_paras)
            
            for (p, t) in zip(paras, trans_paras):
                self.trans[p] = t
            self.save_translations()
        

        print("******** SENTS ***********")
        sents = [s for s in self.todos['sents'] if s not in self.trans]
        trans_sents = self.translate_sents(sents)

        for (s, t) in zip(sents, trans_sents):
            self.trans[s] = t
        self.save_translations()
        print("******** DONE ***********")


def main():
    input_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if len(sys.argv) != 3:
        print("Usage: {sys.argv[0]} <input_dir> <output_dir>")
        print("\tinput_dir contains doc_translations_todo.json")
        sys.exit(1)

    todo_files = input_dir.glob('todos-*.json*')

    for todo_file in todo_files:
        trans_file = output_dir / todo_file.name.replace('todos', 'trans')
        translator = Translator(trans_file, todo_file, "mar_Deva", "eng_Latn")
        translator.translate()


if __name__ == "__main__":
    main()
