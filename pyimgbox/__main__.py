# This file is part of pyimgbox.
#
# This program is free software: you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this
# program.  If not, see <https://www.gnu.org/licenses/>.


def main():
    import pyimgbox
    args = _get_cli_args()

    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG,
                            format='%(module)s: %(message)s')

    gallery = pyimgbox.Gallery(title=args.title,
                               comments_enabled=args.comments,
                               thumb_width=args.thumbnail_size)
    if args.json:
        _json_output(gallery, args.files)
    else:
        _text_output(gallery, args.files)


def _text_output(gallery, filepaths):
    try:
        gallery.create()
    except ConnectionError as e:
        print(str(e))
    else:
        print(f'Gallery: {gallery.url}')
        print(f'   Edit: {gallery.edit_url}')
        for sub in gallery.add(*filepaths):
            print(f'* {sub.filepath}')
            if sub.success:
                print(f'      Image: {sub.image_url}')
                print(f'  Thumbnail: {sub.thumbnail_url}')
                print(f'    Webpage: {sub.web_url}')
            else:
                print(f'  {sub.error}')


def _json_output(gallery, filepaths):
    info = {'success': None,
            'error': None,
            'gallery_url': None,
            'edit_url': None,
            'images': []}
    try:
        gallery.create()
    except ConnectionError as e:
        info['success'] = False
        info['error'] = str(e)
    else:
        info['success'] = True
        info['error'] = None
        info['gallery_url'] = gallery.url
        info['edit_url'] = gallery.edit_url
        for sub in gallery.add(*filepaths):
            info['images'].append(dict(sub))
    import json
    import sys
    sys.stdout.write(json.dumps(info, indent=4) + '\n')


def _get_cli_args():
    import pyimgbox
    import argparse
    argparser = argparse.ArgumentParser(description='Upload images to imgbox.com')
    argparser.add_argument('files', nargs='+',
                           help='Image files to upload')
    argparser.add_argument('--thumbnail-size', '-s', default=200, type=int,
                           help='Thumbnail width in pixels')
    argparser.add_argument('--title', '-t', default=None,
                           help='Gallery title')
    argparser.add_argument('--comments', '-c', action='store_true',
                           help='Enable comments')
    argparser.add_argument('--json', '-j', action='store_true',
                           help='Print URLs as JSON object')
    argparser.add_argument('--version', '-V', action='version',
                           version=f'%(prog)s {pyimgbox.__version__}')
    argparser.add_argument('--debug', action='store_true',
                           help='Print debugging information')
    args = argparser.parse_args()
    return args
