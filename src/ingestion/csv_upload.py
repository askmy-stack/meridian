"""CSV upload service for supplier data ingestion.

Parses CSV files and creates Supplier nodes in Neo4j.
Supports standard supplier data formats with validation.
"""

from io import StringIO
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import structlog

from ..graph.models import Supplier
from ..graph.repositories.supplier_repository import (
    SupplierRepository,
    get_supplier_repository,
)

logger = structlog.get_logger(__name__)


# Expected CSV columns (flexible mapping)
CSV_COLUMN_MAPPINGS = {
    # Supplier name
    "name": ["name", "supplier_name", "company", "company_name", "supplier"],
    # Country
    "country_iso": ["country", "country_iso", "country_code", "iso", "cc"],
    # Region
    "region": ["region", "state", "province"],
    # Tier
    "tier": ["tier", "supply_tier", "tier_level"],
    # Industry
    "industry": ["industry", "sector", "category"],
    # Revenue
    "annual_revenue_usd": ["revenue", "annual_revenue", "revenue_usd", "annual_revenue_usd"],
    # Employees
    "employee_count": ["employees", "employee_count", "headcount"],
    # City
    "city": ["city", "town"],
    # Coordinates
    "latitude": ["lat", "latitude"],
    "longitude": ["lon", "lng", "longitude"],
    # Risk flags
    "single_source_flag": ["single_source", "sole_source", "is_single_source"],
    "critical_flag": ["critical", "is_critical", "strategic"],
}


class CSVUploadResult:
    """Result of CSV upload operation."""
    
    def __init__(
        self,
        total_rows: int = 0,
        success_count: int = 0,
        error_count: int = 0,
        errors: Optional[List[Dict[str, Any]]] = None,
        created_ids: Optional[List[str]] = None
    ):
        self.total_rows = total_rows
        self.success_count = success_count
        self.error_count = error_count
        self.errors = errors or []
        self.created_ids = created_ids or []
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_rows == 0:
            return 0.0
        return (self.success_count / self.total_rows) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_rows": self.total_rows,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": round(self.success_rate, 2),
            "errors": self.errors[:10],  # Limit errors in response
            "created_ids": self.created_ids[:10]  # Limit IDs in response
        }


class SupplierCSVUploadService:
    """Service for uploading supplier data via CSV.
    
    Usage:
        service = SupplierCSVUploadService()
        with open("suppliers.csv", "rb") as f:
            result = service.upload(f.read())
        print(f"Created {result.success_count} suppliers")
    """
    
    def __init__(self, repository: Optional[SupplierRepository] = None):
        """Initialize upload service.
        
        Args:
            repository: SupplierRepository instance (uses singleton if None)
        """
        self.repository = repository or get_supplier_repository()
        self.logger = logger.bind(service="SupplierCSVUploadService")
    
    def upload(
        self,
        csv_content: bytes,
        encoding: str = "utf-8",
        delimiter: str = ",",
        batch_size: int = 100
    ) -> CSVUploadResult:
        """Upload suppliers from CSV content.
        
        Args:
            csv_content: Raw CSV file content as bytes
            encoding: File encoding (default: utf-8)
            delimiter: CSV delimiter (default: comma)
            batch_size: Number of records to insert per batch
            
        Returns:
            CSVUploadResult with success/failure counts
        """
        try:
            # Parse CSV with pandas
            df = self._parse_csv(csv_content, encoding, delimiter)
            
            if df.empty:
                self.logger.warning("csv_empty")
                return CSVUploadResult(total_rows=0)
            
            self.logger.info(
                "csv_parsed",
                rows=len(df),
                columns=list(df.columns)
            )
            
            # Normalize column names
            df = self._normalize_columns(df)
            
            # Validate and convert to Supplier models
            suppliers, errors = self._validate_dataframe(df)
            
            # Create suppliers in batches
            created_ids = []
            for i in range(0, len(suppliers), batch_size):
                batch = suppliers[i:i + batch_size]
                try:
                    created = self.repository.create_many(batch)
                    created_ids.extend([s.id for s in created])
                    self.logger.info(
                        "batch_created",
                        batch_num=i // batch_size + 1,
                        count=len(created)
                    )
                except Exception as e:
                    self.logger.error("batch_create_failed", error=str(e))
                    # Add errors for this batch
                    for j in range(len(batch)):
                        errors.append({
                            "row": i + j + 2,  # +2 for header and 1-indexing
                            "error": f"Batch insert failed: {str(e)}"
                        })
            
            result = CSVUploadResult(
                total_rows=len(df),
                success_count=len(created_ids),
                error_count=len(errors),
                errors=errors,
                created_ids=created_ids
            )
            
            self.logger.info(
                "upload_complete",
                total=result.total_rows,
                success=result.success_count,
                errors=result.error_count
            )
            
            return result
            
        except pd.errors.EmptyDataError:
            self.logger.warning("csv_empty_no_data")
            return CSVUploadResult(total_rows=0)
        except pd.errors.ParserError as e:
            self.logger.error("csv_parse_error", error=str(e))
            return CSVUploadResult(
                total_rows=0,
                error_count=1,
                errors=[{"row": 0, "error": f"CSV parse error: {str(e)}"}]
            )
        except Exception as e:
            self.logger.error("upload_failed", error=str(e))
            return CSVUploadResult(
                total_rows=0,
                error_count=1,
                errors=[{"row": 0, "error": f"Upload failed: {str(e)}"}]
            )
    
    def _parse_csv(
        self,
        csv_content: bytes,
        encoding: str,
        delimiter: str
    ) -> pd.DataFrame:
        """Parse CSV content to DataFrame.
        
        Args:
            csv_content: Raw CSV bytes
            encoding: File encoding
            delimiter: CSV delimiter
            
        Returns:
            pandas DataFrame
        """
        # Decode bytes to string
        content_str = csv_content.decode(encoding, errors="replace")
        
        # Parse with pandas
        return pd.read_csv(
            StringIO(content_str),
            delimiter=delimiter,
            dtype=str,  # Read all as strings initially
            keep_default_na=False,
            na_values=["", "NULL", "null", "NA", "na"]
        )
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize CSV column names to match Supplier model.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with normalized column names
        """
        # Convert column names to lowercase and strip whitespace
        df.columns = df.columns.str.lower().str.strip()
        
        # Create mapping from input columns to model fields
        column_mapping = {}
        for model_field, csv_aliases in CSV_COLUMN_MAPPINGS.items():
            for alias in csv_aliases:
                if alias in df.columns:
                    column_mapping[alias] = model_field
                    break
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        return df
    
    def _validate_dataframe(
        self,
        df: pd.DataFrame
    ) -> Tuple[List[Supplier], List[Dict[str, Any]]]:
        """Validate DataFrame rows and convert to Supplier models.
        
        Args:
            df: DataFrame with normalized columns
            
        Returns:
            Tuple of (valid Suppliers, list of error dicts)
        """
        suppliers = []
        errors = []
        
        required_fields = ["name", "country_iso"]
        
        for idx, row in df.iterrows():
            row_num = idx + 2  # +2 for header and 1-indexing
            
            try:
                # Check required fields
                missing = []
                for field in required_fields:
                    if field not in row or pd.isna(row[field]) or row[field] == "":
                        missing.append(field)
                
                if missing:
                    errors.append({
                        "row": row_num,
                        "error": f"Missing required fields: {', '.join(missing)}"
                    })
                    continue
                
                # Build supplier data dict
                supplier_data: Dict[str, Any] = {
                    "name": str(row["name"]).strip(),
                    "country_iso": str(row["country_iso"]).strip().upper(),
                }
                
                # Optional fields
                if "region" in row and not pd.isna(row["region"]):
                    supplier_data["region"] = str(row["region"]).strip()
                
                if "city" in row and not pd.isna(row["city"]):
                    supplier_data["city"] = str(row["city"]).strip()
                
                if "industry" in row and not pd.isna(row["industry"]):
                    supplier_data["industry"] = str(row["industry"]).strip()
                
                # Numeric fields
                if "tier" in row and not pd.isna(row["tier"]):
                    try:
                        supplier_data["tier"] = int(float(row["tier"]))
                    except (ValueError, TypeError):
                        pass
                
                if "annual_revenue_usd" in row and not pd.isna(row["annual_revenue_usd"]):
                    try:
                        val = str(row["annual_revenue_usd"]).replace(",", "").replace("$", "")
                        supplier_data["annual_revenue_usd"] = float(val)
                    except (ValueError, TypeError):
                        pass
                
                if "employee_count" in row and not pd.isna(row["employee_count"]):
                    try:
                        val = str(row["employee_count"]).replace(",", "")
                        supplier_data["employee_count"] = int(float(val))
                    except (ValueError, TypeError):
                        pass
                
                # Coordinates
                if "latitude" in row and not pd.isna(row["latitude"]):
                    try:
                        supplier_data["latitude"] = float(row["latitude"])
                    except (ValueError, TypeError):
                        pass
                
                if "longitude" in row and not pd.isna(row["longitude"]):
                    try:
                        supplier_data["longitude"] = float(row["longitude"])
                    except (ValueError, TypeError):
                        pass
                
                # Boolean flags
                if "single_source_flag" in row and not pd.isna(row["single_source_flag"]):
                    val = str(row["single_source_flag"]).lower()
                    supplier_data["single_source_flag"] = val in ["true", "yes", "1", "y"]
                
                if "critical_flag" in row and not pd.isna(row["critical_flag"]):
                    val = str(row["critical_flag"]).lower()
                    supplier_data["critical_flag"] = val in ["true", "yes", "1", "y"]
                
                # Create Supplier model (validates data)
                supplier = Supplier(**supplier_data)
                suppliers.append(supplier)
                
            except Exception as e:
                errors.append({
                    "row": row_num,
                    "error": f"Validation error: {str(e)}"
                })
        
        return suppliers, errors
    
    def get_template_csv(self) -> str:
        """Get template CSV content for users to download.
        
        Returns:
            CSV string with template headers
        """
        headers = [
            "name", "country_iso", "region", "city",
            "tier", "industry", "annual_revenue_usd", "employee_count",
            "latitude", "longitude",
            "single_source_flag", "critical_flag"
        ]
        
        # Example row
        example = [
            "Acme Manufacturing", "US", "Texas", "Austin",
            "1", "Electronics", "50000000", "500",
            "30.2672", "-97.7431",
            "false", "true"
        ]
        
        return ",".join(headers) + "\n" + ",".join(example) + "\n"


# Singleton instance
_service: Optional[SupplierCSVUploadService] = None


def get_csv_upload_service() -> SupplierCSVUploadService:
    """Get or create singleton SupplierCSVUploadService.
    
    Returns:
        SupplierCSVUploadService singleton
    """
    global _service
    if _service is None:
        _service = SupplierCSVUploadService()
    return _service
