from fastapi import HTTPException, status

from .common import required


def map_devops_operation(provider: str, operation: str, body: dict) -> dict:
    if provider == "github":
        if operation == "list_repos":
            params = {
                k: v
                for k, v in body.items()
                if k in {"per_page", "sort", "direction", "page", "type", "visibility"}
            }
            return {
                "method": "GET",
                "endpoint": "/user/repos",
                "params": params if params else body.get("params"),
            }
        if operation == "get_repo":
            return {
                "method": "GET",
                "endpoint": f"/repos/{required(body, 'owner', operation)}/{required(body, 'repo', operation)}",
            }
        if operation == "list_issues":
            owner = body.get("owner")
            repo = body.get("repo")
            if owner and repo:
                endpoint = f"/repos/{owner}/{repo}/issues"
            else:
                endpoint = "/user/issues"
            params = {
                k: v
                for k, v in body.items()
                if k in {
                    "state",
                    "assignee",
                    "created",
                    "updated",
                    "sort",
                    "direction",
                    "page",
                    "per_page",
                    "labels",
                    "since",
                }
            }
            return {"method": "GET", "endpoint": endpoint, "params": params if params else None}
        if operation == "create_issue":
            return {
                "method": "POST",
                "endpoint": f"/repos/{required(body, 'owner', operation)}/{required(body, 'repo', operation)}/issues",
                "json": {
                    "title": required(body, "title", operation),
                    "body": body.get("body", ""),
                    "assignees": body.get("assignees", []),
                    "labels": body.get("labels", []),
                },
            }

    if provider == "gitlab":
        project_id = body.get("project_id")
        if operation == "list_projects":
            return {"method": "GET", "endpoint": "/projects", "params": body.get("params")}
        if operation == "get_project":
            return {"method": "GET", "endpoint": f"/projects/{required(body, 'project_id', operation)}"}
        if operation == "list_merge_requests":
            return {
                "method": "GET",
                "endpoint": f"/projects/{required({'project_id': project_id}, 'project_id', operation)}/merge_requests",
            }
        if operation == "create_merge_request":
            return {
                "method": "POST",
                "endpoint": f"/projects/{required({'project_id': project_id}, 'project_id', operation)}/merge_requests",
                "json": {
                    "source_branch": required(body, "source_branch", operation),
                    "target_branch": required(body, "target_branch", operation),
                    "title": required(body, "title", operation),
                    "description": body.get("description", ""),
                },
            }

    if provider == "bitbucket":
        workspace = required(body, "workspace", operation)
        if operation == "list_repos":
            return {"method": "GET", "endpoint": f"/repositories/{workspace}"}
        if operation == "get_repo":
            return {
                "method": "GET",
                "endpoint": f"/repositories/{workspace}/{required(body, 'repo_slug', operation)}",
            }
        if operation == "list_pull_requests":
            return {
                "method": "GET",
                "endpoint": f"/repositories/{workspace}/{required(body, 'repo_slug', operation)}/pullrequests",
            }
        if operation == "create_pull_request":
            return {
                "method": "POST",
                "endpoint": f"/repositories/{workspace}/{required(body, 'repo_slug', operation)}/pullrequests",
                "json": required(body, "payload", operation),
            }

    if provider == "vercel":
        if operation == "list_projects":
            return {"method": "GET", "endpoint": "/v9/projects"}
        if operation == "get_project":
            return {"method": "GET", "endpoint": f"/v9/projects/{required(body, 'project_id', operation)}"}
        if operation == "list_deployments":
            return {"method": "GET", "endpoint": "/v6/deployments", "params": body.get("params")}
        if operation == "create_deployment":
            return {"method": "POST", "endpoint": "/v13/deployments", "json": required(body, "payload", operation)}

    if provider == "render":
        if operation == "list_services":
            return {"method": "GET", "endpoint": "/services"}
        if operation == "get_service":
            return {"method": "GET", "endpoint": f"/services/{required(body, 'service_id', operation)}"}
        if operation == "list_deploys":
            return {"method": "GET", "endpoint": f"/services/{required(body, 'service_id', operation)}/deploys"}
        if operation == "trigger_deploy":
            return {"method": "POST", "endpoint": f"/services/{required(body, 'service_id', operation)}/deploys"}

    if provider == "cloudflare":
        if operation == "list_zones":
            return {"method": "GET", "endpoint": "/zones"}
        if operation == "get_zone":
            return {"method": "GET", "endpoint": f"/zones/{required(body, 'zone_id', operation)}"}
        if operation == "list_dns_records":
            return {"method": "GET", "endpoint": f"/zones/{required(body, 'zone_id', operation)}/dns_records"}
        if operation == "create_dns_record":
            return {
                "method": "POST",
                "endpoint": f"/zones/{required(body, 'zone_id', operation)}/dns_records",
                "json": required(body, "record", operation),
            }

    if provider == "railway":
        if operation == "list_projects":
            return {
                "method": "POST",
                "endpoint": "/",
                "json": {"query": "query { projects { edges { node { id name } } } }"},
            }
        if operation == "project_details":
            return {
                "method": "POST",
                "endpoint": "/",
                "json": {
                    "query": "query($projectId: String!) { project(id: $projectId) { id name services { edges { node { id name } } } } }",
                    "variables": {"projectId": required(body, "project_id", operation)},
                },
            }

    raise HTTPException(
        status.HTTP_400_BAD_REQUEST,
        f"Unsupported devops operation '{operation}' for provider '{provider}'",
    )
