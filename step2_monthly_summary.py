import csv
from collections import defaultdict

input_file = "nasa_field_2022.csv"
output_file = "nasa_monthly_2022.csv"

monthly_precip = defaultdict(float)
monthly_temp = defaultdict(list)
monthly_moisture = defaultdict(list)

with open(input_file, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Extract month number (e.g., '20220114' -> 1)
        month = int(row["date"][4:6])
        precip = float(row["precip_mm"])
        temp = float(row["temp_c"])
        moisture = float(row["soil_moisture"])

        if precip >= 0:
            monthly_precip[month] += precip
        if temp > -90:
            monthly_temp[month].append(temp)
        if moisture >= 0:
            monthly_moisture[month].append(moisture)

with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["month", "total_precip_mm", "avg_temp_c", "avg_soil_moisture"])
    for m in range(1, 13):
        avg_t = sum(monthly_temp[m]) / len(monthly_temp[m])
        avg_sm = sum(monthly_moisture[m]) / len(monthly_moisture[m])
        writer.writerow([
            m,
            round(monthly_precip[m], 1),
            round(avg_t, 2),
            round(avg_sm, 3)
        ])

print(f"Done! Created 12-month summary in {output_file}")