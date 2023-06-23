from datetime import datetime, timedelta
from pandas import DataFrame

initial_date: datetime = datetime(2023, 6, 5, 0, 0, 0)
final_date: datetime = datetime(2023, 6, 11, 23, 45, 0)

dates: list = [initial_date]
count: int = 1
while dates[-1] != final_date:
    dates.append(initial_date + timedelta(minutes=15*count))
    count += 1

contracted_power: DataFrame = DataFrame()
contracted_power['InitialDatetime'] = dates
contracted_power['FinalDatetime'] = contracted_power['InitialDatetime'].apply(lambda x: x + timedelta(minutes=15))

holidays: list = [datetime(2023, 1, 6), datetime(2023, 1, 24), datetime(2023, 3, 20), datetime(2023, 4, 6),
                  datetime(2023, 4, 7), datetime(2023, 5, 1), datetime(2023, 5, 2), datetime(2023, 5, 15),
                  datetime(2023, 8, 15), datetime(2023, 10, 12), datetime(2023, 11, 1), datetime(2023, 12, 6),
                  datetime(2023, 12, 8), datetime(2023, 12, 25)]

p1: float = 2172
p2: float = 2222

power: list = []
for date in dates:
    if date.hour <= 7 or datetime(date.year, date.month, date.day) in holidays or (6 <= date.isoweekday() <= 7):
        power.append(p2)
    else:
        power.append(p1)

contracted_power['Magnitude'] = 'contracted_power'
contracted_power['MagnitudeValue'] = power
contracted_power['MagnitudeUnits'] = 'kW'

contracted_power.to_csv('contractedPower.csv', sep=';', index=False)
