Easy uploading to [imgbox.com](https://imgbox.com/).

- CLI tool

    ```sh
    $ imgbox foo.jpg bar.png --title "My Gallery" --thumb-width 500
    ```

- Shell script to generate BBCode

    ```sh
    imgbox --json --thumb-width 350 "$@" > images.json
    echo "[url=$(jq -r '.gallery_url' < images.json)]Gallery[/url]"
    echo "[url=$(jq -r '.edit_url' < images.json)]Edit Gallery[/url]"
    while read image; do
        image_url=$(jq -r '.image_url' <<< "$image")
        thumbnail_url=$(jq -r '.thumbnail_url' <<< "$image")
        echo "[url=$image_url][img]$thumbnail_url[/img][/url]"
    done <<< $(jq -c '.images[]' images.json)
    ```

- Python

    ```python
    import pyimgbox
    import pprint
    files = ("this.jpg", "and/that.png")
    gallery = pyimgbox.Gallery(title="Hello, World!")
    try:
        gallery.create()
    except ConnectionError as e:
        print('Oh no!', str(e))
    else:
        print('Gallery URL:', gallery.url)
        for submission in gallery.add(*files):
            pprint.pprint(submission)
    ```

### Installation

```sh
$ sudo apt install pipx
$ pipx install --upgrade pyimgbox
```
