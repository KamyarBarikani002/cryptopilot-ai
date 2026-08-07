from risk_manager import calculate_position_size, calculate_stop_loss


capital = 200

risk_percent = 2

stop_loss_percent = 3

entry_price = 63500


position = calculate_position_size(
    capital,
    risk_percent,
    stop_loss_percent
)


stop = calculate_stop_loss(
    entry_price,
    stop_loss_percent
)


print("======================")
print("Risk Manager Test")
print("======================")

print("Capital:", capital, "$")
print("Risk:", risk_percent, "%")
print("Entry:", entry_price)

print("----------------------")

print("Position Size:", round(position, 2), "$")
print("Stop Loss:", round(stop, 2))