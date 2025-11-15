import sys
from pathlib import Path

import docint  # noqa
import orgpedia  # noqa


def order_num(pdf_path):
    org_code, num = pdf_path.stem.rsplit("-", 1)
    return int(num)


if __name__ == "__main__":
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    viz = docint.load("src/extract_mla.yml")

    assert input_path.suffix.lower() == ".pdf"
    doc = viz(input_path)
    doc.to_disk(output_path)
