"""FastAPI application for Meridian REST API.

Provides endpoints for supplier management, data ingestion, and system health.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..graph import get_neo4j_client, get_supplier_repository
from ..graph.models import Supplier
from ..ingestion import get_csv_upload_service
from .routes import alerts as alerts_routes

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager — handles startup and shutdown."""
    # Startup
    logger.info("api_startup")
    
    # Test Neo4j connection
    client = get_neo4j_client()
    if not client.health_check():
        logger.warning("neo4j_unhealthy_on_startup")
    
    yield
    
    # Shutdown
    logger.info("api_shutdown")
    client = get_neo4j_client()
    client.close()


app = FastAPI(
    title="Meridian Supply Chain Risk Intelligence API",
    description="REST API for supplier management, risk scoring, and data ingestion",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware — origins configured via CORS_ALLOWED_ORIGINS env var
# Defaults to localhost dev origins; production must set explicit allowlist.
_default_cors = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"
_cors_origins = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", _default_cors).split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Mount route modules
app.include_router(alerts_routes.router)


# Health check endpoints

@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "meridian-api"}


@app.get("/health/neo4j", tags=["Health"])
async def neo4j_health():
    """Check Neo4j database connectivity."""
    client = get_neo4j_client()
    is_healthy = client.health_check()
    
    if is_healthy:
        return {"status": "healthy", "database": "neo4j"}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j database is unreachable"
        )


# Supplier endpoints

@app.post(
    "/suppliers",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    tags=["Suppliers"]
)
async def create_supplier(supplier_data: dict):
    """Create a new supplier.
    
    Required fields:
    - name: Supplier company name
    - country_iso: Two-letter country code (e.g., "US", "CN")
    
    Optional fields:
    - region, city, tier, industry, annual_revenue_usd, employee_count
    - latitude, longitude, single_source_flag, critical_flag
    """
    try:
        # Validate and create Supplier model
        supplier = Supplier(**supplier_data)
        
        # Create in Neo4j
        repo = get_supplier_repository()
        created = repo.create(supplier)
        
        logger.info(
            "supplier_created_via_api",
            supplier_id=created.id,
            name=created.name
        )
        
        return {
            "id": created.id,
            "name": created.name,
            "country_iso": created.country_iso,
            "created_at": created.created_at.isoformat() if created.created_at else None
        }
        
    except Exception as e:
        logger.error("supplier_create_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create supplier: {str(e)}"
        )


@app.get(
    "/suppliers/{supplier_id}",
    response_model=dict,
    tags=["Suppliers"]
)
async def get_supplier(supplier_id: str):
    """Get a supplier by ID."""
    repo = get_supplier_repository()
    supplier = repo.get_by_id(supplier_id)
    
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier not found: {supplier_id}"
        )
    
    return supplier.model_dump()


@app.get(
    "/suppliers",
    response_model=dict,
    tags=["Suppliers"]
)
async def list_suppliers(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    country: Optional[str] = Query(default=None, description="Filter by country ISO code")
):
    """List suppliers with pagination and optional country filter."""
    repo = get_supplier_repository()
    
    if country:
        suppliers = repo.get_by_country(country.upper(), limit=limit)
    else:
        suppliers = repo.get_all(limit=limit, offset=offset)
    
    total = repo.count()
    
    return {
        "suppliers": [s.model_dump() for s in suppliers],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.put(
    "/suppliers/{supplier_id}",
    response_model=dict,
    tags=["Suppliers"]
)
async def update_supplier(supplier_id: str, updates: dict):
    """Update a supplier by ID.
    
    Provide only fields to update. Cannot update id or created_at.
    """
    repo = get_supplier_repository()
    
    # Check if supplier exists
    existing = repo.get_by_id(supplier_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier not found: {supplier_id}"
        )
    
    # Remove immutable fields
    updates.pop("id", None)
    updates.pop("created_at", None)
    
    try:
        updated = repo.update(supplier_id, updates)
        
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update failed"
            )
        
        logger.info("supplier_updated_via_api", supplier_id=supplier_id)
        return updated.model_dump()
        
    except Exception as e:
        logger.error("supplier_update_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update supplier: {str(e)}"
        )


@app.delete(
    "/suppliers/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Suppliers"]
)
async def delete_supplier(supplier_id: str):
    """Delete a supplier by ID."""
    repo = get_supplier_repository()
    
    # Check if exists
    existing = repo.get_by_id(supplier_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier not found: {supplier_id}"
        )
    
    # Delete
    deleted = repo.delete(supplier_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delete failed"
        )
    
    logger.info("supplier_deleted_via_api", supplier_id=supplier_id)
    return None


@app.post(
    "/suppliers/upload",
    response_model=dict,
    tags=["Suppliers"]
)
async def upload_suppliers_csv(file: UploadFile = File(...)):
    """Upload suppliers via CSV file.
    
    Expected CSV columns:
    - name (required)
    - country_iso (required, 2-letter code)
    - region, city, tier, industry, annual_revenue_usd, employee_count
    - latitude, longitude
    - single_source_flag, critical_flag
    
    Returns upload statistics including success count and any errors.
    """
    # Validate file type
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV"
        )
    
    try:
        # Read file content
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is empty"
            )
        
        # Process CSV
        service = get_csv_upload_service()
        result = service.upload(content)
        
        logger.info(
            "suppliers_csv_uploaded",
            filename=file.filename,
            total=result.total_rows,
            success=result.success_count
        )
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("csv_upload_failed", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@app.get(
    "/suppliers/template/download",
    response_class=JSONResponse,
    tags=["Suppliers"]
)
async def download_supplier_template():
    """Download a CSV template for supplier uploads."""
    service = get_csv_upload_service()
    template = service.get_template_csv()
    
    return JSONResponse(
        content={
            "template": template,
            "description": "CSV template for supplier uploads. Save this content as a .csv file and fill in your data."
        }
    )


# Statistics endpoints

@app.get(
    "/stats",
    response_model=dict,
    tags=["Statistics"]
)
async def get_statistics():
    """Get system statistics."""
    repo = get_supplier_repository()
    
    supplier_count = repo.count()
    
    return {
        "suppliers": {
            "total": supplier_count
        },
        "version": "0.1.0"
    }


# Visualization endpoints

@app.get(
    "/visualization/network",
    response_model=dict,
    tags=["Visualization"]
)
async def get_network_graph(
    center_supplier_id: Optional[str] = None,
    depth: int = Query(default=2, ge=1, le=5),
    min_risk_score: float = Query(default=0.0, ge=0.0, le=1.0)
):
    """Get supply chain network graph for visualization.
    
    Returns nodes (suppliers, ports, chokepoints) and edges (relationships)
    for D3.js or Cytoscape.js network visualization.
    
    Args:
        center_supplier_id: Optional supplier to center graph on
        depth: BFS depth to explore (1-5)
        min_risk_score: Filter entities by minimum risk score
    """
    try:
        from ..graph import get_neo4j_client
        from ..simulation import get_propagation_engine
        
        client = get_neo4j_client()
        
        # Build query based on parameters
        if center_supplier_id:
            # Get subgraph around specific supplier
            query = """
            MATCH path = (center:Supplier {id: $supplier_id})-[*1..$depth]-(connected)
            WHERE connected.risk_score >= $min_risk OR connected.risk_score IS NULL
            RETURN center, connected, relationships(path) as rels
            LIMIT 100
            """
            result = client.execute_query(query, {
                "supplier_id": center_supplier_id,
                "depth": depth,
                "min_risk": min_risk_score
            })
        else:
            # Get global network (top suppliers by risk)
            query = """
            MATCH (s:Supplier)
            OPTIONAL MATCH (s)-[r]->(n)
            RETURN s, collect(DISTINCT n) as neighbors, collect(DISTINCT r) as relationships
            ORDER BY s.risk_score DESC
            LIMIT 50
            """
            result = client.execute_query(query)
        
        # Transform to visualization format
        nodes = []
        edges = []
        node_ids = set()
        
        for record in result:
            # Add center/supplier node
            supplier = record.get("s") or record.get("center")
            if supplier and supplier.get("id") not in node_ids:
                nodes.append({
                    "id": supplier["id"],
                    "type": "supplier",
                    "label": supplier.get("name", "Unknown"),
                    "country": supplier.get("country_iso"),
                    "risk_score": supplier.get("risk_score", 0),
                    "latitude": supplier.get("latitude"),
                    "longitude": supplier.get("longitude"),
                    "critical": supplier.get("critical_flag", False)
                })
                node_ids.add(supplier["id"])
            
            # Add connected nodes
            neighbors = record.get("neighbors", []) or [record.get("connected")]
            for neighbor in neighbors:
                if neighbor and neighbor.get("id") not in node_ids:
                    node_type = list(neighbor.labels)[0].lower() if hasattr(neighbor, 'labels') else 'unknown'
                    nodes.append({
                        "id": neighbor["id"],
                        "type": node_type,
                        "label": neighbor.get("name", neighbor.get("locode", "Unknown")),
                        "country": neighbor.get("country_iso"),
                        "risk_score": neighbor.get("risk_score", 0),
                        "latitude": neighbor.get("latitude"),
                        "longitude": neighbor.get("longitude")
                    })
                    node_ids.add(neighbor["id"])
            
            # Add edges
            rels = record.get("relationships", []) or record.get("rels", [])
            for rel in rels:
                if hasattr(rel, 'start_node') and hasattr(rel, 'end_node'):
                    edges.append({
                        "source": rel.start_node["id"],
                        "target": rel.end_node["id"],
                        "type": type(rel).__name__
                    })
        
        logger.info(
            "network_graph_generated",
            nodes=len(nodes),
            edges=len(edges),
            center=center_supplier_id
        )
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "center_supplier": center_supplier_id,
                "depth": depth
            }
        }
        
    except Exception as e:
        logger.error("network_graph_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate network graph: {str(e)}"
        )


@app.get(
    "/visualization/risk-map",
    response_model=dict,
    tags=["Visualization"]
)
async def get_risk_map_data(
    entity_type: str = Query(default="supplier", enum=["supplier", "port", "chokepoint"]),
    min_risk: float = Query(default=0.0, ge=0.0, le=1.0)
):
    """Get geospatial risk data for Mapbox visualization.
    
    Returns entities with lat/lon and risk scores for heatmap/scatter plot.
    """
    try:
        from ..graph import get_neo4j_client
        
        client = get_neo4j_client()
        
        query = f"""
        MATCH (n:{entity_type})
        WHERE n.risk_score >= $min_risk AND n.latitude IS NOT NULL AND n.longitude IS NOT NULL
        RETURN n.id as id, n.name as name, n.latitude as lat, n.longitude as lon,
               n.risk_score as risk, n.country_iso as country
        ORDER BY n.risk_score DESC
        LIMIT 500
        """
        
        result = client.execute_query(query, {"min_risk": min_risk})
        
        features = []
        for record in result:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [record["lon"], record["lat"]]
                },
                "properties": {
                    "id": record["id"],
                    "name": record["name"],
                    "risk_score": record["risk"],
                    "risk_category": _risk_to_category(record["risk"]),
                    "country": record["country"]
                }
            })
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "entity_type": entity_type,
                "count": len(features),
                "min_risk": min_risk
            }
        }
        
    except Exception as e:
        logger.error("risk_map_data_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate risk map data: {str(e)}"
        )


def _risk_to_category(risk: float) -> str:
    """Convert risk score to category."""
    if risk is None:
        return "UNKNOWN"
    if risk < 0.2:
        return "NONE"
    elif risk < 0.4:
        return "LOW"
    elif risk < 0.6:
        return "MEDIUM"
    elif risk < 0.8:
        return "HIGH"
    else:
        return "CRITICAL"


@app.get(
    "/suppliers/{supplier_id}/explanation",
    response_model=dict,
    tags=["Suppliers"]
)
async def get_supplier_risk_explanation(supplier_id: str):
    """Get SHAP-based risk explanation for a supplier.
    
    Returns feature contributions and top risk factors.
    """
    try:
        from ..intelligence import get_supplier_risk
        
        result = get_supplier_risk(supplier_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        # Format SHAP explanation
        current_risk = result.get("current_risk", {})
        explanations = []
        
        for factor in current_risk.get("top_factors", []):
            explanations.append({
                "feature": factor["feature"],
                "description": factor["description"],
                "contribution": factor["contribution"],
                "direction": factor["direction"]
            })
        
        return {
            "supplier_id": supplier_id,
            "risk_score": current_risk.get("risk_score"),
            "risk_category": current_risk.get("risk_category"),
            "explanations": explanations,
            "model_version": result.get("model_versions", {}).get("risk_scorer"),
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("risk_explanation_failed", error=str(e), supplier_id=supplier_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate explanation: {str(e)}"
        )


@app.post(
    "/intelligence/weekly-digest",
    response_model=dict,
    tags=["Intelligence"]
)
async def generate_weekly_digest():
    """Generate weekly risk digest using LLM.
    
    Summarizes week's events, top risks, and recommendations.
    """
    try:
        from ..graph import get_neo4j_client
        from ..intelligence import get_intelligence_service
        
        client = get_neo4j_client()
        
        # Get week's events
        query = """
        MATCH (e:Event)
        WHERE e.resolved_at > datetime() - duration('P7D')
        RETURN e.event_type as type, count(e) as count
        ORDER BY count DESC
        """
        events = client.execute_query(query)
        
        # Get top risky suppliers
        suppliers_query = """
        MATCH (s:Supplier)
        WHERE s.risk_score > 0.6
        RETURN s.id as id, s.name as name, s.risk_score as risk
        ORDER BY s.risk_score DESC
        LIMIT 10
        """
        risky_suppliers = client.execute_query(suppliers_query)
        
        # Get active alerts
        alerts_query = """
        MATCH (e:Event)-[:AFFECTS]->(s)
        WHERE e.resolved_at > datetime() - duration('P7D')
        RETURN count(DISTINCT e) as total_events, count(DISTINCT s) as affected_suppliers
        """
        alert_stats = client.execute_query(alerts_query)
        
        # Build digest content
        digest = {
            "period": "Last 7 days",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_events": alert_stats[0].get("total_events", 0) if alert_stats else 0,
                "affected_suppliers": alert_stats[0].get("affected_suppliers", 0) if alert_stats else 0,
                "top_event_types": [
                    {"type": e["type"], "count": e["count"]} for e in events[:5]
                ] if events else []
            },
            "top_risks": [
                {
                    "supplier_id": s["id"],
                    "name": s["name"],
                    "risk_score": s["risk"],
                    "risk_category": _risk_to_category(s["risk"])
                }
                for s in risky_suppliers[:5]
            ] if risky_suppliers else [],
            "recommendations": _generate_digest_recommendations(risky_suppliers),
            "narrative": _generate_narrative(events, risky_suppliers, alert_stats)
        }
        
        logger.info("weekly_digest_generated")
        
        return digest
        
    except Exception as e:
        logger.error("weekly_digest_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate digest: {str(e)}"
        )


def _generate_digest_recommendations(risky_suppliers: list) -> list:
    """Generate recommendations based on risk data."""
    recommendations = []
    
    if risky_suppliers and len(risky_suppliers) > 0:
        recommendations.append(
            f"Review top {min(3, len(risky_suppliers))} high-risk suppliers immediately"
        )
    
    if risky_suppliers and any(s.get("risk", 0) > 0.8 for s in risky_suppliers[:3]):
        recommendations.append("Activate contingency plans for CRITICAL risk suppliers")
    
    recommendations.extend([
        "Review inventory buffers for affected SKUs",
        "Check alternative supplier availability",
        "Update stakeholders on risk landscape"
    ])
    
    return recommendations


def _generate_narrative(events: list, suppliers: list, stats: list) -> str:
    """Generate human-readable narrative summary."""
    total_events = stats[0].get("total_events", 0) if stats else 0
    affected = stats[0].get("affected_suppliers", 0) if stats else 0
    
    if total_events == 0:
        return "This week was relatively quiet with no significant supply chain disruptions detected."
    
    narrative = f"This week saw {total_events} risk events affecting {affected} suppliers. "
    
    if suppliers:
        top = suppliers[0]
        narrative += f"The highest risk is {top['name']} with a {top['risk']:.0%} risk score. "
    
    if events:
        top_event = events[0]
        narrative += f"Most common events were {top_event['type']} ({top_event['count']} occurrences). "
    
    narrative += "Monitor these developments closely and review contingency plans where needed."
    
    return narrative


# Import auth endpoints
from ..api.auth.jwt import create_auth_endpoints
create_auth_endpoints(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
