from trade_journal import save_trade_log, load_history


trade = {
    "asset": "BTC",
    "price": 63500,
    "decision": "ACCUMULATE",
    "amount": 50
}


save_trade_log(trade)


history = load_history()


print("================")
print("TRADE JOURNAL")
print("================")


for item in history:
    print(item)