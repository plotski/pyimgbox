MAX_FILE_SIZE = 10485760  # 10 MiB (10290152 bytes were allowed on 2020-09-24)
CSRF_TOKEN_HEADER = 'X-CSRF-Token'

SERVICE_DOMAIN = 'imgbox.com'
TOKEN_URL = f'https://{SERVICE_DOMAIN}/ajax/token/generate'
PROCESS_URL = f'https://{SERVICE_DOMAIN}/upload/process'
EDIT_URL_FORMAT = f'https://{SERVICE_DOMAIN}/upload/edit/{{token_id}}/{{token_secret}}'
GALLERY_URL_FORMAT = f'https://{SERVICE_DOMAIN}/g/{{gallery_id}}'

THUMBNAIL_SIZES_SQUARE = {
    150: '150c',
    200: '200c',
    250: '250c',
    300: '300c',
    350: '350c',
    500: '500c',
    800: '800c',
}

THUMBNAIL_SIZES_KEEP_ASPECT = {
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
    'family': '1',
    'adult': '2',
}
