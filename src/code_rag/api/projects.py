from fastapi import APIRouter, HTTPException

from code_rag.models.project import Project

router = APIRouter()


@router.get("/projects", response_model=list[Project])
async def list_projects():
    """列出所有已索引的專案。"""
    from code_rag.main import get_state_db, get_qdrant

    state_db = get_state_db()
    qdrant = get_qdrant()
    projects = state_db.get_all_projects()

    result = []
    for p in projects:
        stats = qdrant.get_project_stats(p["project_name"])
        result.append(
            Project(
                name=p["project_name"],
                path="",
                file_count=p.get("total_files", 0),
                chunk_count=stats["chunk_count"],
                indexed_at=p.get("completed_at"),
            )
        )
    return result


@router.delete("/projects/{project_name}")
async def delete_project(project_name: str):
    """移除專案索引。"""
    from code_rag.main import get_state_db, get_qdrant

    state_db = get_state_db()
    qdrant = get_qdrant()

    status = state_db.get_index_status(project_name)
    if not status:
        raise HTTPException(404, f"Project '{project_name}' not found")

    if status["status"] == "running":
        raise HTTPException(409, f"Project '{project_name}' is currently being indexed, cannot delete")

    qdrant.delete_by_project(project_name)
    state_db.remove_project(project_name)
    return {"message": f"Project '{project_name}' removed"}
