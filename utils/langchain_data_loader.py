import os
import camelot
from tabulate import tabulate
from llama_index.readers.schema.base import Document
from utils.docAI_extraction import process_document_form_sample
from utils.para_detector import raw_text_extract, check_toc_data, dataframe_generation
from utils.table_extraction import get_latex_tables_camelot


def data_loader_custom(files_list: str):
    """Get PDF text into a list

    Arguments:
        pdf_path {str} -- Path of the PDF file

    Keyword Arguments:
        None

    Returns:
        {list} -- List of paragraphs in the PDF file
    """
    
    documents = []
    for file_path in files_list:
        if file_path.endswith(".pdf"):

            # text extraction
            pdf_path = file_path
            raw_text, _ = raw_text_extract(pdf_path)
            is_toc, toc_start, toc_end = check_toc_data(raw_text)
            df = dataframe_generation(raw_text, is_toc, pdf_path[:-4], toc_start, toc_end)

            # table extraction
            tables_lst = get_latex_tables_camelot(pdf_path)
    
            paragraphs = []
            
            for i in range(len(df["paragraph_content"])):
                for tuple in df.iloc[i]["paragraph_content"]:
                    paragraphs.append(tuple[0])
            
            # adding tables to the list of paragraphs
            paragraphs.extend(tables_lst)

            document = "\n".join(paragraphs)
        
            # documents.append("Here's the data from document 1: {}".format(file_path.split("/")[-1]))
            documents.append(document)
    
    
    
    return [Document(d) for d in documents]


def data_loader_docai(files_list: str, project_id = 'llmapps', location = 'us', processor_id = 'c0ec8848a9756a33', mime_type = 'application/pdf'):

    documents = []

    for idx, file_path in enumerate(files_list):

        if file_path.endswith(".pdf"):
            extracted_text = process_document_form_sample(project_id, location, processor_id, file_path, mime_type)
            documents.append("Here's the data from document {}: {}".format(idx, file_path.split("/")[-1]))
            documents.append(extracted_text)
    
    return [Document(d) for d in documents]