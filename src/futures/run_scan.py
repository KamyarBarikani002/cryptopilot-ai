from src.futures.scanner import scan_market


def print_opportunity(o):

    print(
        o["symbol"],
        "|", o["direction"],
        "| Score:", o["score"],
        "| Entry:", o["entry_price"],
        "| Stop Loss:", o["stop_loss_price"],
        "| Take Profit:", o["take_profit_price"],
        "| Leverage:", str(o["leverage"]) + "x",
        "| Position Size: $" + str(o["position_size_usd"]),
        "| Margin: $" + str(o["margin_required_usd"])
    )


result = scan_market()

print("========================================")
print("اسکن بازار فیوچرز -", result["scanned"], "ارز بررسی شد")
print("========================================")

print()
print("----------------------------------------")
print("فرصت‌های LONG")
print("----------------------------------------")

if result["longs"]:
    for opportunity in result["longs"]:
        print_opportunity(opportunity)
else:
    print("در حال حاضر فرصت لانگ واضحی پیدا نشد.")

print()
print("----------------------------------------")
print("فرصت‌های SHORT")
print("----------------------------------------")

if result["shorts"]:
    for opportunity in result["shorts"]:
        print_opportunity(opportunity)
else:
    print("در حال حاضر فرصت شارت واضحی پیدا نشد.")

if result["skipped"]:
    print()
    print("----------------------------------------")
    print(len(result["skipped"]), "ارز به دلیل خطا رد شدند")
    print("----------------------------------------")

    for item in result["skipped"]:
        print(item["symbol"], ":", item["error"])

print()
print("========================================")
print("⚠️  این خروجی فقط پیشنهاد بر اساس تحلیل تکنیکال ساده (MA/RSI) است، نه تضمین سود.")
print("⚠️  اهرم پیشنهادی محافظه‌کارانه و تخمینی است؛ لیکویید شدن واقعی به مارجین نگهداری،")
print("    کارمزد و فاندینگ صرافی هم بستگی دارد و ممکن است زودتر از حد ضرر اتفاق بیفتد.")
print("========================================")
