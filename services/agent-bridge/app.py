"""
Agent Bridge — Agno AgentOS → OpenAI-Uyumlu API Köprüsü
─────────────────────────────────────────────────────────
SDLCAgents'ın AgentOS API'sini OpenAI chat completions formatında sunar.
LiteLLM ve Open WebUI bu endpoint üzerinden agent'lara erişir.
"""

import json
import time
import uuid
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="Agent Bridge", version="1.0.0")

AGENTOS_BASE_URL = "http://agentos-api:7777"

# model_id → AgentOS agent_id eşlemesi
AGENTS = {
    "sdlc-analyst": {
        "name": "SDLC Analyst Agent",
        "description": "Belgeleri okur, gereksinimleri çıkarır, GitHub Issue oluşturur, kabul kriterlerini yazar",
        "agent_id": "analyst-agent",
    },
    "sdlc-architect": {
        "name": "SDLC Architect Agent",
        "description": "Mimari kararlar alır, ADR'ler yazar, teknoloji stack seçer",
        "agent_id": "architect-agent",
    },
    "sdlc-be-developer": {
        "name": "SDLC Backend Developer Agent",
        "description": "Backend (.NET) kodu yazar, birim testleri oluşturur, PR açar",
        "agent_id": "be-developer-agent",
    },
    "sdlc-fe-developer": {
        "name": "SDLC Frontend Developer Agent",
        "description": "Frontend (React/TypeScript) kodu yazar, component testleri oluşturur",
        "agent_id": "fe-developer-agent",
    },
    "sdlc-reviewer": {
        "name": "SDLC Reviewer Agent",
        "description": "PR değişikliklerini inceler, güvenlik/kalite kontrolleri yapar",
        "agent_id": "reviewer-agent",
    },
    "sdlc-qa": {
        "name": "SDLC QA Agent",
        "description": "Test planları oluşturur, kapsamı doğrular, son onayı verir",
        "agent_id": "qa-agent",
    },
    "sdlc-supervisor": {
        "name": "SDLC Supervisor (Tam Pipeline)",
        "description": "Analyst→Architect→BE Dev→FE Dev→Reviewer→QA tam SDLC hattını çalıştırır",
        "agent_id": "__supervisor__",
    },
}


@app.get("/v1/models")
async def list_models():
    """OpenAI uyumlu model listesi."""
    models = []
    for model_id, info in AGENTS.items():
        models.append({
            "id": model_id,
            "object": "model",
            "created": 1700000000,
            "owned_by": "sdlc-agents",
            "description": info["description"],
        })
    return {"object": "list", "data": models}


@app.get("/health")
async def health():
    return {"status": "ok"}


def _make_chunk(model: str, content: str, finish_reason: str | None = None) -> str:
    """SSE formatında bir chunk oluştur."""
    chunk = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"content": content} if content else {},
            "finish_reason": finish_reason,
        }],
    }
    return f"data: {json.dumps(chunk)}\n\n"


async def _run_agent_stream(
    agent_id: str, model_id: str, messages: list[dict]
) -> AsyncGenerator[str, None]:
    """AgentOS'a istek gönder ve SSE stream olarak döndür."""
    # Tüm mesaj geçmişinden user mesajını al
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    if not user_message:
        yield _make_chunk(model_id, "Mesaj bulunamadı.", "stop")
        yield "data: [DONE]\n\n"
        return

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
            if agent_id == "__supervisor__":
                # Supervisor endpoint
                url = f"{AGENTOS_BASE_URL}/supervisor/run"
                response = await client.post(url, json={"content": user_message})
                response.raise_for_status()
                result = response.json()
                text = json.dumps(result, indent=2, ensure_ascii=False)
                for i in range(0, len(text), 200):
                    yield _make_chunk(model_id, text[i:i+200])
                yield _make_chunk(model_id, "", "stop")
                yield "data: [DONE]\n\n"
            else:
                # AgentOS agent run endpoint: POST /agents/{agent_id}/runs (multipart/form-data)
                url = f"{AGENTOS_BASE_URL}/agents/{agent_id}/runs"
                form_data = {
                    "message": user_message,
                    "stream": "false",
                }

                async with client.stream("POST", url, data=form_data) as response:
                    response.raise_for_status()
                    buffer = ""
                    current_event = ""
                    async for chunk in response.aiter_text():
                        buffer += chunk
                        while "\n" in buffer:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line:
                                current_event = ""
                                continue

                            if line.startswith("event:"):
                                current_event = line.split(":", 1)[1].strip()
                                continue

                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    yield _make_chunk(model_id, "", "stop")
                                    yield "data: [DONE]\n\n"
                                    return
                                try:
                                    parsed = json.loads(data)
                                    event = parsed.get("event", current_event)

                                    # Sadece RunResponse/RunContent event'lerinin content'ini stream et
                                    if event in ("RunResponse", "RunContent"):
                                        content = parsed.get("content", "")
                                        if content:
                                            yield _make_chunk(model_id, content)

                                    # Tool call bilgisi göster
                                    elif event == "ToolCallStarted":
                                        tool_name = parsed.get("tool_name", "")
                                        if tool_name:
                                            yield _make_chunk(model_id, f"\n🔧 *{tool_name}* çalıştırılıyor...\n")

                                    elif event == "ToolCallCompleted":
                                        yield _make_chunk(model_id, " ✅\n")

                                except json.JSONDecodeError:
                                    pass

                yield _make_chunk(model_id, "", "stop")
                yield "data: [DONE]\n\n"

    except httpx.HTTPStatusError as e:
        try:
            await e.response.aread()
            error_text = e.response.text[:500]
        except Exception:
            error_text = str(e)
        yield _make_chunk(model_id, f"Hata ({e.response.status_code}): {error_text}")
        yield _make_chunk(model_id, "", "stop")
        yield "data: [DONE]\n\n"
    except httpx.ConnectError:
        yield _make_chunk(model_id, "AgentOS servisi çalışmıyor.", "stop")
        yield "data: [DONE]\n\n"
    except Exception as e:
        yield _make_chunk(model_id, f"Hata: {str(e)}", "stop")
        yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI uyumlu chat completions endpoint."""
    body = await request.json()
    model_id = body.get("model", "")
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    # model_id'den "openai/" prefix'ini temizle (LiteLLM ekleyebilir)
    model_id = model_id.replace("openai/", "")

    agent_info = AGENTS.get(model_id)
    if not agent_info:
        return {"error": {"message": f"Bilinmeyen model: {model_id}", "type": "invalid_request_error"}}

    agent_id = agent_info["agent_id"]

    if stream:
        return StreamingResponse(
            _run_agent_stream(agent_id, model_id, messages),
            media_type="text/event-stream",
        )
    else:
        # Non-streaming: agent'ı çalıştır ve tam yanıt döndür
        chunks = []
        async for chunk_str in _run_agent_stream(agent_id, model_id, messages):
            if chunk_str.startswith("data: ") and chunk_str.strip() != "data: [DONE]":
                try:
                    chunk_data = json.loads(chunk_str[6:])
                    content = chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        chunks.append(content)
                except (json.JSONDecodeError, IndexError):
                    pass

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_id,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "".join(chunks)},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8506)
