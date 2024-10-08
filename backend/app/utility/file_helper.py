import re
import zipfile
import csv
from io import BytesIO, StringIO
from os import path
from typing import List

from app.models.project_models import TextDocument
from fastapi import HTTPException, UploadFile, status
from pdfminer.high_level import extract_text


def createDocument(content: str, name: str, tag: List[str] = []) -> TextDocument:
    if(tag == None):
        tag = []
    text = TextDocument(name=name, value=content, tags=tag)
    return text


def handlePdf(file: bytes, name: str) -> TextDocument:
    content = extract_text(BytesIO(file))
    content = re.sub('\s\s+', ' ', content)
    return createDocument(content, name)


async def handleZip(file: bytes) -> List[TextDocument]:
    result = list()
    fileIo = BytesIO(file)
    with zipfile.ZipFile(fileIo) as archive:
        for filename in archive.namelist():
            name, file_ext = path.splitext(filename)
            content = archive.read(filename)
            result.extend(await checkExtensios(content, name, file_ext))
    return result


def handleCsv(file: bytes, fileName: str) -> List[TextDocument]:
    file = StringIO(file.decode())
    reader = csv.reader(file, delimiter=';')
    header = next(reader)
    header = [text.casefold().strip() for text in header]
    textIndex = findIndex(header, "text")
    nameIndex = findIndex(header, "name", False)
    tagIndex = findIndex(header, "tag", False)
    texts = []
    idx = 1
    for row in reader:
        tag = []
        name = f'{fileName}_{idx}'
        text = row[textIndex]
        if(tagIndex != -1):
            try:
                tag = row[tagIndex].casefold().split(',')
            except:
                pass
        if(nameIndex != -1):
            try:
                if(row[nameIndex]):
                    name = row[nameIndex]
            except:
                pass
        idx = idx + 1
        texts.append(createDocument(
            text, name, [value.casefold().strip() for value in tag]))
    return texts


def findIndex(list: List[str], header: str, throw: bool = True) -> int:
    found = True
    index = -1
    try:
        index = list.index(header)
    except ValueError:
        found = False
    finally:
        if(not found and throw):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Header: "{header}" not found in csv file'
            )
    return index


async def checkExtensios(file: bytes, name: str, extension: str) -> List[TextDocument]:
    result = list()
    if(extension == ".txt"):
        result.append(createDocument(file, name))
    elif(extension == ".pdf"):
        result.append(handlePdf(file, name))
    elif(extension == ".zip"):
        result.extend(await handleZip(file))
    elif(extension == ".csv"):
        result.extend(handleCsv(file, name))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{extension} files are not allowed"
        )
    return result


async def handleFile(file: UploadFile) -> List[TextDocument]:
    name, file_ext = path.splitext(file.filename)
    content = await file.read()
    return await checkExtensios(content, name, file_ext)
