
# NOTE: FreeSimpleGUIのAPIに合わせています（PySimpleGUIでも多くは互換）。
import os
from datetime import datetime
try:
    import FreeSimpleGUI as sg
except Exception:
    import PySimpleGUI as sg

from ..infra.logging_conf import get_logger
from ..usecase import inspection as uc
from ..infra import repo
from .inventory_ui import build_tab as build_inv_tab, handle_event as handle_inv_event

LOGGER = get_logger(__name__)

# --- Inspection (点検) キーをプレフィクス化 ---
I_LOAD = "-I-LOAD-"
I_SAVE = "-I-SAVE-"
I_EXPORT = "-I-EXPORT-"
I_SET_EXCEL = "-I-SET-EXCEL-"
I_YEAR = "-I-YEAR-"
I_MONTH = "-I-MONTH-"
I_MACHINE = "-I-MACHINE-"
I_TYPE = "-I-TYPE-"
I_GRID = "-I-GRID-"
I_EXCEL_TXT = "-I-EXCEL-PATH-TXT-"

def _grid_layout(state, font):
    items = list(state.items.keys())
    num_days = state.num_days
    header = [sg.Text("点検項目", size=(18,1), font=font)]
    header += [sg.Text(str(d), size=(3,1), justification="center", font=font) for d in range(1, num_days+1)]

    rows = []
    rows.append(header)
    for it in items:
        line = [sg.Text(it, size=(18,1), font=font)]
        row = state.items[it]
        for d in range(1, num_days+1):
            key = f"-I-CHECK_{it}_{d}-"
            label = row[d-1] if row[d-1] else "　"
            line.append(sg.Button(label, key=key, size=(2,1), pad=(1,1)))
        rows.append(line)

    # サイン行
    sign_row = [sg.Text("サイン", size=(18,1), font=font)]
    for d in range(1, num_days+1):
        key = f"-I-SIGN_{d}-"
        sign_row.append(sg.Input(state.sign[d-1], key=key, size=(4,1), pad=(1,1)))
    rows.append(sign_row)

    return rows

def build_inspection_tab():
    sg.theme("DarkBlue3")
    font = ("Meiryo UI", 10)

    now = datetime.now()
    year_spin = sg.Spin(values=list(range(now.year-1, now.year+3)), initial_value=now.year, key=I_YEAR)
    month_spin = sg.Spin(values=list(range(1,13)), initial_value=now.month, key=I_MONTH)
    machine_combo = sg.Combo(values=["1番充填","2番充填","3番充填"], default_value="1番充填", key=I_MACHINE, readonly=True, size=(12,1))
    type_combo = sg.Combo(values=["始業前点検","保全点検"], default_value="始業前点検", key=I_TYPE, readonly=True, size=(12,1))

    top = [
        [sg.Text("年"), year_spin, sg.Text("月"), month_spin, sg.Text("機械"), machine_combo, sg.Text("種別"), type_combo,
         sg.Button("読込/新規", key=I_LOAD), sg.Button("保存", key=I_SAVE), sg.Button("Excel出力", key=I_EXPORT)]
    ]

    st = uc.load_or_init_state(type_combo.DefaultValue, int(year_spin.DefaultValue), int(month_spin.DefaultValue), machine_combo.DefaultValue)
    grid_container = sg.Column(_grid_layout(st, font), key=I_GRID, scrollable=True, vertical_scroll_only=True, expand_x=True, expand_y=True, pad=(0,0))

    peek_path = repo.peek_excel_path_for_month(st.type_name, st.year, st.month) or "（未設定）"
    bottom = [
        [sg.Text("Excel保存先（参照時は未設定でもOK）："), sg.Text(peek_path, key=I_EXCEL_TXT),
         sg.Button("この年月のExcel保存先を設定", key=I_SET_EXCEL)]
    ]

    layout = top + [[grid_container]] + bottom
    return sg.Tab("点検", layout, key="-I-TAB-"), st, font

def rerender_grid(window, state, font):
    cont = window[I_GRID]
    if hasattr(cont, "Widget"):
        for child in cont.Widget.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass
    cont.Widget.update()
    cont.Layout(_grid_layout(state, font))
    cont.Widget.update()

def build_window():
    # 点検タブ
    i_tab, i_state, i_font = build_inspection_tab()
    # 在庫タブ
    v_tab = build_inv_tab()

    tabs = sg.TabGroup([[i_tab, v_tab]], expand_x=True, expand_y=True, key="-TABGROUP-")
    win = sg.Window("工場アプリ（点検・在庫 統合版）", [[tabs]], resizable=True, finalize=True)
    return win, i_state, i_font

def main_loop():
    window, i_state, i_font = build_window()
    while True:
        ev, vals = window.read(timeout=100)
        if ev in (sg.WIN_CLOSED, None):
            break

        # --- 点検 ---
        if ev == I_LOAD:
            year = int(vals[I_YEAR]); month = int(vals[I_MONTH]); machine = vals[I_MACHINE]; type_name = vals[I_TYPE]
            i_state = uc.load_or_init_state(type_name, year, month, machine)
            rerender_grid(window, i_state, i_font)
            peek = repo.peek_excel_path_for_month(type_name, year, month) or "（未設定）"
            window[I_EXCEL_TXT].update(peek)

        elif ev == I_SAVE:
            for d in range(1, i_state.num_days+1):
                s = vals.get(f"-I-SIGN_{d}-", "")
                uc.set_sign(i_state, d, s)
            path = uc.save_state(i_state)
            sg.popup_no_wait(f"保存しました：\n{path}")

        elif ev == I_EXPORT:
            for d in range(1, i_state.num_days+1):
                s = vals.get(f"-I-SIGN_{d}-", "")
                uc.set_sign(i_state, d, s)
            peek = repo.peek_excel_path_for_month(i_state.type_name, i_state.year, i_state.month)
            if peek and os.path.isdir(os.path.dirname(peek)):
                save_path = peek
            else:
                fname = f"{i_state.type_name}_{i_state.year}-{i_state.month:02d}_{i_state.machine}.xlsx".replace("/", "_")
                save_path = os.path.join(os.getcwd(), fname)
            out = uc.export_excel(i_state, save_path)
            sg.popup_no_wait(f"Excel出力完了：\n{out}")

        elif ev == I_SET_EXCEL:
            try:
                save_to = sg.popup_get_file("保存先Excelファイルを選択または入力", save_as=True, default_extension=".xlsx", file_types=(("Excel", "*.xlsx"),))
                if save_to:
                    repo.set_excel_path_for_month(i_state.type_name, i_state.year, i_state.month, save_to)
                    window[I_EXCEL_TXT].update(save_to)
            except Exception as e:
                LOGGER.error(e)

        elif isinstance(ev, str) and ev.startswith("-I-CHECK_"):
            try:
                _, item, day = ev.replace("-I-CHECK_", "").rstrip("-").split("_", 2)
                day = int(day)
                uc.toggle_item(i_state, item, day)
                label = i_state.items[item][day-1] if i_state.items[item][day-1] else "　"
                window[ev].update(label)
            except Exception as e:
                LOGGER.error(e)

        # --- 在庫 ---
        else:
            handle_inv_event(ev, vals, window)

    window.close()
