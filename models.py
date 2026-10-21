from dataclasses import dataclass


@dataclass
class MarketQuote:
    platform: str
    target: float
    up: float
    down: float
    close_time: str
