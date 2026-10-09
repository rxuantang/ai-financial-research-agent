from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class ToolResult:
    tool: str
    status: str
    data: Any = None
    error: str | None = None

    def to_dict(self):
        return asdict(self)