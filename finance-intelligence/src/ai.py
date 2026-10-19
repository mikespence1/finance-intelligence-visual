"""AI interprets precomputed metrics only; it never writes to source data."""
import json
import os
import streamlit as st

def generate_board_commentary(comparison, period, grain, model=None):
    from openai import OpenAI
    api_key = os.environ.get('OPENAI_API_KEY') or st.secrets.get('OPENAI_API_KEY')

    if not api_key:
        raise RuntimeError('OPENAI_API_KEY is not configured. Use an environment variable, not a GitHub file.')
    client = OpenAI(api_key=api_key)
    context = [{key: (None if __import__('pandas').isna(val) else val) for key, val in record.items()} for record in comparison.to_dict(orient='records')]
    response = client.responses.create(
        model=model or os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini'),
        store=False,
        instructions=('You are a careful FP&A analyst for a packaging manufacturer. '
          'Only use supplied computed figures. Do not fabricate causes, forecasts or metrics. '
          'Label inferences as hypotheses, distinguish percentage points from percent, '
          'and flag unavailable information. Provide concise board-ready sections: '
          'Executive summary, Performance vs budget, Risks and questions, Proposed actions. '
          'Amounts use the currency configured in the dashboard. Numerical results are authoritative. '
          'Never suggest that any AI-generated explanation is a verified root cause.'),
        input=f'Reporting grain: {grain}; period: {period}. KPI comparison (JSON): {json.dumps(context, default=str)}',
        max_output_tokens=900,
    )
    return response.output_text
