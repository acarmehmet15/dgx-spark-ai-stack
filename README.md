# DGX Spark AI Stack

NVIDIA DGX Spark üzerinde **Open WebUI + LiteLLM + vLLM** ile lokal AI chatbot stack'i. Docker Compose ile tek komutla kurulum.

## Mimari

```
┌─────────────────────────────────────────────┐
│               Open WebUI (:3000)            │
│            (Chat Arayüzü / RAG)             │
├─────────────────────────────────────────────┤
│              LiteLLM (:4000)                │
│        (API Gateway / Model Router)         │
├─────────────────────────────────────────────┤
│               vLLM (:8000)                  │
│          (GPU Model Inference)              │
├─────────────────────────────────────────────┤
│          NVIDIA DGX Spark GPU               │
└─────────────────────────────────────────────┘
```

## Bileşenler

| Bileşen | Açıklama | Port |
|---------|----------|------|
| **Open WebUI** | ChatGPT benzeri web arayüzü, RAG desteği | `:3000` |
| **LiteLLM** | Birden fazla model için API gateway ve yönlendirici | `:4000` |
| **vLLM** | GPU hızlandırmalı yüksek performanslı LLM inference engine | `:8000` |

## Gereksinimler

- NVIDIA DGX Spark
- Ubuntu 22.04+ veya desteklenen Linux dağıtımı
- NVIDIA Driver 535+
- Docker & NVIDIA Container Toolkit

## Hızlı Kurulum

```bash
git clone https://github.com/acarmehmet15/dgx-spark-ai-stack.git
cd dgx-spark-ai-stack
docker compose up -d
```

## Kullanım

Kurulum tamamlandıktan sonra:

- **Chat Arayüzü:** http://localhost:3000
- **LiteLLM API:** http://localhost:4000
- **vLLM API:** http://localhost:8000

## Lisans

Bu proje MIT lisansı altında sunulmaktadır.
