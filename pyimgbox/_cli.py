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

import argparse
import asyncio
import os
import sys
import traceback
from os.path import exists as _path_exists
from os.path import getsize as _path_filesize

import pyimgbox


def main(argv=sys.argv[1:]):
    loop = asyncio.get_event_loop()
    exit_code = loop.run_until_complete(
        run(argv)
    )
    return exit_code


async def run(argv):
    args = _get_cli_args(argv)

    if args.debug:
        import logging
        logging.basicConfig(level=logging.DEBUG,
                            format='%(module)s: %(message)s')

    exit_code = 0
    try:
        files = _get_files(args)
    except ValueError as e:
        print(e, file=sys.stderr)
        exit_code = 1
    else:
        async with pyimgbox.Gallery(title=args.title,
                                    adult=args.adult,
                                    thumb_width=args.thumb_width,
                                    square_thumbs=args.square_thumbs,
                                    comments_enabled=args.comments) as gallery:
            try:
                if args.json:
                    exit_code = await _json_output(gallery, files)
                else:
                    exit_code = await _text_output(gallery, files)
            except Exception as e:
                exit_code = 100
                print(''.join(traceback.format_exception(type(e), e, e.__traceback__)), file=sys.stderr)
                print('Please report this as a bug: '
                      'https://github.com/plotski/pyimgbox/issues',
                      file=sys.stderr)

    return exit_code


def _path_readable(path):
    return os.access(path, os.R_OK)


def _get_files(args):
    # Read files from arguments and from stdin
    files = []
    if not sys.stdin.isatty():
        files.extend(f.rstrip('\n') for f in sys.stdin.readlines() if f.strip())
    if args.files != ['-']:
        files.extend(args.files)

    if not files:
        raise ValueError('Missing at least one image file. '
                         f'Run "{pyimgbox.__command_name__} -h" for more information.')

    for f in files:
        if not _path_exists(f):
            raise ValueError(f'File does not exist: {f}')
        if not _path_readable(f):
            raise ValueError(f'File is not readable: {f}')
        if _path_filesize(f) >= pyimgbox.MAX_FILE_SIZE:
            raise ValueError(f'File is larger than {pyimgbox.MAX_FILE_SIZE} B: {f}')

    return files


async def _text_output(gallery, filepaths):
    exit_code = 0
    try:
        await gallery.create()
    except ConnectionError as e:
        exit_code = 1
        print(str(e), file=sys.stderr)
    else:
        print(f'Gallery: {gallery.url}')
        print(f'   Edit: {gallery.edit_url}')
        async for sub in gallery.add(*filepaths):
            print(f'* {sub.filename}')
            if sub.success:
                print(f'      Image: {sub.image_url}')
                print(f'  Thumbnail: {sub.thumbnail_url}')
                print(f'    Webpage: {sub.web_url}')
            else:
                print(f'  {sub.error}')
                exit_code = 2
    return exit_code


async def _json_output(gallery, filepaths):
    exit_code = 0
    info = {'success': None,
            'error': None,
            'gallery_url': None,
            'edit_url': None,
            'images': []}
    try:
        await gallery.create()
    except ConnectionError as e:
        exit_code = 1
        info['success'] = False
        info['error'] = str(e)
    else:
        info['success'] = True
        info['error'] = None
        info['gallery_url'] = gallery.url
        info['edit_url'] = gallery.edit_url
        async for sub in gallery.add(*filepaths):
            info['images'].append(sub)
            if not sub.success:
                exit_code = 2
    import json
    sys.stdout.write(json.dumps(info, indent=4) + '\n')
    return exit_code


def _get_cli_args(argv):
    argparser = argparse.ArgumentParser(description='Upload images to imgbox.com')
    argparser.add_argument('files', nargs='*',
                           help=('Image files to upload; newline-separated file paths '
                                 'are also read from stdin'))
    argparser.add_argument('--title', '-t', default=None,
                           help='Gallery title')
    argparser.add_argument('--thumb-width', '-w', default=100, type=int,
                           help='Thumbnail width in pixels')
    argparser.add_argument('--adult', '-a', action='store_true',
                           help='Mark gallery as adult-only')
    argparser.add_argument('--square-thumbs', '-q', action='store_true',
                           help='Make square thumbnails')
    argparser.add_argument('--comments', '-c', action='store_true',
                           help='Enable comments')
    argparser.add_argument('--json', '-j', action='store_true',
                           help='Print URLs as JSON object')
    argparser.add_argument('--version', '-V', action='version',
                           version=f'{pyimgbox.__command_name__} {pyimgbox.__version__}')
    argparser.add_argument('--debug', action='store_true',
                           help='Print debugging information')
    args = argparser.parse_args(argv)
    return args
