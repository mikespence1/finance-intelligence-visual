"""AI interprets precomputed metrics only; it never writes to source data."""
import json
import os
from pathlib import Path
import tomllib

def openai_client():
    from openai import OpenAI
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        secrets_file = Path(__file__).resolve().parents[1] / '.streamlit' / 'secrets.toml'
        if secrets_file.is_file():
            with secrets_file.open('rb') as handle:
                api_key = tomllib.load(handle).get('OPENAI_API_KEY')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY is not configured. Set an environment variable or .streamlit/secrets.toml.')
    return OpenAI(api_key=api_key, timeout=45, max_retries=1)


def generate_board_commentary(comparison, period, grain, model=None, currency='AED', baseline='budget'):
    client = openai_client()
    baseline = 'budget and forecast' if baseline == 'both' else baseline
    context = [{key: (None if __import__('pandas').isna(val) else val) for key, val in record.items()} for record in comparison.to_dict(orient='records')]
    response = client.responses.create(
        model=model or os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini'),
        store=False,
        instructions=('You are a careful FP&A analyst for a sustainable packaging manufacturer. '
          f'The comparison baseline is {baseline}; name it accurately throughout the report. '
          'Discuss material waste, recycled inputs, recovery, returns, stock, customer credit, '
          'supplier payments, staff costs and headcount when supplied. Staff Costs are included '
          'in Operating Expenses; waste cost and returned order value are analytical measures, '
          'not additional P&L deductions. Headcount and stock use closing balances. '
          'Only use supplied computed figures. Do not fabricate causes, forecasts or metrics. '
          'Label inferences as hypotheses, distinguish percentage points from percent, '
          'and flag unavailable information. Use exactly these four Markdown level-two headings: '
          f'## Executive summary, ## Performance vs {baseline}, ## Risks and questions, ## Proposed actions. '
          'Use short paragraphs or bullets beneath each heading. '
          f'Currency amounts are in {currency}. Numerical results are authoritative. '
          'Never suggest that any AI-generated explanation is a verified root cause.'),
        input=f'Reporting grain: {grain}; period: {period}. KPI comparison (JSON): {json.dumps(context, default=str)}',
        max_output_tokens=900,
    )
    return response.output_text
