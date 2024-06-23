"""

Comprehensive suite of image editors for vector and raster images.

"""

import os
import time
import multiprocessing
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path
from config import Config
from core.editors import get_fpaths
from core.editors.image import Image, ImageGroup
from core.editors.svg import SVG


class PDF:
    """
    Toolkit for processing a PDF
    """

    def __init__(self, pdf_path, out_dir=None, max_pages=30):
        """

        :param pdf_path:
        :type pdf_path:
        :param out_dir:
        :type out_dir:
        :param max_pages:
        :type max_pages:
        """
        self.out_dir = out_dir or Config.TEMP_DIR
        self.pdf_path = pdf_path
        self.pdf_dir, self.pdf_fname = os.path.dirname(pdf_path), os.path.basename(pdf_path)
        self.max_pages = max_pages
        self.bg_spread = './data/toolkit/pdf_to_layouts/in/open-bluespiral-book.png'
        self.bg_folded = './data/toolkit/pdf_to_layouts/in/bluepspiral-book-foldedleft.png'
        self.left_page_even = True

    @property
    def num_pages(self):
        """
        get the count of pages in the PDF
        :return:
        :rtype:
        """
        input_pdf = PdfReader(open(self.pdf_path, "rb"))
        return len(input_pdf.pages)

    def split(self, out_dir=None):
        """
        Split a multi-page pdf into a dir of single-page pdfs and return the list of absolute file paths
        :param out_dir:
        :type out_dir:
        :return:
        :rtype:
        """
        input_pdf = PdfReader(open(self.pdf_path, "rb"))
        out_dir = out_dir or self.out_dir
        out_list = []
        for i in range(len(input_pdf.pages)):
            output = PdfWriter()
            output.add_page(input_pdf.pages[i])
            temp_name = os.path.join(out_dir, os.path.basename(self.pdf_path).replace('.pdf', ''))
            out_fname = f"{temp_name}_{i:03}.pdf"
            out_list.append(out_fname)
            with open(out_fname, "wb") as outputStream:
                output.write(outputStream)
        return out_list

    def to_svgs(self, out_dir=None):
        """
        Convert a multi-page pdf into a directory of svgs
        :param out_dir:
        :type out_dir:
        :return:
        :rtype:
        """
        svgs = [SVG.from_pdf(target_pdf_path=each_pdf) for each_pdf in self.split(out_dir=out_dir)]
        # TODO - clean pdfs out of directory
        return svgs

    def to_image_group(self, first_idx=0, last_idx=None):
        """
        Turn a PDF into a raster ImageGroup
        :param first_idx:
        :type first_idx:
        :param last_idx:
        :type last_idx:
        :return:
        :rtype:
        """
        last_idx = last_idx or first_idx + 11
        images = convert_from_path(os.path.join(self.pdf_dir, self.pdf_fname),
                                   first_page=first_idx,
                                   last_page=last_idx,
                                   thread_count=2)
        return ImageGroup(image_list=[Image(img=img) for img in images])

    @staticmethod
    def crop_page_margins(page, uxuy_lxly_scale):
        """
        Crop the margins of a PdfReader PDF page and scale it back to size
        :param page:
        :type page:
        :param uxuy_lxly_scale:
        :type uxuy_lxly_scale:
        :return:
        :rtype:
        """
        page.mediabox.lower_left, page.mediabox.upper_right, scale = uxuy_lxly_scale
        page.scale_by(scale)
        return page

    @staticmethod
    def get_crop_margins(page, crop_percent, side='both'):
        """
        Get the margins to remove from all sides using the crop_percent
        :param page:
        :type page:
        :param crop_percent:
        :type crop_percent:
        :param side:
        :type side:
        :return:
        :rtype:
        """
        width, height = page.mediabox.upper_right
        w_diff, h_diff = float(width) * (crop_percent / 2), float(height) * (crop_percent / 2)
        scale = (width / (width - w_diff * 2))
        if side == 'left':
            return (w_diff * 2, h_diff), (width, height - h_diff), scale
        elif side == 'right':
            return (0, h_diff), (width - w_diff * 2, height - h_diff), scale
        else:
            return (w_diff, h_diff), (width - w_diff, height - h_diff), scale

    @staticmethod
    def crop_page(kwargs):
        """
        Thread-safe page cropping for pypdf2 pdf pages.
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        page, page_idx, crop_percent = kwargs['page'], int(kwargs['page_idx']), float(kwargs['crop_percent'])
        even_idx_right = kwargs.get('even_idx_right', True)
        if even_idx_right:
            side = 'right' if page_idx % 2 == 0 else 'left'
        else:
            side = 'left' if page_idx % 2 == 0 else 'right'
        uxuy_lxly_scale = PDF.get_crop_margins(page, crop_percent, side=side)
        page = PDF.crop_page_margins(page, uxuy_lxly_scale)
        return page_idx, page

    def crop_pdf_margins(self):
        """
        Crop the margins of a PDF on alternating sides.
        """
        page_crop_percent = 0.05

        in_dir = './data/toolkit/crop_pdf/in'
        out_dir = './data/toolkit/crop_pdf/out'
        pdf_list = get_fpaths(in_dir, 'pdf')

        for pdf_path in pdf_list:
            pdf_dir, pdf_fname = os.path.dirname(pdf_path), os.path.basename(pdf_path)
            pdf_out = os.path.join(out_dir, pdf_fname)

            start_time = time.time()
            pdf_reader = PdfReader(pdf_path)
            pdf_writer = PdfWriter()

            pool = multiprocessing.Pool(processes=6)
            page_params = [{'page': page, 'page_idx': idx, 'crop_percent': page_crop_percent}
                           for idx, page in enumerate(pdf_reader.pages)]
            pages = pool.map(self.crop_page, page_params)
            pool.close()
            pool.join()
            sorted_pages = sorted(pages, key=lambda tup: tup[0])
            [pdf_writer.add_page(page[1]) for page in sorted_pages]

            with open(pdf_out, 'wb') as output_file:
                pdf_writer.write(output_file)

    def sample_pdf_pages(self, page_list, pdf_writer=None):
        """
        Get the specified pages in a list from a PDF.
        :param page_list:
        :type page_list:
        :param pdf_writer:
        :type pdf_writer:
        :return:
        :rtype:
        """
        if pdf_writer is None:
            pdf_writer = PdfWriter()
        pdf = PdfReader(self.pdf_path)
        [pdf_writer.add_page(pdf.pages[page]) for page in page_list]
        return pdf_writer

    def process(self, out_fname, **kwargs):
        # Sample pages within and between pdfs to build the target PDF
        if 'pdf_list' in kwargs.keys():
            pass
        if 'sample_page_list' in kwargs.keys():
            pass
        # Crop margins, apply fixed crop, and rescale
        if 'crop_margin' in kwargs.keys():
            pass
        elif 'uxuy_lxly_scale' in kwargs.keys():
            pass
        # Export results in different formats
        if 'svg_out_dir' in kwargs.keys():
            pass
        if 'png_out_dir' in kwargs.keys():
            pass
        if 'pdf_fname' in kwargs.keys():
            pass
        return self


class PdfGroup:
    def __init__(self, pdf_list: list):
        self.pdf_list = pdf_list

    def sample(self, out_path, page_list):
        """
        Get a range of pages from each pdf in a folder
        :param out_path:
        :type out_path:
        :param page_list:
        :type page_list:
        :return:
        :rtype:
        """
        pdf_writer = PdfWriter()
        for each_pdf in self.pdf_list:
            pdf_writer = PDF(each_pdf).sample_pdf_pages(page_list, pdf_writer)
        with open(out_path, 'wb') as output_pdf:
            pdf_writer.write(output_pdf)
