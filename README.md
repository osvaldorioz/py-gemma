El proyecto es un microservicio híbrido que combina C++ y Python para crear un chatbot experto en cervezas. Sus componentes principales son:

- FastAPI/Uvicorn: Proporciona endpoints REST (/chat/startChat, /chat/{chatId}, /documents/upload, /load_embeddings) para manejar consultas.
- Streamlit: Ofrece una interfaz web en http://localhost:8501 para interactuar con el chatbot.
- Redis: Ejecutado en un contenedor Docker (py-gemma-redis-1, puerto 6379 mapeado a 0.0.0.0:6379), almacena metadatos y embeddings de cervezas de beers.json.gz.
- pybind11: Integra el código C++ (gemma_agent.cpp) con Python, implementando la clase BeerRAGAgent para generación aumentada por recuperación (RAG).
- Ollama API: Hospeda el modelo gemma3:270m en http://localhost:11434/api/generate para generación de texto.
- sentence-transformers: Utiliza el modelo all-MiniLM-L6-v2 (ejecutado en CPU) para generar embeddings, ya que gemma3:270m no soporta embeddings.
- config.json: Inspirado en mcp-sql y con un prompt Java (system-qa.st), define instrucciones para respuestas amigables sobre cervezas, incluyendo maridajes y sugerencias de visualización.

El microservicio procesa consultas sobre cervezas, recupera metadatos de Redis y genera respuestas naturales usando gemma3:270m.
