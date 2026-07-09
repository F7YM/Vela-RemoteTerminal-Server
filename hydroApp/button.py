from .base import UIComponent

class Button(UIComponent):
    type = "btn"

    def __init__(self, text: str = "", action: str = "", props: dict | None = None, **styles):
        super().__init__(props=props, **styles)
        self.text = text
        self.action = action

    def to_dict(self) -> dict:
        item = super().to_dict()
        item["txt"] = self.text
        if self.action:
            item["a"] = self.action
        return item
