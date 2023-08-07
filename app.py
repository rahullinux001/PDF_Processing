#!/usr/bin/env python

""" LeasesApp_Multiple: To answer questions from multiple documents using OpenAI's GPT-3 API
"""

# Importing libraries
import os
import time
import openai
import camelot
import uvicorn

import gradio as gr
import pandas as pd

from fastapi import Depends, FastAPI
from collections import defaultdict
from tenacity import (retry, stop_after_attempt, wait_random_exponential)

# Imports from the utils folder
from utils.token_counter import count_tokens
from utils.table_extraction import get_pdf_table_latex
from utils.para_detector import raw_text_extract, check_toc_data, dataframe_generation

# Imports from the login folder
from login.db import User, create_db_and_tables
from login.schemas import UserCreate, UserRead, UserUpdate
from login.users import auth_backend, current_active_user, fastapi_users

# Authorship information
__author__ = "Akash Kamble"
__copyright__ = "Copyright 2023, Argonaut AI"
__credits__ = ["Akash Kamble", "Darren Mateshow", "Komal Diwe"]
__version__ = "1.0.1"
__maintainer__ = "Akash Kamble"
__email__ = "kambleakash0@gmail.com"
__status__ = "Development"

# OpenAI API Key
openai.api_key = "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"

# Starting system message
messages = [{"role": "system", "content": "You are a very obedient, kind and a helpful AI assistant. Be brief in your answers."}]

# Negative terms
negative_terms = [
    "sorry",
    "not found",
    "not stated",
    "not defined",
    "not provided",
    "not indicated",
    "not specified",
    "not mentioned",
    "couldn't find",
    "no mention of",
    "could not find",
    "no reference to",
    "no indication of",
    "could not be found",
    "no clear indication",
    "not clearly specified",
    "not clearly mentioned",
    "not explicitly stated",
    "not specifically stated",
    "no information provided",
    "not explicitly mentioned",
    "there is no information about",
]



# OpenAI ChatCompletion API call with backoff
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(3))
def chat_completion_with_backoff(**kwargs):
    """OpenAI ChatCompletion API call with backoff
    
    Arguments:
        None
    
    Keyword Arguments:
        **kwargs {dict} -- Keyword arguments

    Returns: 
        {dict} -- OpenAI ChatCompletion API response
    """
    return openai.ChatCompletion.create(**kwargs)

# OpenAI Completion API call with backoff
@retry(wait=wait_random_exponential(min=1, max=10), stop=stop_after_attempt(3))
def completion_with_backoff(**kwargs):
    """OpenAI Completion API call with backoff
    
    Arguments:
        None

    Keyword Arguments:
        **kwargs {dict} -- Keyword arguments

    Returns:
        {dict} -- OpenAI Completion API response
    """
    return openai.Completion.create(**kwargs)


# dummy auth function
def same_auth(username: str, password: str):
    """Dummy auth function
    This function is used to authenticate the user.

    Arguments:
        username {str} -- Username of the user
        password {str} -- Password of the user

    Keyword Arguments:
        None

    Returns:
        {bool} -- True if username and password are correct else False
    """
    return username == 'admin' and password == 'adminllm'


# Get PDF text into a list
def get_pdf_text(pdf_path: str):
    """Get PDF text into a list

    Arguments:
        pdf_path {str} -- Path of the PDF file

    Keyword Arguments:
        None

    Returns:
        {list} -- List of paragraphs in the PDF file
    """
    raw_text, _ = raw_text_extract(pdf_path)
    is_toc, toc_start, toc_end = check_toc_data(raw_text)
    df = dataframe_generation(raw_text, is_toc, pdf_path[:-4], toc_start, toc_end)
    # print(df)
    
    paragraphs = []
    for i in range(len(df["paragraph_content"])):
        for tuple in df.iloc[i]["paragraph_content"]:
            paragraphs.append(tuple)
            # print(tuple)
    return paragraphs

# get PDF tables' rows into a list
def get_pdf_table(pdf_path: str):
    # extract tables using Camelot
    tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
    # print(list(row) for row in tables[0].df.iterrows())
    # create a list where each row of each table corresponds to one line
    rows = []
    for table in tables:
        page = table.parsing_report['page']
        table_df = table.df
        for _, row in table_df.iterrows():
            if not all(val == '' for val in row):
                rows.append(tuple([' '.join(list(row)), page]))
        rows.append(tuple(['', page]))
    
    return rows

# Process
def process(files: gr.File, question: str):
    """Process the files and question to get the answer
    
    Arguments:
        files {list} -- List of files uploaded by the user
        question {str} -- Question asked by the user
        
    Keyword Arguments:
        None
        
    Returns:
        {df} -- Answer to the question
    """

    if not files:
        print("Please upload at lease one PDF file.")
        raise gr.Error("Please upload at lease one PDF file.")

    for file_obj in files:

        # validate file type
        if file_obj.name[-4:] != ".pdf":
            print("All files should be PDFs. {} is not a PDF file.".format(file_obj.name.split("/")[-1]))
            raise gr.Error("All files should be PDFs. {} is not a PDF file.".format(file_obj.name.split("/")[-1]))
    
    # initialize global variables for the run
    global messages
    global negative_terms

    # initialize local variables for the run
    token_limit = 3700
    tokens_so_far = 0
    answers = []
    question_lst = [question, question]

    messages.append({
        "role": "user", 
        "content": "Identify and write 5-10 words for the core subject of this question: '{}' \
                    What's being asked to find?".format(question_lst[0])
    })
    
    chat = chat_completion_with_backoff(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=40,
        timeout=10,
        top_p=0.1,
    )
    print("Prompt: ", messages[-1]["content"])
    reply = chat.choices[0].message.content
    messages.pop()
    print("Reply: ", reply)
    question_lst[1] = reply
    print(question_lst,"\n")

    paragraphs = list(range(len(files)))

    

    # get paragraphs from pdfs
    for i in range(len(files)):
        paragraphs[i] = get_pdf_text(files[i].name)
        paragraphs[i].extend(get_pdf_table(files[i].name))
    
    debug_text = ""
    for i in range(len(paragraphs)):
        for j in range(len(paragraphs[i])):
            debug_text = debug_text +  paragraphs[i][j][0] + '\n'
        debug_text = debug_text + '\n'

    # print(paragraphs[0][0][0])
    # return

    # Loop through documents
    for doc_idx in range(len(files)):
        para_idx = 0
        # Loop through paragraphs
        while para_idx < len(paragraphs[doc_idx]):
            # Reset the context
            messages.clear()
            messages.append({
                "role": "system", 
                "content": "You are a very obedient, kind and a helpful AI assistant. \
                            Read the given text and answer the questions."
            })
            tokens_so_far = count_tokens(messages)
            para_text = paragraphs[doc_idx][para_idx][0]
            page_no = paragraphs[doc_idx][para_idx][1]
            doc_no = doc_idx + 1
            doc_name = files[doc_idx].name.split("/")[-1]
            # print(doc_name, page_no, para_text)
            feed_dict = {
                "role": "user",
                "content": "[Document {} - {}] Text: {} Page: {}".format(doc_no, doc_name, para_text, page_no)
            }
            
            # Add paragraphs till the token limit is reached
            while para_idx < len(paragraphs[doc_idx]) and (tokens_so_far + count_tokens([feed_dict])) < token_limit:
                para_text = paragraphs[doc_idx][para_idx][0]
                page_no = paragraphs[doc_idx][para_idx][1]
                doc_no = doc_idx + 1
                doc_name = files[doc_idx].name.split("/")[-1]
                feed_dict = {
                    "role": "user",
                    "content": "[Document {} - {}] Text: {} Page: {}".format(doc_no, doc_name, para_text, page_no)
                }
                messages.append(feed_dict)
                
                tokens_so_far = count_tokens(messages)
                para_idx += 1
            
            print("\n", "Document: {} | Text loaded till page {}".format(doc_name, page_no), "\n")

            # Ask the question
            prompt_dict = {
                "role": "user",
                "content": "Can you tell me anything related to the following from the above text: '{}'. \
                            For now get it only from the current document (Document {}). \
                            If nothing is found, just write 'NF'.".format(question_lst[1], doc_no)
            }

            # Add the question to the messages
            messages.append(prompt_dict)

            # Get the reply from the model
            chat = chat_completion_with_backoff(
                model="gpt-3.5-turbo", 
                messages=messages, 
                timeout=10, 
                temperature=0
            )
            reply = chat.choices[0].message.content
            
            # Check if the answer is found
            # found = True
            for term in negative_terms:
                if 'NF' in reply or term in reply.lower():
                    found = False
                    # print("Not found")
                    break
            
            # if not found:
            #     pass
            # else:
            # Ask for reference
            prompt_dict = {
                "role": "user",
                "content": "Where did you find it? \
                            Do you have the relevant document no / page no / section / article, etc. \
                            If not found, just write 'NF'.".format(question_lst[1])
            }
            
            # Add the question to the messages
            messages.append(prompt_dict)

            # Get the reply from the model
            chat = chat_completion_with_backoff(
                model="gpt-3.5-turbo", 
                messages=messages, 
                timeout=10, 
                temperature=0
            )
            reference = chat.choices[0].message.content
            messages.pop()
            messages.pop()
            answers.append(tuple([question_lst[1], reply, reference]))
            # end if

            # Print the question, context, and reply (optional)
            print("Question --->", question_lst[1])
            print("Ans --->", reply)
            print("Reference --->", reference)
            print("Tokens --->", count_tokens(messages))
            print()

            # Wait for 0.1 seconds
            time.sleep(0.1)
    
    inference_dict = defaultdict(list)
    for entry in answers:
        inference_dict[entry[0]].append([entry[1], entry[2]])

    # print("\n\n", inference_dict, "\n\n")
    # Reset the context
    answers.clear()
    messages.clear()
    messages.append({
        "role": "system", 
        "content": "You are a very obedient, kind and a helpful AI assistant. Read the given text and answer the questions."
    })
    
    # Loop through the stage-1 answers and ask the original question on it 
    for key, value_list in inference_dict.items():
        question = question_lst[0]
        messages.append({
            "role": "user", 
            "content": "Key: {}".format(key)
        })
        for value in value_list:
            entry = " Value: Discovery: {} Reference: {}".format(value[0], value[1])
            messages.append({
                "role": "user", 
                "content": entry
            })
        
    # ask the question
    messages.append({
        "role": "user", 
        "content": "Question: {}\
                    Remember 'first contract' or 'first version' in Key refers to document 1, second to document 2, and so on.".format(question)
    })
    chat = chat_completion_with_backoff(
        model="gpt-3.5-turbo", 
        messages=messages, 
        timeout=10, 
        temperature=0
    )
    # get the answer
    answer = chat.choices[0].message.content
    messages.append({
        "role": "assistant", 
        "content": answer
    })

    # ask the follow-up question
    messages.append({
        "role": "user", 
        "content": "Can you tell me where you found it in the references?"
    })
    chat = chat_completion_with_backoff(
        model="gpt-3.5-turbo", 
        messages=messages, 
        timeout=10, 
        temperature=0
    )
    # get the answer
    reference = chat.choices[0].message.content
    messages.pop()
    messages.pop()
    messages.pop()

    # append the answer
    answers.append(tuple([question, answer, reference]))

    # Print the question, context, and reply (optional)
    print("Question --->", question)
    print("Ans --->", answer)
    print("Reference --->", reference)
    print("Tokens --->", count_tokens(messages))
    print()

    df = pd.DataFrame(answers, columns=["Label", "Discovery", "Reference"], index=None)
    # print(inference_dict)
    print("Done\n\n")
    
    return df, debug_text


# Upload the file
def upload_file(file: gr.File):
    """Uploads a file object and returns the full (temp) path of the file"""
    return file.name


# Gradio stuff starts here
with gr.Blocks(
    css=""" 
        footer { display: none !important; } 
        .gradio-container { min-height: 0px !important; }
        """
    ) as demo:
    
    # title of the app (goes in <head> tag of the page source)
    demo.title = "Leases"

    # App's <body> starts here
    gr.Markdown("Leases QnA")

    # Row of input for file upload
    with gr.Row(variant="default"):
        # gradio file object with support for multiple files
        file = gr.File(interactive=False, file_count="multiple", file_types=["file"])
        # gradio upload button
        upload_button = gr.UploadButton("Click to Upload Documents", file_count="multiple", file_types=["file"])

    # event handler for the upload button
    upload_button.upload(lambda files:[file.name for file in files] , upload_button, file)

    # Output for the processed text (gradio dataframe object)
    output = gr.DataFrame(type="pandas", label="Output", wrap=True)
    
    # Row of input for text box and the primary process button
    with gr.Row(variant="panel").style(equal_height=True):
        
        with gr.Column():
            # gradio text box
            prompt_box = gr.Textbox(
                label="Question",
                lines=2,
                placeholder="Enter a question",
            )
        
        with gr.Column(scale=0.3):
            # gradio buttons for clearing the text box and processing the documents
            clear_btn = gr.Button("Clear", variant="secondary")
            process_btn = gr.Button("Process", variant="primary")

    # debug output for checks
    debug_output = gr.Textbox(label="Debug", lines=10, placeholder="Debug output")
    
    # event handlers for the clear and process buttons
    clear_btn.click(lambda: "", inputs=[], outputs=[prompt_box])
    process_btn.click(
        fn=process,
        inputs=[file, prompt_box],
        outputs=[output, debug_output],
        api_name="process",
        show_progress=True,
    )


## FastAPI app
app = FastAPI()

app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}


@app.on_event("startup")
async def on_startup():
    # Not needed if you setup a migration system like Alembic
    await create_db_and_tables()

@app.get("/")
def read_main():
    return "Hi"

# Run the app
if __name__ == "__main__":

    # Normal Gradio demo
    gr.close_all()
    demo.launch(
        auth=same_auth,
        server_port=int(os.environ.get("PORT", 7860)),
    )

    # Gradio demo with login page
    # app = gr.mount_gradio_app(app, demo, path="/app")
    # uvicorn.run(app,
    #             host='localhost',
    #             # reload=True,
    # )
