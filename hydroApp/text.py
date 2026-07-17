from .base import UIComponent

class Text(UIComponent):
    type = "text"

    def __init__(self, value: str = "", props: dict | None = None, **styles):
        super().__init__(props=props, **styles)
        self.value = value

    def to_dict(self) -> dict:
        item = super().to_dict()
        item["v"] = self.value
        if self.props.get("lines"):
            item["lines"] = self.props["lines"]
        return item
