from src.trade_journal import save_trade_log, load_history


class JournalLoader:

    def save(self, data):

        save_trade_log(
            data
        )


    def history(self):

        return load_history()
