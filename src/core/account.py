from datetime import datetime

from config.settings import MONTHLY_INVESTMENT
from src.portfolio.portfolio_state import load_state, save_state
from src.portfolio.portfolio_loader import PortfolioLoader
from src.monthly_investment import calculate_monthly_plan


class Account:

    """
    وضعیت واقعی و ماندگار سرمایه: نقد + دارایی‌های خریداری‌شده.
    بین اجراهای مختلف بات از روی فایل database/portfolio_state.json خونده و ذخیره می‌شه.
    """

    def __init__(self):

        self.state = load_state()
        self.is_first_run = self.state["last_contribution_period"] is None
        self.portfolio_loader = PortfolioLoader()

    def current_period(self):
        return datetime.now().strftime("%Y-%m")

    def _deploy(self, allocation, prices):

        deployed = {}

        for asset, dollar_amount in allocation.items():

            if asset == "Cash":
                self.state["cash"] += dollar_amount
                deployed[asset] = round(dollar_amount, 2)
                continue

            price = prices.get(asset)

            if not price:
                # قیمت این دارایی موجود نیست؛ به‌جای گم شدن پول، نقد نگه می‌داریم
                self.state["cash"] += dollar_amount
                continue

            units = dollar_amount / price

            current_units = self.state["holdings"].get(asset, 0)
            self.state["holdings"][asset] = current_units + units

            deployed[asset] = {
                "usd": round(dollar_amount, 2),
                "units": units,
                "price": price
            }

        return deployed

    def apply_monthly_contribution(self, regime, prices):

        """
        اگر از آخرین واریز، ماه جدیدی شروع شده باشه، سرمایه رو اضافه و طبق
        رژیم فعلی بازار بین دارایی‌ها تخصیص می‌ده. اولین اجرا هم همینجا
        سرمایه اولیه (INITIAL_CAPITAL) رو برای اولین‌بار سرمایه‌گذاری می‌کنه.
        """

        period = self.current_period()

        if self.state["last_contribution_period"] == period:
            return None

        if self.is_first_run:
            amount = self.state["cash"]
            self.state["cash"] = 0
            allocation = self.portfolio_loader.create(amount, regime)
        else:
            amount = MONTHLY_INVESTMENT
            self.state["cash"] += amount
            self.state["total_contributed"] += amount
            allocation = calculate_monthly_plan(amount, regime)

        deployed = self._deploy(allocation, prices)

        contribution_record = {
            "period": period,
            "amount": round(amount, 2),
            "regime": regime,
            "allocation": deployed,
            "time": str(datetime.now())
        }

        self.state["contributions"].append(contribution_record)
        self.state["last_contribution_period"] = period

        return contribution_record

    def apply_signal(self, decision, price, risk):

        """
        سیگنال خرید/فروش BTC رو روی نقد و دارایی واقعی و ماندگار پیاده می‌کنه.
        """

        if decision in ("BUY", "ACCUMULATE") and self.state["cash"] > 0:

            position_size = min(
                self.state["cash"],
                risk["position_size"]
            )

            if position_size <= 0:
                return None

            units = position_size / price

            current_units = self.state["holdings"].get("BTC", 0)
            self.state["holdings"]["BTC"] = current_units + units
            self.state["cash"] -= position_size

            return {
                "type": decision,
                "usd": round(position_size, 2),
                "units": units,
                "price": price
            }

        if decision == "SELL" and self.state["holdings"].get("BTC", 0) > 0:

            units = self.state["holdings"]["BTC"]
            proceeds = units * price

            self.state["cash"] += proceeds
            self.state["holdings"]["BTC"] = 0

            return {
                "type": "SELL",
                "usd": round(proceeds, 2),
                "units": units,
                "price": price
            }

        return None

    def portfolio_value(self, prices):

        value = self.state["cash"]

        breakdown = {
            "Cash": round(self.state["cash"], 2)
        }

        for asset, units in self.state["holdings"].items():

            price = prices.get(asset, 0)
            asset_value = units * price

            value += asset_value
            breakdown[asset] = round(asset_value, 2)

        return round(value, 2), breakdown

    def save(self):
        save_state(self.state)
