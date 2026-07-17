STYLE_MAP = {
    "fs": "font-size", "clr": "color", "fw": "font-weight", "ta": "text-align",
    "mt": "margin-top", "mb": "margin-bottom", "ml": "margin-left", "mr": "margin-right",
    "pt": "padding-top", "pb": "padding-bottom", "pl": "padding-left", "pr": "padding-right",
    "w": "width", "h": "height", "bg": "background-color", "br": "border-radius",
    "jc": "justify-content", "ai": "align-items", "of": "object-fit",
    "to": "text-overflow", "lines": "lines",
}
SIZE_PROPS = {"fs", "mt", "mb", "ml", "mr", "pt", "pb", "pl", "pr", "w", "h", "br"}


def build_style(props: dict) -> str:
    parts = []
    for key, value in props.items():
        if key not in STYLE_MAP or value is None:
            continue
        css_prop = STYLE_MAP[key]
        if key in SIZE_PROPS and isinstance(value, (int, float)):
            parts.append(f"{css_prop}: {value}px")
        else:
            parts.append(f"{css_prop}: {value}")
    return "; ".join(parts)


class UIComponent:
    type: str = ""

    def __init__(self, props: dict | None = None, **styles):
        self.props = {}
        if props:
            self.props.update(props)
        self.props.update(styles)
        self.props = {k: v for k, v in self.props.items() if v is not None}

    def to_dict(self) -> dict:
        item = {"t": self.type}
        if self.props:
            s = build_style(self.props)
            if s:
                item["s"] = s
            if self.props.get("a"):
                item["a"] = self.props["a"]
        return item


class Container(UIComponent):
    def __init__(self, *children, props: dict | None = None, **styles):
        super().__init__(props=props, **styles)
        self.children = list(children)

    def to_dict(self) -> dict:
        if self.props.get("a"):
            self._propagate_action(self.props["a"])
        item = super().to_dict()
        if self.children:
            item["c"] = [c.to_dict() for c in self.children]
        if self.props.get("a"):
            item["a"] = self.props["a"]
        return item

    def _propagate_action(self, action: str):
        for child in self.children:
            if isinstance(child, UIComponent):
                if not getattr(child, "action", None) and not child.props.get("a"):
                    child.props["a"] = action
                if hasattr(child, "_propagate_action"):
                    child._propagate_action(action)
