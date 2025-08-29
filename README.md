El proyecto es un microservicio híbrido que combina C++ y Python para crear un chatbot experto en cervezas. Sus componentes principales son:

- FastAPI/Uvicorn: Proporciona endpoints REST (/chat/startChat, /chat/{chatId}, /documents/upload, /load_embeddings) para manejar consultas.
- Streamlit: Ofrece una interfaz web en http://localhost:8501 para interactuar con el chatbot.
- Redis: Ejecutado en un contenedor Docker (py-gemma-redis-1, puerto 6379 mapeado a 0.0.0.0:6379), almacena metadatos y embeddings de cervezas de beers.json.gz.
- pybind11: Integra el código C++ (gemma_agent.cpp) con Python, implementando la clase BeerRAGAgent para generación aumentada por recuperación (RAG).
- Ollama API: Hospeda el modelo gemma3:270m en http://localhost:11434/api/generate para generación de texto.
- sentence-transformers: Utiliza el modelo all-MiniLM-L6-v2 (ejecutado en CPU) para generar embeddings, ya que gemma3:270m no soporta embeddings.
- config.json: Inspirado en mcp-sql y con un prompt Java (system-qa.st), define instrucciones para respuestas amigables sobre cervezas, incluyendo maridajes y sugerencias de visualización.

El microservicio procesa consultas sobre cervezas, recupera metadatos de Redis y genera respuestas naturales usando gemma3:270m.


<img width="904" height="939" alt="screen1" src="https://github.com/user-attachments/assets/0d49fe4c-817f-4e80-b033-a19e90a1586e" />


<img width="853" height="922" alt="screen2" src="https://github.com/user-attachments/assets/61988dfa-a329-478c-aaae-5ef5fa06ff81" />


Descripción de gemma3:270m y su Rol

¿Qué es gemma3:270m?

gemma3:270m es un modelo de lenguaje ligero y de código abierto desarrollado por Google, parte de la familia Gemma, con 270 millones de parámetros. Está optimizado para tareas de generación de texto, como responder preguntas o generar texto natural.
Es eficiente, requiere aproximadamente 0.5 GB de RAM, lo que lo hace adecuado para hardware ajustado como el que se tiene en openshift.
No genera embeddings, por lo que se complementa con sentence-transformers para esta tarea.
En este proyecto, gemma3:270m se ejecuta a través de Ollama, accesible mediante la API en http://localhost:11434/api/generate.

Rol en el Microservicio:

Generación de Texto: gemma3:270m produce respuestas en lenguaje natural a consultas sobre cervezas (por ejemplo, "Háblame de Nut Brown Ale") basadas en un prompt que combina metadatos de Redis y la consulta del usuario.
Flujo RAG (Retrieval-Augmented Generation):

Recuperación: La clase BeerRAGAgent (en C++) recupera metadatos de cervezas (nombre, descripción, estilo, ABV) de Redis para claves beer:meta:*.
Construcción del Prompt: Los metadatos se formatean en un prompt usando la plantilla (PROMPT_TEMPLATE) y las instrucciones de config.json, que requieren respuestas claras, maridajes (por ejemplo, con pizza o postres) y sugerencias de visualización (por ejemplo, gráficos de barras).
Generación: El prompt se envía a gemma3:270m a través de la API de Ollama, que genera una respuesta natural.


Ejemplo: Para la consulta "Háblame de Nut Brown Ale", se recuperan metadatos como "Nombre: Nut Brown Ale, Descripción: Una cerveza marrón maltosa con notas de caramelo, Estilo: Brown Ale, ABV: 5.5", se construye un prompt, y gemma3:270m genera una respuesta como: "Nut Brown Ale es una cerveza marrón maltosa con notas de caramelo y un ABV de 5.5%. Combina bien con carnes asadas o postres de chocolate."

Implementación en el Microservicio Híbrido
El microservicio integra gemma3:270m con componentes C++ y Python para crear un chatbot robusto. A continuación, se detalla cómo se implementó:
1. Capa Python (app.py)

Propósito: Gestiona el servidor FastAPI, interacciones con Redis, generación de embeddings y comunicación con la API de Ollama.
Componentes Clave:

Conexión a Redis: Se conecta al contenedor Redis en localhost:6379 con decode_responses=True para garantizar cadenas UTF-8.
Generación de Embeddings: Usa sentence-transformers (all-MiniLM-L6-v2, en CPU) para generar embeddings de beers.json.gz. Los embeddings se almacenan como cadenas base64 en beer:embed:{id} (para posibles búsquedas de similitud), mientras que los metadatos se guardan como JSON en beer:meta:{id}.
Carga Manual de Datos: El endpoint /load_embeddings limpia Redis con FLUSHDB para evitar datos inválidos, carga beers.json.gz y almacena metadatos y embeddings, verificando claves existentes para evitar duplicados.
Integración con Ollama: La función generate_text envía prompts a gemma3:270m mediante POST a http://localhost:11434/api/generate, manejando respuestas en streaming y errores (por ejemplo, tiempos de espera).
Endpoints:

/chat/startChat: Genera un ID de chat único (UUID).
/chat/{chatId}: Procesa consultas, pasando el texto a BeerRAGAgent para generar respuestas RAG.
/load_embeddings: Carga manualmente datos en Redis.



2. Capa C++ (gemma_agent.cpp)

Propósito: Implementa la clase BeerRAGAgent usando pybind11 para integrarse con Python, manejando la recuperación de datos de Redis y la construcción de prompts.
Componentes Clave:

Recuperación de Redis: La función retrieve_from_redis obtiene metadatos de claves beer:meta:*, parsea el JSON y construye una cadena legible (por ejemplo, "Nombre: Nut Brown Ale, Descripción: ..., Estilo: Brown Ale, ABV: 5.5").
Construcción del Prompt: Combina metadatos con PROMPT_TEMPLATE e INSTRUCTIONS de config.json, luego pasa el prompt a la función Python generate_text (enlazada vía pybind11) para llamar a gemma3:270m.
Manejo de Errores: Valida campos JSON (name, description, style, abv) y maneja errores de parseo para evitar datos no válidos.


3. Interfaz Streamlit (front.py)

Propósito: Proporciona una interfaz web para interactuar con el chatbot.
Implementación: Envía consultas al endpoint /chat/{chatId}, muestra respuestas y mantiene un chat_id de sesión.
Integración con gemma3:270m: Usa gemma3:270m indirectamente a través del endpoint FastAPI, que ejecuta el flujo RAG.

4. Redis y Gestión de Datos

Fuente de Datos: beers.json.gz contiene información de cervezas (por ejemplo, {"id": 1, "name": "Nut Brown Ale", "description": "Una cerveza marrón maltosa con notas de caramelo.", "style": "Brown Ale", "abv": 5.5}).
Almacenamiento:

Metadatos en beer:meta:{id} como JSON.
Embeddings en beer:embed:{id} como base64.


Carga: El endpoint /load_embeddings limpia Redis y carga datos, evitando duplicados.

5. Integración con Ollama API

Configuración: El servidor Ollama (ollama serve) hospeda gemma3:270m localmente.
Llamadas API: app.py envía solicitudes POST a http://localhost:11434/api/generate con un payload JSON especificando el modelo, prompt, temperatura (entre 0.2 y 0.3,  se describe mas adelante el impacto de este cambio) y máximo de tokens (512).
Streaming: Las respuestas se procesan en streaming para manejar salidas largas de manera eficiente.

6. Configuración (config.json)

Instrucciones: Define el chatbot como experto en cervezas, requiriendo respuestas claras, maridajes y sugerencias de visualización.
Plantilla de Prompt: Estructura prompts como: "Eres un experto en cervezas. Usa la siguiente información para responder. Siempre sugiere un maridaje. Información de contexto: {documents} Pregunta: {query}".
Sugerencias de Visualización: Soporta consultas analíticas con sugerencias de gráficos (por ejemplo, gráfico de barras para comparar ABV).

7. Docker y Entorno

Redis: Ejecutado vía docker-compose.yml con redis/redis-stack-server.
Dependencias: Paquetes Python (fastapi, uvicorn, redis, sentence-transformers, streamlit, requests) y bibliotecas C++ (libhiredis-dev, redis++, pybind11).
Directorio: /home/hadoop/Documentos/cpp_programs/pybind/py-gemma.

<img width="845" height="869" alt="screen3" src="https://github.com/user-attachments/assets/722cb5ea-0e19-409f-b13b-98b8671cb049" />


Ejemplo de Flujo:

Para la consulta "Háblame de Nut Brown Ale":

Streamlit envía la consulta a /chat/{chatId}.
app.py llama a BeerRAGAgent::generate_response (C++).
BeerRAGAgent recupera metadatos de Redis (por ejemplo, beer:meta:1).
Se construye un prompt: "Eres un experto en cervezas. ... Información de contexto: Nombre: Nut Brown Ale, Descripción: Una cerveza marrón maltosa con notas de caramelo, Estilo: Brown Ale, ABV: 5.5\nPregunta: Háblame de Nut Brown Ale".
El prompt se envía a gemma3:270m vía la API de Ollama.
La respuesta se muestra en Streamlit, como: "Nut Brown Ale es una cerveza marrón maltosa con notas de caramelo y un ABV de 5.5%. Combina bien con carnes asadas o postres de chocolate."

¿Qué es la Temperatura en Modelos de Lenguaje?
La temperatura es un hiperparámetro en modelos de lenguaje como gemma3:270m que ajusta la aleatoriedad de las predicciones al generar texto. Afecta la distribución de probabilidad sobre el vocabulario del modelo durante la generación de tokens:

Temperatura baja (por ejemplo, 0.2): Hace que el modelo sea más determinista, favoreciendo tokens con mayor probabilidad. Las respuestas son más predecibles, coherentes y enfocadas, pero menos creativas.
Temperatura alta (por ejemplo, 0.3 o más): Aumenta la aleatoriedad al aplanar la distribución de probabilidad, dando más peso a tokens menos probables. Las respuestas son más variadas y creativas, pero pueden ser menos coherentes o desviarse del contexto.
Rango típico: La temperatura suele estar entre 0.0 (completamente determinista) y 2.0 (muy aleatoria). Valores como 0.2 y 0.3 están en el rango bajo, adecuado para respuestas controladas.

Impacto de Cambiar la Temperatura de 0.2 a 0.3
Cambiar la temperatura de 0.2 a 0.3 en la función generate_text de app.py tendrá los siguientes efectos en las respuestas generadas por gemma3:270m:

Mayor Variabilidad en las Respuestas:

Con temperature=0.2, las respuestas son muy enfocadas y tienden a ser consistentes en múltiples ejecuciones para la misma consulta (por ejemplo, "Háblame de Nut Brown Ale" siempre describirá la cerveza de manera similar, con un maridaje como "carnes asadas o postres de chocolate").
Con temperature=0.3, el modelo tiene más libertad para elegir palabras y estructuras, lo que introduce variaciones sutiles. Por ejemplo, para la misma consulta, podría sugerir diferentes maridajes (por ejemplo, "pizza con pepperoni" en lugar de "carnes asadas") o usar un lenguaje ligeramente más creativo (por ejemplo, "una cerveza marrón con un toque seductor de caramelo" en lugar de "maltosa con notas de caramelo").
Ejemplo:

0.2: "Nut Brown Ale es una cerveza marrón maltosa con notas de caramelo y un ABV de 5.5%. Combina bien con carnes asadas o postres de chocolate."
0.3: "Nut Brown Ale es una cerveza marrón con un sabor maltoso y dulces notas de caramelo, ABV 5.5%. Prueba combinarla con un postre de nuez o una pizza rústica."




Ligero Aumento en Creatividad:

A 0.3, el modelo puede generar frases más expresivas o inesperadas, lo que puede hacer las respuestas más interesantes para el usuario. Por ejemplo, al responder "Qué cerveza va bien con pizza?", podría sugerir maridajes más variados o descripciones más coloridas.
Sin embargo, dado que 0.3 sigue siendo un valor bajo, el aumento en creatividad es moderado, y las respuestas seguirán siendo coherentes y relevantes para el contexto proporcionado por los metadatos de Redis y el config.json.


Menor Riesgo de Desviación:

Un cambio de 0.2 a 0.3 es pequeño, por lo que el riesgo de respuestas incoherentes o irrelevantes es mínimo. El modelo seguirá respetando las instrucciones de config.json (respuestas claras, maridajes, sugerencias de visualización) y los metadatos de Redis (por ejemplo, "Nombre: Nut Brown Ale, Descripción: ...").
Comparado con valores más altos (por ejemplo, 0.7 o 1.0), 0.3 mantiene las respuestas enfocadas, lo que es ideal para un chatbot experto en cervezas donde la precisión es clave.


Impacto en Maridajes y Visualizaciones:

Las instrucciones en config.json requieren maridajes y sugerencias de visualización. Con temperature=0.3, el modelo podría proponer maridajes más diversos (por ejemplo, "quesos añejos" en lugar de "carnes asadas") o sugerencias de visualización más variadas (por ejemplo, "gráfico de dispersión" en lugar de "gráfico de barras").
Ejemplo para "Mostrar la distribución de estilos de cerveza":

0.2: "Estilos disponibles: Brown Ale, IPA. Sugiero un gráfico de pastel para mostrar la distribución."
0.3: "Tenemos estilos como Brown Ale y IPA. Un gráfico de pastel o una tabla colorida podrían ilustrar bien la distribución."



Rendimiento y Consistencia:

El cambio no afecta el rendimiento (tiempo de respuesta o uso de recursos), ya que la temperatura solo modifica la distribución de probabilidad, no la carga computacional.
La consistencia entre respuestas para la misma consulta disminuirá ligeramente, pero seguirá siendo alta debido al valor bajo de 0.3.

<img width="1124" height="974" alt="screen5" src="https://github.com/user-attachments/assets/035451c2-7936-47c7-9d96-edd247345149" />

