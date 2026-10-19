"""Editable PowerPoint export using the same calculated KPIs as the dashboard."""
from io import BytesIO

import pandas as pd
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt

from src.finance import METRIC_GROUPS, compare_scenarios
from src.presentation import METRIC_LABELS, format_metric, period_label, title_case

NAVY, TEAL, GREY = '0B1F33', '00A6A6', '667085'


def board_pack(kpis, selected, grain, currency='AED', source='Uploaded data', coverage_note=''):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    title_period = period_label(selected, grain)

    def text(slide, value, x, y, w, h, size=16, color=NAVY, bold=False):
        box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        box.text_frame.word_wrap = True
        for i, line in enumerate(value.split('\n')):
            p = box.text_frame.paragraphs[0] if i == 0 else box.text_frame.add_paragraph()
            p.text = line
            p.font.size, p.font.bold = Pt(size), bold
            p.font.color.rgb = RGBColor.from_string(color)
        return box

    def raised_card(page, x, y, width, height):
        # Layered, editable shapes provide depth without rasterising the pack.
        shadow = page.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x+.06), Inches(y+.07), Inches(width), Inches(height))
        shadow.fill.solid()
        shadow.fill.fore_color.rgb = RGBColor.from_string('C4D0DE')
        shadow.line.fill.background()
        box = page.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(width), Inches(height))
        box.fill.gradient()
        box.fill.gradient_stops[0].color.rgb = RGBColor.from_string('FFFFFF')
        box.fill.gradient_stops[1].color.rgb = RGBColor.from_string('E8EEF5')
        box.line.color.rgb = RGBColor.from_string('D5DFEA')
        return box

    def slide(title, subtitle=''):
        page = prs.slides.add_slide(prs.slide_layouts[6])
        page.background.fill.solid()
        page.background.fill.fore_color.rgb = RGBColor.from_string('F8FAFC')
        text(page, 'SUSTAINABLE PACKAGING / BOARD REPORT', .5, .2, 12, .3, 11, TEAL, True)
        text(page, title_case(title), .5, .65, 12.3, .65, 28, bold=True)
        text(page, subtitle, .5, 1.35, 12.3, .65, 12, GREY)
        text(page, f'{title_period} | {currency} | {source} | {len(prs.slides):02d}', .5, 7.08, 12.3, .25, 10, GREY)
        raised_card(page, .45, 2.0, 12.35, 4.9)
        return page

    actual = kpis[(kpis.label == selected) & (kpis.scenario == 'actual')].iloc[0]
    page = slide('Sustainable packaging performance', f'{title_period} | Monthly board meeting pack' if grain == 'Month' else title_period)
    for i, metric in enumerate(['Revenue', 'EBITDA', 'Scrap Rate %', 'Cash']):
        x, y = .55 + (i % 2) * 6.3, 2.25 + (i // 2) * 1.65
        raised_card(page, x, y, 5.95, 1.4)
        text(page, title_case(metric), x+.15, y+.1, 5.5, .4, 18, GREY)
        text(page, format_metric(actual[metric], metric, currency), x+.15, y+.5, 5.5, .7, 32, bold=True)
    text(page, coverage_note, .55, 5.8, 12, .9, 12, GREY)

    for heading, metrics in METRIC_GROUPS.items():
        page = slide(heading, 'Actual vs budget and forecast | Delta = actual minus comparator; margin/rate deltas are percentage points.')
        budget = compare_scenarios(kpis, selected, 'budget').set_index('Metric')
        forecast = compare_scenarios(kpis, selected, 'forecast').set_index('Metric')
        headers = ['Metric', 'Actual', 'Budget', 'Δ budget', 'Forecast', 'Δ forecast']
        table = page.shapes.add_table(len(metrics)+1, 6, Inches(.5), Inches(2.1), Inches(12.3), Inches(.47*(len(metrics)+1))).table
        for col, width in zip(table.columns, [3.5, 1.85, 1.85, 1.6, 1.85, 1.65]):
            col.width = Inches(width)
        for row_index, values in enumerate([headers] + [
            [title_case(METRIC_LABELS.get(m, m)), format_metric(actual[m], m, currency),
             format_metric(budget.loc[m, 'Budget'], m, currency),
             ('No Data' if pd.isna(budget.loc[m, 'Variance']) else f"{budget.loc[m, 'Variance']:+,.1f}" + (' pp' if '%' in m else '')),
             format_metric(forecast.loc[m, 'Forecast'], m, currency),
             ('No Data' if pd.isna(forecast.loc[m, 'Variance']) else f"{forecast.loc[m, 'Variance']:+,.1f}" + (' pp' if '%' in m else ''))]
            for m in metrics]):
            for column_index, value in enumerate(values):
                cell = table.cell(row_index, column_index)
                cell.text = value
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor.from_string(NAVY if row_index == 0 else ('FFFFFF' if row_index % 2 else 'E2E8F0'))
                for p in cell.text_frame.paragraphs:
                    p.font.size = Pt(14)
                    p.font.bold = row_index == 0
                    p.font.color.rgb = RGBColor.from_string('FFFFFF' if row_index == 0 else NAVY)

    for metric in ['Revenue', 'EBITDA', 'Scrap Rate %', 'Return Rate %']:
        page = slide(f'{metric} | performance trend', 'Editable chart | Actual, budget and forecast. Missing data remains unavailable.')
        data = CategoryChartData()
        labels = sorted(kpis.label.unique())
        data.categories = [period_label(label, grain) for label in labels]
        for scenario in ['actual', 'budget', 'forecast']:
            values = kpis[kpis.scenario == scenario].set_index('label').reindex(labels)[metric]
            data.add_series(scenario.title(), [None if pd.isna(v) else float(v) for v in values])
        chart = page.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, Inches(.65), Inches(2.1), Inches(12), Inches(4.65), data).chart
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.category_axis.tick_labels.font.size = Pt(14)
        chart.value_axis.tick_labels.font.size = Pt(14)
        chart.legend.font.size = Pt(14)
        for series, color in zip(chart.series, [TEAL, '667085', 'F26B5B']):
            series.format.line.color.rgb = RGBColor.from_string(color)

    page = slide('Definitions & board discussion', 'Review results with management before circulation.')
    text(page, '\n'.join([
        'Staff costs are included within operating expenses; do not add them twice.',
        'Wastage cost and returned order value are analytical measures, not extra P&L deductions.',
        'Wastage rate = scrap / (good production + scrap). Recycled input = recycled / total input.',
        'Return rate = returns recorded in period / orders shipped in period; not a shipment-cohort return rate.',
        'Stock, headcount and credit exposure use the latest closing month; flows sum over the period.',
        'Credit headroom = approved customer limits minus receivables; aggregate headroom can mask individual breaches.',
        'Forecast is one uploaded planning snapshot, not a predictive model. Missing values are unavailable.',
        'Discuss: waste drivers, returns causes, overdue collections, supplier settlement and staffing actions.',
    ]), .65, 2.1, 12, 4.7, 17)
    output = BytesIO()
    prs.save(output)
    return output.getvalue()
