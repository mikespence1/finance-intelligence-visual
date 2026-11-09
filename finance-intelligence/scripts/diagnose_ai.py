"""Small live connectivity check. Never prints credentials or raw API error bodies."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ai import openai_client
from openai import APIStatusError, APIConnectionError, APITimeoutError

try:
    client=openai_client()
    response=client.responses.create(model=os.environ.get('OPENAI_MODEL','gpt-4.1-mini'),input='Reply with OK.',max_output_tokens=16,store=False)
    print('AI_CONNECTION_OK',bool(response.output_text))
except APIStatusError as error:
    code=error.code if isinstance(error.code,str) else 'unknown'
    print('AI_API_ERROR',error.status_code,'code',code)
    sys.exit(2)
except (APIConnectionError,APITimeoutError) as error:
    print('AI_NETWORK_ERROR',type(error).__name__,'cause',type(error.__cause__).__name__)
    sys.exit(3)
except RuntimeError:
    print('AI_CONFIG_ERROR: no usable server-side API key')
    sys.exit(4)
