import pandas as pd
import json

xls = pd.ExcelFile("READY.xlsx")
df1 = pd.read_excel(xls, "Sheet1")
df2 = pd.read_excel(xls, "VARIANT")

print(df2)

# product_json = {}

# for index, row in dataframe.iterrows():
#     product_json[index] = {
#         "title": row['title'],
#         "description": row['description'],
#         "image": row['image'],
#         "category": row['category']
#     }

# out = df1.to_json(orient='records')[1:-1].replace('},{', '} {')
out = "["
out += df1.to_json(orient="records")[1:-1] + "]"

product_json = []

data = json.loads(out)
print(type(data))
for index, item in enumerate(data):
    # print(item)
    # print("--------------------------------")
    # Below code eliminates the None values from the dictionary (deleted keys with None values)
    filtered_item = {k: v for k, v in item.items() if v is not None}
    product_json.append({"model": "marketing.Product", "pk": index + 1, "fields": filtered_item})

# print("your product json is: ")
# print(product_json)

# filtered_data = {k: v for k, v in data.items() if v is not None}




with open('../erp/marketing/fixtures/marketing/Product.json', 'w') as f:
    json.dump(product_json, f)
