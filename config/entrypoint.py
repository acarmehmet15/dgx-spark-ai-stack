"""DGX Spark AI Stack — AgentOS Entrypoint.

Ollama registry patch'ini yükler, sonra orijinal main.py'yi çalıştırır.
"""

# Önce Ollama desteğini registry'ye ekle
import config.registry_patch  # noqa: F401

# Sonra orijinal uygulamayı başlat
from src.main import app  # noqa: F401

if __name__ == "__main__":
    from src.main import agent_os
    agent_os.serve(
        app="config.entrypoint:app",
        host="0.0.0.0",
        port=7777,
        reload=False,
    )
