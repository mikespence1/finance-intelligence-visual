"""Readable brand styling for generated Excel management packs."""
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def style_workbook(workbook):
    for sheet in workbook.worksheets:
        sheet.freeze_panes = 'B2'
        sheet.sheet_view.showGridLines = False
        sheet.sheet_view.zoomScale = 110
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.fill = PatternFill('solid', fgColor='0B1F33')
            cell.font = Font(name='Aptos', size=16, bold=True, color='FFFFFF')
            cell.alignment = Alignment(vertical='center', wrap_text=True)
            cell.border = Border(bottom=Side(style='medium', color='00A6A6'))
        sheet.row_dimensions[1].height = 52
        for row in sheet.iter_rows(min_row=2):
            sheet.row_dimensions[row[0].row].height = 34
            for cell in row:
                cell.fill = PatternFill('solid', fgColor='F8FAFC' if cell.row % 2 else 'E8EEF5')
                header = str(sheet.cell(1, cell.column).value)
                cell.font = Font(name='Aptos', size=14, color='0B1F33', bold=header == 'Actual')
                cell.alignment = Alignment(vertical='center')
                cell.border = Border(top=Side(style='thin', color='FFFFFF'),
                                     bottom=Side(style='thin', color='C4D0DE'),
                                     right=Side(style='thin', color='D5DFEA'))
                if isinstance(cell.value, (int, float)):
                    cell.number_format = '#,##0.0;[Red](#,##0.0);0.0'
        for column in sheet.columns:
            maximum = max(len(str(cell.value or '')) for cell in column)
            sheet.column_dimensions[get_column_letter(column[0].column)].width = min(46, max(20, maximum+5))
