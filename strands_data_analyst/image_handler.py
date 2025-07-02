import os
from uuid import uuid4


class Image:
    def __init__(self, path, url, caption):
        self.path = path
        self.url = url
        self.caption = caption or ""
    
    def markdown(self):
        return f"![{self.caption}]({self.url})"


class ImageHandler:
    def __init__(self, img_dir, img_url):
        os.makedirs(img_dir, exist_ok=True)
        
        self.img_dir = img_dir
        self.img_url = img_url
        self.images = []

    def reset(self):
        self.images = []

    def save_img(self, img, caption):
        filename = f"{uuid4()}.png"
        filepath = self.img_dir / filename
        img.savefig(filepath, format="png")

        image = Image(
            filepath,
            os.path.join(self.img_url, filename),
            caption)
        self.images.append(image)
        return image

    def update_paths(self, html):
        return html.replace(self.img_url, self.img_dir.name)

