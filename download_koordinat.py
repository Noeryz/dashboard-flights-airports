import pandas as pd

url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"

kolom = ["Airport_ID","Name","City","Country","IATA","ICAO","Latitude","Longitude",
         "Altitude","Timezone","DST","Tz_Database","Type","Source"]

df_coords = pd.read_csv(url, names=kolom, header=None, keep_default_na=False)
df_coords = df_coords[["IATA", "Latitude", "Longitude"]]

df_coords.to_csv("airports_coords.csv", index=False)
print("Selesai, tersimpan:", df_coords.shape)