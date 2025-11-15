import functools
import re
import subprocess
from pathlib import Path
from more_itertools import partition, first


from docint import pdfwrapper
from docint.vision import Vision
from PIL import Image


def extract_assembly_members(doc, images_dir):
    def line_has_y(line, y):
        return line and (line.ymin <= y <= line.ymax)


    def line_below_y(line, y):
        return line and (line.ymin > y)

    
    def build_member_info(pdf_page, page, tomerge_imageidxs, image_idx):
        result_image_path = images_dir / f'P{page.page_idx+1}-{image_idx+1}.jpg'

        if not result_image_path.exists():
            pidx = page.page_idx
            tomerge_idxs = [tup[0] for tup in tomerge_imageidxs]
        
            tomerge_paths = [images_dir / Path(f"P-{pidx}") / f'I-{i:03}.ppm' for i in tomerge_idxs]
            tomerge_paths = [str(p) for p in tomerge_paths]
            cmd = f"convert -append {' '.join(tomerge_paths)} {str(result_image_path)}"

            subprocess.check_call(cmd.split(' '))

        top_img = tomerge_imageidxs[0][1]
        top_x, top_y = top_img.bounding_box[0]/pdf_page.width, top_img.bounding_box[1]/pdf_page.height
        
        top_ln = first((ln for ln in page.lines if line_has_y(ln, top_y)), None)
        
        if not top_ln:
            print('** Top line not found')
            top_ln = first((ln for ln in page.lines if line_below_y(ln, top_y)), None)        
        
        def is_greater(word):
            return word.xmin > top_x
        
        lft_words, rgt_words = partition(is_greater, top_ln.words)
        
        lft_txt = "".join(w.text_with_break(ignore_line_break=True) for w in lft_words)
        rgt_txt = "".join(w.text_with_break(ignore_line_break=True) for w in rgt_words)        
        return lft_txt.strip(), rgt_txt.strip(), str(result_image_path)

    def merge_images(result_image_idxs, image_idx):
        if not result_image_idxs:
            result_image_idxs.append([image_idx])
            return result_image_idxs

        last_image = result_image_idxs[-1][-1][1]
        image = image_idx[1]
        if (image.bounding_box[1] - last_image.bounding_box[3]) < 5:
            result_image_idxs[-1].append(image_idx)
        else:
            result_image_idxs.append([image_idx])
            
        return result_image_idxs

    def extract_all_images(pdf_path, page_idx):
        page_dir = images_dir / f'P-{page_idx}'
        if not page_dir.exists():
            page_dir.mkdir(exist_ok=True)
            cmd = f"pdfimages -f {page_idx+1} -l {page_idx+1} {str(pdf_path)} {str(page_dir)}/I"
            subprocess.check_call(cmd.split())
        
    
    member_start_page_idx = 11
    member_end_page_idx = 86
    
    pdf = pdfwrapper.open(doc.pdf_path)

    members = []
    for page_idx in range(member_start_page_idx, member_end_page_idx):
        extract_all_images(doc.pdf_path, page_idx)
        
        pdf_page, page = pdf.pages[page_idx], doc.pages[page_idx]
        pdf_images_idxs = sorted(enumerate(pdf_page.images), key=lambda img_tup: img_tup[1].bounding_box[1])
        
        tomerge_imageidxs_list = functools.reduce(merge_images, pdf_images_idxs, [])
        
        for (image_idx, tomerge_imageidxs) in enumerate(tomerge_imageidxs_list):
            m = {'name': '', 'constituency': '', 'image_path': '', 'page_idx': page_idx}
            member_info = build_member_info(pdf_page, page, tomerge_imageidxs, image_idx)
            constituency, name, m['image_path'] = member_info
            if ',' in name:
                last_name, first_name = name.split(',', 1)
                name = f'{first_name.strip()} {last_name.strip()}'

            constituency = re.sub(r'^[\d]+', '', constituency).strip()
            print(f'{constituency:50} {name}')
                
            m['name'], m['constituency'] = name, constituency
            members.append(m)
    return members


def extract_council_members(doc, images_dir):

    def extract_image(pdf_path, page_idx):
        image_stub = images_dir / f'P-{page_idx}'
        cmd = f"pdfimages -f {page_idx+1} -l {page_idx+1} -png {str(pdf_path)} {str(image_stub)}"
        subprocess.check_call(cmd.split())
        return images_dir / f'P-{page_idx:03}.png'

    def line_in_image(line, ymin, ymax):
        return line and (ymin <= line.ymin <= ymax)

    def get_member_info(pdf_page, page, member_image):
        img_ymin = member_image.bounding_box[1]/pdf_page.height
        img_ymax = member_image.bounding_box[3]/pdf_page.height
        
        name_lines = [ln for ln in page.lines if line_in_image(ln, img_ymin, img_ymax)]

        name = ' '.join(ln.text_with_break() for ln in name_lines)
        return name
    
    member_start_page_idx = 41
    member_end_page_idx = 173
    
    pdf = pdfwrapper.open(doc.pdf_path)
    members = []
    for page_idx in range(member_start_page_idx, member_end_page_idx):
        pdf_page, page = pdf.pages[page_idx], doc.pages[page_idx]
        if not pdf_page.images:
            continue
        
        assert len(pdf_page.images) == 1
        image_path = extract_image(doc.pdf_path, page_idx)
        name = get_member_info(pdf_page, page, pdf_page.images[0])
        if ',' in name:
            last_name, first_name = name.split(',', 1)
            name = f'{first_name.strip()} {last_name.strip()}'


        print(name)
        member_info = {'name': name, 'image_path': str(image_path)}
        members.append(member_info)
    return members



@Vision.factory(
    "member_extractor",
    default_config={
        "output_dir": "output",
    },
)
class MemberExtractor:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / 'images'
        self.images_dir.mkdir(exist_ok=True)

    def __call__(self, doc):
        doc.add_extra_page_field("member_infos", ("noparse", "", ""))
        
        if doc.info['house'] == 'Assembly' and doc.info['doc_type'] == 'Members':
            assembly_dir = self.images_dir / 'Assembly' / Path(doc.pdf_name.replace('.pdf', ''))
            assembly_dir.mkdir(exist_ok=True, parents=True)
            doc.member_infos = extract_assembly_members(doc, assembly_dir)

        elif doc.info['house'] == 'Council' and doc.info['doc_type'] == 'Members':
            assembly_dir = self.images_dir / 'Council' / Path(doc.pdf_name.replace('.pdf', ''))
            assembly_dir.mkdir(exist_ok=True, parents=True)
            doc.member_infos = extract_council_members(doc, assembly_dir)
        return doc



"""
    def build_member_info(pdf_page, page, tomerge_images, image_idx):
        pdf_xmin = min(img.bounding_box[0] for img in tomerge_images)
        pdf_ymin = min(img.bounding_box[1] for img in tomerge_images)
        pdf_xmax = max(img.bounding_box[2] for img in tomerge_images)
        pdf_ymax = max(img.bounding_box[3] for img in tomerge_images)

        pil_images = [img.to_pil() for img in tomerge_images]
        
        merge_width = max(img.width for img in pil_images)
        x_scale =  merge_width/(pdf_xmax - pdf_xmin)

        merge_height = int(x_scale * (pdf_ymax-pdf_ymin))
        merge_image = Image.new('RGB', (merge_width, merge_height))
        
        for pdf_img, pil_img in zip(tomerge_images, pil_images):
            x, y = pdf_img.bounding_box[0] - pdf_xmin, pdf_img.bounding_box[1] - pdf_ymin
            merge_image.paste(pil_img, (0, int(y * x_scale)))

        images_path = images_dir / f'P{page.page_idx+1}-{image_idx+1}.jpg'
        merge_image.save(images_path)
        return [], [], images_path

"""
