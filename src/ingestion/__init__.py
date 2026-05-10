"""Data ingestion module for Meridian.

Provides CSV upload and other data import capabilities.
"""

from .csv_upload import (
    CSVUploadResult,
    SupplierCSVUploadService,
    get_csv_upload_service,
)

__all__ = [
    "CSVUploadResult",
    "SupplierCSVUploadService",
    "get_csv_upload_service",
]
