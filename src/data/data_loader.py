from src.market_data import get_btc_price


class MarketDataLoader:

    def get_price(self):
        return get_btc_price()
