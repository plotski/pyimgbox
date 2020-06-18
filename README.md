- CLI tool

    ```sh
    $ imgbox foo.jpg bar.png --title "My Gallery" --thumb-width 500
    $ imgbox --thumb-width 123 < list_of_file_paths.txt
    $ generate_file_paths | imgbox --json | jq -r ".images[].image_url"
    ```

- Shell script to generate BBCode

    ```sh
    imgbox --json --thumb-width 350 "$@" > upload.json
    echo "[url=$(jq -r '.gallery_url' < upload.json)]Gallery[/url]"
    echo "[url=$(jq -r '.edit_url' < upload.json)]Edit Gallery[/url]"
    while read image; do
        image_url=$(jq -r '.image_url' <<< "$image")
        thumbnail_url=$(jq -r '.thumbnail_url' <<< "$image")
        echo "[url=$image_url][img]$thumbnail_url[/img][/url]"
    done <<< $(jq -c '.images[]' upload.json)
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
        print('   Edit URL:', gallery.edit_url)
        for submission in gallery.add(*files):
            pprint.pprint(submission)
    ```

### Installation

```sh
$ sudo apt install pipx
$ pipx install --upgrade pyimgbox
```
