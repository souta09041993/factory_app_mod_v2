
try:
    import FreeSimpleGUI as sg
except Exception:
    import PySimpleGUI as sg
from datetime import datetime
import pandas as pd
from ..usecase import inventory as uc
from ..infra.inventory_repo import ENC

DATE_TODAY = datetime.now().strftime("%Y/%m/%d")

TABLE_KEY = "-INV-TABLE-"
PM_COMBO_KEY = "-INV-PRODUCT-"
EXP_IN = "-INV-EXP-"
IN_IN = "-INV-IN-"
QTY_IN = "-INV-QTY-"
BTN_INBOUND = "-INV-INBOUND-"
BTN_OUTBOUND = "-INV-OUTBOUND-"
BTN_RETURN = "-INV-RETURN-"
MSG_TXT = "-INV-MSG-"

def _df_to_values(df: pd.DataFrame):
    if df.empty:
        return []
    return df.values.tolist()

def build_tab():
    inv_df, pm_df = uc.load_tables()
    pm_values = pm_df["product_code"].dropna().astype(str).tolist()

    layout = [
        [sg.Text("製品"), sg.Combo(pm_values, key=PM_COMBO_KEY, size=(20,1), enable_events=True),
         sg.Text("賞味期限"), sg.Input(DATE_TODAY, key=EXP_IN, size=(12,1)),
         sg.Text("入庫日"), sg.Input(DATE_TODAY, key=IN_IN, size=(12,1)),
         sg.Text("数量"), sg.Input("0", key=QTY_IN, size=(8,1)),
         sg.Button("入庫", key=BTN_INBOUND),
         sg.Button("出庫", key=BTN_OUTBOUND),
         sg.Button("戻し", key=BTN_RETURN)],
        [sg.Text("", key=MSG_TXT, size=(80,1))],
        [sg.Table(values=_df_to_values(inv_df),
                  headings=["製品","賞味期限","入庫日","数量","更新時刻"],
                  key=TABLE_KEY, auto_size_columns=False,
                  col_widths=[18,12,12,8,20],
                  num_rows=12, enable_events=False, justification="left")]
    ]
    return sg.Tab("在庫", layout, key="-INV-TAB-")

def handle_event(ev, vals, window):
    if ev in (BTN_INBOUND, BTN_OUTBOUND, BTN_RETURN):
        code = vals.get(PM_COMBO_KEY, "")
        exp = vals.get(EXP_IN, "")
        ind = vals.get(IN_IN, "")
        qty = vals.get(QTY_IN, "")
        if not code:
            window[MSG_TXT].update("製品コードを選択してください。")
            return

        if ev == BTN_INBOUND:
            ok, msg, df = uc.inbound(code, exp, ind, qty)
        elif ev == BTN_OUTBOUND:
            ok, msg, df = uc.outbound(code, exp, qty)
        else:
            ok, msg, df = uc.return_in(code, exp, ind, qty)

        window[MSG_TXT].update(msg)
        # テーブル更新（headingsは作成時のみ指定、updateは値だけ）
        window[TABLE_KEY].update(values=_df_to_values(df))
