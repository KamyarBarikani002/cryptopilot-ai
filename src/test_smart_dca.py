from smart_dca import get_dca_triggers


price = 63500
ma = 64300
rsi = 15.5


triggers = get_dca_triggers(
    price,
    ma,
    rsi
)


print("================")
print("SMART DCA")
print("================")


for step, rule in triggers.items():
    print(step, ":", rule)