from .base import UIComponent

class Image(UIComponent):
    type = "img"

    def __init__(self, src: str = "", props: dict | None = None, **styles):
        super().__init__(props=props, **styles)
        self.src = src

    def to_dict(self) -> dict:
        item = super().to_dict()
        item["src"] = self.src
        return item
