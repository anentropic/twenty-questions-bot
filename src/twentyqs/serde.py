import json
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class DateTimeDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        for key, value in obj.items():
            try:
                obj[key] = datetime.fromisoformat(value)
            except (AttributeError, TypeError, ValueError):
                pass
        return obj


def serialize(obj, /, **kwargs):
    kwargs["cls"] = DateTimeEncoder
    return json.dumps(obj, **kwargs)


def deserialize(obj, /, **kwargs):
    kwargs["cls"] = DateTimeDecoder
    return json.loads(obj, **kwargs)
