def safe_area_style(shape: str = "") -> str:
    """根据屏幕形状返回安全区 CSS，开发者手动传入 Page(content_style=...)"""
    if not shape:
        return ""
    if shape == "circle":
        return "padding: 0 30px 40px; margin-top: 40px"
    if shape in ("rect", "pill-shaped"):
        return "margin-top: 40px"
    return ""


class Page:
    def __init__(self, *children, refresh_interval: int = 0, content_style: str = "",
                 audio: dict | None = None, audio_cmd: str = ""):
        self.children = list(children)
        self.refresh_interval = refresh_interval
        self.content_style = content_style
        self.audio = audio
        self.audio_cmd = audio_cmd

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_dict(self) -> dict:
        d = {
            "ri": self.refresh_interval,
            "c": [c.to_dict() for c in self.children]
        }
        if self.content_style:
            d["cs"] = self.content_style
        if self.audio:
            d["audio"] = self.audio
        if self.audio_cmd:
            d["audioCmd"] = self.audio_cmd
        return d
