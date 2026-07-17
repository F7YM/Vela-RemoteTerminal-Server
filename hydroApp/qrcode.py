from .base import UIComponent

class QRCode(UIComponent):
    type = "qr"

    def __init__(self, data: str = "", props: dict | None = None, **styles):
        super().__init__(props=props, **styles)
        self.data = data

    def to_dict(self) -> dict:
        item = super().to_dict()
        item["data"] = self.data
        return item
