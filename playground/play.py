import pandas as pd
df = pd.read_excel("karven_stock.xlsx", header=0)
df = df.dropna(how="all").dropna(axis=1, how="all")
print(df.head())