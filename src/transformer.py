import os
import json
import logging
import pandas as pd
from deltalake import DeltaTable, write_deltalake
from .config import Config

logger = logging.getLogger(__name__)

class GameTransformer:
    """
    Transforms data from Bronze to Silver layer.
    """

    def __init__(self):
        self.bronze_path = Config.BRONZE_PATH
        self.silver_path = Config.SILVER_PATH

    def process(self):
        """
        Main execution method for the transformation pipeline.
        Reads Bronze -> Cleans -> Unnests -> Aggregates -> Writes Silver.
        """
        logger.info("Starting Silver Layer transformation...")

        # 1. READ Bronze Games
        games_path = os.path.join(self.bronze_path, "games")
        try:
            dt = DeltaTable(games_path)
            df = dt.to_pandas()
            logger.info(f"Loaded {len(df)} records from Bronze Games.")
        except Exception as e:
            logger.error(f"Failed to load Bronze data from {games_path}: {e}")
            return

        if df.empty:
            logger.warning("Bronze DataFrame is empty. Skipping transformation.")
            return

        # 2. DATA CLEANING & TYPING
        # Convert 'released' to datetime
        df['released'] = pd.to_datetime(df['released'], errors='coerce')
        
        # Deduplication: Keep one record per game PER DAY (Daily History)
        # This allows tracking evolution (e.g. rating changes) over time.
        # We sort by extraction_date to ensure deterministic results.
        df.sort_values(by='extraction_date', ascending=True, inplace=True)
        df.drop_duplicates(subset=['id', 'extraction_date'], keep='last', inplace=True)

        # 3. COMPLEX TRANSFORMATION (Logic)
        # Metacritic: Impute or Create logic
        # Logic: Create is_top_rated if metacritic > 85
        
        df['metacritic'] = pd.to_numeric(df['metacritic'], errors='coerce')
        df['is_top_rated'] = df['metacritic'] > 85

        # 4. UNNESTING / JOIN PREP
        # 'genres' is a JSON string in Bronze. Need to parse it.
        def extract_genre_names(genre_json_str):
            if not genre_json_str:
                return []
            try:
                genres = json.loads(genre_json_str)
                if isinstance(genres, list):
                    return [g.get('name') for g in genres]
            except:
                pass
            return []

        df['genre_list'] = df['genres'].apply(extract_genre_names)
        # Create a primary genre for simple analysis
        df['primary_genre'] = df['genre_list'].apply(lambda x: x[0] if x else "Unknown")
        
        # Extract Year
        df['released_year'] = df['released'].dt.year
        
        # 5. SAVE SILVER (Refined)
        # Select useful columns
        refined_cols = [
            'id', 'slug', 'name', 'released', 'released_year', 'tba', 
            'background_image', 'rating', 'rating_top', 'metacritic', 'is_top_rated',
            'primary_genre', 'extraction_date'
        ]
        # Filter for columns that actually exist
        available_cols = [c for c in refined_cols if c in df.columns]
        df_refined = df[available_cols].copy()
        
        refined_path = os.path.join(self.silver_path, "games_refined")
        try:
            write_deltalake(refined_path, df_refined, mode="overwrite")
            logger.info(f"Saved {len(df_refined)} records to {refined_path}")
        except Exception as e:
            logger.error(f"Failed to write refined data: {e}")

        # 6. AGGREGATION & ANALYTICS
        # Explode genres to count games per genre properly
        df_exploded = df.explode('genre_list')
        df_exploded.rename(columns={'genre_list': 'genre'}, inplace=True)
        
        # Group by Year and Genre
        # Filter out invalid years or genres
        df_analytics = df_exploded.dropna(subset=['released_year', 'genre'])
        
        analytics_df = df_analytics.groupby(['released_year', 'genre']).agg(
            avg_rating=('rating', 'mean'),
            game_count=('id', 'count')
        ).reset_index()
        
        # Sort for better readability
        analytics_df.sort_values(by=['released_year', 'game_count'], ascending=[False, False], inplace=True)
        
        # Reset index completely to avoid __index_level_0__ artifact in Delta Lake
        analytics_df.reset_index(drop=True, inplace=True)
        
        analytics_path = os.path.join(self.silver_path, "games_analytics")
        try:
            write_deltalake(analytics_path, analytics_df, mode="overwrite")
            logger.info(f"Saved {len(analytics_df)} analytics records to {analytics_path}")
        except Exception as e:
            logger.error(f"Failed to write analytics data: {e}")
