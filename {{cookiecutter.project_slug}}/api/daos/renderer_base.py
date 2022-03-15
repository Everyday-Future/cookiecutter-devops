"""

Parsers, loaders, and transformers to help in the conversion of elements between svgs, website rendering,
and pdf rendering. These functions glue together other higher-level functions for rendering.

"""

import os
import re
import json
import multiprocessing
from PyPDF4 import PdfFileMerger
from PyPDF2 import PdfFileWriter, PdfFileReader
from jinja2 import Environment, BaseLoader, StrictUndefined
from api import global_config


def ordered_dedupe(seq):
    """
    Deduplicate a list while preserving its order.
    :param seq:
    :return:
    """
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def str_is_parametrized(target_str):
    """
    Determine if there are jinja2 parameters in the string
    :param target_str:
    :return:
    """
    return '{' + '{' in target_str or '{' + '%' in target_str


def get_newline_str(do_escape_n=True, do_br_tag=True):
    """
    Get the string to be used to indicate newlines in documents. Return a space if neither are specified.
    :param do_escape_n:
    :param do_br_tag:
    :return:
    """
    if do_escape_n is False and do_br_tag is False:
        return " "
    newline_str = ""
    if do_escape_n:
        newline_str += "\n"
    if do_br_tag:
        newline_str += "<br/>"
    return newline_str


def newline_prep(target_str, do_escape_n=True, do_br_tag=True):
    """
    Set up the newlines in a block of text so that they will be processed correctly by Reportlab and logging
    :param target_str:
    :param do_escape_n:
    :param do_br_tag:
    :return:
    """
    newline_str = get_newline_str(do_escape_n=do_escape_n, do_br_tag=do_br_tag)
    # Save the newline characters that appear together to a temporary tag
    target_str = target_str.replace("\n<br/>", "<newline>").replace("<br/>\n", "<newline>")
    # Change the characters that appear individually
    target_str = target_str.replace("\n", "<newline>").replace("<br/>", "<newline>")
    target_str = target_str.replace("\r", "<newline>")
    # Set everything to the target newline string
    target_str = target_str.replace("<newline><newline>", "<newline>").replace("<newline>", newline_str)
    return target_str


def replace_newline(target_str, do_escape_n=True, do_br_tag=True, do_strip=True, double_newline=True):
    """
    Replace all of the newline characters in the template with the specified version.
    :param target_str: String to be edited
    :param do_escape_n: Add \n tag for txt and csv files
    :param do_br_tag: Add <br/> tag for ReportLab
    :param do_strip: Strip off whitespace at the beginning and end of lines
    :param double_newline: (default==True) Replace newlines with double-newlines
    :return:
    """
    prepped_str = newline_prep(target_str, do_escape_n=do_escape_n, do_br_tag=do_br_tag)
    newline_str = get_newline_str(do_escape_n=do_escape_n, do_br_tag=do_br_tag)
    str_list = prepped_str.split(newline_str)
    if double_newline is True and newline_str != " ":
        newline_str = newline_str + newline_str
    if do_strip:
        return newline_str.join([x.strip() for x in str_list if x.strip()])
    else:
        return newline_str.join([x for x in str_list if x.strip()])


def replace_citations(target_str, is_blog=False):
    """
    replace all shorthand citations {14} in a string with either Jinja2 citation indicators or
    superscript citations to render them as they appear in copy.
    :param target_str: String to be edited
    :param is_blog: boolean (default False) - return Jinja2 citation if true. Return superscript otherwise.
    :return: String with citations as {{ citation(14) }} if is_blog==True else <sup>14</sup>
    """
    target_str = target_str.replace('{{citation(', '{').replace(')}}', '}')
    # Find all citations as {149} or { 14 } or {1 } etc...
    citation_list = re.findall(r'{(\s*\d+\s*)}', target_str)
    # Drop the first and last characters to get citation numbers.
    citation_idx_list = [int(cit.strip()) for cit in citation_list]
    for idx, citation in enumerate(citation_list):
        # Replace the citation shorthand with the proper markdown.
        if is_blog is True:
            target_str = target_str.replace(citation, f'{{ citation({citation_idx_list[idx]}) }}')
        else:
            target_str = target_str.replace("{" + citation + "}", f'<sup>{citation_idx_list[idx]}</sup>')
    return target_str


def replace_image_link(target_str):
    """
    Replace the shorthand of an image link { image.jpg } with the full link {{ img_tag("image.jpg") | safe }}
    :param target_str: String with images in it to be edited
    :return: string with images formatted as {{ img_tag("image.jpg") | safe }}
    """
    # Find all image links as {image.jpg} or { image.jpg } etc...
    image_list = re.findall(r'{(\s*\w+\.\w+\s*)}', target_str)
    # Drop the first and last characters to get citation numbers.
    img_name_list = [cit.strip() for cit in image_list]
    for idx, img in enumerate(image_list):
        # Replace the citation shorthand with the proper markdown.
        target_str = target_str.replace(img, f'{{ img_tag("{img_name_list[idx]}") | safe }}')
    return target_str


def edit_string(in_text, story: dict):
    """
    Simple wrapper for editing a string with Jinja2 templating
    :param in_text: The string that will be edited
    :param story: The dictionary of content to replace, sometimes including {"story": Story()}
    :return:
    """
    # Try to catch all parsing issues in unit and integration testing.
    # but use less strict parsing in production
    if global_config.DEBUG_MODE is False:
        template = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True).from_string(in_text)
    else:
        template = Environment(loader=BaseLoader(), trim_blocks=True, lstrip_blocks=True,
                               undefined=StrictUndefined).from_string(in_text)
    if not isinstance(story, dict):
        story = {"story": story}
    return template.render(**story)


def is_json_serializable(x):
    """
    Check if an object is serializable by serializing it and catching exceptions
    :param x:
    :type x:
    :return:
    :rtype:
    """
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False


def validate_param(value, invalid_list=None):
    """
    Ensure the param is a valid value by checking that it's not present in a list of invalid values.
    :param value: Param value to be tested
    :type value: string, list, or object
    :param invalid_list: (optional) List of values to be considered invalid
    :type invalid_list: list
    :return: Param value if valid, else None
    :rtype: string, list, or object
    """
    invalid_list = invalid_list or [None, '', ' ', 0, '0', [], [''], {}, {''}]
    if value not in invalid_list:
        return value
    else:
        return None


def process_marker_fonts(prompt):
    """
    Replace <s> with sharpie font sections
    """
    prompt = prompt.replace('<s>', '<font name="PermanentMarker" color="#B1BDC3">')
    prompt = prompt.replace('</s>', '</font>')
    if '<font' in prompt and '</font>' not in prompt:
        prompt = prompt + '</font>'
    return prompt


def book_from_pdf_list(pdf_fnames, out_fname):
    """
    Merge a list of pdfs into a single document.
    This is used to merge flowable documents with different svg styling or templating.
    """
    merger = PdfFileMerger()
    for fname in pdf_fnames:
        # Unroll nested lists if they come up
        if isinstance(fname, (tuple, list)):
            for sub_fname in fname:
                with open(sub_fname, "rb") as pdfb:
                    merger.append(pdfb)
        else:
            with open(fname, "rb") as pdfb:
                merger.append(pdfb)
    with open(out_fname, "wb") as fb:
        merger.write(fb)
    merger.close()
    return out_fname


def split_pdf(target_pdf_fname):
    """
    Open a PDF, split it into single-page PDFs, then return the list.
    :param target_pdf_fname:
    :type target_pdf_fname:
    :return:
    :rtype:
    """
    input_pdf = PdfFileReader(open(target_pdf_fname, "rb"))
    out_list = []
    for i in range(input_pdf.numPages):
        output = PdfFileWriter()
        output.addPage(input_pdf.getPage(i))
        temp_name = os.path.join(global_config.TEMP_DIR, os.path.basename(target_pdf_fname).replace('.pdf', ''))
        out_fname = f"{temp_name}_{i:03}.pdf"
        out_list.append(out_fname)
        with open(out_fname, "wb") as outputStream:
            output.write(outputStream)
    return out_list


def crop_page_margins(page, uxuy_lxly_scale):
    """ Crop the margins of a PdfFileReader PDF page and scale it back to size """
    page.mediaBox.lowerLeft, page.mediaBox.upperRight, scale = uxuy_lxly_scale
    page.scaleBy(scale)
    return page


def get_crop_margins(page, crop_percent, side='both'):
    """ Get the margins to remove from all sides using the crop_percent """
    width, height = page.mediaBox.upperRight
    w_diff, h_diff = float(width) * (crop_percent / 2), float(height) * (crop_percent / 2)
    scale = (width / (width - w_diff * 2))
    if side == 'left':
        return (w_diff * 2, h_diff), (width, height - h_diff), scale
    elif side == 'right':
        return (0, h_diff), (width - w_diff * 2, height - h_diff), scale
    else:
        return (w_diff, h_diff), (width - w_diff, height - h_diff), scale


def crop_page(kwargs):
    """ Thread-safe page cropping for pypdf2 pdf pages."""
    page, page_idx, crop_percent = kwargs['page'], int(kwargs['page_idx']), float(kwargs['crop_percent'])
    even_idx_right = kwargs.get('even_idx_right', True)
    if even_idx_right:
        side = 'right' if page_idx % 2 == 0 else 'left'
    else:
        side = 'left' if page_idx % 2 == 0 else 'right'
    uxuy_lxly_scale = get_crop_margins(page, crop_percent, side=side)
    page = crop_page_margins(page, uxuy_lxly_scale)
    return page_idx, page


def crop_pdf_margins(target_pdf, page_crop_percent=0.05):
    """
    Crop the margins of a PDF on alternating sides.
    """
    pdf_dir, pdf_fname = os.path.dirname(target_pdf), os.path.basename(target_pdf)
    pdf_out = os.path.join(global_config.TEMP_DIR, pdf_fname)
    pdf_reader = PdfFileReader(target_pdf)
    pdf_writer = PdfFileWriter()
    pool = multiprocessing.Pool(processes=6)
    page_params = [{'page': page, 'page_idx': idx, 'crop_percent': page_crop_percent}
                   for idx, page in enumerate(pdf_reader.pages)]
    pages = pool.map(crop_page, page_params)
    pool.close()
    pool.join()
    sorted_pages = sorted(pages, key=lambda tup: tup[0])
    [pdf_writer.addPage(page[1]) for page in sorted_pages]
    with open(pdf_out, 'wb') as output_file:
        pdf_writer.write(output_file)
    return pdf_out


def get_size_str(grid_width, grid_height, book_size='digest'):
    """
    Get a string that matches the size of a component/composite
    :param grid_width:
    :type grid_width:
    :param grid_height:
    :type grid_height:
    :param book_size:
    :type book_size:
    :return:
    :rtype:
    """
    return f"{book_size}_{grid_width}x{grid_height}"


class RenderMode:
    """
    Enumerable for types of Rendering - printable, book, sheet, etc...
    """
    printable = 'printable'
    book = 'book'
    pdf = 'pdf'
    all = 'all'

    def __init__(self, mode_name='pdf'):
        self.mode = mode_name

    def list(self):
        if self.mode == 'printable':
            return [self.printable]
        elif self.mode == 'book':
            return [self.book]
        elif self.mode == 'pdf':
            return [self.printable, self.book]
        elif self.mode == 'all':
            return [self.printable, self.book]
        else:
            return []
