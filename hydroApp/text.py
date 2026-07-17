from .base import UIComponent

class Text(UIComponent):
    type = "text"

    def __init__(self, value: str = "", props: dict | None = None, **styles):
        super().__init__(props=props, **styles)
        self.value = value

    def to_dict(self) -> dict:
        item = super().to_dict()
        item["v"] = self.value
        return item


class ProgressText(UIComponent):
    type = "prog"

    def __init__(self, value: str = "", props: dict | None = None, **styles):
        super().__init__(props=props, **styles)
        self.value = value

    def to_dict(self) -> dict:
        item = super().to_dict()
        item["v"] = self.value
        return item
