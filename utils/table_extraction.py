import camelot
import pdfplumber
from tabulate import tabulate
import pandas as pd

def get_pdf_table_latex(pdf_path: str):
    """Extracts tables from a PDF file using the Camelot library and returns a
    LaTeX string with the tables formatted using the tabulate library.

    Args:
        pdf_path (str): The path to the PDF file to extract tables from.

    Returns:
        str: A LaTeX string containing the tables extracted from the PDF file.
    """ 

    # extract tables using Camelot
    tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
    
    # create a list of tables, where each table is a list of rows
    tables_list = []
    for table in tables:
        header = [str(col) for col in table.df.columns.tolist()]  # get header from first row
        table_list = [header]
        for _, row in table.df.iterrows():
            if not all(val == '' for val in row):
                table_list.append([str(val) for val in row])
        if table_list:
            tables_list.append(table_list)
    
    # create LaTeX table using tabulate
    latex_tables = []
    for table in tables_list:
        latex_table = tabulate(table, headers='firstrow', tablefmt='latex')
        latex_tables.append(latex_table)
    
    # concatenate tables
    latex_table = '\n\n'.join(latex_tables)
    
    return latex_table


##############################################################################################################################

def raw_text_and_tables_extract(pdf_file):
    """
    Extracts raw text and tables from a PDF file.
    Args:
    pdf_file (str): The path to the PDF file.

    Returns:
    list: A list of tables found in the PDF file. Each table is represented as a string in LaTeX format.
    """
   
    page_data = []      # list to store the text for each page of the PDF
    table_data = []     # list to store any tables on each page of the PDF

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            # extract page text
            text = page.extract_text()
            text = text.replace(".  ", ".")

            # extract tables
            tables = page.extract_tables()
            markdown_tables = []

            # convert tables to markdown format
            for table in tables:
                rows = []
                for row in table:
                    if not all(val == '' for val in row):
                        row = [str(val) for val in row if val != '']
                        rows.append(row)
                if rows:
                    headers = rows[0]
                    columns = [list(col) for col in zip(*rows)]
                    columns = [col for col in columns if any(val != '' for val in col)]
                    rows = [list(row) for row in zip(*columns)]
                    rows.insert(0, headers)
                    markdown_table = tabulate(rows, headers='firstrow', tablefmt='latex')
                    # print(markdown_table)
                    markdown_tables.append(markdown_table)
                    # print(markdown_tables)

            # append page text and tables to lists
            page_data.append(text)
            table_data.append(markdown_tables)

    return table_data

def clean_latex_table(table_data):
    cleaned_tables = []
    for table in table_data:
        # Convert list of table rows to string
        table_str = "\\\\\n".join(table)

        # Replace any four backslashes with two backslashes
        # Replace any two backslashes with one backslash
        table_str = table_str.replace('\\\\\\\\', '\\') or table_str.replace('\\\\', '\\')

        # Remove any trailing or leading whitespace
        table_str = table_str.strip()
        table_str = table_str.replace('\n', ' ')

        cleaned_tables.append(table_str)

    # Remove any empty strings from the list
    # cleaned_tables = [table for table in cleaned_tables if table]

    # Return the cleaned tables as a list of strings
    return cleaned_tables
####################################################################################################

def extract_and_clean_tables(pdf_file):
    """
    Extracts tables from a PDF file and cleans them.

    Args:
        pdf_file (str): Filepath of the PDF file.

    Returns:
        list: A list of cleaned tables, where each table is a string.
    """
    # Extract raw text and tables from PDF file
    table_data = raw_text_and_tables_extract(pdf_file)
    
    # Clean the extracted tables
    cleaned_tables = clean_latex_table(table_data)
    cleaned_tables = [table for table in cleaned_tables if table]
    
    # Return cleaned tables
    return cleaned_tables

def get_latex_tables_camelot(pdf_path):
    """Extracts tables from a PDF file using the Camelot library and returns a
    LaTeX string with the tables formatted using the tabulate library.

    Args:
        pdf_path (str): The path to the PDF file to extract tables from.

    Returns:
        str: A LaTeX string containing the tables extracted from the PDF file.
    """

    # Extract tables using Camelot with lattice flavor
    tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')

    # If no tables are detected, try with stream flavor
    if len(tables) == 0:
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')

    # Create a list of tables, where each table is a list of rows
    tables_list = []
    for table in tables:
        header = [str(col) for col in table.df.columns.tolist()] 
        # get header from first row
        table_list = [header]
        for _, row in table.df.iterrows():
            if not all(val == '' for val in row):
                table_list.append([str(val) for val in row])
        if table_list:
            tables_list.append(table_list)

    # Create LaTeX tables using pandas
    latex_tables = []
    for table in tables_list:
        latex_table = pd.DataFrame(table, columns=table[1]) #index was getting appended such as 0,1,2,3... so columns=table
        latex_table = latex_table.drop(0)
        latex_table = latex_table.style.to_latex()
        latex_tables.append(latex_table)

    return latex_tables

