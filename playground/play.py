import pandas as pd


def play():
    karven_stock_file = "/Users/muhammed/Code/erp/playground/karven_stock.xlsx"
    stock_df = pd.read_excel(karven_stock_file)
    stock_df = stock_df[stock_df["quantity"].astype(float) >= 100].reset_index(
        drop=True
    )
    stock_df = stock_df[
        stock_df["client"] != "FIRAT TEKSTİL ve DERİ ÜRÜNLERİ SAN.TİC.LTD.ŞTİ"
    ].reset_index(drop=True)
    print(stock_df.head(20))
    # price_df =
    print(stock_df.shape[0])


# play()


import os
import re

directory_in_str = "/Users/muhammed/Code/demfirat/public/media/products/embroidered_sheer_curtain_fabrics"
directory = os.fsencode(directory_in_str)
print("the length is:", len(os.listdir(directory)))
for index, file in enumerate(os.listdir(directory)):
    filename = os.fsdecode(file)
    print(filename)
    sku = filename.split(".")[0]
    design = sku.split("_")[0]
    if sku.count("_") < 1:
        continue
    variant = sku.split("_")[1]
    design = design.split("-")[0]
    design = re.sub("[^0-9]", "", design)
    print(design)
    if design == "":
        continue
    design = int(design)
    if design < 2000:
        prefix = "N"
    else:
        prefix = "K"
    design = str(design)
    parent_sku = prefix + design 
    print("the parent sku is:", parent_sku, "variant is:", variant)

    # # print(filename)
    # print(index," : ",sku)
    # if filename.endswith(".asm") or filename.endswith(".py"):
    #     # print(os.path.join(directory, filename))
    #     continue
    # else:
    #     continue
