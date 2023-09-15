import datetime
import json
import logging
import sys
from pathlib import Path

from docint.vision import Vision

@Vision.factory(
    "info_reader",
    default_config={
        "info_file": "conf/documents.json",
    },
)
class MetaWriter:
    def __init__(
        self,
        info_file,
    ):
        self.info_file = Path(info_file)

        self.infos = json.loads(self.info_file.read_text())
        self.infos_dict = dict((i['name'], i) for i in self.infos)


    def __call__(self, doc):
        doc.add_extra_field("info", ("noparse", "", ""))
        doc.info = self.infos_dict[doc.pdf_name]
        return doc
