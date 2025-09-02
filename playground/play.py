import pandas as pd


def play():
    karven_stock_file = "/Users/muhammed/Code/erp/playground/karven_stock.xlsx"
    stock_df = pd.read_excel(karven_stock_file)
    stock_df = stock_df[stock_df["quantity"].astype(float) >= 100].reset_index(
        drop=True
    )
    stock_df = stock_df[stock_df["client"] != "FIRAT TEKSTİL ve DERİ ÜRÜNLERİ SAN.TİC.LTD.ŞTİ"].reset_index(drop=True)
    print(stock_df.head(20))
    # price_df =
    print(stock_df.shape[0])


play()
