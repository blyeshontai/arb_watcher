from kalshi import get_kalshi_market
from polymarket import get_polymarket_market, current_event_slug

kalshi = get_kalshi_market()
poly = get_polymarket_market(current_event_slug())

if kalshi is None or poly is None:
    print("One of the markets isn't open right now")
elif kalshi.close_time != poly.close_time:
    print(f"Windows don't match: Kalshi {kalshi.close_time} vs Polymarket {poly.close_time}")
else:
    print(f"Window closes {kalshi.close_time}")
    print(f"Targets: Kalshi {kalshi.target} | Polymarket {poly.target} | Gap {abs(kalshi.target - poly.target):.2f}")
    print(f"Kalshi:     UP {kalshi.up} | DOWN {kalshi.down}")
    print(f"Polymarket: UP {poly.up} | DOWN {poly.down}")

    combo_1 = poly.up + kalshi.down
    print(f"Poly UP + Kalshi DOWN = {combo_1:.3f}")

    combo_2 = poly.down + kalshi.up
    print(f"Poly DOWN + Kalshi UP = {combo_2:.3f}")
