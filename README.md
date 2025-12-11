# 🎮 RAWG Data Engineering Pipeline

Proyecto final de Ingeniería de Datos que implementa un pipeline ETL robusto, modular e idempotente utilizando la **Arquitectura Medallion** (Bronze ➡️ Silver) y **Delta Lake**.

---

## 📋 Descripción del Proyecto
Este sistema extrae datos de videojuegos desde la **RAWG Video Games API**, los almacena en su formato crudo (Bronze) y luego los limpia, transforma y enriquece para generar tablas analíticas (Silver).

### Características Clave
- **Arquitectura Medallion:** Separación clara entre datos crudos (`data/bronze`) y refinados (`data/silver`).
- **Almacenamiento Optimizado:** Uso de **Delta Lake** para ACID transactions y versionado.
- **Carga Incremental e Idempotente:**
  - El proceso de ingestión garantiza que no se generen duplicados si se corre múltiples veces el mismo día.
  - Soporte para **Ingesta Ilimitada**: Capacidad de descargar automáticamente todas las páginas disponibles para un rango de fechas histórico (ej. backfill de 6 meses).
- **Logging Persistente:** Registro detallado de la ejecución en consola y en archivo (`logs/pipeline.log`).
- **Calidad de Datos:** Manejo robusto de esquemas, tipos de datos nulos y estructuras JSON anidadas.
- **Particionamiento:** Datos organizados por fecha de extracción (`extraction_date`).

---

## 🏗️ Estructura del Proyecto
```plaintext
TP-games/
├── .env                  # Variables de entorno (API KEY) - NO COMMIT
├── requirements.txt      # Dependencias del proyecto
├── main.ipynb            # Orquestador del Pipeline (Jupyter Notebook)
├── README.md             # Documentación
├── data/                 # Data Lake Local
│   ├── bronze/           # Ingesta Cruda (JSON strings, particionado)
│   └── silver/           # Datos Transformados (Tablas limpias y KPIs)
└── src/                  # Código Fuente
    ├── config.py         # Configuración y validación de entorno
    ├── connectors.py     # Cliente API con Retries y Rate Limiting
    ├── ingestor.py       # Lógica de extracción (Bronze Layer)
    └── transformer.py    # Lógica de transformación (Silver Layer)
```

## 🚀 Instalación y Configuración

### 1. Pre-requisitos
- Python 3.8+
- Una API Key de [RAWG](https://rawg.io/apidocs) (Gratuita).

### 2. Clonar e Instalar Dependencias
```bash
# Instalar librerías
pip install -r requirements.txt
```

   - **Incremental Load** de Juegos (Últimos 30 días).
   - **Transformación** a capa Silver.
   - **Verificación** mostrando los resultados finales.

---

## 🛠️ Detalles Técnicos
- **Idempotencia:** En la carga incremental de juegos, el script elimina preventivamente los datos de la fecha actual antes de insertar los nuevos, permitiendo re-ejecuciones seguras.
- **Paginación Inteligente:** El ingestor (`src/ingestor.py`) permite un parámetro `max_pages`. Si se omite, iterará infinitamente hasta consumir toda la respuesta de la API, ideal para cargas iniciales masivas.
- **Manejo de Esquemas:** Se utiliza serialización JSON segura para columnas complejas (listas de plataformas, géneros, etc.) para evitar errores de tipo en Delta Lake.

---

## 📊 Resultados (Silver Layer)
Al finalizar, encontrarás dos tablas principales en `data/silver`:
1. **games_refined:** Tabla maestra de juegos limpia, deduplicada y tipada.
2. **games_analytics:** Agregación de métricas (Rating Promedio y Cantidad de Juegos) por Año y Género.

---

## 📝 Comentarios Finales
Este proyecto fue desarrollado bajo estrictas limitaciones de tiempo. Como Científico de Datos, el objetivo principal de cursar esta materia ha sido expandir mis capacidades en el ámbito de la Ingeniería de Datos.

Si bien la implementación actual cumple satisfactoriamente con los requisitos de robustez, idempotencia y arquitectura solicitados, reconozco oportunidades valiosas para una mayor profundización. De haber contado con más tiempo, el siguiente paso lógico hubiese sido una exploración más exhaustiva de los múltiples endpoints de la API de RAWG, permitiendo realizar transformaciones lógicas más complejas e integrar modelos analíticos avanzados sobre los datos recolectados.

---
**Autor:** Daniel Arias
**Materia:** Ingeniería de Datos - UTN

## 🔄 Mejoras Implementadas (Refactorización)
Se han realizado mejoras técnicas y arquitectónicas para aumentar la robustez y mantenibilidad del código:

1.  **Desacoplamiento (Composición sobre Herencia):**
    *   Se refactorizó `GameDataIngestor` para utilizar **composición** en lugar de herencia. Ahora, el ingestor *tiene un* cliente API (`RawgApiClient`) en lugar de *ser un* cliente API. Esto mejora la testabilidad y flexibilidad del código.

2.  **Resiliencia y Manejo de Errores:**
    *   Se implementó una estrategia de **Retries (Reintentos)** automática en `RawgApiClient` utilizando `HTTPAdapter` y `urllib3`. El cliente ahora reintenta automáticamente peticiones fallidas por errores de servidor (5xx) o límites de tasa (429), con un backoff exponencial.
    *   Se mejoró el manejo de excepciones: los métodos ahora levantan excepciones claras en lugar de fallar silenciosamente o retornar `None`, permitiendo que el pipeline reaccione adecuadamente ante errores críticos.

3.  **Robustez en la Ingesta:**
    *   El proceso de ingesta incremental ahora maneja mejor los fallos de red durante la paginación, asegurando que los errores se registren y se detenga el proceso de manera controlada para evitar inconsistencias.
