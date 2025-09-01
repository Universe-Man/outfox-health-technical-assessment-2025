# etl.py
import asyncio
import pandas as pd
import random
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import os
import sys
from dotenv import load_dotenv
import logging
from decimal import Decimal
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Add app directory to path to import models
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.models import Provider, Rating, Base


class HealthcareETL:
    def __init__(self, database_url: str, csv_file_path: str):
        self.database_url = database_url
        self.csv_file_path = csv_file_path
        self.engine = create_async_engine(database_url, echo=False)
        self.AsyncSessionLocal = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self.geocoder = Nominatim(user_agent="healthcare_etl", timeout=10)

    async def create_tables(self):
        """Create database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare the healthcare data"""
        logger.info(f"Starting data cleaning. Original shape: {df.shape}")

        # Display column names for debugging
        logger.info(f"Available columns: {df.columns.tolist()}")

        # Create column mapping (adjust these based on your CSV structure)
        column_mapping = {
            "DRG Definition": "ms_drg_definition",
            "Provider Id": "provider_id",
            "Provider Name": "provider_name",
            "Provider Street Address": "provider_address",
            "Provider City": "provider_city",
            "Provider State": "provider_state",
            "Provider Zip Code": "provider_zip_code",
            "Hospital Referral Region (HRR) Description": "hrr_description",
            "Total Discharges": "total_discharges",
            "Average Covered Charges": "average_covered_charges",
            "Average Total Payments": "average_total_payments",
            "Average Medicare Payments": "average_medicare_payments",
        }

        # Rename columns if they exist
        existing_columns = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=existing_columns)

        # Handle missing columns gracefully
        required_columns = ["provider_id", "provider_name", "ms_drg_definition"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Clean data
        df = df.dropna(subset=required_columns)  # Drop rows with missing required data

        # Clean numeric columns
        numeric_columns = [
            "total_discharges",
            "average_covered_charges",
            "average_total_payments",
            "average_medicare_payments",
        ]
        for col in numeric_columns:
            if col in df.columns:
                # Remove $ signs and commas, convert to numeric
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(r"[\$,]", "", regex=True),
                    errors="coerce",
                )

        # Clean provider_id (ensure it's string and not too long)
        df["provider_id"] = df["provider_id"].astype(str).str[:10]

        # Clean ZIP codes
        if "provider_zip_code" in df.columns:
            df["provider_zip_code"] = df["provider_zip_code"].astype(str).str[:10]

        # Remove duplicates based on provider_id and ms_drg_definition
        df = df.drop_duplicates(subset=["provider_id", "ms_drg_definition"])

        logger.info(f"Data cleaning completed. Final shape: {df.shape}")
        return df

    async def geocode_providers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add latitude and longitude coordinates to providers"""
        logger.info("Starting geocoding process...")

        if "provider_zip_code" not in df.columns:
            logger.warning("No ZIP code column found, skipping geocoding")
            df["latitude"] = None
            df["longitude"] = None
            return df

        # Get unique ZIP codes to minimize API calls
        unique_zips = df["provider_zip_code"].dropna().unique()
        zip_coordinates = {}

        for i, zip_code in enumerate(unique_zips):
            if pd.isna(zip_code) or zip_code == "nan":
                continue

            try:
                location = self.geocoder.geocode(f"{zip_code}, USA")
                if location:
                    zip_coordinates[zip_code] = (location.latitude, location.longitude)
                    logger.info(
                        f"Geocoded {zip_code}: {location.latitude}, {location.longitude}"
                    )
                else:
                    zip_coordinates[zip_code] = (None, None)
                    logger.warning(f"Could not geocode ZIP: {zip_code}")

                # Rate limiting to avoid hitting API limits
                time.sleep(0.1)

            except (GeocoderTimedOut, Exception) as e:
                logger.error(f"Geocoding failed for {zip_code}: {str(e)}")
                zip_coordinates[zip_code] = (None, None)

            # Progress update
            if (i + 1) % 50 == 0:
                logger.info(f"Geocoded {i + 1}/{len(unique_zips)} ZIP codes")

        # Map coordinates back to dataframe
        df["latitude"] = df["provider_zip_code"].map(
            lambda x: zip_coordinates.get(x, (None, None))[0]
        )
        df["longitude"] = df["provider_zip_code"].map(
            lambda x: zip_coordinates.get(x, (None, None))[1]
        )

        geocoded_count = df["latitude"].notna().sum()
        logger.info(f"Successfully geocoded {geocoded_count}/{len(df)} providers")

        return df

    def generate_mock_ratings(self, provider_ids: list) -> list:
        """Generate mock star ratings for providers"""
        logger.info(f"Generating mock ratings for {len(provider_ids)} providers")

        ratings = []
        for provider_id in provider_ids:
            # Generate 1-3 ratings per provider with realistic distribution
            num_ratings = random.randint(1, 3)
            for _ in range(num_ratings):
                # Weighted towards higher ratings (realistic hospital distribution)
                rating = random.choices(
                    population=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                    weights=[1, 1, 2, 3, 5, 8, 12, 15, 10, 8],
                    k=1,
                )[0]

                ratings.append({"provider_id": provider_id, "rating": float(rating)})

        logger.info(f"Generated {len(ratings)} total ratings")
        return ratings

    async def load_providers(self, df: pd.DataFrame):
        """Load provider data into database"""
        logger.info("Loading provider data into database...")

        async with self.AsyncSessionLocal() as session:
            try:
                providers_data = []
                for _, row in df.iterrows():
                    provider_data = {
                        "provider_id": str(row["provider_id"]),
                        "provider_name": str(row["provider_name"])[:255],
                        "provider_city": (
                            str(row.get("provider_city", ""))[:100]
                            if pd.notna(row.get("provider_city"))
                            else None
                        ),
                        "provider_state": (
                            str(row.get("provider_state", ""))[:2]
                            if pd.notna(row.get("provider_state"))
                            else None
                        ),
                        "provider_zip_code": (
                            str(row.get("provider_zip_code", ""))[:10]
                            if pd.notna(row.get("provider_zip_code"))
                            else None
                        ),
                        "latitude": (
                            float(row["latitude"])
                            if pd.notna(row.get("latitude"))
                            else None
                        ),
                        "longitude": (
                            float(row["longitude"])
                            if pd.notna(row.get("longitude"))
                            else None
                        ),
                        "ms_drg_definition": (
                            str(row["ms_drg_definition"])
                            if pd.notna(row.get("ms_drg_definition"))
                            else None
                        ),
                        "total_discharges": (
                            int(row["total_discharges"])
                            if pd.notna(row.get("total_discharges"))
                            else None
                        ),
                        "average_covered_charges": (
                            float(row["average_covered_charges"])
                            if pd.notna(row.get("average_covered_charges"))
                            else None
                        ),
                        "average_total_payments": (
                            float(row["average_total_payments"])
                            if pd.notna(row.get("average_total_payments"))
                            else None
                        ),
                        "average_medicare_payments": (
                            float(row["average_medicare_payments"])
                            if pd.notna(row.get("average_medicare_payments"))
                            else None
                        ),
                    }
                    providers_data.append(provider_data)

                # Bulk insert providers
                await session.execute(
                    text(
                        """
                        INSERT INTO providers (
                            provider_id, provider_name, provider_city, provider_state, 
                            provider_zip_code, latitude, longitude, ms_drg_definition,
                            total_discharges, average_covered_charges, average_total_payments, 
                            average_medicare_payments
                        ) VALUES (
                            :provider_id, :provider_name, :provider_city, :provider_state,
                            :provider_zip_code, :latitude, :longitude, :ms_drg_definition,
                            :total_discharges, :average_covered_charges, :average_total_payments,
                            :average_medicare_payments
                        )
                    """
                    ),
                    providers_data,
                )

                await session.commit()
                logger.info(
                    f"Successfully loaded {len(providers_data)} provider records"
                )

            except Exception as e:
                await session.rollback()
                logger.error(f"Error loading providers: {str(e)}")
                raise

    async def load_ratings(self, ratings_data: list):
        """Load ratings data into database"""
        logger.info("Loading ratings data into database...")

        async with self.AsyncSessionLocal() as session:
            try:
                await session.execute(
                    text(
                        """
                        INSERT INTO ratings (provider_id, rating)
                        VALUES (:provider_id, :rating)
                    """
                    ),
                    ratings_data,
                )

                await session.commit()
                logger.info(f"Successfully loaded {len(ratings_data)} rating records")

            except Exception as e:
                await session.rollback()
                logger.error(f"Error loading ratings: {str(e)}")
                raise

    async def run_etl(self):
        """Run the complete ETL process"""
        logger.info("Starting Healthcare Cost Navigator ETL process...")

        try:
            # Step 1: Create database tables
            await self.create_tables()

            # Step 2: Load and clean CSV data
            logger.info(f"Loading CSV file: {self.csv_file_path}")
            df = pd.read_csv(self.csv_file_path)
            df = self.clean_data(df)

            # Step 3: Geocode provider locations
            df = await self.geocode_providers(df)

            # Step 4: Load provider data
            await self.load_providers(df)

            # Step 5: Generate and load mock ratings
            unique_provider_ids = df["provider_id"].unique().tolist()
            ratings_data = self.generate_mock_ratings(unique_provider_ids)
            await self.load_ratings(ratings_data)

            logger.info("ETL process completed successfully!")

            # Print summary statistics
            await self.print_summary()

        except Exception as e:
            logger.error(f"ETL process failed: {str(e)}")
            raise
        finally:
            await self.engine.dispose()

    async def print_summary(self):
        """Print summary of loaded data"""
        async with self.AsyncSessionLocal() as session:
            try:
                # Count providers
                provider_count = await session.execute(
                    text("SELECT COUNT(*) FROM providers")
                )
                provider_count = provider_count.scalar()

                # Count ratings
                rating_count = await session.execute(
                    text("SELECT COUNT(*) FROM ratings")
                )
                rating_count = rating_count.scalar()

                # Count geocoded providers
                geocoded_count = await session.execute(
                    text("SELECT COUNT(*) FROM providers WHERE latitude IS NOT NULL")
                )
                geocoded_count = geocoded_count.scalar()

                # Sample data
                sample_providers = await session.execute(
                    text(
                        """
                    SELECT provider_name, provider_city, provider_state, ms_drg_definition, average_covered_charges
                    FROM providers 
                    LIMIT 5
                """
                    )
                )

                print("\n" + "=" * 50)
                print("ETL SUMMARY")
                print("=" * 50)
                print(f"Total providers loaded: {provider_count}")
                print(f"Total ratings generated: {rating_count}")
                print(f"Providers with coordinates: {geocoded_count}")
                print(
                    f"Geocoding success rate: {(geocoded_count/provider_count)*100:.1f}%"
                )

                print(f"\nSample providers:")
                for row in sample_providers:
                    print(
                        f"- {row[0]} ({row[1]}, {row[2]}) - {row[3]} - ${row[4]:,.2f}"
                    )

                print("=" * 50)

            except Exception as e:
                logger.error(f"Error generating summary: {str(e)}")


async def main():
    """Main function to run ETL"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return

    csv_file_path = "sample_prices_ny.csv"
    if not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        logger.info(
            "Please download the file from the provided link and place it in the project root"
        )
        return

    etl = HealthcareETL(database_url, csv_file_path)
    await etl.run_etl()


if __name__ == "__main__":
    asyncio.run(main())
