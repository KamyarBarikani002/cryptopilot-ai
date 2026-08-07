from src.candle_data import get_btc_candles


class CandleLoader:

    def get_data(self):
        return get_btc_candles()
