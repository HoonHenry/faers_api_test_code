import json
import pandas as pd


def save_json(data, fname:str) -> None:
    with open(fname, 'w', encoding='utf-8') as wj:
        json.dump(data, wj, ensure_ascii=False, indent=2)

    return

def save_tsv(data, fname:str, **kw) -> None:
    df = pd.DataFrame(data)

    sep = '\t'
    index_bool = False
    header_bool = False
    
    df.to_csv(fname, sep=sep, index=index_bool, header=header_bool)

    return
