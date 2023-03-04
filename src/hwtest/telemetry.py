from typing import Tuple

from hwtest.logging import LogEvent


class Telemetry(LogEvent):
    """A logging event in which every field must be a consistent numeric type."""
    type_tag: str = "TELE"
    device: str

    def keys(self) -> Tuple[str]:
        return super().keys() + (
            "device",
        )
