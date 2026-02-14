import json
import subprocess
import time
import httpx
import pytest


@pytest.fixture(scope="module")
def agent_server():
    """エージェントサーバーを起動するフィクスチャ"""
    # エージェントをバックグラウンドで起動
    process = subprocess.Popen(
        ["uv", "run", "python", "my_agent.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    # エージェントの起動を待つ
    max_retries = 30
    for i in range(max_retries):
        try:
            response = httpx.post(
                "http://localhost:8080/invocations",
                json={"prompt": "test"},
                timeout=5.0,
            )
            if response.status_code == 200:
                print("Agent is ready")
                break
        except (httpx.ConnectError, httpx.TimeoutException):
            if i == max_retries - 1:
                process.kill()
                stdout, stderr = process.communicate()
                pytest.fail(f"Agent failed to start.\nStdout: {stdout}\nStderr: {stderr}")
            time.sleep(1)
    
    yield process
    
    # テスト後にプロセスを終了
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def test_agent_basic_response(agent_server):
    """基本的な応答テスト"""
    response = httpx.post(
        "http://localhost:8080/invocations",
        json={"prompt": "こんにちは"},
        timeout=30.0,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # レスポンスにresultが含まれているか確認
    assert "result" in data
    assert isinstance(data["result"], dict)
    assert "content" in data["result"]


def test_agent_calculation(agent_server):
    """計算テスト"""
    response = httpx.post(
        "http://localhost:8080/invocations",
        json={"prompt": "1+1は？"},
        timeout=30.0,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # レスポンスに結果が含まれているか確認
    assert "result" in data
    result_str = json.dumps(data["result"])
    
    # 答えの「2」が含まれているか確認
    assert "2" in result_str


def test_agent_multiple_requests(agent_server):
    """複数リクエストのテスト"""
    prompts = [
        "おはよう",
        "今日の天気は？",
        "ありがとう",
    ]
    
    for prompt in prompts:
        response = httpx.post(
            "http://localhost:8080/invocations",
            json={"prompt": prompt},
            timeout=30.0,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "result" in data


def test_agent_empty_prompt(agent_server):
    """空のプロンプトテスト"""
    response = httpx.post(
        "http://localhost:8080/invocations",
        json={"prompt": ""},
        timeout=30.0,
    )
    
    # 空のプロンプトでも応答すること
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
