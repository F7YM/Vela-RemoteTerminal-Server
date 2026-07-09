class Page:
    def __init__(self, *children, refresh_interval: int = 0):
        self.children = list(children)
        self.refresh_interval = refresh_interval

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_dict(self) -> dict:
        return {
            "ri": self.refresh_interval,
            "c": [c.to_dict() for c in self.children]
        }
