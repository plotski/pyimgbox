import asyncio
import sys

import pyimgbox

# # Uncomment this to enable debugging messages
# import logging
# logging.basicConfig(level=logging.DEBUG)


# Using Gallery as an asynchronous context manager is the simplest usage.

async def example1(filepaths):
    async with pyimgbox.Gallery(title="Hello, World!") as gallery:
        async for submission in gallery.add(filepaths):
            if not submission['success']:
                print(f"{submission['filename']}: {submission['error']}")
            else:
                print(submission)


# Without the asynchronous context manager, close() must be called manually.

async def example2(filepaths):
    gallery = pyimgbox.Gallery(title="Hello, World!")
    try:
        async for submission in gallery.add(filepaths):
            print(submission)
    finally:
        await gallery.close()


# If you need the gallery's URL before the first upload,
# you can call create() manually.

async def example3(filepaths):
    async with pyimgbox.Gallery(title="Hello, World!") as gallery:
        try:
            await gallery.create()
        except ConnectionError as e:
            print('Gallery creation failed:', str(e))
        else:
            print('Gallery URL:', gallery.url)
            print('   Edit URL:', gallery.edit_url)
            async for submission in gallery.add(filepaths):
                print(submission)


# Use upload() instead of add() fore more flexibility.

async def example4(filepaths):
    async with pyimgbox.Gallery(title="Hello, World!") as gallery:
        submission1 = await gallery.upload(filepaths[0])
        submission2 = await gallery.upload(filepaths[1])
        submission3 = await gallery.upload(filepaths[2])
    print('Submissions:', submission1, submission2, submission3)


asyncio.run(example1(sys.argv[1:]))
