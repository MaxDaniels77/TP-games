import os
import json
import logging
import pandas as pd
from datetime import datetime
from deltalake import write_deltalake, DeltaTable
from typing import List, Dict, Any, Optional

from .connectors import RawgApiClient
from .config import Config

logger = logging.getLogger(__name__)

class GameDataIngestor(RawgApiClient):
    """
    Ingesta datos desde la API de RAWG hacia la capa Bronze (Delta Lake).
    Hereda de RawgApiClient para manejar la conexión HTTP.
    """

    def __init__(self):
        super().__init__()
        self.bronze_path = Config.BRONZE_PATH

    def get_genres_full(self):
        """
        Obtiene todos los géneros y realiza una Carga Completa (Full Load).
        Estrategia: Overwrite (Sobreescritura total).
        Es 100% idempotente: cada ejecución deja la tabla en el mismo estado limpio.
        """
        endpoint = "genres"
        logger.info(f"Iniciando Full Load para {endpoint}...")
        
        # Pagina 1 con 40 resultados suele ser suficiente para los géneros principales
        response = self._get(endpoint, params={"page_size": 40})
        
        if not response or "results" not in response:
            logger.error("No se pudieron obtener los géneros.")
            return

        df = pd.DataFrame(response["results"])
        
        # Serializamos columnas complejas (listas/dicts) a JSON string para consistencia
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
                df[col] = df[col].apply(json.dumps)
        
        save_path = os.path.join(self.bronze_path, "genres")
        try:
            write_deltalake(save_path, df, mode="overwrite")
            logger.info(f"Guardados {len(df)} géneros en {save_path} (Mode: overwrite).")
        except Exception as e:
            logger.error(f"Error escribiendo en Delta Lake: {e}")

    def get_games_incremental(self, start_date: str, end_date: str):
        """
        Obtiene juegos incrementalmente basado en un rango de fechas.
        Estrategia: Append con Idempotencia por Partición.
        
        Pasos para Idempotencia:
        1. Identificamos la fecha de extracción actual.
        2. Si ya existen datos para esta fecha en Delta Lake, LOS BORRAMOS.
        3. Escribimos los nuevos datos (Append).
        Esto permite re-ejecutar el script el mismo día sin generar duplicados.
        """
        endpoint = "games"
        logger.info(f"Iniciando Carga Incremental para juegos ({start_date} a {end_date})...")
        
        all_games = []
        page = 1
        max_pages = 5 
        dates_param = f"{start_date},{end_date}"
        
        # Bucle de Paginación
        while page <= max_pages:
            logger.info(f"Cargando página {page}/{max_pages}...")
            params = {
                "dates": dates_param,
                "page": page,
                "page_size": 20,
                "ordering": "-released"
            }
            
            response = self._get(endpoint, params=params)
            
            if not response or "results" not in response:
                break
            
            results = response["results"]
            if not results:
                break
                
            all_games.extend(results)
            
            if not response.get("next"):
                break
            page += 1
            
        if not all_games:
            logger.warning("No se encontraron juegos en el rango especificado.")
            return

        # Preparación del DataFrame
        df = pd.DataFrame(all_games)
        
        # Columnas de Auditoría
        extraction_ts = datetime.now()
        extraction_date_str = extraction_ts.strftime("%Y-%m-%d")
        
        df["extraction_ts"] = extraction_ts
        df["extraction_date"] = extraction_date_str
        
        # --- Manejo Robusto de Esquema para Delta Lake ---
        # Convertimos estructuras anidadas (dicts/listas) a JSON strings y manejamos Nulos.
        # Esto evita errores de "Type Mismatch" o "Ambiguous Boolean".
        
        complex_cols = ["platforms", "parent_platforms", "genres", "stores", "tags", "esrb_rating", "short_screenshots"]
        
        def safe_serialize(x):
            """Serializa objetos a JSON string de forma segura, evitando errores de numpy/pandas."""
            if x is None: return None
            if isinstance(x, (list, dict)): return json.dumps(x)
            if hasattr(x, 'tolist'): return json.dumps(x.tolist()) # Numpy arrays
            if pd.isna(x): return None
            return str(x)

        for col in df.columns:
            # 1. Si toda la columna es nula, forzamos tipo string
            if df[col].isnull().all():
                df[col] = df[col].astype(str)
                continue

            # 2. Si detectamos columnas complejas, aplicamos serialización
            is_complex = col in complex_cols
            if not is_complex:
                try:
                    # Heurística rápida para detectar objetos anidados
                    if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
                        is_complex = True
                except:
                    pass
            
            if is_complex:
                df[col] = df[col].apply(safe_serialize)
                df[col] = df[col].astype(str).replace('None', None)

        # --- Escritura Idempotente ---
        save_path = os.path.join(self.bronze_path, "games")
        
        try:
            # Paso A: Intentamos conectar a la tabla Delta existente
            if os.path.exists(save_path):
                dt = DeltaTable(save_path)
                # Paso B: Borramos datos previos de ESTA fecha de extracción (Idempotencia)
                logger.info(f"Limpiando partición existente para extraction_date='{extraction_date_str}'...")
                dt.delete(f"extraction_date = '{extraction_date_str}'")
            
            # Paso C: Escribimos los nuevos datos (Append)
            write_deltalake(
                save_path, 
                df, 
                mode="append", 
                partition_by=["extraction_date"],
                schema_mode="merge"
            )
            logger.info(f"Guardados {len(df)} juegos exitosamente (Mode: Idempotent Append).")
            
        except Exception as e:
            # Si la tabla no existe (primera ejecución), simplemente escribimos
            if "No file" in str(e) or "Not a Delta table" in str(e) or not os.path.exists(save_path):
                write_deltalake(
                    save_path, 
                    df, 
                    mode="append", 
                    partition_by=["extraction_date"]
                )
                logger.info(f"Creada nueva tabla Delta con {len(df)} juegos.")
            else:
                logger.error(f"Fallo crítico escribiendo en Delta Lake: {e}")
