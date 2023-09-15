import functools
from operator import attrgetter
from pathlib import Path

from docint import pdfwrapper
from docint.shape import Coord, Edge
from docint.vision import Vision

DEFAULT_Y_TOLERANCE = 3

@Vision.factory(
    "dashes_finder",
    default_config={
        'y_tol': DEFAULT_Y_TOLERANCE,
    },
)
class PDFReader:
    def __init__(self, y_tol):
        self.y_tol = y_tol

    def cluster_pdfwords(self, pdfwords):
        pdfwords.sort(key=lambda bb: bb.bounding_box[1])

        def group_words_inline(lines, word):
            if not lines:
                return [[word]]

            last_line, last_word = lines[-1], lines[-1][-1]
            if (word.bounding_box[1] - last_word.bounding_box[1]) > self.y_tol:
                lines.append([word])
            else:
                last_line.append(word)
            return lines

        lines = functools.reduce(group_words_inline, pdfwords, [])
        [ln.sort(key=attrgetter('bounding_box')) for ln in lines]
        return lines
        

    def __call__(self, doc):
        def to_doc_coord(bbox, page):
            x0, y0, x1, y1 = bbox
            top = Coord(x=x0/page.width, y=y0/page.height)
            bot = Coord(x=x1/page.width, y=y1/page.height)
            return top, bot

        def is_dashed(ln):
            ln_text = ''.join(w.text for w in ln).strip()
            if len(set(ln_text)) > 2:
                return False
            return '-----' in ln_text or '_____' in ln_text or '————' in ln_text

        doc.add_extra_page_field("dash_edges", ("list", "docint.shape", "Edge"))
        
        pdf = pdfwrapper.open(doc.pdf_path)
        for page, pdf_page in zip(doc.pages, pdf.pages):
            page.dash_edges = []

            lines = self.cluster_pdfwords(pdf_page.words)
            dashed_lines = [ln for ln in lines if is_dashed(ln)]
            #print(f'Page: {page.page_idx}: Lines: {len(dashed_lines)}')

            for dline in dashed_lines:
                lft, _ = to_doc_coord(dline[0].bounding_box, page)
                _, rgt = to_doc_coord(dline[-1].bounding_box, page)

                e = Edge(coord1=lft, coord2=rgt, orientation='h')
                #print(f'\t{e}')
                page.dash_edges.append(e)
        return doc
