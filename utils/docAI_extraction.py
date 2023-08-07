from __future__ import annotations

from collections.abc import Sequence

from google.api_core.client_options import ClientOptions
from google.cloud import documentai  # type: ignore

project_id = 'llmapps'
location = 'us' # Format is 'us' or 'eu'
processor_id = 'c0ec8848a9756a33' # Create processor before running sample
# cred_file_path = 
mime_type = 'application/pdf'

def process_document(
    project_id: str, location: str, processor_id: str, file_path: str, mime_type: str
) -> documentai.Document:
    # You must set the api_endpoint if you use a location other than 'us'.
    opts = ClientOptions(
        api_endpoint=f"{location}-documentai.googleapis.com",
        credentials_file="/mnt/creds/llmapps-creds.json",
    )

    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    # The full resource name of the processor, e.g.:
    # projects/project_id/locations/location/processor/processor_id
    name = client.processor_path(project_id, location, processor_id)

    # Read the file into memory
    with open(file_path, "rb") as image:
        image_content = image.read()

    # Load Binary Data into Document AI RawDocument Object
    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)

    # Configure the process request
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)

    result = client.process_document(request=request)

    return result.document

def print_table_rows(
    table_rows: Sequence[documentai.Document.Page.Table.TableRow], text: str
) -> str:
    output = ""
    for table_row in table_rows:
        row_text = ""
        for cell in table_row.cells:
            cell_text = layout_to_text(cell.layout, text)
            row_text += f"{repr(cell_text.strip())} | "
        output += row_text + "\n"
    return output

def layout_to_text(layout: documentai.Document.Page.Layout, text: str) -> str:
    """
    Document AI identifies text in different parts of the document by their
    offsets in the entirety of the document's text. This function converts
    offsets to a string.
    """
    response = ""
    # If a text segment spans several lines, it will
    # be stored in different text segments.
    for segment in layout.text_anchor.text_segments:
        start_index = int(segment.start_index)
        end_index = int(segment.end_index)
        response += text[start_index:end_index]
    return response

def process_document_form_sample(
    project_id: str, location: str, processor_id: str, file_path: str, mime_type: str
) -> str:
    output = ""

    # Online processing request to Document AI
    document = process_document(
        project_id, location, processor_id, file_path, mime_type
    )

    # Read the table and form fields output from the processor
    # The form processor also contains OCR data. For more information
    # on how to parse OCR data please see the OCR sample.

    # For a full list of Document object attributes, please reference this page:
    # https://cloud.google.com/python/docs/reference/documentai/latest/google.cloud.documentai_v1.types.Document

    text = document.text
    output += f"Full document text: {repr(text)}\n"
    output += f"There are {len(document.pages)} page(s) in this document.\n"

    for page in document.pages:
        page_number = page.page_number
        page_text = layout_to_text(page.layout, text)

        output += f"\n\n**** Page {page_number} ****\n"
        output += f"Page text: {repr(page_text)}\n"

        # Read the form fields and tables output from the processor
        output += f"\nFound {len(page.tables)} table(s):\n"
        for table in page.tables:
            num_columns = len(table.header_rows[0].cells)
            num_rows = len(table.body_rows)
            output += f"Table with {num_columns} columns and {num_rows} rows:\n"

            # Print header rows
            output += "Columns:\n"
            output += print_table_rows(table.header_rows, text)
            # Print body rows
            output += "Table body data:\n"
            output += print_table_rows(table.body_rows, text)

        output += f"\nFound {len(page.form_fields)} form field(s):\n"
        for field in page.form_fields:
            name = layout_to_text(field.field_name, text)
            value = layout_to_text(field.field_value, text)
            output += f"    * {repr(name.strip())}: {repr(value.strip())}\n"

    return output