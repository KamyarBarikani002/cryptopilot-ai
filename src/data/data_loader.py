from src.market_data import get_btc_price, get_prices


class MarketDataLoader:

    def get_price(self):
        return get_btc_price()

    def get_prices(self, asset_symbols):
        return get_prices(asset_symbols)
