import pandas as pd
import numpy as np

df = pd.read_csv("../data/PhiUSIIL.csv")

print("Shape:", df.shape)
print("\nColumns:\n", list(df.columns))
print("\nMissing values total:", df.isnull().sum().sum())
print("\nLabel distribution:\n", df['label'].value_counts() if 'label' in df.columns else "no 'label' col")

# PhiUSIIL uses column name 'label' -> 1 = legitimate, 0 = phishing
for col in df.columns:
    if col.lower() == 'label':
        print("\nFound label col:", col)

print("\nDtypes:\n", df.dtypes.value_counts())
print("\nSample row:\n", df.iloc[0])
