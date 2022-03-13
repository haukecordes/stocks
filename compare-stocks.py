# preinstalled with python
import csv
import json
import os
import time
import webbrowser

# not preinstalled
from requests import get
from pandas import read_csv


def trick_detection(url):
    webbrowser.open(url, new=0)
    counter = 25
    while True:
        counter -= 1
        if str(get(url)) == "<Response [200]>":
            break
        else:
            time.sleep(.2)
            print("waiting for response...")
            if counter < 1:
                raise Exception("Not a symbol or Timeout!")
    print("Opening", url, "...")


def get_data(symbol, side, time_period):
    url_infos = f"https://seekingalpha.com/api/v3/symbols/{symbol}"
    url_price = f"https://finance.api.seekingalpha.com/v2/real-time-prices?symbols={symbol}"
    url_data = f"https://seekingalpha.com/symbol/{symbol}/financials-data?period_type={time_period}&statement_type=" \
               f"{side}&order_type=latest_right&is_pro=false"
    if side == "income-statement" or side == "balance-sheet":
        url = url_data
    elif side == "summary":
        url = url_infos
    elif side == "prices":
        url = url_price
    else:
        raise Exception("Side does not exist")

    if not os.path.exists(f"Json Files/{symbol}-{time_period}-{side}.json"):
        trick_detection(url)
        response = get(url)
        data = response.json()

        print(f"Data for {symbol}-{time_period}-{side} collected")

        with open(f'Json Files/{symbol}-{time_period}-{side}.json', 'w') as fp:
            json.dump(data, fp)

        print(f"{symbol}-{time_period}-{side}.json downloaded from seeking alpha")

    else:
        with open(f"Json Files/{symbol}-{time_period}-{side}.json") as json_file:
            data = json.load(json_file)
            print(f"{symbol}-{time_period}-{side}.json loaded from drive")

    wanted_data = decode(data, side)

    return wanted_data


def decode(data, side):
    decoded_data = {}

    if side == "income-statement" or side == "balance-sheet":
        if side == "income-statement":
            keys = ["Net Income", "Total Revenues", "Basic EPS"]
        else:
            keys = ["Total Current Assets", "Total Assets", "Total Current Liabilities", "Total Equity", "Inventory"]

        for k in range(len(data["data"])):
            for j in range(len(data["data"][k])):
                for i in range(len((data["data"][k][j]))):
                    tr1 = data["data"][k][j][i]["name"]
                    tr2 = data["data"][k][j][i]["value"]
                    name = str(data["data"][k][j][0]["value"])
                    if tr2[0] != "<" and name in keys:
                        name = name.replace(" ", "-")
                        if i != 0:
                            decoded_data.setdefault(name, {})
                            decoded_data[name][tr1] = tr2.replace(',', '')

    elif side == "summary":
        decoded_data["sector"] = data["included"][0]["attributes"]["name"]
        decoded_data["industry"] = data["included"][1]["attributes"]["name"]
        try:
            decoded_data["company"] = data["data"]["attributes"]["company"]
        except KeyError:
            pass
        try:
            decoded_data["company2"] = data["data"][0]["attributes"]["company"]
        except KeyError:
            pass
        decoded_data["exchange"] = data["data"]["attributes"]["exchange"]

    else:
        decoded_data["last"] = data["data"][0]["attributes"]["last"]

    return decoded_data


def use_data(symbol, data):
    # given: ["Net Income", "Total Revenues", "Basic EPS", "Total Current Assets", "Total Assets",
    #          "Total Current Liabilities", "Total Equity", "Inventory"]

    sorted_data = []
    to_sort = data[symbol]

    for time in list(to_sort["Basic-EPS"].keys()):
        eps = to_sort["Basic-EPS"]
        tca = to_sort["Total-Current-Assets"]
        tcl = to_sort["Total-Current-Liabilities"]
        ni = to_sort["Net-Income"]
        tr = to_sort["Total-Revenues"]
        ta = to_sort["Total-Assets"]
        te = to_sort["Total-Equity"]

        try:
            inv = to_sort["Inventory"]
            if "-" in list(inv.values()):
                for _key in list(inv.keys()):
                    inv[_key] = "0"
            all_values = [eps, tca, inv, tcl, ni, tr, ta, te]

        except KeyError:
            inv = 0
            all_values = [eps, tca,  tcl, ni, tr, ta, te]

        for i, v in enumerate(all_values):
            try:
                v = v[time].replace("$", "")
            except KeyError:
                v = v["Last Report"].replace("$", "")

            if type(v) == str and v[0] == "(" and v[-1] == ")":
                v = "-" + v[1:-2]

            all_values[i] = float(v)

        if inv:
            eps, tca, inv, tcl, ni, tr, ta, te = all_values
        else:
            eps, tca, tcl, ni, tr, ta, te = all_values

        qr = (tca - inv) / tcl
        npm = ni / tr
        at = tr / ta
        em = ta / te
        roe = ni / te

        all_computed = [symbol, time, eps, qr, npm, at, em, roe]
        for i, x in enumerate(all_computed):
            all_computed[i] = round(x, 3) if type(x) != str else x

        sorted_data += [all_computed]

    return sorted_data


def use_infos(symbol, data, time_period):
    data = data[symbol]

    try:
        company = data["company"]
    except KeyError:
        company = data["company2"]

    sector = data["sector"]
    ind = data["industry"]
    exc = data["exchange"]
    price = data["last"]
    key = list(data["Basic-EPS"].keys())[-1]
    earnings_per_share_ttm = data["Basic-EPS"][key]
    pe = round(float(str(price).replace("$", "")) /
               float(str(earnings_per_share_ttm).replace("$", "").replace("(", "-").replace(")", "")), 3)
    if not time_period == "annual":
        pe *= (1 / 4)
    sorted_infos = [[symbol, price, pe, company, sector, ind, exc]]
    return sorted_infos


def get_symbols():
    print("Enter one or multiple symbols to compare their stocks!")
    print("To compute enter an empty input.")

    syms = []
    while True:
        try:
            sym = str(input("Stock symbol: ")).upper().strip()
        except ValueError:
            print("Enter a valid stock symbol!")
        if sym == "" and syms:
            return syms
        elif sym == "":
            print("Enter a valid stock symbol!")
        else:
            syms.append(sym)


def get_time_period():
    time_periods = ["annual", "quarterly", "ttm-by-quarter"]
    while True:
        user_input = input("Chose a period type ('annual', 'quarterly', 'ttm-by-quarter'): ").lower().strip()
        if user_input in time_periods or user_input in ["0", "1", "2"]:
            if user_input in ["0", "1", "2"]:
                user_input = time_periods[int(user_input)]
            return user_input
        else:
            print("Input not a viable option!")


# main stuff
while True:
    symbols = get_symbols()
    comparison = {}
    short_comparison = {}
    period = get_time_period()

    # create folders
    folders = ["Json Files", "CSV Files", "Excel Files"]
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)

    # different places to pull json files from
    sides = ["income-statement", "balance-sheet", "summary", "prices"]

    try:
        for symbol in symbols:
            # get data
            symbol_data = {f"{symbol}": {}}
            for side in sides:
                if side in ["summary", "prices"]:
                    _period = "now"
                else:
                    _period = period
                symbol_data[symbol].update(get_data(symbol, side, _period))

            # store data as json
            json_string = json.dumps(symbol_data)
            with open(f"Json Files/{symbol}-{period}-data.json", "w") as json_file:
                json.dump(symbol_data, json_file)

            # use data for calculation
            comparison[f"{symbol}"] = use_data(symbol, symbol_data)
            short_comparison[f"{symbol}"] = use_infos(symbol, symbol_data, period)

    except IndexError as e:
        raise Exception("Wanted Data was not at expected position!\n", e)
    except:
        raise Exception("Something went wrong :(\nCheck your symbol!")

    # save calculations as csv files
    with open(f"CSV Files/{period}-comparison.csv", "w") as csv_file:
        csv_writer = csv.writer(csv_file)
        to_compute = ["stock", "time-interval", "earnings-per-share", "quick-ratio", "net-profit-margin",
                      "asset-turnover", "equity-multiplier", "return on investment"]

        csv_writer.writerow(to_compute)
        for stock in comparison.values():
            for row in stock:
                csv_writer.writerow(row)

    with open(f"CSV Files/{period}-short_comparison.csv", "w") as csv_file_short:
        csv_writer = csv.writer(csv_file_short)
        to_compute_short = ["symbol", "last", "PE", "company", "sector", "industry", "exchange"]

        csv_writer.writerow(to_compute_short)
        for stock in short_comparison.values():
            for row in stock:
                csv_writer.writerow(row)

    # convert csv files to Excel Worksheets for easy access
    symbols_as_str = "("
    for i, sym in enumerate(symbols):
        if i == 0:
            symbols_as_str += str(sym)
        else:
            symbols_as_str += "--" + str(sym)
    symbols_as_str += ")"

    read_long = read_csv(f'CSV Files/{period}-comparison.csv')
    read_long.to_excel(f'Excel Files/FundamentalsComparison-{period}-{symbols_as_str}.xlsx', index=None, header=True)

    read_short = read_csv(f'CSV Files/{period}-short_comparison.csv')
    read_short.to_excel(f'Excel Files/ShortComparison-{period}-{symbols_as_str}.xlsx', index=None, header=True)

    print("\n#####\nYour Excel Worksheets have been created. You can find them in the 'Excel Files' folder. :)\n"
          "(all browser tabs are no longer needed)\n#####")

    input("\n Hit enter to restart...")
