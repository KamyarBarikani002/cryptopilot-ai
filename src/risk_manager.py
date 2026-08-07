def calculate_position_size(
    capital,
    risk_percent,
    stop_loss_percent
):

    risk_amount = capital * (risk_percent / 100)

    position_size = risk_amount / (stop_loss_percent / 100)

    return position_size


def calculate_stop_loss(
    entry_price,
    stop_percent
):

    stop_price = entry_price * (1 - stop_percent / 100)

    return stop_price