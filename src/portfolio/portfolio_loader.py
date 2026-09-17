from src.portfolio_manager import create_portfolio
from src.dynamic_portfolio import create_dynamic_portfolio
from src.monthly_investment import calculate_monthly_plan


class PortfolioLoader:

    def create(self, capital, regime):

        portfolio = create_dynamic_portfolio(
            capital,
            regime
        )

        return portfolio


    def monthly_plan(self, capital, regime):

        return calculate_monthly_plan(
            capital,
            regime
        )
