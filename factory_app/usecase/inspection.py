
from typing import List, Dict, Any
from dataclasses import asdict
from ..domain.state import MonthlyState, CIRCLE
from ..infra import repo
from ..infra.excel_export import export_monthly_check_sheet
from ..infra.logging_conf import get_logger

LOGGER = get_logger(__name__)

def load_or_init_state(type_name: str, year: int, month: int, machine: str) -> MonthlyState:
    data = repo.load_monthly_state(type_name, year, month, machine)
    items_master = repo.default_items(type_name)
    if data is None:
        st = MonthlyState(year=year, month=month, machine=machine, type_name=type_name)
        st.ensure_shapes(items_master)
        return st
    st = MonthlyState(**data)
    st.ensure_shapes(items_master)
    return st

def save_state(state: MonthlyState) -> str:
    return repo.save_monthly_state(state.type_name, state.year, state.month, state.machine, asdict(state))

def toggle_item(state: MonthlyState, item: str, day: int) -> None:
    if item not in state.items:
        raise KeyError(f"Unknown item: {item}")
    idx = day - 1
    row = state.items[item]
    row[idx] = CIRCLE if row[idx] != CIRCLE else ""
    state.items[item] = row

def set_sign(state: MonthlyState, day: int, text: str) -> None:
    idx = day - 1
    state.sign[idx] = text

def export_excel(state: MonthlyState, save_path: str) -> str:
    items = list(state.items.keys())
    return export_monthly_check_sheet(
        year=state.year, month=state.month, machine=state.machine, type_name=state.type_name,
        items=items, matrix=state.items, signs=state.sign, save_path=save_path
    )
