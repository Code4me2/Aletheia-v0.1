import logging
import base64
import os
#from typing import List

# for some reason the docker container errors unless you do these two imports in this way 
# (not in the format of "from ... import ...")
import fastapi
import pydantic

from unstructured.partition.auto import partition


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = fastapi.FastAPI(
    title="Unstructured.io Legal Document Service",
    description="API for legal document parsing and OCR with Unstructured.io",
    version="0.1.0"
)

""" Data structures of the request and the response"""
class ParseRequest(pydantic.BaseModel):
    file_name: str
    input_base64: str


class ParseResponse(pydantic.BaseModel):
    text: str
    structured_text: list[str]



@app.post("/parse_documents", response_model=ParseResponse)
async def search_documents(request: ParseRequest):
    """Handling the POST /parse_documents request"""


    # Send back an error if the filename doesn't include a valid ending
    if('.' not in request.file_name):
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="Filename seems to not have a valid extension (ie. .pdf, .doc, .docx, .txt, etc)"
        )

    """ First we decode the file from base64 back to the original binary"""
    decoded_file = base64.b64decode(request.input_base64)

    try:
        with open(request.file_name, "wb") as f:
            f.write(decoded_file)

        print("successfully converted input to file")

    except IOError as e:
        print(f"Error writing file: {e}")


    """ Now we call the unstructured.io library to parse the document"""

    elements = partition(filename=request.file_name)


    text = "\n\n".join([str(el) for el in elements])

    structured_text:list[str] = []

    for element in elements:
    
        structured_text.append(str(element))


    """ Once we're done reading the file, we can safely remove it, as to not waste hard drive space"""
    if(os.path.exists(request.file_name)):
        os.remove(request.file_name)

    else:
        print("Failed to remove file")


    """ Return a response with the data from unstructured.io"""

    return ParseResponse(
        text = text,
        structured_text = structured_text
    )
