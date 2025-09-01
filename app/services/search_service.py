# app/services/search_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from typing import Optional, Tuple
import logging
from ..crud import get_providers_by_drg_and_location, get_provider_count
from ..schemas import ProvidersSearchResponse, ProviderResponse

logger = logging.getLogger(__name__)


class GeocodingService:
    def __init__(self):
        self.geocoder = Nominatim(user_agent="healthcare_cost_navigator")

    async def get_coordinates_from_zip(
        self, zip_code: str
    ) -> Optional[Tuple[float, float]]:
        """Convert ZIP code to latitude/longitude coordinates"""
        try:
            # Add country code for more accurate results
            location = self.geocoder.geocode(f"{zip_code}, USA", timeout=10)
            if location:
                return (location.latitude, location.longitude)
            return None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Geocoding failed for ZIP {zip_code}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected geocoding error for ZIP {zip_code}: {str(e)}")
            return None


geocoding_service = GeocodingService()


async def search_providers(
    db: AsyncSession,
    drg: Optional[str] = None,
    zip_code: Optional[str] = None,
    radius_km: Optional[float] = 25.0,
    limit: int = 20,
) -> ProvidersSearchResponse:
    """
    Search for healthcare providers based on DRG and location criteria
    """
    latitude, longitude = None, None

    # Convert ZIP code to coordinates if provided
    if zip_code:
        coords = await geocoding_service.get_coordinates_from_zip(zip_code)
        if coords:
            latitude, longitude = coords
        else:
            logger.warning(f"Could not geocode ZIP code: {zip_code}")

    # Search providers
    provider_results = await get_providers_by_drg_and_location(
        db=db,
        drg=drg,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit,
    )

    # Convert to response format
    hospitals = []
    for provider, distance, avg_rating in provider_results:
        hospital_data = ProviderResponse(
            provider_id=provider.provider_id,
            provider_name=provider.provider_name,
            provider_city=provider.provider_city,
            provider_state=provider.provider_state,
            provider_zip_code=provider.provider_zip_code,
            ms_drg_definition=provider.ms_drg_definition,
            total_discharges=provider.total_discharges,
            average_covered_charges=provider.average_covered_charges,
            average_total_payments=provider.average_total_payments,
            average_medicare_payments=provider.average_medicare_payments,
            distance_km=round(distance, 1) if distance is not None else None,
            average_rating=round(avg_rating, 1) if avg_rating > 0 else None,
        )
        hospitals.append(hospital_data)

    return ProvidersSearchResponse(hospitals=hospitals, total_count=len(hospitals))


# app/services/__init__.py
# Empty file to make this a package
