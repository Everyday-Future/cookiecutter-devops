"""

Comprehensive suite of image editors for vector and raster images.

"""

import os
import re
import subprocess
from collections import Counter
from functools import lru_cache
from difflib import SequenceMatcher
from svglib.svglib import svg2rlg
from scour.scour import scourString
from reportlab.graphics import renderPDF, renderPM
from urllib.request import urlopen
from PIL import Image as PilImage
from config import Config
from core.adapters.parser import edit_string
from core.editors.image import Image


@lru_cache(maxsize=3200)
def get_file_txt_remote(fname):
    target_url = Config.CDN + '/' + fname
    return scourString(urlopen(target_url).replace('\n', '').replace('\t', ''))


def get_file_txt_local(fname):
    if not "http" in fname:
        with open(os.path.join(Config.TEST_ASSETS_DIR, os.path.basename(fname)), 'r') as fp:
            return scourString(fp.read().replace('\n', '').replace('\t', ''))
    else:
        return None


class SVGExtractor:
    """
    JSON representation of an SVG file for DynamicSVG rendering.
    """

    def __init__(self, fname):
        self.fname = fname
        self.path_regex = '<path[^>]+>'
        self.line_regex = '<line[^>]+>'
        self.rect_regex = '<rect[^>]+>'
        self.text_regex = '<text(?<=<text).*?(?=<\/text>)<\/text>'
        self.tspan_regex = '<tspan[^>]*>[^>]+tspan>'
        self.style_regex = '<style[^>]*>[^>]+>'
        # Get it from the inserts dir or fail over to the image CDN
        self.txt = get_file_txt_local(fname)
        if self.txt is None:
            self.txt = get_file_txt_remote(fname)

    @staticmethod
    def get_attribute(attr_name, target_str, default=None):
        try:
            out_str = re.findall(f'{attr_name}="[^"]*"', target_str)[0]
            return out_str.replace(f'{attr_name}="', '').replace('"', '')
        except IndexError as err:
            if default is not None:
                return default
            else:
                raise

    def get_path_markdown(self, path_str):
        out_md = {'type': 'path',
                  'd': re.findall('d="[mM][^"]+"', path_str)[0].replace('d="', '').replace('"', '')}
        if 'style' in path_str:
            out_md['style'] = self.get_attribute('style', path_str)
        if 'class' in path_str:
            out_md['class'] = self.get_attribute('class', path_str)
        return out_md

    def get_paths(self):
        paths = re.findall(self.path_regex, self.txt)
        return [self.get_path_markdown(txt) for txt in paths]

    def get_line_markdown(self, line_str):
        out_md = {'type': 'line',
                  'x1': self.get_attribute('x1', line_str, default=0),
                  'x2': self.get_attribute('x2', line_str, default=0),
                  'y1': self.get_attribute('y1', line_str, default=0),
                  'y2': self.get_attribute('y2', line_str, default=0)}
        if 'style' in line_str:
            out_md['style'] = self.get_attribute('style', line_str)
        if 'class' in line_str:
            out_md['class'] = self.get_attribute('class', line_str)
        return out_md

    def get_lines(self):
        lines = re.findall(self.line_regex, self.txt)
        return [self.get_line_markdown(txt) for txt in lines]

    def get_rect_markdown(self, rect_str):
        out_md = {'type': 'rect',
                  'x': self.get_attribute('x', rect_str, 0),
                  'y': self.get_attribute('y', rect_str, 0),
                  'width': self.get_attribute('width', rect_str),
                  'height': self.get_attribute('height', rect_str)}
        if 'style' in rect_str:
            out_md['style'] = self.get_attribute('style', rect_str)
        if 'class' in rect_str:
            out_md['class'] = self.get_attribute('class', rect_str)
        return out_md

    def get_rects(self):
        rects = re.findall(self.rect_regex, self.txt)
        return [self.get_rect_markdown(txt) for txt in rects]

    def get_text_markdown(self, text_str):
        out_md = {'type': 'text'}
        if '<tspan' in text_str and 'tspan>' in text_str:
            out_md['text'] = [re.findall('>[^<]+', txt)[0].replace('>', '') for txt in
                              re.findall(self.tspan_regex, text_str)]
            if len(out_md['text'][0]) > 1:
                out_md['text'] = ' '.join(out_md['text'])
            else:
                out_md['text'] = ''.join(out_md['text'])
        else:
            out_md['text'] = re.findall('>[^<]+', re.findall('<text[^>]+>[^>]+text>', text_str)[0])[0].replace('>', '')
        if 'transform' in text_str:
            out_md['transform'] = self.get_attribute('transform', text_str)
        if 'style' in text_str:
            out_md['style'] = self.get_attribute('style', text_str)
        if 'class' in text_str:
            out_md['class'] = self.get_attribute('class', text_str)
        return out_md

    def get_texts(self):
        texts = re.findall(self.text_regex, self.txt)
        return [self.get_text_markdown(txt) for txt in texts]

    def get_style(self):
        styles = re.findall(self.style_regex, self.txt)
        if len(styles) > 0:
            return styles[0]
        else:
            return ''

    def get_style_unfilled(self):
        """
        Change the styles into the transparent starting style for the animations
        :return:
        :rtype:
        """
        _hex_fill_colour = re.compile(r'fill:#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b')
        _hex_stroke_colour = re.compile(r'stroke:#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b')
        style = re.sub(_hex_fill_colour, 'fill:transparent', self.get_style())
        style = re.sub(_hex_stroke_colour, 'stroke:transparent', style)
        return style

    def get_viewbox(self):
        return self.get_attribute('viewBox', self.txt)

    def get_data(self):
        return {'style': self.get_style(),
                'styleUnfilled': self.get_style_unfilled(),
                'viewbox': self.get_viewbox(),
                'lines': self.get_paths() + self.get_lines() + self.get_rects(),
                'texts': self.get_texts()}


class SVG:
    """
    Toolkit for processing an SVG
    """

    def __init__(self, fpath):
        self.fpath = fpath

    def load(self):
        """
        Get the target svg file as a txt string
        :return:
        :rtype:
        """
        with open(self.fpath, 'r') as fp:
            return fp.read()

    def save(self, new_txt, target_fpath=None):
        """
        Save a txt string to a target path or the SVG.fpath
        :return:
        :rtype:
        """
        target_fpath = target_fpath or self.fpath
        with open(target_fpath, 'w') as fp:
            return fp.write(new_txt)

    # noinspection Restricted_Python_calls
    @classmethod
    def from_pdf(cls, target_pdf_path, target_svg_path=None):
        target_svg_path = target_svg_path or target_pdf_path.replace(".pdf", ".svg")
        subprocess.Popen(['inkscape.exe',
                          '--without-gui',
                          f'--export-plain-svg={target_svg_path}',
                          f'{target_pdf_path}'],
                         executable=Config.INKSCAPE_DIR)
        return cls(fpath=target_svg_path)

    @lru_cache()
    def get_size(self, dpi=72.0):
        """
        Render an SVG into a 72dpi png and get its dimensions in px.
        :return:
        :rtype:
        """
        output_path = self.fpath.replace(".svg", ".png")
        self.to_png(output_path, dpi=dpi)
        im = PilImage.open(output_path)
        width, height = im.size
        return width, height

    @property
    def color_palette(self):
        """ Extract the color palette in order of use frequency from an svg. """
        with open(self.fpath, 'r') as fp:
            svg_txt = fp.read()
        all_colors = re.findall(
            r'\:(?:(?!(?:\;|\n|\r))[\w\W])*?\#((?:[a-fA-F0-9]{3}){1,2})(?:(?!(?:\;|\n|\r))[\w\W])*?(?:\;|\n|\r)',
            svg_txt)
        all_colors = [color_str.upper() for color_str in all_colors]
        # sort colors by their frequency in the SVG to try to make matches based on freq
        color_freq = Counter(all_colors)
        color_palette = list(dict(sorted(color_freq.items(), key=lambda item: -item[1])).keys())
        color_palette = [f"#{col}" for col in color_palette]
        return color_palette

    def remap_colors(self, color_map: dict, out_fname):
        """
        Consume a map of colors and emit an svg with those colors re-mapped.
        :param color_map: Map of {in_color: out_color, ...}
        :type color_map: dict
        :param out_fname:
        :type out_fname:
        :return:
        :rtype:
        """
        # Map all colors to intermediate values, then convert all to prevent color confusion
        with open(self.fpath, 'r') as fp:
            svg_txt = fp.read()
        # Replace all colors with lowercase stand-ins
        for in_color, out_color in color_map.items():
            svg_txt = svg_txt.replace(in_color.upper(), out_color.upper())
            svg_txt = svg_txt.replace(in_color.lower(), out_color.upper())
        with open(out_fname, 'w') as fp:
            fp.write(svg_txt)

    @staticmethod
    def similarity(svg_fpath_1, svg_fpath_2):
        """
        Compare the text difference between two svg files
        :param svg_fpath_1:
        :type svg_fpath_1:
        :param svg_fpath_2:
        :type svg_fpath_2:
        :return:
        :rtype:
        """
        with open(svg_fpath_1, 'r') as fp:
            svg_txt_1 = fp.read()
        with open(svg_fpath_2, 'r') as fp:
            svg_txt_2 = fp.read()
        return SequenceMatcher(None, svg_txt_1, svg_txt_2).ratio()

    def fill_template(self, story_or_dict, out_fname):
        """
        Fill out the Jinja2 template for the SVG.
        :param story_or_dict:
        :type story_or_dict:
        :param out_fname:
        :type out_fname:
        :return:
        :rtype:
        """
        with open(self.fpath, 'r') as fp:
            svg_txt = fp.read()
        svg_txt = edit_string(svg_txt, story_or_dict)
        with open(out_fname, 'w') as fp:
            fp.write(svg_txt)

    @staticmethod
    def image_to_svg_primitive(in_img: Image, in_fpath, out_fpath, bg_color=None):
        # Save the image without transparency for better rendering
        in_img.transparency_to_bg_color(bg_color=bg_color)
        temp_fpath = os.path.join(Config.TEMP_DIR, os.path.basename(in_fpath))
        in_img.save(temp_fpath)
        # Create svg primitive
        subprocess.call(f'docker run --rm '
                        f'-v {os.path.dirname(os.path.abspath(temp_fpath))}:/input '
                        f'-v {os.path.dirname(os.path.abspath(out_fpath))}:/output '
                        f'renyufu/primitive app '
                        f'-i /input/{os.path.basename(os.path.abspath(temp_fpath))} '
                        f'-o /output/{os.path.basename(os.path.abspath(out_fpath))} '
                        f'-n 100 -bg ffffff -r 256')
        svg = SVG(out_fpath)
        svg.optimize(out_fpath)
        return svg

    def optimize(self, out_fname):
        target_text = self.load()
        out_str = scourString(target_text.replace('\n', '').replace('\t', ''),
                              options={'--enable-comment-stripping': True,
                                       '--indent': None,
                                       '--shorten-ids': True,
                                       '--enable-id-stripping': True})
        self.save(new_txt=out_str, target_fpath=out_fname)
        return out_str

    # Get the dimensions of the files by exporting to png
    def to_png(self, out_fname=None, dpi=72.0, scale=1.0, to_transparent=False):
        """
        Render an svg into a png file with optional scaling and dpi params.
        :param out_fname:
        :type out_fname:
        :param dpi:
        :type dpi:
        :param scale:
        :type scale:
        :param to_transparent:
        :type to_transparent:
        :return:
        :rtype:
        """
        out_fname = out_fname or self.fpath.replace(".svg", ".png")
        drawing = svg2rlg(self.fpath)
        drawing.scale((dpi / 72.0) * scale, (dpi / 72.0) * scale)
        renderPM.drawToFile(drawing, out_fname, 'PNG', dpi=dpi * scale)
        if to_transparent is True:
            Image(img_fpath=out_fname).bg_to_transparent().save(out_fname)
        return out_fname

    def to_pdf(self, out_fname=None):
        """
        Render an SVG image into a PDF page
        :param out_fname:
        :type out_fname:
        :return:
        :rtype:
        """
        out_fname = out_fname or self.fpath.replace(".svg", ".pdf")
        drawing = svg2rlg(self.fpath)
        if drawing is not None:
            renderPDF.drawToFile(drawing, out_fname)

    def to_json(self):
        svge = SVGExtractor(fname=self.fpath)
        return svge.get_data()

    def process(self, out_fname, **kwargs):
        # Apply transformations on the base image
        if 'story' in kwargs.keys():
            pass
        if 'color_map' in kwargs.keys():
            pass
        if 'do_optimize' in kwargs.keys():
            pass
        if 'png_fname' in kwargs.keys():
            pass
        if 'pdf_fname' in kwargs.keys():
            pass
        return self


class SvgGroup:
    def __init__(self, svg_list):
        if isinstance(svg_list[0], SVG):
            self.svg_list = svg_list
        elif isinstance(svg_list[0], str):
            self.svg_list = [SVG(each_svg) for each_svg in svg_list]

    @property
    def count(self):
        return len(self.svg_list)

    def deduplicate_svgs(self, window_size=10, start_padding=10, difference_threshold=0.01):
        """
        Given a list of svg filenames, move a window across them and delete each target if one of the other
        svgs is within a threshold difference %.
        :param window_size: Size of the window for each svg to be compared to previous
        :type window_size: int
        :param start_padding: Deadband at the beginning of the list to keep all. Should be >= window size
        :type start_padding: int
        :param difference_threshold: Difference is required to be less than this to be kept
        :type difference_threshold: float
        :return: Reduced length list of svgs
        :rtype: list
        """
        keep_idx = [True] * len(self.svg_list)
        # Ensure that the window size is at least as long as the list
        window_size = min(window_size, self.count)
        # Ensure that the start padding is at least as long as the window size
        start_padding = max(start_padding, window_size)
        for target_idx in range(start_padding, self.count):
            target_fpath = self.svg_list[target_idx].fpath
            sims = [SVG.similarity(target_fpath, window.fpath) for window
                    in self.svg_list[target_idx - window_size: target_idx]]
            max_sim = max(sims)
            if max_sim > 0.99:
                keep_idx[target_idx] = False
        self.svg_list = [svg for idx, svg in enumerate(self.svg_list) if keep_idx[idx] is True]
        return self


class SVGDAO:
    """
    Get interpretations of svgs
    """
    @classmethod
    def get(cls, name):
        """
        Get an SVG Extractor object for an SVG in the CDN
        :param name:
        :type name:
        :return:
        :rtype:
        """
        return SVGExtractor(name)

    @classmethod
    def get_data(cls, name):
        """
        Get the data from an SVG in the CDN
        :param name:
        :type name:
        :return:
        :rtype:
        """
        return cls.get(name).get_data()
