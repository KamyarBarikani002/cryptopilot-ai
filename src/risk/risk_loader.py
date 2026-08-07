from src.risk_manager import (
    calculate_position_size,
    calculate_stop_loss
)


class RiskLoader:

    def manage(self, capital, risk, entry_price):

        stop_percent = 3

        position_size = calculate_position_size(
            capital,
            risk,
            stop_percent
        )

        stop_loss = calculate_stop_loss(
            entry_price,
            stop_percent
        )

        return {
            "position_size": position_size,
            "stop_loss": stop_loss
        }
