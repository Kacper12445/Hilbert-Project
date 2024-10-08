import io
import json
import os
import zipfile
import csv
from typing import List

from app.models.actions import Action
from app.models.project_models import Project, TextDocument
from app.models.request_models import FileDeleteRequest
from app.utility.connectors.rabbitmq_sender import rabbitBroker
from app.utility.file_helper import handleFile
from app.utility.security import check_for_project_ownership
from app.utility.websocket_manager import wsManager
from beanie import WriteRules
from bson import ObjectId
from fastapi import (APIRouter, Depends, HTTPException, Response, UploadFile,
                     WebSocketDisconnect, status)
from fastapi.responses import FileResponse
from starlette.websockets import WebSocket

router = APIRouter(
    prefix="/project",
    tags=["Project Data"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "User not authenticated"},
        status.HTTP_403_FORBIDDEN: {
            "description": "User not authorized for specific project"}
    }
)


@router.websocket("/{projectId}/ws")
async def project_websocket(projectId: str, websocket: WebSocket):
    connection = await wsManager.connect(websocket, projectId)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        wsManager.disconnect(connection)


@router.get("/{project_id}/metrics")
async def get_project_metrics(project: Project = Depends(check_for_project_ownership)):
    folderpath = f'/var/results/{str(project.id)}'
    if(os.path.isdir(folderpath)):
        f = open(f'{folderpath}/config.json')
        configData = json.load(f)
        f.close()
        f = open(f'{folderpath}/metrics.json')
        trainData = json.load(f)
        f.close()
        return {"config": configData, "trainData": trainData}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Project model not initialized")


@router.post("/{project_id}/clear")
async def clear_tags(project: Project = Depends(check_for_project_ownership)):
    await project.fetch_all_links()
    for text in project.texts:
        text.tags = []
        await text.save()
    return "OK"


@router.post("/{project_id}/train")
async def queue_model_training(project: Project = Depends(check_for_project_ownership)):
    projectId = str(project.id)
    project.model_state = "Training"
    await project.save()
    await wsManager.send_by_projectId(Action.ModelTraining, projectId)
    return await rabbitBroker.sendMessage(projectId)


@router.get("/{project_id}/model",
            response_class=FileResponse,
            responses={
                status.HTTP_400_BAD_REQUEST: {
                    "description": "Model not found on server"}
            })
async def download_model(project: Project = Depends(check_for_project_ownership)):
    folderpath = f'/var/results/{str(project.id)}'
    if(os.path.isdir(folderpath)):
        zip_filename = "model.zip"
        stream = io.BytesIO()
        zipFile = zipfile.ZipFile(stream, "w")
        for root, dirs, files in os.walk(folderpath):
            for file in files:
                zipFile.write(os.path.join(root, file), file)
        zipFile.close()
        return Response(stream.getvalue(), media_type="application/x-zip-compressed", headers={
            'Content-Disposition': f'attachment;filename={zip_filename}'
        })
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No model found on server. Please train your model first."
        )


@router.get("/{project_id}/file")
async def get_files(project: Project = Depends(check_for_project_ownership)):
    await project.fetch_all_links()
    stream = io.StringIO()
    csvFile = csv.writer(stream, delimiter=';')
    csvFile.writerow(["name", "text", "tag"])
    for text in project.texts:
        csvFile.writerow(
            [text.name, text.value, ", ".join(tag for tag in text.tags)])
    return Response(stream.getvalue(), media_type="text/csv")


@router.post("/{project_id}/file")
async def upload_file(files: List[UploadFile], project: Project = Depends(check_for_project_ownership)):
    documents: List[TextDocument] = list()
    for file in files:
        result = await handleFile(file)
        documents.extend(result)
    for document in documents:
        if(not all(tag in project.data.tags for tag in document.tags)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Tags: {document.tags} are not compatible with project'
            )
    for document in documents:
        await document.insert()
        project.texts.append(document)
    await project.save(link_rule=WriteRules.WRITE)
    await wsManager.send_by_projectId(Action.FileAdded, str(project.id))
    return documents


@router.delete("/{project_id}/file",
               responses={
                   status.HTTP_400_BAD_REQUEST: {
                       "description": "File not found"}
               })
async def delete_file(file_id: FileDeleteRequest, project: Project = Depends(check_for_project_ownership)):
    notFoundException = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="File not found"
    )

    await project.fetch_all_links()
    try:
        fileId = ObjectId(file_id.file_id)
    except:
        raise notFoundException
    fileToDelete = await TextDocument.find_one(TextDocument.id == fileId)
    if(fileToDelete and any(file.id == fileId for file in project.texts)):
        await fileToDelete.delete()
        await wsManager.send_by_projectId(Action.FileDeleted, str(project.id))
    else:
        raise notFoundException


# @router.post("/{project_id}/tag", responses={
#     status.HTTP_409_CONFLICT: {"description": "Duplicate tag"}
# })
# async def add_tag(tag: Tag,  project: Project = Depends(check_for_project_ownership)):
#     tag = tag.tag.casefold()
#     if(any(x == tag for x in project.data.tags)):
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail="Duplicate tag")
#     else:
#         project.data.tags.append(tag)
#         await project.save()
#         return f"Tag created: {tag}"


# @router.delete("/{project_id}/tag", responses={
#     status.HTTP_404_NOT_FOUND: {"description": "Tag not present in list"}
# })
# async def delete_tag(tag: Tag,  project: Project = Depends(check_for_project_ownership)):
#     tag = tag.tag.casefold()
#     if(any(x == tag for x in project.data.tags)):
#         project.data.tags.remove(tag)
#         await project.save()
#         return f"Tag deleted: {tag}"
#     else:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Tag not present")
