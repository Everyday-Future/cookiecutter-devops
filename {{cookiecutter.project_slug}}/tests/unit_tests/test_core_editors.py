import os
import unittest
import warnings
import PIL.Image as PilImage
from PyPDF2 import PdfReader, PdfWriter
from config import Config
from core.editors import get_fpaths
from core.editors.forms import sanitize_input, sanitize_input_basic
from core.editors.color import Color
from core.editors.svg import SVG, SvgGroup
from core.editors.image import Image, ImageGroup, get_image_group
from core.editors.pdf import PDF, PdfGroup


class EditorsBaseCase(unittest.TestCase):
    def setUp(self) -> None:
        warnings.simplefilter("ignore")

    @staticmethod
    def get_asset_fpath(fname):
        return os.path.join(Config.TEST_ASSETS_DIR, fname)

    def compare_to_truth(self, target_img, truth_fname):
        ground_truth = Image(img_fpath=os.path.join(Config.TEST_ASSETS_DIR, truth_fname))
        return Image.similarity(target_img.img, ground_truth.img)


class EditorsCase(unittest.TestCase):
    def test_get_fpaths(self):
        self.assertEqual({'book_from_pdf_list.pdf', 'music.pdf', 'tablature.pdf'},
                         set([os.path.basename(path) for path in
                              get_fpaths(Config.TEST_ASSETS_DIR, filetype='pdf')]))
        self.assertEqual({'db_uploader-coupon.pkl', 'test_transparency_to_bg_color.jpeg'},
                         set([os.path.basename(path) for path in
                              get_fpaths(Config.TEST_ASSETS_DIR, filetype_list=['jpeg', 'pkl'])]))


class FormsCase(unittest.TestCase):
    def test_sanitize_inputs(self):
        self.assertEqual('1234.@._.blah.,. .blah.-._.',
                         sanitize_input('1234!@#$%^&*()_:"\'<>?{}blah|,./ ;[blah]\-=_+)'))
        self.assertEqual('whitespace', sanitize_input('   whitespace    '))
        allowed = '1234567890QWERTYUIOPASDF  GHJKLZXCVBNM.,.qwertyuiopasdfghjklzxcvbnm'
        self.assertEqual(allowed, sanitize_input(allowed))

    def test_sanitize_inputs_basic(self):
        self.assertEqual('1234!@#$%^&*()_:..?{}blah|,./ .[blah]\-=_+)',
                         sanitize_input_basic('1234!@#$%^&*()_:"\'<>?{}blah|,./ ;[blah]\-=_+)'))
        self.assertEqual('whitespace', sanitize_input_basic('   whitespace    '))
        allowed = '1234567890QWERTYUIOPASDF  GHJKLZXCVBNM.,:qwertyuiopasdfghjklzxcvbnm'
        self.assertEqual(allowed, sanitize_input_basic(allowed))


class ColorCase(EditorsBaseCase):
    def test_init(self):
        color = Color((255, 255, 255))
        self.assertEqual((255, 255, 255), color.value)
        color = Color('#FF00FF')
        self.assertEqual((255, 0, 255), color.value)
        color = Color('#FFFFFF00')
        self.assertEqual((255, 255, 255, 0), color.value)

    def test_hex_to_rgb(self):
        result = Color.hex_to_rgb('#00FF00')
        self.assertEqual((0, 255, 0), result)

    def test_hex_to_rgba(self):
        result = Color.hex_to_rgba('#00FF00FF')
        self.assertEqual((0, 255, 0, 255), result)

    def test_parse_hex(self):
        result = Color.parse_hex('#00FF00')
        self.assertEqual((0, 255, 0), result)
        result = Color.parse_hex('#00FF000F')
        self.assertEqual((0, 255, 0, 15), result)

    def test_hex_to_hsv(self):
        result = Color.hex_to_hsv('#000000')
        self.assertEqual((0, 0, 0), result)
        result = Color.hex_to_hsv('#FFFFFF')
        self.assertEqual((0.0, 0.0, 255), result)
        result = Color.hex_to_hsv('#FF00FF')
        self.assertEqual((0.8333333333333334, 1.0, 255), result)

    def test_rgba_to_rgb(self):
        result = Color.rgba_to_rgb((255, 0, 255, 255))
        self.assertEqual((255, 0, 255), result)
        result = Color.rgba_to_rgb((255, 0, 255, 0))
        self.assertEqual((255, 0, 255), result)

    def test_rgb_to_hsv(self):
        result = Color.rgb_to_hsv((255, 255, 255))
        self.assertEqual((0.0, 0.0, 255), result)
        result = Color.rgb_to_hsv((255, 0, 255))
        self.assertEqual((0.8333333333333334, 1.0, 255), result)

    def test_rgb_to_hex(self):
        result = Color.rgb_to_hex((255, 0, 255))
        self.assertEqual('#FF00FF', result)

    def test_rgba_to_hex(self):
        result = Color.rgba_to_hex((255, 0, 255, 255))
        self.assertEqual('#FF00FFFF', result)

    def test_hsv_to_rgb(self):
        result = Color.hsv_to_rgb((0.0, 0.0, 0))
        self.assertEqual((0, 0, 0), result)
        result = Color.hsv_to_rgb((0.5, 0.5, 255))
        self.assertEqual((127.5, 255.0, 255), result)

    def test_hsv_to_hex(self):
        result = Color.hsv_to_hex((1.0, 0.0, 255))
        self.assertEqual('#FFFFFF', result)
        result = Color.hsv_to_hex((0.5, 0.5, 255))
        self.assertEqual('#7FFFFF', result)


class SVGCase(EditorsBaseCase):
    def setUp(self) -> None:
        super(SVGCase, self).setUp()
        self.static_svg = self.get_asset_fpath('organizer-digest_1x2.svg')
        self.template_svg = self.get_asset_fpath('custom_time_blocking-digest_2x2.svg')
        self.from_pdf = self.get_asset_fpath('music.pdf')
        self.opaque_image = self.get_asset_fpath('CallsToMake_wide.png')

    def test_init(self):
        # SVG without any templating
        svg = SVG(fpath=self.static_svg)
        self.assertTrue(isinstance(svg, SVG))
        # SVG that is expecting Jinja template injection
        svg = SVG(fpath=self.template_svg)
        self.assertTrue(isinstance(svg, SVG))

    def test_from_pdf(self):
        try:
            svg = SVG.from_pdf(self.from_pdf)
            self.assertTrue(isinstance(svg, SVG))
        except FileNotFoundError as err:
            print(f'WARNING - Inkscape not found at {Config.INKSCAPE_DIR} - {err}')

    @unittest.skip('re-enable after installing Cairo for reportlab')
    def test_get_size(self):
        svg = SVG(fpath=self.static_svg)
        svg_size = svg.get_size()
        self.assertEqual((153, 144), svg_size)
        svg_size = svg.get_size(dpi=300)
        self.assertEqual((638, 600), svg_size)

    def test_get_color_palette(self):
        svg = SVG(fpath=self.static_svg)
        palette = svg.color_palette
        self.assertEqual(['#6A7B84', '#6B7C85'], palette)

    def test_remap_colors(self):
        palettes = {'amuse': ['#E5BD5E', '#E66156', '#EAE4DE', '#FFFFFF', '#E57A59'],
                    'athlete1': ['#E66156', '#6B7B85', '#CDDBDF', '#FFFFFF', '#DC9F91'],
                    'athlete2': ['#6B7B85', '#E66156', '#CDDBDF', '#333333', '#FFFFFF'],
                    'journal': ['#6A7B84', '#6B7C85', '#E66156', '#CDDBDF', '#7A8992'],
                    'notebook': ['#C2B59B', '#E66156', '#6B7B85', '#DE7865', '#D58D75'],
                    'planner': ['#6B7B85', '#E66156', '#CDDBDF', '#EAE4DE', '#AEBEC4'],
                    'travel': ['#444A47', '#E66156', '#CDDBDF', '#6B7B85', '#576163']}
        for pal_name in palettes.keys():
            color_map = {planner_col: athlete_col for planner_col, athlete_col in
                         zip(palettes['journal'], palettes[pal_name])}
            svg = SVG(fpath=self.static_svg)
            svg.remap_colors(color_map, out_fname=os.path.join(Config.TEST_GALLERY_DIR,
                                                               f'test_remap_colors-{pal_name}.svg'))

    def test_similarity(self):
        try:
            svg_1 = SVG(fpath=self.static_svg)
            svg_2 = SVG(fpath=self.template_svg)
            sim = SVG.similarity(svg_1.fpath, svg_2.fpath)
            self.assertEqual(0.07500142263699994, sim)
            sim = SVG.similarity(svg_1.fpath, svg_1.fpath)
            self.assertEqual(1.0, sim)
        except FileNotFoundError as err:
            print(f'WARNING - Inkscape not found at {Config.INKSCAPE_DIR} - {err}')

    def test_fill_template(self):
        svg = SVG(fpath=self.template_svg)
        svg.fill_template(story_or_dict={'wake_time': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 18],
                                         'wake_ampm': ['am', 'am', 'am', 'am', 'am', 'am', 'am', 'am', 'am', 'am',
                                                       'am', 'am', 'pm', 'pm', 'pm', 'pm', 'pm', 'pm', 'pm', 'pm',
                                                       'pm', 'pm', 'pm', 'pm', 'pm', 'pm', 'pm', 'pm', 'pm', 'pm']},
                          out_fname=os.path.join(Config.TEST_GALLERY_DIR, 'template.svg'))
        self.assertTrue(os.path.isfile(os.path.join(Config.TEST_GALLERY_DIR, 'template.svg')))

    def test_optimize(self):
        svg = SVG(fpath=self.static_svg)
        out_fname = os.path.join(Config.TEST_GALLERY_DIR, 'test_optimize.svg')
        svg.optimize(out_fname=out_fname)
        self.assertTrue(os.path.isfile(out_fname))

    @unittest.skip(f"requires Docker to run, therefore it is not part of the normal test suite")
    def test_to_svg_primitive(self):
        img = Image(img_fpath=self.opaque_image)
        out_path = os.path.join(Config.TEST_GALLERY_DIR, 'test_to_svg_primitive.svg')
        SVG.image_to_svg_primitive(in_img=img, in_fpath=self.opaque_image, out_fpath=out_path)
        self.assertTrue(os.path.isfile(out_path))

    @unittest.skip('re-enable after installing Cairo for reportlab')
    def test_to_png(self):
        svg = SVG(fpath=self.static_svg)
        out_fname = os.path.join(Config.TEST_GALLERY_DIR, 'SVG.test_to_png.svg')
        svg.to_png(out_fname=out_fname)
        self.assertTrue(os.path.isfile(out_fname))
        # TODO - Change dpi
        # TODO - Rescale

    def test_to_pdf(self):
        svg = SVG(fpath=self.static_svg)
        out_fname = os.path.join(Config.TEST_GALLERY_DIR, 'svg_to_png.svg')
        svg.to_pdf(out_fname=out_fname)
        self.assertTrue(os.path.isfile(out_fname))
        # TODO - Change dpi
        # TODO - Rescale


class SvgGroupCase(EditorsBaseCase):
    def setUp(self) -> None:
        super(SvgGroupCase, self).setUp()
        self.svg_list = [self.get_asset_fpath('organizer-digest_1x2.svg'),
                         self.get_asset_fpath('custom_time_blocking-digest_2x2.svg')]

    def test_init(self):
        svg_group = SvgGroup(svg_list=self.svg_list)
        self.assertTrue(isinstance(svg_group, SvgGroup))

    def test_count(self):
        svg_group = SvgGroup(svg_list=self.svg_list)
        self.assertEqual(2, svg_group.count)

    @unittest.skipIf(Config.BASIC_TESTS is True, "takes about 30 seconds to run")
    def test_deduplicate_svgs(self):
        svg_list = self.svg_list * 10
        svg_group = SvgGroup(svg_list=svg_list)
        self.assertEqual(20, svg_group.count)
        svg_group.deduplicate_svgs(window_size=4, start_padding=4)
        self.assertEqual(4, svg_group.count)


class ImageCase(EditorsBaseCase):
    def setUp(self) -> None:
        super(ImageCase, self).setUp()
        self.opaque_image = self.get_asset_fpath('CallsToMake_wide.png')
        self.transparent_image = self.get_asset_fpath('CallsToMake_wide_t.png')

    def test_init(self):
        # Non-transparent image
        img = Image(img_fpath=self.opaque_image)
        self.assertTrue(isinstance(img, Image))
        # Transparent image
        img = Image(img_fpath=self.transparent_image)
        self.assertTrue(isinstance(img, Image))

    def test_copy(self):
        img = Image(img_fpath=self.opaque_image)
        copy = img.copy()
        self.assertNotEqual(img, copy)
        self.assertEqual(img.img, copy.img)
        self.assertFalse(img.img is copy.img)

    def test_backup_restore(self):
        img = Image(img_fpath=self.opaque_image)
        img.backup()
        img.img = None
        img.img_fpath = None
        self.assertIsNone(img.img)
        self.assertIsNone(img.img_fpath)
        img.restore()
        self.assertIsNotNone(img.img)
        self.assertIsNotNone(img.img_fpath)

    def test_open_as_pil_image(self):
        pil_img = Image.open_as_pil_image(img_fpath=self.opaque_image)
        self.assertTrue(isinstance(pil_img, PilImage.Image))

    def test_properties(self):
        img = Image(img_fpath=self.opaque_image)
        self.assertEqual(324, img.width)
        self.assertEqual(144, img.height)
        self.assertEqual((324, 144), img.size)
        self.assertEqual('RGBA', img.format)
        self.assertEqual(False, img.is_transparent)
        self.assertEqual((255, 255, 255, 0), img.bg_color)
        img = Image(img_fpath=self.transparent_image)
        self.assertEqual(3240, img.width)
        self.assertEqual(1440, img.height)
        self.assertEqual((3240, 1440), img.size)
        self.assertEqual('RGBA', img.format)
        self.assertEqual(True, img.is_transparent)
        self.assertEqual((0, 0, 0, 0), img.bg_color)

    def test_similarity(self):
        img_1 = Image(img_fpath=self.opaque_image)
        img_2 = Image(img_fpath=self.transparent_image)
        img_3 = Image(img_fpath=self.opaque_image)
        sim = Image.similarity(img_1.img, img_2.img)
        sim = Image.similarity(img_1.img, img_3.img)
        self.assertEqual(1.0, sim)
        sim = Image.similarity(img_1.img, img_1.img)
        self.assertEqual(1.0, sim)

    def test_resize_to_width(self):
        img = Image(img_fpath=self.opaque_image)
        img.resize_to_width(1000)
        self.assertEqual(1000, img.width)
        self.assertEqual(444, img.height)

    def test_resize_to_height(self):
        img = Image(img_fpath=self.opaque_image)
        img.resize_to_height(1000)
        self.assertEqual(2250, img.width)
        self.assertEqual(1000, img.height)

    def test_crop_and_resize(self):
        """
        Crop the image if specified with a crop tuple of (x0, y0, x1, y1) and resize to a target width
        """
        img = Image(img_fpath=self.opaque_image)
        img = img.crop_and_resize(crop=(0, 0, 100, 100))
        self.assertEqual(100, img.width)
        self.assertEqual(100, img.height)
        img = Image(img_fpath=self.opaque_image)
        img = img.crop_and_resize(crop=(0, 0, 100, 100), width=200)
        self.assertEqual(200, img.width)
        self.assertEqual(200, img.height)

    def test_expand_bg(self):
        img = Image(img_fpath=self.opaque_image)
        self.assertEqual(324, img.width)
        self.assertEqual(144, img.height)
        img.expand_bg(target_size=(img.width * 2, img.height * 2))
        self.assertEqual(648, img.width)
        self.assertEqual(288, img.height)
        img = Image(img_fpath=self.transparent_image)
        img.expand_bg(target_size=(img.width * 2, img.height * 2))
        self.assertEqual(6480, img.width)
        self.assertEqual(2880, img.height)

    def test_bg_to_transparent(self):
        # White to transparent
        img = Image(img_fpath=self.opaque_image)
        img = img.bg_to_transparent()
        self.assertTrue(isinstance(img, Image))
        # self.assertEqual('RGBA', img.format)
        img.save(os.path.join(Config.TEST_GALLERY_DIR, 'test_bg_to_transparent_0.png'))
        sim = self.compare_to_truth(img, 'test_bg_to_transparent_0.png')
        self.assertEqual(1.0, sim)
        # Already transparent
        img = Image(img_fpath=self.transparent_image)
        img = img.bg_to_transparent()
        img.save(os.path.join(Config.TEST_GALLERY_DIR, 'test_bg_to_transparent_1.png'))

    def test_transparency_to_bg_color(self):
        img = Image(img_fpath=self.transparent_image)
        img.transparency_to_bg_color()
        img.save(os.path.join(Config.TEST_GALLERY_DIR, 'test_transparency_to_bg_color.jpeg'))
        sim = self.compare_to_truth(img, 'test_transparency_to_bg_color.jpeg')
        self.assertTrue(sim > 0.99)

    def test_paste(self):
        img = Image(img_fpath=self.transparent_image)
        bg = Image(img_fpath=self.opaque_image)
        bg.paste(overlay=img.img, paste_coordinates=[0, 0])
        bg.save(os.path.join(Config.TEST_GALLERY_DIR, 'test_paste_to_bg.png'))
        sim = self.compare_to_truth(bg, 'test_paste_to_bg.png')
        self.assertTrue(sim > 0.95)

    def test_convert(self):
        img = Image(img_fpath=self.transparent_image)
        self.assertEqual(img.format, 'RGBA')
        img.convert('RGB')
        self.assertEqual(img.format, 'RGB')

    def test_get_fname(self):
        fname = Image(img_fpath=self.opaque_image).get_fname(base_name=None, out_dir=None,
                                                             width=None, is_transparent=None, new_ext=None)
        self.assertTrue(os.path.basename(fname) == 'CallsToMake_wide.png')
        fname = Image(img_fpath=self.opaque_image).get_fname(base_name=None, out_dir=None,
                                                             width=500, is_transparent=True, new_ext=None)
        self.assertTrue(os.path.basename(fname) == 'CallsToMake_wide--500_t.png')
        fname = Image(img_fpath=self.opaque_image).get_fname(base_name='test_get_fname.png',
                                                             out_dir=Config.TEST_GALLERY_DIR,
                                                             width=500,
                                                             is_transparent=True,
                                                             new_ext='jpeg')
        self.assertTrue(os.path.basename(fname) == 'test_get_fname--500_t.jpeg')

    def test_save(self):
        img = Image(img_fpath=self.transparent_image)
        out_path = os.path.join(Config.TEST_GALLERY_DIR, 'test_save.png')
        img.save(out_path=out_path)
        self.assertTrue(os.path.isfile(out_path))

    @unittest.skip('TODO - debug this non-critical test')
    def test_compress(self):
        img = Image(img_fpath=self.transparent_image)
        out_path = os.path.join(Config.TEST_GALLERY_DIR, 'test_compress.png')
        img.compress(base_name='test_compress.png', out_dir=Config.TEST_GALLERY_DIR)
        self.assertTrue(os.path.isfile(os.path.join(Config.TEST_GALLERY_DIR, 'test_compress--1000_t.png')))
        self.assertTrue(os.path.isfile(os.path.join(Config.TEST_GALLERY_DIR, 'test_compress--1000.jpeg')))
        self.assertTrue(os.path.isfile(os.path.join(Config.TEST_GALLERY_DIR, 'test_compress--1000.webp')))


class ImageGroupCase(EditorsBaseCase):
    def setUp(self) -> None:
        super(ImageGroupCase, self).setUp()
        self.image_list = [self.get_asset_fpath('CallsToMake_wide.png'),
                           self.get_asset_fpath('CallsToMake_wide_t.png')]

    def test_init(self):
        img_group = ImageGroup(image_list=self.image_list)
        self.assertTrue(isinstance(img_group, ImageGroup))

    def test_filter_image_list(self):
        img_list = ['CallsToMake_wide.png', 'CallsToMake_wide', 'CallsToMake_wide.pdf', '.gitkeep']
        result = ImageGroup.filter_image_list(img_list)
        self.assertEqual(['CallsToMake_wide.png'], result)

    def test_to_gif(self):
        img_group = ImageGroup(image_list=self.image_list * 10)
        result = img_group.to_gif(os.path.join(Config.TEST_GALLERY_DIR, 'test_to_gif.gif'))

    def test_to_slideshow(self):
        img_group = ImageGroup(image_list=self.image_list * 10)
        result = img_group.to_slideshow(os.path.join(Config.TEST_GALLERY_DIR, 'test_to_slideshow.ppt'))
        self.assertTrue(os.path.isfile(os.path.join(Config.TEST_GALLERY_DIR, 'test_to_slideshow.ppt')))

    def test_to_pdf(self):
        img_group = ImageGroup(image_list=self.image_list * 10)
        result = img_group.to_pdf(os.path.join(Config.TEST_GALLERY_DIR, 'test_to_pdf.pdf'))
        self.assertTrue(os.path.isfile(os.path.join(Config.TEST_GALLERY_DIR, 'test_to_pdf.pdf')))

    def test_get_image_group(self):
        img_group = get_image_group(image_list=self.image_list)
        self.assertTrue(isinstance(img_group, ImageGroup))


class PDFCase(EditorsBaseCase):
    def setUp(self) -> None:
        super(PDFCase, self).setUp()
        self.target_pdf = self.get_asset_fpath('book_from_pdf_list.pdf')
        self.pdf_list = [self.get_asset_fpath('music.pdf'),
                         self.get_asset_fpath('tablature.pdf')]

    def test_init(self):
        pdf = PDF(pdf_path=self.target_pdf)
        self.assertTrue(pdf, PDF)

    def test_pages(self):
        pdf = PDF(pdf_path=self.target_pdf)
        self.assertEqual(3, pdf.num_pages)

    def test_split(self):
        pdf = PDF(pdf_path=self.target_pdf)
        split_list = pdf.split()
        self.assertEqual(3, len(split_list))

    @unittest.skip('TODO - debug this non-critical test')
    def test_to_svgs(self):
        pdf = PDF(pdf_path=self.target_pdf)
        svgs = pdf.to_svgs(out_dir=Config.TEST_GALLERY_DIR)
        self.assertIsNotNone(svgs[0].fpath)
        svg = SVG(fpath=svgs[0].fpath)
        self.assertIsNotNone(svg.color_palette)

    @unittest.skip('re-enable after installing poppler and inkscape')
    def test_to_image_group(self):
        pdf = PDF(pdf_path=self.target_pdf)
        imgs = pdf.to_image_group()
        self.assertTrue(isinstance(imgs, ImageGroup))

    def get_sample_page(self, in_fpath):
        pdf_reader = PdfReader(in_fpath)
        return pdf_reader.pages[0]

    def write_output_pdf(self, out_fpath, page):
        pdf_writer = PdfWriter()
        pdf_writer.add_page(page)
        with open(out_fpath, 'wb') as output_file:
            pdf_writer.write(output_file)

    def test_crop_page_margins(self):
        pdf_out = os.path.join(Config.TEST_GALLERY_DIR, 'test_crop_page_margins.pdf')
        page = self.get_sample_page(self.target_pdf)
        pdf = PDF(pdf_path=self.target_pdf)
        page = pdf.crop_page_margins(page, [(100, 100), (400, 400), 1.2])
        self.write_output_pdf(pdf_out, page)
        self.assertTrue(os.path.isfile(pdf_out))

    def test_get_crop_margins(self):
        page = self.get_sample_page(self.target_pdf)
        pdf = PDF(pdf_path=self.target_pdf)
        margins = pdf.get_crop_margins(page, crop_percent=0.05, side='both')
        self.assertEqual(((10.350000000000001, 15.75), (403.65, 614.25), 1.0526315789473684), margins)
        margins = pdf.get_crop_margins(page, crop_percent=0.10, side='both')
        self.assertEqual(((20.700000000000003, 31.5), (393.3, 598.5), 1.111111111111111), margins)
        margins = pdf.get_crop_margins(page, crop_percent=0.10, side='left')
        self.assertEqual(((41.400000000000006, 31.5), (414, 598.5), 1.111111111111111), margins)

    def test_crop_page(self):
        pdf_out = os.path.join(Config.TEST_GALLERY_DIR, 'test_crop_page.pdf')
        page = self.get_sample_page(self.target_pdf)
        pdf = PDF(pdf_path=self.target_pdf)
        page_idx, new_page = pdf.crop_page({'page': page, 'page_idx': 0, 'crop_percent': 0.2, 'even_idx_right': False})
        self.write_output_pdf(pdf_out, new_page)
        self.assertTrue(os.path.isfile(pdf_out))

    def test_sample_pdf_pages(self):
        pdf_out = os.path.join(Config.TEST_GALLERY_DIR, 'test_sample_pdf_pages.pdf')
        pdf = PDF(pdf_path=self.target_pdf)
        pdf_writer = pdf.sample_pdf_pages(page_list=[0, 2])
        with open(pdf_out, 'wb') as output_file:
            pdf_writer.write(output_file)
        self.assertTrue(os.path.isfile(pdf_out))


class PdfGroupCase(EditorsBaseCase):
    def setUp(self) -> None:
        super(PdfGroupCase, self).setUp()
        self.target_pdf = self.get_asset_fpath('book_from_pdf_list.pdf')
        self.pdf_list = [self.get_asset_fpath('music.pdf'),
                         self.get_asset_fpath('book_from_pdf_list.pdf')]

    def test_init(self):
        pdf_group = PdfGroup(pdf_list=self.pdf_list)
        self.assertTrue(pdf_group, PdfGroup)

    def test_sample(self):
        pdf_group = PdfGroup(pdf_list=self.pdf_list)
        pdf_sample = pdf_group.sample(out_path=os.path.join(Config.TEST_GALLERY_DIR, 'test_sample.pdf'),
                                      page_list=[0])
        pdf = PDF(pdf_path=os.path.join(Config.TEST_GALLERY_DIR, 'test_sample.pdf'))
        self.assertEqual(2, pdf.num_pages)
