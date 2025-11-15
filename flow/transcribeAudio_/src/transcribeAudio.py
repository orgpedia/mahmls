import sys
from pathlib import Path

from docint.ppln import Pipeline


def order_num(file_path):
    org_code, num = file_path.stem.rsplit("-", 1)
    return int(num)


if __name__ == "__main__":
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    ppln = Pipeline.from_file("src/transcribeAudio.yml")

    if input_path.is_dir():
        assert output_path.is_dir()
        input_files = sorted(input_path.glob("*.webm"), key=order_num)
        print(len(input_files))

        # docs = viz.pipe_all(input_files[:3])
        docs = ppln(input_files)

        for doc in docs:
            output_doc_path = output_path / (doc.get_file_name() + ".audio.json")
            doc.to_disk(output_doc_path)
    elif input_path.suffix.lower() in (".webm", ".mp3"):
        doc = ppln(input_path)
        if doc:
            doc.to_disk(output_path)

    # elif input_path.suffix.lower() in (".list", ".lst"):
    #     print("processing list")
    #     input_files = input_path.read_text().split("\n")

    #     pdf_files = [Path("input") / f for f in input_files if f and f[0] != "#"]
    #     pdf_files = [p for p in pdf_files if p.exists()]

    #     docs = viz.pipe_all(pdf_files)
    #     for doc in docs:
    #         output_doc_path = output_path / (doc.pdf_name + ".doc.json")
    #         doc.to_disk(output_doc_path)

