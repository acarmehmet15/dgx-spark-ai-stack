# DGX Spark AI Stack

NVIDIA DGX Spark üzerinde **Open WebUI + LiteLLM + Ollama + SDLC Agents** ile lokal AI chatbot ve otonom yazılım geliştirme stack'i. Docker Compose ile tek komutla kurulum.

## Mimari

```
┌─────────────────────────────────────────────────────────┐
│                  Open WebUI (:3000)                      │
│         Chat / RAG / Model & Agent Seçimi                │
├─────────────────────────────────────────────────────────┤
│                  LiteLLM (:4000)                         │
│          API Gateway + KVKK Guardrail 🔒                 │
│  ┌────────────┬───────────────┬──────────────┐           │
│  │  Ollama    │ Agent Bridge  │  CLIProxy    │           │
│  │  (:11434)  │   (:8506)     │  (:8317)     │           │
│  │            │      ↓        │              │           │
│  │ deepseek   │ AgentOS API   │ Claude Max   │           │
│  │ qwen2.5    │   (:7777)     │              │           │
│  │ gpt-oss    │ SDLC Agents   │              │           │
│  └────────────┴───────────────┴──────────────┘           │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL │ Redis │ OTel │ Prometheus │ Grafana        │
│  (:5432)    │(:6379)│(:4317)│ (:9090)   │ (:3001)       │
└─────────────────────────────────────────────────────────┘
│               NVIDIA DGX Spark GPU                       │
└─────────────────────────────────────────────────────────┘
```

## Bileşenler

| Bileşen | Açıklama | Port |
|---------|----------|------|
| **Open WebUI** | ChatGPT benzeri web arayüzü, RAG desteği | `:3000` |
| **LiteLLM** | API gateway, model router, KVKK guardrail | `:4000` |
| **Agent Bridge** | Agno agent'larını OpenAI-uyumlu API olarak sunar | `:8506` |
| **AgentOS API** | SDLC Agent takımı backend'i (Agno framework) | `:7777` |
| **CLIProxy** | Claude Max üyeliğini API olarak sunar | `:8317` |
| **Ollama** | Lokal LLM inference (host üzerinde çalışır) | `:11434` |
| **PostgreSQL** | Agent durumu, bellek, bilgi tabanı (pgvector) | `:5432` |
| **Redis** | Görev kuyruğu, önbellek | `:6379` |
| **Prometheus** | Metrik toplama | `:9090` |
| **Grafana** | İzleme panoları | `:3001` |

## SDLC Agent'ları

Open WebUI'dan seçilebilir agent'lar:

| Agent | Görev |
|-------|-------|
| **sdlc-analyst** | Gereksinim analizi, issue oluşturma, kabul kriterleri |
| **sdlc-architect** | Mimari kararlar, ADR yazma, tech stack seçimi |
| **sdlc-be-developer** | Backend (.NET) kod yazma, test, PR açma |
| **sdlc-fe-developer** | Frontend (React/TS) kod yazma, test |
| **sdlc-reviewer** | Kod inceleme, güvenlik/kalite kontrol |
| **sdlc-qa** | Test planları, kapsam doğrulama, son onay |
| **sdlc-supervisor** | Tam SDLC pipeline'ı otomatik çalıştırma |

## KVKK Guardrail

LiteLLM gateway seviyesinde tüm trafiği filtreler:

- **Gizli Bilgi Tespiti:** API anahtarları, tokenlar, şifreler, DB URI'leri, JWT, private key
- **KVK Maskeleme:** TC Kimlik No, e-posta, telefon, IBAN, kredi kartı, IP adresi
- **Çalışma Modu:** Input (pre_call) + Output (post_call), tüm modeller için varsayılan açık

## Gereksinimler

- NVIDIA DGX Spark
- Ubuntu 22.04+
- NVIDIA Driver 535+
- Docker & NVIDIA Container Toolkit
- Ollama (host üzerinde kurulu)

## Hızlı Kurulum

```bash
git clone --recurse-submodules https://github.com/acarmehmet15/dgx-spark-ai-stack.git
cd dgx-spark-ai-stack
cp .env.example .env
# .env dosyasını düzenleyin (GITHUB_TOKEN vb.)
docker compose up -d
```

## Kullanım

- **Chat Arayüzü:** http://localhost:3000
- **LiteLLM API:** http://localhost:4000
- **Grafana:** http://localhost:3001

## Lisans

Bu proje MIT lisansı altında sunulmaktadır.
