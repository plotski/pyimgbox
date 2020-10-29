Python 3.6+ library for uploading images to [https://imgbox.com/](imgbox.com).

### Installation

pyimgbox is on [PyPI](https://pypi.org/project/pyimgbox/).

```sh
$ pip install pyimgbox
```

### Usage

```python
import asyncio
import pprint
import sys

import pyimgbox

async def main():
    files = sys.argv[1:]
    try:
        async with pyimgbox.Gallery(title="Hello, World!") as gallery:
            await gallery.create()
            print('Gallery URL:', gallery.url)
            print('   Edit URL:', gallery.edit_url)
            async for submission in gallery.add(*files):
                pprint.pprint(submission)
    except ConnectionError as e:
        print('Oh no!', str(e))

asyncio.run(main())
```
