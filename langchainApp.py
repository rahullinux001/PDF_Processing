
from utils.langchain_data_loader import data_loader_docai, data_loader_custom
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.chains import SimpleSequentialChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate

# General
import gradio as gr
import openai
import pandas as pd
import numpy as np
import sys
import os

# Authorship information
__author__ = "Sri Lingamneni"
__copyright__ = "Copyright 2023, Argonaut AI"
__credits__ = ["Sri Lingamneni", "Jaival Desai", "Akash Kamble", "Komal Diwe"]
__version__ = "1.0.1"
__maintainer__ = "Sri Lingamneni"
__email__ = "srilakshmi.iitm@gmail.com"
__status__ = "Development"

# OpenAI API Key
openai.api_key = "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"


def extract_text(pdf_files: str):

    extraction = os.environ.get("TXT", "custom")

    if extraction == "docai":
        documents = data_loader_docai(pdf_files)
    elif extraction == "custom":
        print("it was ran")
        documents = data_loader_custom(pdf_files)
    else:
        print("'TXT' environment variable must be one of ['docai', 'custom']. Default: docai")
        raise gr.Error("'TXT' environment variable must be one of ['docai', 'custom']. Default: docai")
    
    # print('Here is the output from data loader: ')
    # print(documents[0].text)

    with open('doc_output.txt', 'w',encoding='utf-8') as f:
        f.write(documents[0].text)

    return documents[0].text


def upload_files(files: gr.File):
    if not files:
        print("Please upload at lease one PDF file.")
        raise gr.Error("Please upload at lease one PDF file.")

    files_list = []
    for file_obj in files:

        # validate file type
        if file_obj.name[-4:] != ".pdf":
            print("All files should be PDFs or CSVs. {} is not a PDF file or a CSV file.".format(file_obj.name.split("/")[-1]))
            raise gr.Error("All files should be PDFs or CSVs. {} is not a PDF file or a CSV file.".format(file_obj.name.split("/")[-1]))
        
        files_list.append(file_obj.name)

    csv_files = []
    pdf_files = []
    for file_path in files_list:
        if file_path.endswith(".pdf"):
            pdf_files.append(file_path)
       
    if len(pdf_files) == 0:
        print('Contract file in pdf format has not been uploaded, please upload the contract to proceed')
        raise gr.Error('Contract file in pdf format has not been uploaded, please upload the contract to proceed')
    
    return files_list

def clear_docs():
    """
    Clears the docs folder of any existing files
    """

    print('Current items in docs: ', os.listdir("docs"))

    for file in os.listdir("docs"):
        os.remove(os.path.join("docs", file))


def process(files: gr.File):

    files_list = []
    for file_obj in files:
        files_list.append(file_obj.name)

    csv_files = []
    pdf_files = []
    for file_path in files_list:
        if file_path.endswith(".pdf"):
            pdf_files.append(file_path)

        elif file_path.endswith(".csv"):
            csv_files.append(file_path)

    print('PDF files: ', pdf_files)
    print('CSV files: ', csv_files)

    text = extract_text(pdf_files)

    print("Here is the 'text' input for the LLM:")
    print(text)


    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", max_tokens=2048)
    prompt = PromptTemplate(
        input_variables=["file"],
        template="Show me the string of text before you encounter the first table in this {file}. The output should only be the text and nothing else. This is how a table would start:'\begin' ")

    chain = LLMChain(llm=llm, prompt=prompt)

    # Run the chain only specifying the input variable.
    #print(chain.run( ))

    second_prompt = PromptTemplate(
    input_variables=["text"],
    template="""Now, using this {text}, extract all the unique Tax Identification Numbers. 
    The format of the output should be as follows one after the other:
    Tax Identification Number: 'The actual number should go here'
    """
    )
    chain_two = LLMChain(llm=llm, prompt=second_prompt)


    overall_chain = SimpleSequentialChain(chains=[chain,chain_two], verbose=True)

    # Run the chain specifying only the input variable for the first chain.
    text_catchphrase = overall_chain.run(text)
    print("This is the text_catchphrase:")
    print(text_catchphrase)

    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", max_tokens=2048)
    prompt = PromptTemplate(
        input_variables=["file"],
        template="Show me the string of text before you encounter the first table in this {file}. The output should only be the text and nothing else. This is how a table would start:'\begin' ")

    chain = LLMChain(llm=llm, prompt=prompt)

        # Run the chain only specifying the input variable.
    #print(chain.run( ))

    second_prompt = PromptTemplate(
    input_variables=["text"],
    template="""Now, using this {text}, extract the EFFECTIVE DATE. 
    The format of the date should be as follows : mm/dd/yyyy

    """
    )
    chain_two = LLMChain(llm=llm, prompt=second_prompt)

    overall_chain = SimpleSequentialChain(chains=[chain,chain_two], verbose=True)

    #     # Run the chain specifying only the input variable for the first chain.
    date_catchphrase = overall_chain.run(text)
    print("Here is the date_catchphrase: ", date_catchphrase)

    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", max_tokens=2048)
    prompt = PromptTemplate(
        input_variables=["file"],
        template="Show me table in this {file}. The output should only be the text and nothing else. This is how a table would start:'\begin' ")

    chain = LLMChain(llm=llm, prompt=prompt)

    overall_chain = SimpleSequentialChain(chains=[chain], verbose=True)

    #     # Run the chain specifying only the input variable for the first chain.
    table_catchphrase = overall_chain.run(text)
    #print("Table Catch Phrase: ", table_catchphrase)

    start_index = table_catchphrase.find('|   |')
    table_catchphrase = table_catchphrase[start_index:]
    print("Table Catch Phrase: ", table_catchphrase)

    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", max_tokens=2048)

    second_prompt = PromptTemplate(
    input_variables=["table"],
    template="""Now, using this {table} create a new table with the following column titles:: 
    "DRG", "Base Rate", "OutlierPctBC", “OutlierThreshold%","Line of Business", "Payment Method".

    1. "DRG" column should have 001-999, explode the
    001-999, showing only one number per each row
    2. "Base Rate" column with the payment value listed
    under “"HMO/POS" column for "MSDRG's 001-999" row. All rows in this first set should have the same value.
    3. update the "“OutlierPctBC" column with the "MSDRG
    Outlier Rate % Second $" for "HMO/POS"
    4. update "OutlierThreshold%" with the values from
    “Outlier Threshold $" row listed under "HMO/POS"
    column. Note, for this column, show me only the "%"
    and drop “of DRG"
    5. The "Line of Business" Column for this set should have "HMO/POS" as the value.

    6. "DRG" column should have another set of 001-999, explode the
    001-999, showing only one number per each row
    7. "Base Rate" column with the payment value listed
    under "PPO" column for "MSDRG's 001-999" row. All rows in this second set should have the same value.
    9. update the "“OutlierPctBC" column with the "MSDRG
    Outlier Rate % Second $" for "PPO"
    9. update "OutlierThreshold%" with the values from
    “Outlier Threshold $" row listed under "PPO"
    column. Note, for this column, show me only the "%"
    and drop “of DRG"
    10. The "Line of Business" Column for this set should have "PPO" as the value.

    11. "DRG" column should have another set of 001-999, explode the
    001-999, showing only one number per each row
    12. "Base Rate" column with the payment value listed
    under "traditional" column for "MSDRG's 001-999" row. All rows in this third set should have the same value.
    13. update the "“OutlierPctBC" column with the "MSDRG
    Outlier Rate % Second $" for "traditional"
    14. update "OutlierThreshold%" with the values from
    “Outlier Threshold $" row listed under "traditional"
    column. Note, for this column, show me only the "%"
    and drop “of DRG"
    15. The "Line of Business" Column for this set should have "Traditional" as the value.


    16. The 'Payment Method' column should have 'DRG' as the value across all three sets above
    17. Import pandas on the top

    Also give me the pandas code to generate this as a dataframe. Save this dataframe as 'drg_df' 

    """
    )
    chain_two = LLMChain(llm=llm, prompt=second_prompt)

    third_prompt = PromptTemplate(
    input_variables=["table"],
    template="Just show me the pandas code to generate the {table} above as a dataframe using list comprehension.",
    )
    chain_three = LLMChain(llm=llm, prompt=third_prompt)

    overall_chain = SimpleSequentialChain(chains=[chain_two, chain_three], verbose=True)

    #     # Run the chain specifying only the input variable for the first chain.
    DRG_catchphrase = overall_chain.run(table_catchphrase)
    print("DRG_catchphrase: ", DRG_catchphrase)


    second_prompt = PromptTemplate(
    input_variables=["table"],
    template="""Now, using this {table} create a new table with the following column titles: 
    "DRG", "Case Rate", "Payment Method", "Case Rate Days", "PDRate1", "Line of Business". 
    Fill this table columns with the following values: 
    1. "DRG" column should have "MS DRG" values for the numerical DRG ranges in  "Maternity C-section days" 
        and "Maternity Normal Delivery days" and explode the DRG range to show only one DRG number per each row.
        Make sure you only include the number. There is no need to include "MS DRG" before the number. 
        Make sure all numbers in the range are displayed. 
    2. update "Case Rate" column with the values from "Maternity C-section days" and 
        "Maternity Normal Delivery days" rows listed under "HMO/POS" column.
    3.  update the "Payment Method" column with the payment method listed for 
        "Maternity C-section days" and "Maternity Normal Delivery days" under "HMO/POS" column. 
    4.  update "Case Rate Days" column with the maximum number of days values listed in "Maternity C-section days" 
        and "Maternity Normal Delivery days" rows .
    5.  Populate "PDRate1" with "Maternity Outlier Day" rates listed for "HMO/POS" 
    6. "Line of Business" should have "HMO/POS" as the value.

    7. "DRG" column should have "MS DRG" values for the numerical DRG ranges in  "Maternity C-section days" 
        and "Maternity Normal Delivery days" and explode the DRG range to show only one DRG number per each row.
        Make sure you only include the number. There is no need to include "MS DRG" before the number. 
        Make sure all numbers in the range are displayed. 
    8. update "Case Rate" column with the values from "Maternity C-section days" and 
        "Maternity Normal Delivery days" rows listed under "PPO" column.
    9.  update the "Payment Method" column with the payment method listed for 
        "Maternity C-section days" and "Maternity Normal Delivery days" under "PPO" column. 
    10.  update "Case Rate Days" column with the maximum number of days values listed in "Maternity C-section days" 
        and "Maternity Normal Delivery days" rows .
    11.  Populate "PDRate1" with "Maternity Outlier Day" rates listed for "PPO" 
    12. "Line of Business" should have "PPO" as the value.

    13. "DRG" column should have "MS DRG" values for the numerical DRG ranges in  "Maternity C-section days" 
        and "Maternity Normal Delivery days" and explode the DRG range to show only one DRG number per each row.
        Make sure you only include the number. There is no need to include "MS DRG" before the number. 
        Make sure all numbers in the range are displayed. 
    14. update "Case Rate" column with the values from "Maternity C-section days" and 
        "Maternity Normal Delivery days" rows listed under the "Traditional" column.
    15.  update the "Payment Method" column with the payment method listed for 
        "Maternity C-section days" and "Maternity Normal Delivery days" under "Traditional" column. 
    16.  update "Case Rate Days" column with the maximum number of days values listed in "Maternity C-section days" 
        and "Maternity Normal Delivery days" rows .
    17.  Populate "PDRate1" with "Maternity Outlier Day" rates listed for "Traditional" 
    18. "Line of Business" should have "Traditional" as the value.

    """
    )
    chain_two = LLMChain(llm=llm, prompt=second_prompt)

    third_prompt = PromptTemplate(
    input_variables=["table"],
    template="Show me the pandas code to generate the {table} above as a dataframe and save the dataframe as 'maternity_df'. Use list comprehension to make the pandas code easier to read",
    )
    chain_three = LLMChain(llm=llm, prompt=third_prompt)

    overall_chain = SimpleSequentialChain(chains=[chain_two, chain_three], verbose=True)

    #     # Run the chain specifying only the input variable for the first chain.
    Maternity_catchphrase = overall_chain.run(table_catchphrase)
    print("Maternity_catchphrase: ", Maternity_catchphrase)

    llm = lm=ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", max_tokens=2048)

    second_prompt = PromptTemplate(
    input_variables=["table"],
    template="""Now, using this {table} create a new table with the following column titles: MS-"DRG",
    "Payment Method", "PDRate1", "PDDays1", "Line of Business".
    When the generated dictionary is used to create a pandas dataframe, these keys should form the columns.
    The values for each key in the dictionary come from the following:
    1. "DRG" column should have "MS DRG" values listed in  "Normal Newborn", "Low Level Neonate"
        and "High Level Neonate".
        If there is more than one DRG number separated by commas in the row, they must be split into individual rows and each row should have the same values across all columns in the resulting table.
        Make sure you only include the number. There is no need to include "MS DRG" before the number.
        Make sure all numbers are displayed.
    2.  update the "Payment Method" column with the payment method listed for
        "Normal Newborn", "Low Level Neonate"and "High Level Neonate" under "Payment Method" column.
    3.  update "PDDays1" column with 999 as the value in each row .
    4.  Populate "PDRate1" with "Normal Newborn", "Low Level Neonate"
        and "High Level Neonate" rates listed for "HMO/POS"
    5. "Line of Business" should have "HMO/POS" as the value.
    6. "DRG" column should have "MS DRG" values listed in  "Normal Newborn", "Low Level Neonate"
        and "High Level Neonate".
        If there is more than one DRG number separated by commas in the row, they must be split into individual rows and each row should have the same values across all columns in the resulting table.
        Make sure you only include the number. There is no need to include "MS DRG" before the number.
        Make sure all numbers are displayed.
    7.  update the "Payment Method" column with the payment method listed for
        "Normal Newborn", "Low Level Neonate"and "High Level Neonate" under "Payment Method" column.
    8.  update "PDDays1" column with 999 as the value in each row .
    9.  Populate "PDRate1" with "Normal Newborn", "Low Level Neonate"
        and "High Level Neonate" rates listed for "PPO"
    10. "Line of Business" should have "PPO" as the value.
    11. "DRG" column should have "MS DRG" values listed in  "Normal Newborn", "Low Level Neonate"
        and "High Level Neonate".
        If there is more than one DRG number separated by commas in the row, they must be split into individual rows and each row should have the same values across all columns in the resulting table.
        Make sure you only include the number. There is no need to include "MS DRG" before the number.
        Make sure all numbers are displayed.
    12.  update the "Payment Method" column with the payment method listed for
        "Normal Newborn", "Low Level Neonate"and "High Level Neonate" under "Payment Method" column.
    13.  update "PDDays1" column with 999 as the value in each row .
    14.  Populate "PDRate1" with "Normal Newborn", "Low Level Neonate"
        and "High Level Neonate" rates listed for "Traditional"
    15. "Line of Business" should have "Traditional" as the value.

    """
    )
    chain_two = LLMChain(llm=llm, prompt=second_prompt)

    third_prompt = PromptTemplate(
    input_variables=["table"],
    template="Show me the pandas code to generate the {table} above as a dataframe and save the dataframe as 'neonatal_df'. ",
    )
    chain_three = LLMChain(llm=llm, prompt=third_prompt)

    overall_chain = SimpleSequentialChain(chains=[chain_two, chain_three], verbose=True)

    #     # Run the chain specifying only the input variable for the first chain.
    Neonatal_catchphrase = overall_chain.run(table_catchphrase)
    print("Neonatal_catchphrase: ", Neonatal_catchphrase)

    llm = lm=ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", max_tokens=2048)

    second_prompt = PromptTemplate(
    input_variables=["table"],
    template="""Now, using this {table}, create a new table with the following columns: 
    "RevCode", "Payment Method", "PDDays1", "PctBC", "StopLossCalcExclusion", "Line of Business"
    and fill this table columns with the following values: 
    1. RevCode: "RevCode" column should have "Rev Code" values listed for only the "Rehabilitation" row and explode any revenue codes that are listed as a range to show only one "Rev Code" number per each row. Only keep the number and drop prefix "Rev Code"
    2. Payment Method: update the  "Payment Method" column with the payment method listed for "Rehabilitation" row under "Payment Method" column
    3. PDDays1: For the rows with "Payment Method" = "Per Diem", update the "PDDays1" column with 999
    4. PctBC: update the "PctBC" column with the values listed under "HMO/POS" column. Note, perform this action only if the values are listed as a percentage of billed charge and show only the % value without any prefixes or suffixes. Add '%'after the value 
    5. StopLossCalcExclusion: update the "StopLossCalcExclusion" column with value of "Y" for the above rows
    6. Line of Business: Update the "Line of Business" with 'HMO/POS'

    7. RevCode: "RevCode" column should have "Rev Code" values listed for only the "Rehabilitation" row and explode any revenue codes that are listed as a range to show only one "Rev Code" number per each row. Only keep the number and drop prefix "Rev Code"
    8. Payment Method: update the  "Payment Method" column with the payment method listed for "Rehabilitation" row under "Payment Method" column
    9. PDDays1: For the rows with "Payment Method" = "Per Diem", update the "PDDays1" column with 999
    10. PctBC: update the "PctBC" column with the values listed under "HMO/POS" column. Note, perform this action only if the values are listed as a percentage of billed charge and show only the % value without any prefixes or suffixes. Add '%'after the value 
    11. StopLossCalcExclusion: update the "StopLossCalcExclusion" column with value of "Y" for the above rows
    12. Line of Business: Update the "Line of Business" with 'PPO'

    13. RevCode: "RevCode" column should have "Rev Code" values listed for only the "Rehabilitation" row and explode any revenue codes that are listed as a range to show only one "Rev Code" number per each row. Only keep the number and drop prefix "Rev Code"
    14. Payment Method: update the  "Payment Method" column with the payment method listed for "Rehabilitation" row under "Payment Method" column
    15. PDDays1: For the rows with "Payment Method" = "Per Diem", update the "PDDays1" column with 999
    16. PctBC: update the "PctBC" column with the values listed under "HMO/POS" column. Note, perform this action only if the values are listed as a percentage of billed charge and show only the % value without any prefixes or suffixes. Add '%'after the value 
    17. StopLossCalcExclusion: update the "StopLossCalcExclusion" column with value of "Y" for the above rows
    18. Line of Business: Update the "Line of Business" with 'Traditional'


    """
    )
    chain_two = LLMChain(llm=llm, prompt=second_prompt)

    third_prompt = PromptTemplate(
    input_variables=["table"],
    template="Show me the pandas code to generate the {table} above as a dataframe and save the dataframe as 'rehabrow_df'",
    )
    chain_three = LLMChain(llm=llm, prompt=third_prompt)

    overall_chain = SimpleSequentialChain(chains=[chain_two, chain_three], verbose=True)

    #     # Run the chain specifying only the input variable for the first chain.
    Rehab_catchphrase = overall_chain.run(table_catchphrase)
    print("Rehab_catchphrase: ", Rehab_catchphrase)


    llm = lm=ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", max_tokens=2048)

    second_prompt = PromptTemplate(
    input_variables=["table"],
    template="""Now,using this {table}, create a new table with the following columns: 
    "RevCode", "Payment Method", "PDDays1", "PctBC", "StopLossCalcExclusion","Line of Business" 
    and fill this table columns with the following values: 
    1. RevCode: "RevCode" column should have "Rev Code" values listed for "Implants" and "High Cost Drugs" rows and explode any revenue codes that are listed as a range to show only one "Rev Code" number per each row. Only keep the number and drop prefix "Rev Code"
    2. Payment Method: update the  "Payment Method" column in this table with the payment method listed for "Implants" and "High Cost Drugs" rows under "Payment Method" column in the original table
    3. PDDays1: Skip this column if the "Payment Method" value = ""
    4. PctBC:  If the value for "Implants" and "High Cost Drugs" rows under "HMO/POS" column is shown as "Included in DRG", then populate as 0
    5. StopLossCalcExclusion: update the "StopLossCalcExclusion" column with value of "Y" for the above rows
    6. Line Of Business: Update the "Line of Business" with 'HMO/POS' 

    7. RevCode: "RevCode" column should have "Rev Code" values listed for "Implants" and "High Cost Drugs" rows and explode any revenue codes that are listed as a range to show only one "Rev Code" number per each row. Only keep the number and drop prefix "Rev Code"
    8. Payment Method: update the  "Payment Method" column in this table with the payment method listed for "Implants" and "High Cost Drugs" rows under "Payment Method" column in the original table
    9. PDDays1: Skip this column if the "Payment Method" value = ""
    10. PctBC:  If the value for "Implants" and "High Cost Drugs" rows under "HMO/POS" column is shown as "Included in DRG", then populate as 0
    11. StopLossCalcExclusion: update the "StopLossCalcExclusion" column with value of "Y" for the above rows
    12. Line Of Business: Update the "Line of Business" with 'PPO' 

    13. RevCode: "RevCode" column should have "Rev Code" values listed for "Implants" and "High Cost Drugs" rows and explode any revenue codes that are listed as a range to show only one "Rev Code" number per each row. Only keep the number and drop prefix "Rev Code"
    14. Payment Method: update the  "Payment Method" column in this table with the payment method listed for "Implants" and "High Cost Drugs" rows under "Payment Method" column in the original table
    15. PDDays1: Skip this column if the "Payment Method" value = ""
    16. PctBC:  If the value for "Implants" and "High Cost Drugs" rows under "HMO/POS" column is shown as "Included in DRG", then populate as 0
    17. StopLossCalcExclusion: update the "StopLossCalcExclusion" column with value of "Y" for the above rows
    18. Line Of Business: Update the "Line of Business" with 'Traditional' 

    """
    )
    chain_two = LLMChain(llm=llm, prompt=second_prompt)

    third_prompt = PromptTemplate(
    input_variables=["table"],
    template="Show me the pandas code to generate the {table} above as a dataframe and save the dataframe as 'implants_hcdrugs_df'",
    )
    chain_three = LLMChain(llm=llm, prompt=third_prompt)

    overall_chain = SimpleSequentialChain(chains=[chain_two, chain_three], verbose=True)

    #     # Run the chain specifying only the input variable for the first chain.
    Implants_HCdrugs_catchphrase = overall_chain.run(table_catchphrase)
    print("Implants_HCdrugs_catchphrase: ", Implants_HCdrugs_catchphrase)

    namespace = {}
    
    start_index = DRG_catchphrase.find('import')
    end_index = DRG_catchphrase.find('})') +2

    drg_df_statement = DRG_catchphrase[start_index:end_index]

    # Execute the extracted code in a Python cell
    exec(drg_df_statement,namespace)

    drg_df = namespace['drg_df']

    drg_df['Base Rate'] = pd.to_numeric(drg_df['Base Rate'].replace('[\$,\,]', '', regex=True))
    drg_df['OutlierPctBC_ratio'] = pd.to_numeric(drg_df['OutlierPctBC'].str.rstrip('%')) / 100
    drg_df['OutlierThreshold%_ratio'] = pd.to_numeric(drg_df['OutlierThreshold%'].str.rstrip('%')) / 100
    drg_df['DRG'] = drg_df['DRG'].astype(np.int64)
    # Verify the dataframe is created
    print("drg_df")
    print(drg_df)

    # Execute the extracted code in a Python cell
    exec("import pandas as pd\n" +  Maternity_catchphrase,namespace)

    maternity_df = namespace['maternity_df']

    maternity_df['Case Rate'] = pd.to_numeric(maternity_df['Case Rate'].replace('[\$,\,]', '', regex=True))
    maternity_df['PDRate1'] = pd.to_numeric(maternity_df['PDRate1'].replace('[\$,\,]', '', regex=True))
    maternity_df['PDDays1'] = 999
    # Verify the dataframe is created
    print("maternity_df")
    print(maternity_df)

    start_index = Neonatal_catchphrase.find('import')
    
    neonatal_df_statement = Neonatal_catchphrase[start_index:]

    # Execute the extracted code in a Python cell
    exec(neonatal_df_statement,namespace)
    neonatal_df = namespace['neonatal_df']
    #neonatal_df['PDRate1'] = pd.to_numeric(neonatal_df['PDRate1'].replace('[\$,\,]', '', regex=True))
    # Verify the dataframe is created
    
    neonatal_df.rename(columns={'MS-DRG': 'DRG'}, inplace=True)
    neonatal_df['PDRate1'] = pd.to_numeric(neonatal_df['PDRate1'].replace('[\$,\,]', '', regex=True))
    print("neonatal_df")
    print(neonatal_df)

    # Step 1: Left Join drg_df with maternity_df
    merged_df = drg_df.merge(maternity_df, on=['DRG', 'Line of Business'], how='left')

    # Update columns to 0 or 0.0 for matching rows
    columns_to_update = ['Base Rate', 'OutlierPctBC', 'OutlierThreshold%', 'OutlierPctBC_ratio', 'OutlierThreshold%_ratio']
    merged_df.loc[merged_df['Payment Method_y'].notnull(), columns_to_update] = 0

    # Update 'Payment Method' value of drg_df with 'Payment Method' value of maternity_df
    merged_df.loc[merged_df['Payment Method_y'].notnull(), 'Payment Method_x'] = merged_df['Payment Method_y']

    # # Drop unnecessary columns
    merged_df.drop(['Payment Method_y'], axis=1, inplace=True)
    merged_df.rename(columns={'Payment Method_x': 'Payment Method'}, inplace=True)

    # Step 2: Left Join merged_df with neonatal_df
    final_df = merged_df.merge(neonatal_df, on=['DRG', 'Line of Business'], how='left')

    # Update columns to 0 or 0.0 for matching rows
    final_df.loc[final_df['Payment Method_y'].notnull(), columns_to_update] = 0

    # Update 'Payment Method' value of merged_df with 'Payment Method' value of neonatal_df
    final_df.loc[final_df['Payment Method_y'].notnull(), 'Payment Method_x'] = final_df['Payment Method_y']
    final_df.loc[final_df['PDRate1_y'].notnull(), 'PDRate1_x'] = final_df['PDRate1_y']

    # Drop unnecessary columns
    final_df.drop(['Payment Method_y'], axis=1, inplace=True)
    final_df.rename(columns={'Payment Method_x': 'Payment Method'}, inplace=True)
    final_df.drop(['PDRate1_y'], axis=1, inplace=True)
    final_df.rename(columns={'PDRate1_x': 'PDRate1'}, inplace=True)

    # Print the final merged dataframe
    print(final_df.head())

    cms_df = pd.read_csv(csv_files[0])
    new_column_names = cms_df.iloc[0]
    cms_df = cms_df.rename(columns=new_column_names)
    cms_df = cms_df[1:].reset_index(drop=True)
    cms_df =cms_df.rename(columns={"MS-DRG ": "DRG"})
    cms_df = cms_df.drop(['FY 2022 Final Post-Acute DRG','FY 2022 Final Special Pay DRG','MDC','TYPE','MS-DRG Title'], axis=1)
    cms_df['DRG'] = cms_df['DRG'].astype(np.int64)
    cms_df = cms_df[:-2]

    cms_df['Weights'] = cms_df['Weights'].astype(float)
    cms_df['Geometric mean LOS'] = cms_df['Geometric mean LOS'].astype(float)
    cms_df['Arithmetic mean LOS'] = cms_df['Arithmetic mean LOS'].astype(float)

    combined_df = pd.merge(final_df, cms_df, on='DRG', how='inner')
    combined_df['OutlierThreshold$'] = round(combined_df['Base Rate']*combined_df['Weights']*combined_df['OutlierThreshold%_ratio'],0)
    combined_df['DateInd'] = 'D'
    combined_df['Tax IDs'] = text_catchphrase
    combined_df['Effective Date'] = date_catchphrase

    combined_df.drop(['OutlierThreshold%_ratio','OutlierPctBC_ratio'], axis=1, inplace=True)
    combined_df.to_csv('processed_contract.csv')
    file = 'processed_contract.csv'

    return file


# Gradio stuff starts here
with gr.Blocks(
    css=""" 
        footer { display: none !important; } 
        .gradio-container { min-height: 0px !important; }
        """
    ) as demo:

    # title of the app (goes in <head> tag of the page source)
    demo.title = "Aspirion"

    # App's <body> starts here
    gr.Markdown("Aspirion Demo")

    # Row of input for file upload
    with gr.Row(variant="default"):
        # gradio file object with support for multiple files
        input_files = gr.File(interactive=False, file_count="multiple", file_types=["file"])
        # gradio upload button
        upload_button = gr.UploadButton("Click to Upload Documents", file_count="multiple", file_types=["file"])

    # event handler for the upload button
    # upload_button.upload(lambda files:[file.name for file in files] , upload_button, file)
    upload_button.upload(upload_files, upload_button, input_files)

    # Row of input for text box and the primary process button
    with gr.Row(variant="panel").style(equal_height=True):
        
        # gradio buttons for clearing the text box and processing the documents
        process_btn = gr.Button("Process", variant="primary")
        output_file = gr.File(label="Output File",file_count="single")

        # process_btn.click(process, upload_button, output_file)
        process_btn.click(
        fn=process,
        inputs=[input_files],
        outputs=[output_file],
        api_name="process",
        show_progress=True)


# Run the app
if __name__ == "__main__":

    # Clear the docs folder of any existing files
    # clear_docs()

    # Normal Gradio demo
    gr.close_all()
    demo.launch(
        server_port=int(os.environ.get("PORT", 7860)),
    )
    

# index = construct_index("docs")