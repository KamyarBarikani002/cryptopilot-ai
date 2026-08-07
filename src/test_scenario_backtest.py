from src.backtest.scenario_backtest import run_scenario_backtest



def build_market(btc_prices):

    return {

        "BTC": btc_prices,

        "ETH": [
            x * 0.05
            for x in btc_prices
        ],

        "LINK": [
            x * 0.0003
            for x in btc_prices
        ],

        "ONDO": [
            x * 0.00002
            for x in btc_prices
        ],

        "NEAR": [
            x * 0.00008
            for x in btc_prices
        ]

    }



scenarios = {


    "BULL MARKET":

    build_market(
        [
            60000,
            61000,
            62000,
            63000,
            64000,
            65000,
            66000,
            68000,
            70000,
            72000,
            74000,
            76000,
            78000,
            80000,
            82000,
            84000,
            86000,
            88000,
            90000,
            92000,
            95000,
            100000,
            105000
        ]
    ),



    "BEAR MARKET":

    build_market(
        [
            105000,
            100000,
            95000,
            90000,
            85000,
            80000,
            75000,
            70000,
            65000,
            60000,
            55000,
            50000,
            48000,
            46000,
            44000,
            42000,
            40000,
            38000,
            36000,
            35000,
            34000,
            33000,
            32000
        ]
    ),



    "CRASH RECOVERY":

    build_market(
        [
            80000,
            78000,
            75000,
            70000,
            65000,
            60000,
            55000,
            50000,
            48000,
            52000,
            58000,
            65000,
            72000,
            80000,
            88000,
            95000,
            100000,
            105000,
            110000,
            115000,
            120000,
            125000,
            130000
        ]
    )

}



report = run_scenario_backtest(
    scenarios,
    200
)



print("========================")
print("Scenario Comparison")
print("========================")


for name, result in report.items():

    print()

    print(name)

    print(
        "Final:",
        result["final_value"],
        "$"
    )

    print(
        "Profit:",
        result["profit"],
        "$"
    )

    print(
        "Return:",
        result["return"],
        "%"
    )

    print(
        "Max Drawdown:",
        result["drawdown"],
        "%"
    )

    print(
        "Allocation Changes:",
        result["regime_changes"]
    )


print("========================")
