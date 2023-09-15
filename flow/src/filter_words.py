import shlex
from pathlib import Path

from docint.util import load_config
from docint.vision import Vision


@Vision.factory(
    "filter_words",
    default_config={
        "stub": "filter_words"
    },
)
class FilterWords:
    def __init__(self, stub):
        self.stub = stub
        self.conf_dir = Path('conf')

    def __call__(self, doc):
        cfg = load_config(self.conf_dir, doc.pdf_name, self.stub)
        if not cfg:
            return doc

        text_edits = {}
        for line_idx, edit_line in enumerate(cfg.get('text_edits')):
            edit_list = shlex.split(edit_line.strip())
            cmd = edit_list.pop(0)
            if cmd == 'replace_text':
                t1, t2 = edit_list[0], edit_list[1]
                text_edits[t1] = t2
            elif cmd == 'clear_text':
                t1 = edit_list[0]
                text_edits[t1] = ''
            else:
                raise ValueError(f'Unknown Command {cmd} on line: {line_idx}')

        for word in [w for p in doc.pages for w in p.words]:
            if word.text in text_edits:
                word.text_ = text_edits[word.text]
        return doc
