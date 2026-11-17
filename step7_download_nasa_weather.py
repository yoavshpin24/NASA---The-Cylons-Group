import requests
import pandas as pd

LAT = 0.5
LON = 34.5

START_DATE = "20190501"
END_DATE = "20191130"

url = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR,T2M&community=AG&longitude={LON}&latitude={LAT}&start={START_DATE}&end={END_DATE}&format=JSON"

print("Fetching daily climate data from NASA POWER...")
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    
    dates = list(data["properties"]["parameter"]["PRECTOTCORR"].keys())
    precip = list(data["properties"]["parameter"]["PRECTOTCORR"].values())
    temp = list(data["properties"]["parameter"]["T2M"].values())
    
    df = pd.DataFrame({
        "date": dates,
        "precipitation_mm": precip,
        "temperature_c": temp
    })
    
    df = df[df["precipitation_mm"] != -999.0]
    df = df[df["temperature_c"] != -999.0]
    
    output_file = "nasa_climate_kenya_2019.csv"
    df.to_csv(output_file, index=False)
    print(f"  -> Success! Climate data saved to {output_file}")
    print(df.head())
else:
    print(f"Error fetching data: HTTP {response.status_code}")