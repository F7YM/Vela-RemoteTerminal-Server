from .base import UIComponent


class Button(UIComponent):
    type = "btn"

    def __init__(self, text: str = "", action: str = "", image: str = "", props: dict | None = None, **styles):
        super().__init__(props=props, **styles)
        self.text = text
        self.action = action
        self.image = image

    def to_dict(self) -> dict:
        item = super().to_dict()
        item["txt"] = self.text
        if self.image:
            item["img"] = self.image
        if self.action:
            item["a"] = self.action
        if self.props.get("fw"):
            item["fw"] = self.props["fw"]
        if self.props.get("data"):
            item["data"] = self.props["data"]
        return item