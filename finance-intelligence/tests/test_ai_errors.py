import httpx
import pytest
from fastapi import HTTPException
from openai import AuthenticationError, RateLimitError, NotFoundError, APIConnectionError, APITimeoutError
from backend.main import ai_request
from src.ai import AIConfigurationError


def status_error(kind,status,code):
    response=httpx.Response(status,request=httpx.Request('POST','https://api.openai.com/v1/responses'))
    return kind('private-secret-must-not-leak',response=response,body={'code':code})

@pytest.mark.parametrize('error,expected',[
    (AIConfigurationError('private-secret-must-not-leak'),'No server-side OpenAI API key'),
    (status_error(AuthenticationError,401,'invalid_api_key'),'rejected the server API key'),
    (status_error(RateLimitError,429,'insufficient_quota'),'no available quota'),
    (status_error(RateLimitError,429,'rate_limit_exceeded'),'rate-limiting'),
    (status_error(NotFoundError,404,'model_not_found'),'model is unavailable'),
    (APIConnectionError(request=httpx.Request('POST','https://api.openai.com')),'cannot connect'),
    (APITimeoutError(request=httpx.Request('POST','https://api.openai.com')),'timed out'),
])
def test_ai_failure_categories_are_actionable_and_do_not_leak_credentials(monkeypatch,error,expected):
    monkeypatch.setenv('AI_DISABLED','0')
    def fail():raise error
    with pytest.raises(HTTPException) as result:ai_request(fail)
    assert result.value.status_code==503
    assert expected in result.value.detail
    assert 'private-secret' not in result.value.detail
