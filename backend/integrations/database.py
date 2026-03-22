from fastapi import HTTPException, status
from .common import required

def map_database_operation(provider: str, operation: str, body: dict) -> dict:
    if provider == "neondb":
        # Check if they passed a connection string instead of an API key
        if "://" in str(body.get("api_key", "")) or "@" in str(body.get("api_key", "")):
             raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "NeonDB API requires an API Key (neon_...), but a connection string was provided."
            )

        if operation == "list_projects":
            return {
                "method": "GET",
                "endpoint": "/projects",
            }
        if operation == "get_project":
            return {
                "method": "GET",
                "endpoint": f"/projects/{required(body, 'project_id', operation)}",
            }
        if operation == "list_tables":
            # For NeonDB, this might require a specific branch/endpoint
            project_id = required(body, "project_id", operation)
            branch_id = body.get("branch_id", "main")
            return {
                "method": "GET",
                "endpoint": f"/projects/{project_id}/branches/{branch_id}/databases",
            }

    if provider == "supabase":
        if operation == "list_projects":
            return {"method": "GET", "endpoint": "/projects"}
        
    if provider == "xata":
        if operation == "list_workspaces":
            return {"method": "GET", "endpoint": "/workspaces"}

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Unsupported database operation '{operation}' for provider '{provider}'",
    )
