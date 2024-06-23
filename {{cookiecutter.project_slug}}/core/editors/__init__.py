"""

Comprehensive suite of image editors for vector and raster images.

Dependency order is:
- SVG
- Image - depends on SVG
- PDF - depends on SVG and PDF

"""


import os


def get_fpaths(target_dir, filetype='pdf', filetype_list=None):
    """
    Get a list of all the file paths of a specified filetype or list of filetypes in a directory
    :param target_dir:
    :type target_dir:
    :param filetype:
    :type filetype:
    :param filetype_list:
    :type filetype_list:
    :return:
    :rtype:
    """
    if filetype_list is None:
        return [os.path.join(target_dir, fname) for fname in os.listdir(target_dir)
                if fname.lower().endswith(filetype)]
    else:
        return [os.path.join(target_dir, fname) for fname in os.listdir(target_dir)
                if any([fname.lower().endswith(ext) for ext in filetype_list])]
