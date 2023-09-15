import multiprocessing
import gzip
import json
import os
import time
import sys
from itertools import tee
from pathlib import Path

from typing import List

import ctranslate2
import sentencepiece as spm
import pysbd

from indicnlp.tokenize import indic_detokenize
from indicnlp.transliterate import unicode_transliterate



def pairwise(iterable):
    # pairwise('ABCDEFG') --> AB BC CD DE EF FG
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


LangSuffix = {
    'mar_Deva': 'mr',
    'hin_Deva': 'hi',
    'kan_Knda': 'kn',
}

ModelDir = os.environ.get(
    "MODEL_DIR", "/content/drive/My Drive/Translate/ct2_int8_model"
)

class Translator:
    def __init__(self, src_lang, tgt_lang, ckpt_dir=ModelDir, device="cuda"):
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang

        self.tgt_suffix = LangSuffix[tgt_lang]

        if src_lang == 'eng_Latn':
            from sacremoses import MosesPunctNormalizer, MosesTokenizer, MosesDetokenizer

            self.en_tok = MosesTokenizer(lang="en")
            self.en_normalizer = MosesPunctNormalizer()
            self.en_detok = MosesDetokenizer(lang="en")
        else:
            assert False
            pass

        self.queue_len = 4
        self.max_batch_size = 1024 * self.queue_len
        self.num_threads = multiprocessing.cpu_count() // 2

        self.seg = pysbd.Segmenter(language="en", clean=False)

        self.story_batch = 500
        self.file_batch = 5000

        import ctranslate2
        self.ckpt_dir = ckpt_dir
        self.device = device
        self.translator = ctranslate2.Translator(
            self.ckpt_dir,
            device=self.device,
            device_index=0,
            #inter_threads=self.num_threads,
            #intra_threads=4,
            compute_type="default")

        self.sp_src = spm.SentencePieceProcessor(
            model_file=os.path.join(ckpt_dir, "vocab", "model.SRC")
        )
        self.sp_tgt = spm.SentencePieceProcessor(
            model_file=os.path.join(ckpt_dir, "vocab", "model.TGT")
        )
        self.xliterator = unicode_transliterate.UnicodeIndicTransliterator()

    def print_memory(self):
        import psutil
        import humanize
        import os
        import GPUtil as GPU
        GPUs = GPU.getGPUs()
        # XXX: only one GPU on Colab and isn’t guaranteed
        gpu = GPUs[0]
        process = psutil.Process(os.getpid())
        print("Gen RAM Free: " + humanize.naturalsize( psutil.virtual_memory().available ), " | Proc size: " + humanize.naturalsize( process.memory_info().rss))
        print("GPU RAM Free: {0:.0f}MB | Used: {1:.0f}MB | Util {2:3.0f}% | Total {3:.0f}MB".format(gpu.memoryFree, gpu.memoryUsed, gpu.memoryUtil*100, gpu.memoryTotal))

    def translate_lines(self, lines: List[str]) -> List[str]:
        tokenized_sents = [x.strip().split(" ") for x in lines]

        print(f"#Lines: {len(lines)} #Tokens: {sum(len(s) for s in tokenized_sents)}")
        #self.print_memory()

        translations = self.translator.translate_batch(
            tokenized_sents,
            max_batch_size=self.max_batch_size,
            batch_type="tokens",
            max_input_length=160,
            max_decoding_length=256,
            beam_size=2,
        )
        translations = [" ".join(x.hypotheses[0]) for x in translations]
        #print(translations[0])
        #print('#After translation')
        #self.print_memory()
        #print('-----------------')
        #print()


        assert len(translations) == len(lines)
        #print(f"*** Error Counts: {self.get_errors(lines, translations)}")
        return translations

    def preprocess_sent(
        self, sent: str, normalizer, lang: str
    ) -> str:

        sent = punc_norm(sent, 'en')
        if lang == "eng_Latn":
            processed_sent = " ".join(
                self.en_tok.tokenize(self.en_normalizer.normalize(sent.strip()), escape=False)
            )
            return processed_sent
        else:
            pass



    def preprocess(self, sents: List[str], lang: str) -> List[str]:
        """
        Preprocess a batch of input sentences for the translation.

        Args:
            sents (List[str]): batch of input sentences to preprocess.
            lang (str): flores language code of the input sentences.

        Returns:
            List[str]: preprocessed batch of input sentences.
        """
        if lang == "eng_Latn":
            processed_sents = [self.preprocess_sent(sent, None, lang) for sent in sents]
        else:
            pass

        return processed_sents



    def preprocess_batch(self, batch: List[str], src_lang: str, tgt_lang: str) -> List[str]:
        """
        Preprocess an array of sentences by normalizing, tokenization, and possibly transliterating it.

        Args:
            batch (List[str]): input list of sentences to preprocess.
            src_lang (str): flores language code of the input text sentences.
            tgt_lang (str): flores language code of the output text sentences.

        Returns:
            str: preprocessed input text sentence.
        """


        def add_token(sent: str, src_lang: str, tgt_lang: str, delimiter: str = " ") -> str:
            return src_lang + delimiter + tgt_lang + delimiter + sent

        def apply_spm(sents: List[str]) -> List[str]:
            return [" ".join(self.sp_src.encode(sent, out_type=str)) for sent in sents]

        def apply_lang_tags(sents: List[str], src_lang: str, tgt_lang: str) -> List[str]:
            tagged_sents = []
            for sent in sents:
                tagged_sent = add_token(sent.strip(), src_lang, tgt_lang)
                tagged_sents.append(tagged_sent)
            return tagged_sents

        def truncate_long_sentences(sents: List[str]) -> List[str]:
            MAX_SEQ_LEN = 256
            new_sents = []

            for sent in sents:
                words = sent.split()
                num_words = len(words)
                if num_words > MAX_SEQ_LEN:
                    print_str = " ".join(words[:5]) + " .... " + " ".join(words[-5:])
                    sent = " ".join(words[:MAX_SEQ_LEN])
                    print(
                        f"WARNING: Sentence {print_str} truncated to 256 tokens"
                    )

                new_sents.append(sent)
            return new_sents

        preprocessed_sents = self.preprocess(batch, lang=src_lang)
        tokenized_sents = apply_spm(preprocessed_sents)
        tagged_sents = apply_lang_tags(tokenized_sents, src_lang, tgt_lang)
        tagged_sents = truncate_long_sentences(tagged_sents)

        return tagged_sents

    def postprocess_batch(self, sents: List[str], lang: str) -> List[str]:
        common_lang = 'hin_Deva'
        flores_codes = {
            "hin_Deva": "hi",
            "mar_Deva": "mr",
            "kan_Knda": "kn",
        }
        sents = [self.sp_tgt.decode(x.split(" ")) for x in sents]
        postprocessed_sents = []
        if lang == "eng_Latn":
            for sent in sents:
                postprocessed_sents.append(self.en_detok.detokenize(sent.split(" ")))
        else:
            for sent in sents:
                outstr = indic_detokenize.trivial_detokenize(
                    self.xliterator.transliterate(
                        sent, flores_codes[common_lang], flores_codes[lang],
                    ),
                    flores_codes[lang],
                )
                postprocessed_sents.append(outstr)
        return postprocessed_sents

    # translate a batch of sentences from src_lang to tgt_lang
    def batch_translate(self, batch, src_lang: str, tgt_lang: str):
        """
        Translates a batch of input sentences (including pre/post processing)
        from source language to target language.

        Args:
            batch (List[str]): batch of input sentences to be translated.
            src_lang (str): flores source language code.
            tgt_lang (str): flores target language code.

        Returns:
            List[str]: batch of translated-sentences generated by the model.
            int: number of tokens
        """

        assert isinstance(batch, (list, set)), f" batch expected list is of {type(batch)}"
        preprocessed_sents = self.preprocess_batch(batch, src_lang, tgt_lang)

        num_tokens, batch_sents, translations, total_tokens = 0, [], [], 0
        for sent in preprocessed_sents:
            num_sent_tokens = len(sent.strip().split(' '))
            if num_tokens + num_sent_tokens >= self.max_batch_size-10:
                translations += self.translate_lines(batch_sents)
                batch_sents.clear()
                total_tokens += num_tokens
                num_tokens = 0
            batch_sents.append(sent)
            num_tokens += num_sent_tokens

        if batch_sents:
            total_tokens += num_tokens
            translations += self.translate_lines(batch_sents)

        post_sents = self.postprocess_batch(translations, tgt_lang)
        return post_sents, total_tokens


    def translate_stories(self, en_stories):
        def get_sents_partitions(story):
            story_sents, story_partitions = [], [0]
            for para in story.strip().split('\n'):
                sents = self.seg.segment(para)
                story_sents.extend([s.strip() for s in sents])
                story_partitions.append(len(story_sents))
            return story_sents, story_partitions

        def build_story(story_sents, story_partitions):
            tgt_story = ''
            for (s, e) in pairwise(story_partitions):
                tgt_story += ' '.join(story_sents[s:e]) + '\n'
            return tgt_story.strip()

        en_sents, en_partitions, all_story_partitions = [], [0], []
        for story in en_stories:
            story_sents, story_partitions = get_sents_partitions(story)
            en_sents.extend(story_sents)
            en_partitions.append(len(en_sents))
            all_story_partitions.append(story_partitions)

        start_time = time.time()
        (tgt_sents, num_tokens) = self.batch_translate(en_sents, self.src_lang, self.tgt_lang)
        end_time = time.time()

        total_secs = end_time - start_time
        print(f'Tokens/sec: {num_tokens/total_secs} Time: {total_secs}')

        tgt_stories = []
        for idx, (s, e) in enumerate(pairwise(en_partitions)):
            story_partitions = all_story_partitions[idx]
            tgt_story = build_story(tgt_sents[s:e], story_partitions)

            # print('--------------------')
            # print(en_stories[idx])
            # print('=====')
            # print(tgt_story)
            # print('--------------------')

            tgt_stories.append(tgt_story)
        return tgt_stories


    def translate(self, en_json_file, output_dir):
        def write_stories(tgt_stories, tgt_json_file):
            print(f'\tWriting: {tgt_json_file}')
            with gzip.open(tgt_json_file, "wb") as f:
                f.write(bytes(json.dumps(tgt_stories, separators=(',', ':'), ensure_ascii=False), encoding='utf-8'))

        assert en_json_file.suffix == '.gz'

        with gzip.open(en_json_file, "rb") as f:
            en_stories = json.loads(f.read())

        file_num = en_json_file.stem.replace('train','').replace('.json', '').replace('.en','')
        tgt_json_dir = output_dir / f'train{file_num}'
        assert tgt_json_dir.exists()

        tgt_json_files = list(tgt_json_dir.glob('*.json.gz'))
        start_num = len(tgt_json_files) * self.file_batch
        tgt_num = len(tgt_json_files)

        print(f'Dir: {tgt_json_dir} start_num: {start_num} tgt_num: {tgt_num}')

        tgt_stories = []
        for start_idx in range(start_num, len(en_stories), self.story_batch):
            tgt_stories += self.translate_stories(en_stories[start_idx:start_idx + self.story_batch])
            print(f'Done Translating [{start_idx}:{start_idx+self.story_batch}]')
            if len(tgt_stories) == self.file_batch:
                tgt_json_file = tgt_json_dir / f'train{file_num}-{tgt_num:02d}.json.gz'
                write_stories(tgt_stories, tgt_json_file)
                tgt_stories.clear()
                tgt_num += 1

def main():
    input_dir = Path('/content/drive/My Drive/Translate')
    output_dir = Path('/content/drive/My Drive/Translate')
    tgt_lang = 'kan_Knda'

    assert tgt_lang in ['mar_Deva', 'hin_Deva', 'kan_Knda']

    translator = Translator("eng_Latn", tgt_lang, device="cuda")
    num = 1
    en_json_file = input_dir / f'train{num:02d}.en.json.gz'
    translator.translate(en_json_file, output_dir)

import re

multispace_regex = re.compile("[ ]{2,}")
end_bracket_space_punc_regex = re.compile(r"\) ([\.!:?;,])")
digit_space_percent = re.compile(r"(\d) %")
double_quot_punc = re.compile(r"\"([,\.]+)")
digit_nbsp_digit = re.compile(r"(\d) (\d)")


def punc_norm(text, lang="en"):
    text = (
        text.replace("\r", "")
        .replace("(", " (")
        .replace(")", ") ")
        .replace("( ", "(")
        .replace(" )", ")")
        .replace(" :", ":")
        .replace(" ;", ";")
        .replace("`", "'")
        .replace("„", '"')
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", " - ")
        .replace("´", "'")
        .replace("‘", "'")
        .replace("‚", "'")
        .replace("’", "'")
        .replace("''", '"')
        .replace("´´", '"')
        .replace("…", "...")
        .replace(" « ", ' "')
        .replace("« ", '"')
        .replace("«", '"')
        .replace(" » ", '" ')
        .replace(" »", '"')
        .replace("»", '"')
        .replace(" %", "%")
        .replace("nº ", "nº ")
        .replace(" :", ":")
        .replace(" ºC", " ºC")
        .replace(" cm", " cm")
        .replace(" ?", "?")
        .replace(" !", "!")
        .replace(" ;", ";")
        .replace(", ", ", ")
    )

    text = multispace_regex.sub(" ", text)
    text = end_bracket_space_punc_regex.sub(r")\1", text)
    text = digit_space_percent.sub(r"\1%", text)
    text = double_quot_punc.sub(r'\1"', text)  # English "quotation," followed by comma, style
    text = digit_nbsp_digit.sub(r"\1.\2", text)  # What does it mean?
    return text.strip(" ")

