# pyimgbox

```python
import pyimgbox
import json
files = ("this.jpg", "and/that.png")
gallery = pyimgbox.Gallery(title="Hello, World!")
for submission in gallery.submit(*files, thumb_width=200):
    print(json.dumps(submission, indent=4))
```
