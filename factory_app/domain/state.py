
from dataclasses import dataclass, field
from typing import Dict, List

CIRCLE = "○"

@dataclass
class MonthlyState:
    year: int
    month: int
    machine: str
    type_name: str  # 点検種別（例：始業前点検／保全点検）
    # 点検項目ごとに日毎の記録（"○" or ""）
    items: Dict[str, List[str]] = field(default_factory=dict)
    # サイン／担当者名（各日）
    sign: List[str] = field(default_factory=list)

    @property
    def num_days(self) -> int:
        import calendar
        return calendar.monthrange(self.year, self.month)[1]

    def ensure_shapes(self, master_items: List[str]) -> None:
        """items と sign の長さを month 日数に合わせて整形"""
        nd = self.num_days
        # items: master_items に合わせて並び替え・不足分を追加
        normalized = {}
        for it in master_items:
            row = self.items.get(it, [])
            row = (row + [""] * nd)[:nd]
            normalized[it] = row
        self.items = normalized
        # sign
        self.sign = (self.sign + [""] * nd)[:nd]
