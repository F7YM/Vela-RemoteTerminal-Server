from .base import UIComponent

class Switch(UIComponent):
    type = "sw"

    def __init__(self, checked: bool = False, action: str = "", props: dict | None = None, **styles):
        if 'chk' in styles:
            checked = styles.pop('chk')
        super().__init__(props=props, **styles)
        self.checked = checked
        self.action = action

    def to_dict(self) -> dict:
        item = super().to_dict()
        item["chk"] = self.checked
        if self.action:
            item["a"] = self.action
        return item
