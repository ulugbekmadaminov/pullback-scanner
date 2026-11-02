"""Backtest: python run_backtest.py [--demo]. Natija: state/backtest/latest.json va docs/BACKTEST.md"""
import argparse

from engine import backtest as B
from engine import config as C
from engine.data import write_json
from engine.pipeline import load

ap = argparse.ArgumentParser()
ap.add_argument("--demo", action="store_true")
ap.add_argument("--limit", type=int, default=0, help="sinov uchun aksiyalar sonini cheklash")
a = ap.parse_args()
if a.demo:
    C.STATE = C.ROOT / ".demo-state"
tickers, prices, fund, earn, divs, src = load(a.demo)
if a.limit:
    tickers = tickers[:a.limit]
sectors = {t: (fund.get(t) or {}).get("sector", "") for t in tickers}
rep = B.run(prices, tickers, sectors, earn, demo=a.demo)
rep["universe_source"] = src
write_json(C.STATE / "backtest" / "latest.json", rep)
(C.ROOT / "docs").mkdir(exist_ok=True)
(C.ROOT / ("docs/BACKTEST-demo.md" if a.demo else "docs/BACKTEST.md")).write_text(B.markdown(rep))
print(B.markdown(rep))
