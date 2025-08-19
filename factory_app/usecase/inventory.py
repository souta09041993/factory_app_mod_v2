
from typing import Tuple, List
import pandas as pd
from ..infra import inventory_repo as repo

def load_tables() -> Tuple[pd.DataFrame, pd.DataFrame]:
    inv = repo.load_inventory()
    pm = repo.load_product_master()
    return inv, pm

def inbound(product_code: str, exp_date: str, in_date: str, qty: str):
    try:
        q = float(qty)
    except Exception:
        return False, "数量は数値で入力してください。", repo.load_inventory()
    return repo.inbound(product_code, exp_date, in_date, q)

def outbound(product_code: str, exp_date: str, qty: str):
    try:
        q = float(qty)
    except Exception:
        return False, "数量は数値で入力してください。", repo.load_inventory()
    return repo.outbound(product_code, exp_date, q)

def return_in(product_code: str, exp_date: str, in_date: str, qty: str):
    try:
        q = float(qty)
    except Exception:
        return False, "数量は数値で入力してください。", repo.load_inventory()
    return repo.return_in(product_code, exp_date, in_date, q)
