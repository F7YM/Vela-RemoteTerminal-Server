from .base import UIComponent

class TextInput(UIComponent):
    type = "inp"

    def __init__(self, placeholder: str = "", action: str = "", props: dict | None = None, **styles):
        super().__init__(props=props, **styles)
        self.placeholder = placeholder
        self.action = action

    def to_dict(self) -> dict:
        item = super().to_dict()
        item["v"] = self.placeholder
        if self.action:
            item["a"] = self.action
        return item
