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


DEFAULT_TIMEOUT = 180  # 3 minutes
CSRF_TOKEN_HEADER = 'X-CSRF-Token'
ALLOWED_MIMETYPES = ('image/jpeg', 'image/png')
SERVICE_DOMAIN = 'imgbox.com'
TOKEN_URL = f'https://{SERVICE_DOMAIN}/ajax/token/generate'
PROCESS_URL = f'https://{SERVICE_DOMAIN}/upload/process'
EDIT_URL_FORMAT = f'https://{SERVICE_DOMAIN}/upload/edit/{{token_id}}/{{token_secret}}'
GALLERY_URL_FORMAT = f'https://{SERVICE_DOMAIN}/g/{{gallery_id}}'

THUMBNAIL_WIDTHS_SQUARE = {
    150: '150c',
    200: '200c',
    250: '250c',
    300: '300c',
    350: '350c',
    500: '500c',
    800: '800c',
}

THUMBNAIL_WIDTHS_KEEP_ASPECT = {
    100: '100r',
    150: '150r',
    200: '200r',
    250: '250r',
    300: '300r',
    350: '350r',
    500: '500r',
    800: '800r',
}

CONTENT_TYPES = {
    'family': 1,
    'adult': 2,
}
