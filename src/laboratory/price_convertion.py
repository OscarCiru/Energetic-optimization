from datetime import datetime, timedelta
from pandas import DataFrame

initial_date: datetime = datetime(2023, 1, 1, 0, 0, 0)
final_date: datetime = datetime(2023, 12, 31, 23, 45, 0)

dates: list = [initial_date]
count: int = 1
while dates[-1] != final_date:
    dates.append(initial_date + timedelta(minutes=15*count))
    count += 1

purchase_prices: DataFrame = DataFrame()
purchase_prices['InitialDatetime'] = dates
purchase_prices['FinalDatetime'] = purchase_prices['InitialDatetime'].apply(lambda x: x + timedelta(minutes=15))

holidays: list = [datetime(2023, 1, 6), datetime(2023, 1, 24), datetime(2023, 3, 20), datetime(2023, 4, 6),
                  datetime(2023, 4, 7), datetime(2023, 5, 1), datetime(2023, 5, 2), datetime(2023, 5, 15),
                  datetime(2023, 8, 15), datetime(2023, 10, 12), datetime(2023, 11, 1), datetime(2023, 12, 6),
                  datetime(2023, 12, 8), datetime(2023, 12, 25)]

p1: float = 0.207
p2: float = 0.221
p3: float = 0.207
p4: float = 0.195
p5: float = 0.189
p6: float = 0.180

prices: list = []
for date in dates:
    if date.hour <= 7 or datetime(date.year, date.month, date.day) in holidays or (6 <= date.isoweekday() <= 7):
        prices.append(p6)
    elif date.month == 1 or date.month == 2 or date.month == 7 or date.month == 12:
        if (9 <= date.hour <= 13) or (18 <= date.hour <= 21):
            prices.append(p1)
        else:
            prices.append(p2)
    elif date.month == 3 or date.month == 11:
        if (9 <= date.hour <= 13) or (18 <= date.hour <= 21):
            prices.append(p2)
        else:
            prices.append(p3)
    elif date.month == 4 or date.month == 5 or date.month == 10:
        if (9 <= date.hour <= 13) or (18 <= date.hour <= 21):
            prices.append(p4)
        else:
            prices.append(p5)
    else:
        if (9 <= date.hour <= 13) or (18 <= date.hour <= 21):
            prices.append(p3)
        else:
            prices.append(p4)

purchase_prices['Magnitude'] = 'price'
purchase_prices['MagnitudeValue'] = prices
purchase_prices['MagnitudeUnits'] = '€/kWh'

purchase_prices.to_csv('prices.csv', sep=';', index=False)
