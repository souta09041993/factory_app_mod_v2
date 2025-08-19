
import os
from typing import Tuple
import pandas as pd
from datetime import datetime, timezone, timedelta

ENC = "utf-8-sig"
ROOT = os.path.dirname(os.path.dirname(__file__))
STOR = os.path.join(ROOT, "storage")
os.makedirs(STOR, exist_ok=True)

INVENTORY_CSV = os.path.join(STOR, "inventory.csv")
PRODUCT_MASTER_CSV = os.path.join(STOR, "product_master.csv")

INV_COLUMNS = ["product_code","exp_date","in_date","qty","updated_at"]
PM_COLUMNS = ["product_code","product_name"]

JST = timezone(timedelta(hours=9))

def _fmt_date(s: str) -> str:
    # accepts YYYY/MM/DD or YYYY-MM-DD; returns YYYY/MM/DD
    s = (s or "").strip()
    if not s:
        return datetime.now(JST).strftime("%Y/%m/%d")
    s = s.replace("-", "/")
    parts = s.split("/")
    if len(parts) == 3:
        y, m, d = parts
        return f"{int(y):04d}/{int(m):02d}/{int(d):02d}"
    raise ValueError(f"Invalid date: {s}")

def _now_str() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

def ensure_files():
    if not os.path.exists(INVENTORY_CSV):
        pd.DataFrame(columns=INV_COLUMNS).to_csv(INVENTORY_CSV, index=False, encoding=ENC)
    if not os.path.exists(PRODUCT_MASTER_CSV):
        pd.DataFrame(columns=PM_COLUMNS).to_csv(PRODUCT_MASTER_CSV, index=False, encoding=ENC)

def load_inventory() -> pd.DataFrame:
    ensure_files()
    df = pd.read_csv(INVENTORY_CSV, encoding=ENC)
    if len(df.columns) != len(INV_COLUMNS):
        # try to coerce columns (for older files)
        df = df.reindex(columns=INV_COLUMNS, fill_value="")
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0.0).astype(float)
    return df

def save_inventory(df: pd.DataFrame) -> None:
    df = df.reindex(columns=INV_COLUMNS)
    df.to_csv(INVENTORY_CSV, index=False, encoding=ENC)

def load_product_master() -> pd.DataFrame:
    ensure_files()
    df = pd.read_csv(PRODUCT_MASTER_CSV, encoding=ENC)
    if len(df.columns) != len(PM_COLUMNS):
        df = df.reindex(columns=PM_COLUMNS, fill_value="")
    return df

def inbound(product_code: str, exp_date: str, in_date: str, qty: float) -> Tuple[bool, str, pd.DataFrame]:
    """入庫：同一(product, exp)があるなら加算。in_dateは最新に更新（戻しは別関数）。"""
    try:
        qty = float(qty)
        if qty <= 0:
            return False, "数量は正の数で入力してください。", load_inventory()
        exp_norm = _fmt_date(exp_date)
        in_norm = _fmt_date(in_date)
        df = load_inventory()

        # 既存候補（product+exp）
        mask = (df["product_code"]==product_code) & (df["exp_date"]==exp_norm)
        if mask.any():
            # 同日行があれば加算、なければ代表行に加算して in_date を最新へ更新
            sub = df[mask]
            same_day = sub["in_date"] == in_norm
            idxs = sub[same_day].index.tolist()
            if idxs:
                i = idxs[0]
                df.at[i,"qty"] = float(df.at[i,"qty"]) + qty
                df.at[i,"updated_at"] = _now_str()
            else:
                # 代表行（qty>0の行優先、無ければ最初）
                rep_idx = sub[sub["qty"]>0].index.tolist() or sub.index.tolist()
                i = rep_idx[0]
                df.at[i,"qty"] = float(df.at[i,"qty"]) + qty
                # 最新入庫日へ更新
                cur_in = df.at[i,"in_date"]
                df.at[i,"in_date"] = max(cur_in, in_norm)
                df.at[i,"updated_at"] = _now_str()
        else:
            # 新規行
            new = {
                "product_code": product_code,
                "exp_date": exp_norm,
                "in_date": in_norm,
                "qty": qty,
                "updated_at": _now_str()
            }
            df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)

        save_inventory(df)
        return True, "入庫を反映しました。", df.sort_values(["product_code","exp_date","in_date"]).reset_index(drop=True)
    except Exception as e:
        return False, f"入庫エラー: {e}", load_inventory()

def outbound(product_code: str, exp_date: str, qty: float) -> Tuple[bool, str, pd.DataFrame]:
    """出庫：FIFO（in_date昇順）。不足ならエラー。"""
    try:
        qty = float(qty)
        if qty <= 0:
            return False, "数量は正の数で入力してください。", load_inventory()
        exp_norm = _fmt_date(exp_date)
        df = load_inventory()
        mask = (df["product_code"]==product_code) & (df["exp_date"]==exp_norm) & (df["qty"]>0)
        sub = df[mask].sort_values("in_date")
        total = float(sub["qty"].sum())
        if total < qty:
            return False, f"在庫不足：必要 {qty}、在庫 {total}", df

        remain = qty
        for i, row in sub.iterrows():
            have = float(row["qty"])
            if have >= remain:
                df.at[i,"qty"] = have - remain
                df.at[i,"updated_at"] = _now_str()
                remain = 0.0
                break
            else:
                df.at[i,"qty"] = 0.0
                df.at[i,"updated_at"] = _now_str()
                remain -= have

        save_inventory(df)
        return True, "出庫を反映しました。", df.sort_values(["product_code","exp_date","in_date"]).reset_index(drop=True)
    except Exception as e:
        return False, f"出庫エラー: {e}", load_inventory()

def return_in(product_code: str, exp_date: str, in_date: str, qty: float) -> Tuple[bool, str, pd.DataFrame]:
    """戻し：数量加算。ただし in_date は更新しない（指定日付を保持）。"""
    try:
        qty = float(qty)
        if qty <= 0:
            return False, "数量は正の数で入力してください。", load_inventory()
        exp_norm = _fmt_date(exp_date)
        in_norm = _fmt_date(in_date)
        df = load_inventory()
        mask = (df["product_code"]==product_code) & (df["exp_date"]==exp_norm) & (df["in_date"]==in_norm)
        if mask.any():
            i = df[mask].index[0]
            df.at[i,"qty"] = float(df.at[i,"qty"]) + qty
            df.at[i,"updated_at"] = _now_str()
        else:
            new = {
                "product_code": product_code,
                "exp_date": exp_norm,
                "in_date": in_norm,
                "qty": qty,
                "updated_at": _now_str()
            }
            df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)

        save_inventory(df)
        return True, "戻しを反映しました。", df.sort_values(["product_code","exp_date","in_date"]).reset_index(drop=True)
    except Exception as e:
        return False, f"戻しエラー: {e}", load_inventory()
