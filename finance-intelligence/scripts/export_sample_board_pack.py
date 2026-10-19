"""Generate December synthetic example board outputs without an API call."""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.finance import build_kpis, compare_scenarios
from src.board_pack import board_pack
from src.workbook import style_workbook


if __name__ == '__main__':
    kpis = build_kpis(*(pd.read_csv(ROOT / 'data' / f'{n}.csv') for n in ['finance', 'operations', 'balances']))
    target = ROOT / 'examples'
    target.mkdir(exist_ok=True)
    (target / 'sustainable_packaging_board_2026-12.pptx').write_bytes(
        board_pack(kpis, '2026-12', 'Month', source='Synthetic sample data',
                   coverage_note='Complete synthetic period: all three datasets contain December 2026 actuals.'))
    with pd.ExcelWriter(target / 'sustainable_packaging_board_2026-12.xlsx', engine='openpyxl') as writer:
        compare_scenarios(kpis, '2026-12', 'budget').to_excel(writer, sheet_name='Actual vs Budget', index=False)
        compare_scenarios(kpis, '2026-12', 'forecast').to_excel(writer, sheet_name='Actual vs Forecast', index=False)
        kpis.to_excel(writer, sheet_name='KPI History', index=False)
        style_workbook(writer.book)
    print('Created synthetic PowerPoint and Excel board packs in examples/')
