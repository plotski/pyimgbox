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
    import json
    args = _get_cli_args()
    gallery = pyimgbox.Gallery(title=args.title, comments_enabled=args.comments)
    for submission in gallery.submit(*args.files, thumb_width=200):
        print(json.dumps(submission, indent=4))


def _get_cli_args():
    import argparse
    argparser = argparse.ArgumentParser(description='Upload images to imgbox.com')
    argparser.add_argument('files', nargs='+',
                           help='Image files to upload')
    argparser.add_argument('--title', '-t', default=None,
                           help='Gallery title')
    argparser.add_argument('--comments', '-c', action='store_true',
                           help='Enable comments')
    args = argparser.parse_args()
    return args
