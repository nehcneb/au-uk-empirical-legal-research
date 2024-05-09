# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Preliminaries

# %%
#Preliminary modules
import base64 
import json
import pandas as pd
import shutil
import numpy as np
import re
import datetime
from datetime import date
from datetime import datetime
from dateutil import parser
from dateutil.relativedelta import *
from datetime import datetime, timedelta
import sys
import pause
import os
import io

#Conversion to text
import fitz
#from io import StringIO
from io import BytesIO
import pdf2image
from PIL import Image
import pytesseract
import mammoth

#Streamlit
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste

#OpenAI
import openai
import tiktoken
import math
from math import ceil

#Google
from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb


# %%
#Whether users are allowed to use their account
from extra_functions import own_account_allowed

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

# %%
#Get current directory
current_dir = os.getcwd()


# %%
#today
today_in_nums = str(datetime.now())[0:10]

# %%
# Generate placeholder list of errors
errors_list = set()


# %%
#Create function for saving responses and results
def convert_df_to_json(df):
    return df.to_json(orient = 'split', compression = 'infer')

def convert_df_to_csv(df):
   return df.to_csv(index=False).encode('utf-8')

#Excel metadata
excel_author = 'The Empirical Legal Research Kickstarter'
excel_description = 'A 2022 University of Sydney Research Accelerator (SOAR) Prize partially funded the development of the Empirical Legal Research Kickstarter, which generated this spreadsheet.'

def convert_df_to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    workbook = writer.book
    workbook.set_properties({"author": excel_author, "comments": excel_description})
    worksheet = writer.sheets['Sheet1']
#    format1 = workbook.add_format({'num_format': '0.00'}) 
    worksheet.set_column('A:A', None)#, format1)  
    writer.save()
    processed_data = output.getvalue()
    return processed_data

# %%
#Title of webpage
st.set_page_config(
   page_title="Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Pause

scraper_pause = 5

print(f"\nThe pause between GPT prompting is {scraper_pause} second.")

# %%
#Page bound

default_page_bound = 10

print(f"\nThe maximum number of pages per file is {default_page_bound}.")

if 'page_bound' not in st.session_state:
    st.session_state['page_bound'] = default_page_bound


# %% [markdown]
# # Functions for Own Files

# %%
#function to create dataframe
#@st.cache_data
def create_df():

    #submission time
    timestamp = datetime.now()

        #Personal info entries

    name = ''
    
    email = ''

    gpt_api_key = ''

    try:
        name = name_entry
    except:
        print('Name not entered')
    
    try:
        email = email_entry
    except:
        print('Email not entered')

    try:
        gpt_api_key = gpt_api_key_entry
        #This is the user's entered API key whether valid or invalid, not necessarily the one used to produce outputs
    except:
        print('API key not entered')

    #Own account status
    own_account = st.session_state.own_account
    
    #file counter bound
    file_counter_bound = st.session_state.file_counter_bound

    #Page counter bound

    page_bound = st.session_state.page_bound
    
    #GPT enhancement
    gpt_enhancement = st.session_state.gpt_enhancement_entry

    #GPT choice and entry
    gpt_activation_status = gpt_activation_entry
        
    gpt_questions = gpt_questions_entry[0: question_characters_bound]

    #Get uploaded file names

    file_names_list = []

    for uploaded_doc in uploaded_docs:
        file_names_list.append(uploaded_doc.name)

    for uploaded_image in uploaded_images:
        file_names_list.append(uploaded_image.name)

    #Language choice

    language = language_entry
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Your uploaded files' : str(file_names_list), 
           'Language choice': language, 
           'Maximum number of files': file_counter_bound, 
          'Maximum number of pages per file': page_bound, 
            'Use GPT': gpt_activation_status, 
           'Enter your question(s) for GPT': gpt_questions, 
            'Use own account': own_account,
            'Use latest version of GPT': gpt_enhancement
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
    
#    df_master_new.to_json(current_dir + '/df_master.json', orient = 'split', compression = 'infer')
#    df_master_new.to_excel(current_dir + '/df_master.xlsx', index=False)

#    if len(df_master_new) > 0:
        
    return df_master_new

#    else:
#        return 'Error: spreadsheet of reponses NOT generated.' 


# %%
#File types and languages for processing
doc_types = ["pdf", "txt", 'docx', "xps", "epub", "mobi", 'cs', 'xml', 'json'] #"fb2", "cbz", "svg",
image_types = ["pdf", "jpg", "jpeg", "png", "bmp", "gif", "tiff"] #, "pnm", "pgm", "pbm", "ppm", "pam", "jxr", "jpx", "jp2", "psd"]
languages_dict = {'English': 'eng', 
                  'English, Middle (1100-1500)': 'enm', 
                  'Chinese - Simplified': 'chi_sim', 
                  'Chinese - Traditional': 'chi_tra', 
                  'French': 'fra', 
                  'German' : 'deu',
                  'Greek, Modern (1453-)': 'ell', 
                  'Greek, Ancient (-1453)': 'grc', 
                  'Hebrew' : 'heb', 
                  'Hindi' : 'hin', 
                  'Hungarian': 'hun', 
                  'Indonesian': 'ind', 
                  'Italian': 'ita', 
                  'Italian - Old': 'ita_old', 
                  'Japanese': 'jpn', 
                  'Korean': 'kor', 
                  'Malay': 'msa', 
                  'Panjabi; Punjabi': 'pan', 
                  'Polish': 'pol', 
                  'Portuguese': 'por', 
                  'Russian': 'rus', 
                  'Spanish; Castilian': 'spa', 
                  'Spanish; Castilian - Old': 'spa_old', 
                  'Swedish': 'swe', 
                  'Thai': 'tha', 
                  'Turkish': 'tur', 
                  'Uighur; Uyghur': 'uig', 
                  'Ukrainian': 'ukr', 
                  'Vietnamese': 'vie', 
                  'Yiddish': 'yid'
                 }
languages_list = list(languages_dict.keys())

#languages_words = ', '.join(languages_list)


# %%
#Define format functions for GPT questions    

#Create function to split a string into a list by line
def split_by_line(x):
    y = x.split('\n')
    for i in y:
        if len(i) == 0:
            y.remove(i)
    return y

#Create function to split a list into a dictionary for list items longer than 10 characters

#Apply split_by_line() before the following function
def GPT_label_dict(x_list):
    GPT_dict = {}
    for i in x_list:
        if len(i) > 10:
            GPT_index = x_list.index(i) + 1
            i_label = 'GPT question ' + f'{GPT_index}'
            GPT_dict.update({i_label: i})
    return GPT_dict



# %%
# Function to convert each uploaded file to file name, text
#@st.cache_data
def doc_to_text(uploaded_doc, language, page_bound):
    file_triple = {'File name' : '', 'Language choice': language, 'Page length': '', 'Extracted text': '', 
#                  'Page 2': '' #Test page
                  }
    
    #Get file name
    file_triple['File name']=uploaded_doc.name
    
    #Get file data
    bytes_data = uploaded_doc.getvalue()

    #Get file extension
    extension = file_triple['File name'].split('.')[-1].lower()

    #Create list of pages
    text_list = []

    #Word format
    if extension == 'docx':
        doc_string = mammoth.convert_to_html(BytesIO(bytes_data)).value
        text_list.append(doc_string)

        file_triple['Page length'] = 1
        
    else:
        #text formats
        if extension in ['txt', 'cs', 'xml', 'json']:
            doc = fitz.open(stream=bytes_data, filetype="txt")

        #Other formats
        else:
            doc = fitz.open(stream=bytes_data)

        max_doc_number=min(len(doc), page_bound)
        
        for page_index in list(range(0, max_doc_number)):
            page = doc.load_page(page_index)
            text_page = page.get_text() 
            text_list.append(text_page)

        #Length of pages
        file_triple['Page length'] = len(doc)

    file_triple['Extracted text'] = str(text_list)

    #Test page
#    file_triple['Page 2'] = doc.load_page(1).get_text()
    
    return file_triple


# %%
#Function for images to text
#@st.cache_data
def image_to_text(uploaded_image, language, page_bound):
    file_triple = {'File name' : '', 'Language choice': language, 'Page length': '', 'Extracted text': '', 
#                  'Page 2': '' #Test page
                  }

    #Get file name
    file_triple['File name']=uploaded_image.name

    #Get file data
    bytes_data = uploaded_image.read()

    #Get file extension
    extension = file_triple['File name'].split('.')[-1].lower()

    #Obtain images from uploaded file
    if extension == 'pdf':
        try:
            images = pdf2image.convert_from_bytes(bytes_data, timeout=30)
        except PDFPopplerTimeoutError as pdf2image_timeout_error:
            print(f"pdf2image error: {pdf2image_timeout_error}.")

    else:
        images = []
        image_raw = Image.open(BytesIO(bytes_data))
        images.append(image_raw)
        
    #Extract text from images
    text_list = []
    
    max_images_number=min(len(images), page_bound)

    for image in images[ : max_images_number]:
        try:
            text_page = pytesseract.image_to_string(image, lang=languages_dict[language], timeout=30)
            text_list.append(text_page)
            
        except RuntimeError as pytesseract_timeout_error:
            print(f"pytesseract error: {pytesseract_timeout_error}.")

    file_triple['Extracted text'] = str(text_list)

    #Length of pages
    file_triple['Page length'] = len(images)

    #Test page
#    file_triple['Page 2'] = pytesseract.image_to_string(images[1], lang=languages_dict[language], timeout=30)
        
    return file_triple


# %% [markdown]
# # GPT functions and parameters

# %%
#Check validity of API key

def is_api_key_valid(key_to_check):
    openai.api_key = key_to_check
    
    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": "user", "content": 'Who is Taylor Swift?'}], 
            max_tokens = 5
        )
    except:
        return False
    else:
        return True


# %%
#Module, costs and upperbounds

#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-3.5-turbo-0125"

#Upperbound on number of engagements with GPT

#GPT_use_bound = 3

#print(f"\nPrior number of GPT uses is capped at {GPT_use_bound} times.")

#Define input and output costs, token caps and maximum characters
#each token is about 4 characters

def gpt_input_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_input_cost = 1/1000000*0.5
        
    if gpt_model == "gpt-4-turbo":
        gpt_input_cost = 1/1000000*10
    return gpt_input_cost

def gpt_output_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_output_cost = 1/1000000*0.5
        
    if gpt_model == "gpt-4-turbo":
        gpt_output_cost = 1/1000000*10
        
    return gpt_output_cost

def tokens_cap(gpt_model):
    
    if gpt_model == "gpt-3.5-turbo-0125":
        tokens_cap = int(16385 - 2500) #For GPT-3.5-turbo, token limit covering both input and output is 16385,  while the output limit is 4096.
    
    if gpt_model == "gpt-4-turbo":
        tokens_cap = int(128000 - 6000) #For GPT-4-turbo, token limit covering both input and output is 128000, while the output limit is 4096.

    return tokens_cap
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

#Upperbound on the length of questions for GPT
#if 'question_characters_bound' not in st.session_state:
#    st.session_state['question_characters_bound'] = 1000

question_characters_bound = 1000

print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")

#Upperbound on number of files to scrape

#Default file counter bound

default_file_counter_bound = 10

if 'file_counter_bound' not in st.session_state:
    st.session_state['file_counter_bound'] = default_file_counter_bound

print(f"The default number of files to scrape per request is capped at {default_file_counter_bound}.\n")

# %%
#Define function to determine eligibility for GPT use

#Define a list of privileged email addresses with unlimited GPT uses

privileged_emails = st.secrets["secrets"]["privileged_emails"].replace(' ', '').split(',')

def prior_GPT_uses(email_address, df_online):
    # df_online variable should be the online df_online
    prior_use_counter = 0
    for i in df_online.index:
        if ((df_online.loc[i, "Your email address"] == email_address) 
            and (len(df_online.loc[i, "Processed"])>0)
           ):
            prior_use_counter += 1
    if email_address in privileged_emails:
        return 0
    else:
        return prior_use_counter

#Define function to check whether email is educational or government
def check_edu_gov(email_address):
    #Return 1 if educational or government, return 0 otherwise
    end=email_address.split('@')[1]
    if (('.gov' in end) or ('.edu' in end) or ('.ac' in end)):
        return 1
    else:
        return 0



# %%
#Tokens estimate preliminaries
#encoding = tiktoken.get_encoding("cl100k_base")
#encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
#Tokens estimate function
def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

#Define file input function for JSON approach

#Token limit covering both GTP input and GPT output is 16385, each token is about 4 characters
#tokens_cap(gpt_model) = int(16385 - 3000)

def file_prompt(file_triple, gpt_model):
                
    file_content = 'Based on the following document:  """'+ file_triple['Extracted text'] + '"""'

    file_content_tokens = num_tokens_from_string(file_content, "cl100k_base")
    
    if file_content_tokens <= tokens_cap(gpt_model):
        
        return file_content

    else:
                
        file_chars_capped = int(tokens_cap(gpt_model)*4)
        
        #Keep first x characters rather than cut out the middle
        file_string_trimmed = file_triple['Extracted text'][ : int(file_chars_capped)]

        #If want to cut out the middle instead
#        file_string_trimmed = file_triple['Extracted text'][ :int(file_chars_capped/2)] + file_triple['Extracted text'][-int(file_chars_capped/2): ]
        
        file_content_capped = 'Based on the following document:  """'+ file_string_trimmed + '"""'
        
        return file_content_capped



# %%
#Define system role content for GPT
role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a file. The file may be a document or an image. You will be provided with the file. Please answer questions based only on information contained in the file. Where your answer comes from a specific page or section of the file, provide the page number or section reference as part of your answer. If you cannot answer the questions based on the file, do not make up information, but instead write "answer not found".'

intro_for_GPT = [{"role": "system", "content": role_content}]


# %%
#Define GPT answer function for answers in json form, YES TOKENS
#IN USE

def GPT_json_tokens(questions_json, file_triple, gpt_model):
    #'question_json' variable is a json of questions to GPT

    file_for_GPT = [{"role": "user", "content": file_prompt(file_triple, gpt_model)}]

    json_direction = [{"role": "user", "content": 'You will be given questions to answer in JSON form.'}]

    #Create answer format
    
    q_keys = [*questions_json]
    
    answers_json = {}
    
    for q_index in q_keys:
        answers_json.update({q_index: 'Your answer to the question with index ' + q_index + '. State specific page numbers or sections of the file.'})
    
    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": str(questions_json).replace("\'", '"') + ' Give responses in the following JSON form: ' + str(answers_json).replace("\'", '"')}]
    
    #Create messages in one prompt for GPT
    language_content = f"The file is written in {file_triple['Language choice']}."

    intro_for_GPT = [{"role": "system", "content": role_content + language_content}] 

    messages_for_GPT = intro_for_GPT + file_for_GPT + json_direction + question_for_GPT
    
#   return messages_for_GPT

    #os.environ["OPENAI_API_KEY"] = API_key

    openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model=gpt_model,
            messages=messages_for_GPT, 
            response_format={"type": "json_object"}
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        #To obtain a json directly, use below
        answers_dict = json.loads(completion.choices[0].message.content)
        
        #Obtain tokens
        output_tokens = completion.usage.completion_tokens
        
        prompt_tokens = completion.usage.prompt_tokens
        
        return [answers_dict, output_tokens, prompt_tokens]

    except Exception as error:
        
        for q_index in q_keys:
            answers_json[q_index] = error
        
        return [answers_json, 0, 0]



# %%
#Define GPT function for each respondent's dataframe, index by file then question, with input and output tokens given by GPT itself
#IN USE

#The following function DOES NOT check for existence of questions for GPT
    # To so check, active line marked as #*
def engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, gpt_model):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # f"Length of first 10 pages in tokens (up to {tokens_cap(gpt_model)} given to GPT)"
        # 'GPT cost estimate (USD excl GST)'
        # 'GPT time estimate (seconds)'
        # GPT questions/answers

    #os.environ["OPENAI_API_KEY"] = API_key

    openai.api_key = API_key
    
    #client = OpenAI()
    
    question_keys = [*questions_json]
    
    for file_index in df_individual.index:
        
        file_triple = df_individual.to_dict('index')[file_index]
        
        #Calculate and append number of tokens of file, regardless of whether given to GPT
        file_tokens = num_tokens_from_string(str(file_triple), "cl100k_base")
        df_individual.loc[file_index, f"Length of first {st.session_state.page_bound} pages in tokens (up to {tokens_cap(gpt_model)} given to GPT)"] = file_tokens       

        #Indicate whether file truncated
        
        df_individual.loc[file_index, "File truncated (if given to GPT)?"] = ''       
        
        if file_tokens <= tokens_cap(gpt_model):
            
            df_individual.loc[file_index, "File truncated (if given to GPT)?"] = 'No'
            
        else:
            
            df_individual.loc[file_index, "File truncated (if given to GPT)?"] = 'Yes'

        #Create columns for respondent's GPT cost, time
        df_individual.loc[file_index, 'GPT cost estimate (USD excl GST)'] = ''
        df_individual.loc[file_index, 'GPT time estimate (seconds)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each file, gives answers as a string containing a dictionary

        if int(GPT_activation) > 0:
            GPT_file_triple = GPT_json_tokens(questions_json, file_triple, gpt_model) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_file_triple[0]

            #Calculate and append GPT finish time and time difference to individual df
            GPT_finish_time = datetime.now()
            
            GPT_time_difference = GPT_finish_time - GPT_start_time
    
            df_individual.loc[file_index, 'GPT time estimate (seconds)'] = GPT_time_difference.total_seconds()

        else:
            answers_dict = {}    
            for q_index in question_keys:
                #Increases file index by 2 to ensure consistency with Excel spreadsheet
                answer = 'Placeholder answer for ' + ' file ' + str(int(file_index) + 2) + ' ' + str(q_index)
                answers_dict.update({q_index: answer})
            
            #Own calculation of GPT costs for Placeholder answer fors

            #Calculate capped file tokens

            file_capped_tokens = num_tokens_from_string(file_prompt(file_triple, gpt_model), "cl100k_base")

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(str(questions_json), "cl100k_base")

            #Calculate other instructions' tokens

            other_instructions = role_content + 'The file is written in some language' + 'you will be given questions to answer in JSON form.' + ' Give responses in the following JSON form: '

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. State specific page numbers or sections of the file.", "cl100k_base")

            #Calculate number of tokens of answers
            answers_tokens = num_tokens_from_string(str(answers_dict), "cl100k_base")

            input_tokens = file_capped_tokens + questions_tokens + other_tokens
            
            GPT_file_triple = [answers_dict, answers_tokens, input_tokens]

        #Create GPT question headings and append answers to individual spreadsheets

        for question_index in question_keys:
            question_heading = question_index + ': ' + questions_json[question_index]
            df_individual.loc[file_index, question_heading] = answers_dict[question_index]

        #Calculate GPT costs

        GPT_cost = GPT_file_triple[1]*gpt_output_cost(gpt_model) + GPT_file_triple[2]*gpt_input_cost(gpt_model)

        #Calculate and append GPT cost to individual df
        df_individual.loc[file_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual



# %%
#Obtain parameters

def run(df_master, uploaded_docs, uploaded_images):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your question(s) for GPT'] = df_master['Enter your question(s) for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your question(s) for GPT'].apply(GPT_label_dict)
    
    #Create files file
    Files_file = []

    #Obtain bounds and language

    file_counter_bound = int(df_master.loc[0, 'Maximum number of files'])

    page_bound = int(df_master.loc[0,'Maximum number of pages per file'])

    language = df_master.loc[0, 'Language choice']
    
    #Convert uploaded documents to text

    file_counter = 1 

    for uploaded_doc in uploaded_docs:
        if file_counter <= file_counter_bound:
            file_triple = doc_to_text(uploaded_doc, language, page_bound)
            Files_file.append(file_triple)
            file_counter += 1

    #Convert uploaded images to text

    for uploaded_image in uploaded_images:
        if file_counter <= file_counter_bound:
            file_triple = image_to_text(uploaded_image, language, page_bound)
            Files_file.append(file_triple)
            file_counter += 1
    
    #Create and export json file with search results
    json_individual = json.dumps(Files_file, indent=2)
    
    df_individual = pd.read_json(json_individual)
    
    #GPT model

    #GPT model

    if df_master.loc[0, 'Use latest version of GPT'] == True:
        gpt_model = "gpt-4-turbo"
    else:        
        gpt_model = "gpt-3.5-turbo-0125"
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
        
    #Engage GPT
    df_updated = engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, gpt_model)

    try:
        df_updated.pop('Extracted text')
    except:
        print("No 'Extracted text' columnn.")
    
    return df_updated
    


# %% [markdown]
# # For GPT-4-turbo vision

# %%
#Tokens counter

def get_image_dims(image):
    if re.match(r"data:image\/\w+;base64", image):
        image = re.sub(r"data:image\/\w+;base64,", "", image)
        image = Image.open(BytesIO(base64.b64decode(image)))
        return image.size
    else:
        raise ValueError("Image must be a base64 string.")

def calculate_image_token_cost(image, detail="auto"):
    # Constants
    LOW_DETAIL_COST = 85
    HIGH_DETAIL_COST_PER_TILE = 170
    ADDITIONAL_COST = 85

    if detail == "auto":
        # assume high detail for now
        detail = "high"

    if detail == "low":
        # Low detail images have a fixed cost
        return LOW_DETAIL_COST
    elif detail == "high":
        # Calculate token cost for high detail images
        width, height = get_image_dims(image)
        # Check if resizing is needed to fit within a 2048 x 2048 square
        if max(width, height) > 2048:
            # Resize the image to fit within a 2048 x 2048 square
            ratio = 2048 / max(width, height)
            width = int(width * ratio)
            height = int(height * ratio)
        # Further scale down to 768px on the shortest side
        if min(width, height) > 768:
            ratio = 768 / min(width, height)
            width = int(width * ratio)
            height = int(height * ratio)
        # Calculate the number of 512px squares
        num_squares = math.ceil(width / 512) * math.ceil(height / 512)
        # Calculate the total token cost
        total_cost = num_squares * HIGH_DETAIL_COST_PER_TILE + ADDITIONAL_COST
        return total_cost
    else:
        # Invalid detail_option
        raise ValueError("Invalid value for detail parameter. Use 'low' or 'high'.")


# %%
#def to_base64(uploaded_file):
    #file_buffer = uploaded_file.read()
    #b64 = base64.b64encode(file_buffer).decode()
    #return f"data:image/png;base64,{b64}"

#def to_base64(uploaded_file):
    #file_buffer = uploaded_file.read()
    #b64 = base64.b64encode(file_buffer).decode('utf-8')
    #return b64

def image_to_b64(uploaded_image, language, page_bound):
    file_triple = {'File name' : '', 'Language choice': language, 'b64_list': [], 'Dimensions (width, height)' : [],
                   'Page length': '', 'tokens_raw': 0, 
#                 'Image ID': '', 'Page length': '', 'Page 2': '' #Test page
                  }

    file_triple['File name']=uploaded_image.name

    #Get file extension
    extension = file_triple['File name'].split('.')[-1].lower()

    bytes_data = uploaded_image.read()

    if extension == 'pdf':
        
        images = pdf2image.convert_from_bytes(bytes_data, timeout=30, fmt="jpeg")

        file_triple['Page length'] = len(images)

        #Get page bound
        max_images_number=min(len(images), page_bound)

        for image in images[ : max_images_number]:

            output = BytesIO()
            image.save(output, format='JPEG')
            im_data = output.getvalue()
            
            image_data = base64.b64encode(im_data)
            if not isinstance(image_data, str):
                # Python 3, decode from bytes to string
                image_data = image_data.decode()
            data_url = 'data:image/jpg;base64,' + image_data

            #b64 = base64.b64encode(image_raw).decode('utf-8')

            b64_to_attach = data_url
            #b64_to_attach = f"data:image/png;base64,{b64}"

        file_triple['b64_list'].append(b64_to_attach)
            
        #except PDFPopplerTimeoutError as pdf2image_timeout_error:
            #print(f"pdf2image error: {pdf2image_timeout_error}.")

    else:

        file_triple['Page length'] = 1
    
        b64 = base64.b64encode(bytes_data).decode('utf-8')
    
        b64_to_attach = f"data:image/{extension};base64,{b64}"
        
        #file_triple['b64_list'] = [b64_to_attach]
        file_triple['b64_list'].append(b64_to_attach)
        

        #Get tokens
    
        #file_triple['tokens_raw'] = calculate_image_token_cost(b64_to_attach, detail="auto")
        
    for image_b64 in file_triple['b64_list']:

        #Get dimensions
        try:

            file_triple['Dimensions (width, height)'].append(get_image_dims(b64_to_attach))
        except Exception as e:
            print(f"Cannot obtain dimensions for {file_triple['File name']}, p {file_triple['b64_list'].index(image_b64)}.")
            print(e)
        
        file_triple['tokens_raw'] = file_triple['tokens_raw'] + calculate_image_token_cost(image_b64, detail="auto")
            
    return file_triple


# %%
#Define GPT answer function for answers in json form, YES TOKENS
#For gpt-4-turbo vision

def GPT_b64_json_tokens(questions_json, file_triple, gpt_model):
    #'question_json' variable is a json of questions to GPT

    #file_for_GPT = [{"role": "user", "content": file_prompt(file_triple, gpt_model) + 'you will be given questions to answer in JSON form.'}]

    #Add images to messages to GPT
    image_content_value = [{"type": "text", "text": 'Based on the following images:'}]

    for image_b64 in file_triple['b64_list']:
        image_message_to_attach = {"type": "image_url", "image_url": {"url": image_b64,}}
        image_content_value.append(image_message_to_attach)

    image_content = [{"role": "user", 
                      "content": image_content_value
                     }
                  ]

    json_direction = [{"role": "user", "content": 'You will be given questions to answer in JSON form.'}]

    file_for_GPT = image_content + json_direction
    
    #Create answer format
    
    q_keys = [*questions_json]
    
    answers_json = {}
    
    for q_index in q_keys:
        answers_json.update({q_index: 'Your answer to the question with index ' + q_index + '. State specific page numbers or sections of the file.'})
    
    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": str(questions_json).replace("\'", '"') + ' Give responses in the following JSON form: ' + str(answers_json).replace("\'", '"')}]
    
    #Create messages in one prompt for GPT
    language_content = f"The file is written in {file_triple['Language choice']}."

    intro_for_GPT = [{"role": "system", "content": role_content + language_content}] 

    messages_for_GPT = intro_for_GPT + file_for_GPT + question_for_GPT
    
#   return messages_for_GPT

    #os.environ["OPENAI_API_KEY"] = API_key

    openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model=gpt_model,
            messages=messages_for_GPT, 
            response_format={"type": "json_object"}
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        #To obtain a json directly, use below
        answers_dict = json.loads(completion.choices[0].message.content)
        
        #Obtain tokens
        output_tokens = completion.usage.completion_tokens
        
        prompt_tokens = completion.usage.prompt_tokens
        
        return [answers_dict, output_tokens, prompt_tokens]

    except Exception as error:
        
        for q_index in q_keys:
            answers_json[q_index] = error
        
        return [answers_json, 0, 0]



# %%
#Define GPT function for each respondent's dataframe, index by file then question, with input and output tokens given by GPT itself
#For gpt-4-turbo vision

#The following function DOES NOT check for existence of questions for GPT
    # To so check, active line marked as #*
def engage_GPT_b64_json_tokens(questions_json, df_individual, GPT_activation, gpt_model):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # f"Length of first 10 pages in tokens (up to {tokens_cap(gpt_model)} given to GPT)"
        # 'GPT cost estimate (USD excl GST)'
        # 'GPT time estimate (seconds)'
        # GPT questions/answers

    #os.environ["OPENAI_API_KEY"] = API_key

    openai.api_key = API_key
    
    #client = OpenAI()
    
    question_keys = [*questions_json]
    
    for file_index in df_individual.index:
        
        file_triple = df_individual.to_dict('index')[file_index]
        
        #Calculate and append number of tokens of file, regardless of whether given to GPT
        #file_triple['tokens_raw'] = num_tokens_from_string(str(file_triple), "cl100k_base")
        df_individual.loc[file_index, f"Tokens (up to {tokens_cap(gpt_model)} given to GPT)"] = file_triple['tokens_raw']       

        #Indicate whether file truncated
        
        df_individual.loc[file_index, "File truncated (if given to GPT)?"] = ''       
        
        if file_triple['tokens_raw'] <= tokens_cap(gpt_model):
            
            df_individual.loc[file_index, "File truncated (if given to GPT)?"] = 'No'
            
        else:
            
            df_individual.loc[file_index, "File truncated (if given to GPT)?"] = 'Yes'

        #Create columns for respondent's GPT cost, time
        df_individual.loc[file_index, 'GPT cost estimate (USD excl GST)'] = ''
        df_individual.loc[file_index, 'GPT time estimate (seconds)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each file, gives answers as a string containing a dictionary

        if int(GPT_activation) > 0:
            GPT_file_triple = GPT_b64_json_tokens(questions_json, file_triple, gpt_model) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_file_triple[0]

            #Calculate and append GPT finish time and time difference to individual df
            GPT_finish_time = datetime.now()
            
            GPT_time_difference = GPT_finish_time - GPT_start_time
    
            df_individual.loc[file_index, 'GPT time estimate (seconds)'] = GPT_time_difference.total_seconds()
        
        else:
            answers_dict = {}    
            for q_index in question_keys:
                #Increases file index by 2 to ensure consistency with Excel spreadsheet
                answer = 'Placeholder answer for ' + ' file ' + str(int(file_index) + 2) + ' ' + str(q_index)
                answers_dict.update({q_index: answer})
            
            #Own calculation of GPT costs for Placeholder answer fors

            #Calculate capped file tokens

            file_capped_tokens = min(file_triple['tokens_raw'], tokens_cap(gpt_model))

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(str(questions_json), "cl100k_base")

            #Calculate other instructions' tokens

            other_instructions = role_content + 'The file is written in some language' + 'you will be given questions to answer in JSON form.' + ' Give responses in the following JSON form: '

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. State specific page numbers or sections of the file.", "cl100k_base")

            #Calculate number of tokens of answers
            answers_tokens = num_tokens_from_string(str(answers_dict), "cl100k_base")

            input_tokens = file_capped_tokens + questions_tokens + other_tokens
            
            GPT_file_triple = [answers_dict, answers_tokens, input_tokens]

        #Create GPT question headings and append answers to individual spreadsheets

        for question_index in question_keys:
            question_heading = question_index + ': ' + questions_json[question_index]
            df_individual.loc[file_index, question_heading] = answers_dict[question_index]

        #Calculate GPT costs

        GPT_cost = GPT_file_triple[1]*gpt_output_cost(gpt_model) + GPT_file_triple[2]*gpt_input_cost(gpt_model)

        #Calculate and append GPT cost to individual df
        df_individual.loc[file_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual



# %%
#For gpt-4-turbo vision

def run_b64(df_master, uploaded_images):

    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your question(s) for GPT'] = df_master['Enter your question(s) for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your question(s) for GPT'].apply(GPT_label_dict)

    #Obtain bounds and language

    file_counter_bound = int(df_master.loc[0, 'Maximum number of files'])

    page_bound = int(df_master.loc[0,'Maximum number of pages per file'])

    language = df_master.loc[0, 'Language choice']
    
    #Convert uploaded documents to b64

    file_counter = 1 
    
    #Create files file
    Files_file = []

    #Convert images to b64, then send to GPT
    for uploaded_image in uploaded_images:
        if file_counter <= file_counter_bound:
            file_triple = image_to_b64(uploaded_image, language, page_bound)
            Files_file.append(file_triple)
            file_counter += 1

    #Create and export json file with search results
    json_individual = json.dumps(Files_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    
    #GPT model
    if df_master.loc[0, 'Use latest version of GPT'] == True:
        
        gpt_model = "gpt-4-turbo"

    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    #apply GPT_individual to each respondent's judgment spreadsheet

    df_updated = engage_GPT_b64_json_tokens(questions_json, df_individual, GPT_activation, gpt_model)

    #Remove redundant columns

    for column in ['tokens_raw', 'b64_list']:
        try:
            df_updated.pop(column)
        except:
            print(f"No {column} column.")

    return df_updated


# %% [markdown]
# # Streamlit form, functions and parameters

# %% [markdown]
# ## Function definitions

# %%
def clear_cache_except_validation_df_master():
    keys = list(st.session_state.keys())
    if 'gpt_api_key_validity' in keys:
        keys.remove('gpt_api_key_validity')
    if 'df_master' in keys:
        keys.remove('df_master')
    for key in keys:
        st.session_state.pop(key)


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default values

if 'gpt_enhancement_entry' not in st.session_state:
    st.session_state['gpt_enhancement_entry'] = False

if 'gpt_api_key_validity' not in st.session_state:
    st.session_state['gpt_api_key_validity'] = False

if 'own_account' not in st.session_state:
    st.session_state['own_account'] = False

# %%
#Try to carry over previously entered personal details    
try:
    st.session_state['gpt_api_key_entry'] = st.session_state.df_master.loc[0, 'Your GPT API key']
except:
    st.session_state['gpt_api_key_entry'] = None

try:
    st.session_state['name_entry'] = st.session_state.df_master.loc[0, 'Your name']
except:
    st.session_state['name_entry'] = None

try:
    st.session_state['email_entry'] = st.session_state.df_master.loc[0, '"Your email address']
    
except:
    st.session_state['email_entry'] = None


# %% [markdown]
# ## Form before AI

# %%
#Create form

return_button = st.button('RETURN to first page')

st.header(f"You have selected to study :blue[your own files].")
    
st.write(f'**:green[Please upload your documents or images.]** By default, this program will extract text from up to {default_file_counter_bound} files, and process up to approximately {round(tokens_cap("gpt-3.5-turbo-0125")*3/4)} words from the first {default_page_bound} pages of each file.')

st.write('This program works only if the text from your file(s) is displayed horizontally and neatly.')

st.caption('During the pilot stage, the number of files and the number of words per file to be processed are capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to cover more files or more words per file.')

st.subheader('Upload documents')

st.markdown("""Supported document formats: **searchable PDF**, **DOCX**, **TXT**, **JSON**, CS,  EPUB, MOBI, XML, XPS.
""")

uploaded_docs = st.file_uploader("Please choose your document(s).", type = doc_types, accept_multiple_files=True)

st.caption('DOC is not yet supported. Microsoft Word or a similar program can convert a DOC file to a DOCX file.')

st.subheader('Upload images')

st.markdown("""Supported image formats: **non-searchable PDF**, **JPG**, **JPEG**, **PNG**, BMP, GIF, TIFF.
""")
uploaded_images = st.file_uploader("Please choose your image(s).", type = image_types, accept_multiple_files=True)

st.caption("By default, [Python-tesseract](https://pypi.org/project/pytesseract/) will extract text from images. This tool is based on [Google’s Tesseract-OCR Engine](https://github.com/tesseract-ocr/tesseract).")

st.subheader('Language of uploaded files')

st.markdown("""In what language is the text from your uploaded file(s) written?""")
    
language_entry = st.selectbox("Please choose a language.", languages_list, index=0)

st.caption('During the pilot stage, the languages supported are limited. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to choose a language which is not available under this menu.')



# %% [markdown]
# ## Form for AI and account

# %%
st.header("Use GPT as your research assistant")

st.markdown("**:green[Would you like GPT to answer questions about each file uploaded by you?]**")

st.markdown("""Please consider trying this program without asking GPT any questions first. Doing so will produce a rough cost estimate for using GPT.
""")

gpt_activation_entry = st.checkbox('Use GPT', value = False)

#st.markdown("**:green[GPT can answer questions about each file uploaded by you.]**")

st.caption("Use of GPT is costly and funded by a grant. For the model used by default, Ben's own experience suggests that it costs approximately USD \$0.003-\$0.008 (excl GST) per file. The exact cost for answering a question about a file depends on the length of the question, the length of the file, and the length of the answer produced (as elaborated at https://openai.com/pricing for model gpt-3.5-turbo-0125). You will be given ex-post cost estimates.")

st.subheader("Enter your question(s) for GPT")

st.markdown("""You may enter one or more questions. **Please enter one question per line or per paragraph.**""")

gpt_questions_entry = st.text_area(f"You may enter at most {question_characters_bound} characters.", height= 200, max_chars=question_characters_bound) 

st.caption(f"By default, answers to your questions will be generated by model gpt-3.5-turbo-0125. Due to a technical limitation, this model will be instructed to read up to approximately {round(tokens_cap('gpt-3.5-turbo-0125')*3/4)} words from each file.")

st.markdown("""GPT is instructed to avoid giving answers which cannot be obtained from the relevant file itself. This is to minimise the risk of giving incorrect information (ie hallucination).""")

if st.toggle('See the instruction given to GPT'):
    st.write(f"*{intro_for_GPT[0]['content']}*")

if own_account_allowed() > 0:
    
    st.subheader(':orange[Enhance program capabilities]')
    
    st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or increase the maximum nunber of files to process? You can do so with your own GPT account.
    """)
    
    own_account_entry = st.toggle('Use my own GPT account')
    
    if own_account_entry:
    
        st.session_state["own_account"] = True
    
        st.markdown("""**:green[Please enter your name, email address and API key.]** You can sign up for a GPT account and pay for your own usage at https://platform.openai.com/signup. You can then find your API key at https://platform.openai.com/api-keys.
    """)
            
        name_entry = st.text_input(label = "Your name", value = st.session_state.name_entry)
        
        email_entry = st.text_input(label = "Your email address", value = st.session_state.email_entry)
        
        gpt_api_key_entry = st.text_input(label = "Your GPT API key", value = st.session_state.gpt_api_key_entry)
        
        valdity_check = st.button('VALIDATE your API key')
    
        if valdity_check:
            
            api_key_valid = is_api_key_valid(gpt_api_key_entry)
                    
            if api_key_valid == False:
                st.session_state['gpt_api_key_validity'] = False
                st.error('Your API key is not valid.')
                
            else:
                st.session_state['gpt_api_key_validity'] = True
                st.success('Your API key is valid.')
    
        st.markdown("""**:green[You can use the latest version of GPT model (gpt-4-turbo),]** which is :red[20 times more expensive, per character] than the default model (gpt-3.5-turbo) which you can use for free.""")  
        
        gpt_enhancement_entry = st.checkbox('Use the latest GPT model', value = False)
        st.caption('For more on pricing for different GPT models, please see https://openai.com/api/pricing.')
        
        if gpt_enhancement_entry == True:
        
            st.session_state.gpt_model = "gpt-4-turbo"
            st.session_state.gpt_enhancement_entry = True

        else:
            
            st.session_state.gpt_model = "gpt-3.5-turbo-0125"
            st.session_state.gpt_enhancement_entry = False
        
        st.write(f'**:green[You can increase the maximum number of files to process.]** The default maximum is {default_file_counter_bound}.')
        
        file_counter_bound_entry = round(st.number_input(label = 'Enter the maximum number of files up to 100', min_value=1, max_value=100, value=default_file_counter_bound))
    
        st.session_state.file_counter_bound = file_counter_bound_entry
    
        st.write(f'**:violet[You can increase the maximum number of pages per file to process.]** The default maximum is {default_file_counter_bound}.')
    
        page_bound_entry = round(st.number_input(label = 'Enter the maximum number of pages per file up to 100', min_value=1, max_value=100, value=default_file_counter_bound))
    
        st.session_state.page_bound = page_bound_entry
    
        st.write(f'*GPT model {st.session_state.gpt_model} will answer any questions based on up to approximately {round(tokens_cap(st.session_state.gpt_model)*3/4)} words from the first {st.session_state.page_bound} pages each file, for up to {st.session_state.file_counter_bound} files.*')
    
    else:
        
        st.session_state["own_account"] = False
    
        st.session_state.gpt_model = "gpt-3.5-turbo-0125"
        
        st.session_state.gpt_enhancement_entry = False
    
        st.session_state.file_counter_bound = default_file_counter_bound
    
        #st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]
    
    #file_counter_bound_entry = round(file_counter_bound_entry_raw)


# %% [markdown]
# ## Consent and next steps

# %%
st.header("Consent")

st.markdown("""By running the Empirical Legal Research Kickstarter, you agree that the data and/or information this form provides will be temporarily stored on one or more remote servers for the purpose of producing an output containing data. Any such data and/or information may also be given to an artificial intelligence provider for the same purpose.""")

consent =  st.checkbox('Yes, I agree.', value = False)

st.markdown("""If you do not agree, then please feel free to close this form.""")

st.header("Next steps")

st.markdown("""**:green[You can now run the Empirical Legal Research Kickstarter.]** A spreadsheet which hopefully has the data you seek will be available for download in about 2-3 minutes per 10 files.

You can also download a record of your responses.
""")

#Warning
if st.session_state.gpt_model == 'gpt-3.5-turbo-0125':
    st.warning('A low-cost AI will answer your question(s). Please check at least some of the answers.')

if st.session_state.gpt_model == "gpt-4-turbo":
    st.warning('An expensive AI will answer your question(s). Please be cautious.')

run_button = st.button('RUN the program')

keep_button = st.button('DOWNLOAD your form responses')

reset_button = st.button(label='RESET to start afresh', type = 'primary',  help = "Press to process new search terms or questions.")

if ((st.session_state.gpt_model == "gpt-4-turbo") and (uploaded_images)):

    st.markdown("""By default, this program will use an Optical Character Recognition (OCR) engine to extract text from images, and then send such text to GPT.

Alternatively, you can send images directly to GPT. This alternative approach may produce better responses for "untidy" images, but tends to be slower and costlier than the default approach.
""")
    
    #st.write('Not getting the best responses for your images? You can try a more costly')
    #b64_help_text = 'GPT will process images directly, instead of text first extracted from images by an Optical Character Recognition engine. This only works for PNG, JPEG, JPG, GIF images.'
    run_button_b64 = st.button(label = 'SEND images to GPT directly')

#test_button = st.button('Test')

#Display need resetting message if necessary
if 'need_resetting' in st.session_state:
#if st.session_state.need_resetting == 1:
    st.warning('You must :red[RESET] the program before processing new search terms or questions. Please press the :red[RESET] button above.')


# %% [markdown]
# ## Previous responses and outputs

# %%
#Create placeholder download buttons if previous responses and results in st.session_state:

if (('df_master' in st.session_state) and ('df_individual_output' in st.session_state)):

    #Load previous responses and results

    df_master = st.session_state.df_master
    df_individual_output = st.session_state.df_individual_output

    #Buttons for downloading responses

    st.subheader('Looking for your previous form responses?')

    responses_output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_responses'
    
    csv = convert_df_to_csv(df_master)

    ste.download_button(
        label="Download your previous responses as a CSV (for use in Excel etc)", 
        data = csv,
        file_name=responses_output_name + '.csv', 
        mime= "text/csv", 
#            key='download-csv'
    )

    xlsx = convert_df_to_excel(df_master)
    
    ste.download_button(label='Download your previous responses as an Excel spreadsheet (XLSX)',
                        data=xlsx,
                        file_name=responses_output_name + '.xlsx', 
                        mime='application/vnd.ms-excel',
                       )

    json = convert_df_to_json(df_master)
    
    ste.download_button(
        label="Download your previous responses as a JSON", 
        data = json,
        file_name= responses_output_name + '.json', 
        mime= "application/json", 
    )

    #Button for downloading results

    st.subheader('Looking for your previous results?')

    output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_results'

    csv_output = convert_df_to_csv(df_individual_output)

    ste.download_button(
        label="Download your previous results as a CSV (for use in Excel etc)", 
        data = csv_output,
        file_name= output_name + '.csv', 
        mime= "text/csv", 
#            key='download-csv'
    )

    excel_xlsx = convert_df_to_excel(df_individual_output)
    
    ste.download_button(label='Download your previous results as an Excel spreadsheet (XLSX)',
                        data=excel_xlsx,
                        file_name= output_name + '.xlsx', 
                        mime='application/vnd.ms-excel',
                       )
    
    json_output = convert_df_to_json(df_individual_output)
    
    ste.download_button(
        label="Download your previous results as a JSON", 
        data = json_output,
        file_name= output_name + '.json', 
        mime= "application/json", 
    )

    st.page_link('pages/AI.py', label="ANALYSE your spreadsheet with an AI", icon = '🤔')


# %% [markdown]
# # Save and run

# %%
#if test_button:
    #for uploaded_doc in uploaded_docs:
        #output = doc_to_text(uploaded_doc, language_entry, st.session_state.page_bound)
        #st.write(output)

#    for uploaded_image in uploaded_images:
#        output = image_to_text(uploaded_image, language_entry, st.session_state.page_bound)
#        st.write(output)

    #for uploaded_image in uploaded_images:
        #output = image_to_b64(uploaded_image, language_entry, st.session_state.page_bound)
        #st.write(output)


# %%
if run_button:

    if ((len(uploaded_docs) == 0) and (len(uploaded_images) == 0)):

        st.warning('You must upload some file(s).')

    elif len(gpt_questions_entry) < 5:

        st.warning('You must enter some question(s) for GPT.')


    elif int(consent) == 0:
        st.warning("You must click on 'Yes, I agree.' to run the program.")
    
    elif (('df_master' in st.session_state) and ('df_individual_output' in st.session_state)):
        st.warning('You must :red[RESET] the program before processing new files or questions. Please press the :red[RESET] button above.')
        
        if 'need_resetting' not in st.session_state:
            
            st.session_state['need_resetting'] = 1

    elif ((st.session_state.own_account == True) and (st.session_state.gpt_api_key_validity == False)):
            
        st.warning('You have not validated your API key.')
        quit()

    elif ((st.session_state.own_account == True) and (len(gpt_api_key_entry) < 20)):

        st.warning('You have not entered a valid API key.')
        quit()  
        
    else:

        st.markdown("""Your results will be available for download soon. The estimated waiting time is about 2-3 minutes per 10 files. """)

        with st.spinner('Running...'):
    
            #Using own GPT

            #Create spreadsheet of responses
            df_master = create_df()
        
            #GPT model
        
            #if df_master.loc[0, 'Use latest version of GPT'] == True:
                #gpt_model = "gpt-4-turbo"
            #else:        
                #gpt_model = "gpt-3.5-turbo-0125"
            
            #Activate user's own key or mine
            if st.session_state.own_account == True:
                
                API_key = df_master.loc[0, 'Your GPT API key']

            else:
                API_key = st.secrets["openai"]["gpt_api_key"]

            #
            
            df_individual_output = run(df_master, uploaded_docs, uploaded_images)

            #Keep results in session state
            if "df_individual_output" not in st.session_state:
                st.session_state["df_individual_output"] = df_individual_output
    
            if "df_master" not in st.session_state:
                st.session_state["df_master"] = df_master
            
            st.session_state["page_from"] = 'pages/OWN.py'
    
            #Write results
    
            st.success('Your results are now available for download. Thank you for using the Empirical Legal Research Kickstarter!')
    
            if df_master.loc[0, 'Language choice'] != 'English':
    
                st.warning("If your spreadsheet reader does not display non-English text properly, please change the encoding to UTF-8 Unicode.")
    
            #Button for downloading results
            output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_results'
    
            csv_output = convert_df_to_csv(df_individual_output)
            
            ste.download_button(
                label="Download your results as a CSV (for use in Excel etc)", 
                data = csv_output,
                file_name= output_name + '.csv', 
                mime= "text/csv", 
    #            key='download-csv'
            )
    
            excel_xlsx = convert_df_to_excel(df_individual_output)
            
            ste.download_button(label='Download your results as an Excel spreadsheet (XLSX)',
                                data=excel_xlsx,
                                file_name= output_name + '.xlsx', 
                                mime='application/vnd.ms-excel',
                               )
            
            json_output = convert_df_to_json(df_individual_output)
            
            ste.download_button(
                label="Download your results as a JSON", 
                data = json_output,
                file_name= output_name + '.json', 
                mime= "application/json", 
            )
    
            st.page_link('pages/AI.py', label="ANALYSE your spreadsheet with an AI", icon = '🤔')

            #Keep record on Google sheet
            #Obtain google spreadsheet       
            #conn = st.connection("gsheets_nsw", type=GSheetsConnection)
            #df_google = conn.read()
            #df_google = df_google.fillna('')
            #df_google=df_google[df_google["Processed"]!='']
            #df_master["Processed"] = datetime.now()
            #df_master.pop("Your GPT API key")
            #df_to_update = pd.concat([df_google, df_master])
            #conn.update(worksheet="OWN", data=df_to_update, )


# %%
if ((st.session_state.gpt_model == "gpt-4-turbo") and (uploaded_images)):
    
    if run_button_b64:
    
        if len(uploaded_images) == 0:
    
            st.warning('You must upload some image(s).')
    
        elif len(gpt_questions_entry) < 5:
    
            st.warning('You must enter some question(s) for GPT.')
    
        elif int(consent) == 0:
            st.warning("You must click on 'Yes, I agree.' to run the program.")
        
        elif (('df_master' in st.session_state) and ('df_individual_output' in st.session_state)):
            st.warning('You must :red[RESET] the program before processing new files or questions. Please press the :red[RESET] button above.')
            
            if 'need_resetting' not in st.session_state:
                
                st.session_state['need_resetting'] = 1
    
        elif ((st.session_state.own_account == True) and (st.session_state.gpt_api_key_validity == False)):
        
            #if (st.session_state.gpt_api_key_validity == False):
            
            st.warning('You have not validated your API key. Please do so.')
            #st.warning('You must :red[RESET] the program before processing new search terms or questions. Please press the :red[RESET] button above.')
            quit()
            
        else:
    
            st.markdown("""Your results will be available for download soon. The estimated waiting time is about 1-2 minutes per image. """)
    
            with st.spinner('Running...'):
        
                #Using own GPT
    
                #Create spreadsheet of responses
                df_master = create_df()

                #Check for non-supported file types

                if '.bmp' in str(df_master['Your uploaded files']).lower():
                    st.error('This function does not support BMP images.')
                    quit()
                    
                elif '.tiff' in str(df_master['Your uploaded files']).lower():
                    st.error('This function does not support TIFF images.')
                    quit()
                
                #Activate user's own key or mine
                if st.session_state.own_account == True:
                    
                    API_key = df_master.loc[0, 'Your GPT API key']
    
                else:
                    API_key = st.secrets["openai"]["gpt_api_key"]
    
                #
                
                df_individual_output = run_b64(df_master, uploaded_images)
    
                #Keep results in session state
                if "df_individual_output" not in st.session_state:
                    st.session_state["df_individual_output"] = df_individual_output
        
                if "df_master" not in st.session_state:
                    st.session_state["df_master"] = df_master
                
                st.session_state["page_from"] = 'pages/OWN.py'
        
                #Write results
        
                st.success('Your results are now available for download. Thank you for using the Empirical Legal Research Kickstarter!')
        
                if df_master.loc[0, 'Language choice'] != 'English':
        
                    st.warning("If your spreadsheet reader does not display non-English text properly, please change the encoding to UTF-8 Unicode.")
        
                #Button for downloading results
                output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_results'
        
                csv_output = convert_df_to_csv(df_individual_output)
                
                ste.download_button(
                    label="Download your results as a CSV (for use in Excel etc)", 
                    data = csv_output,
                    file_name= output_name + '.csv', 
                    mime= "text/csv", 
        #            key='download-csv'
                )
        
                excel_xlsx = convert_df_to_excel(df_individual_output)
                
                ste.download_button(label='Download your results as an Excel spreadsheet (XLSX)',
                                    data=excel_xlsx,
                                    file_name= output_name + '.xlsx', 
                                    mime='application/vnd.ms-excel',
                                   )
                
                json_output = convert_df_to_json(df_individual_output)
                
                ste.download_button(
                    label="Download your results as a JSON", 
                    data = json_output,
                    file_name= output_name + '.json', 
                    mime= "application/json", 
                )
        
                st.page_link('pages/AI.py', label="ANALYSE your spreadsheet with an AI", icon = '🤔')
    
                #Keep record on Google sheet
                #Obtain google spreadsheet       
                #conn = st.connection("gsheets_nsw", type=GSheetsConnection)
                #df_google = conn.read()
                #df_google = df_google.fillna('')
                #df_google=df_google[df_google["Processed"]!='']
                #df_master["Processed"] = datetime.now()
                #df_master.pop("Your GPT API key")
                #df_to_update = pd.concat([df_google, df_master])
                #conn.update(worksheet="OWN", data=df_to_update, )
                


# %%
if keep_button:

    if ((len(uploaded_docs) == 0) and (len(uploaded_images) == 0)):

        st.warning('You must upload some file(s).')

    elif len(gpt_questions_entry) < 5:

        st.warning('You must enter some question(s) for GPT.')

    elif (('df_master' in st.session_state) and ('df_individual_output' in st.session_state)):
        st.warning('You must :red[RESET] the program before processing new files or questions. Please press the :red[RESET] button above.')
        
        if 'need_resetting' not in st.session_state:
            
            st.session_state['need_resetting'] = 1
            
    else:
        
        df_master = create_df()
    
        df_master.pop("Your GPT API key")
    
        df_master.pop("Processed")
    
        responses_output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_responses'
    
        #Produce a file to download
    
        csv = convert_df_to_csv(df_master)
        
        ste.download_button(
            label="Download as a CSV (for use in Excel etc)", 
            data = csv,
            file_name=responses_output_name + '.csv', 
            mime= "text/csv", 
    #            key='download-csv'
        )

        xlsx = convert_df_to_excel(df_master)
        
        ste.download_button(label='Download as an Excel spreadsheet (XLSX)',
                            data=xlsx,
                            file_name=responses_output_name + '.xlsx', 
                            mime='application/vnd.ms-excel',
                           )
    
        json = convert_df_to_json(df_master)
        
        ste.download_button(
            label="Download as a JSON", 
            data = json,
            file_name= responses_output_name + '.json', 
            mime= "application/json", 
        )


# %%
if return_button:

    st.switch_page("Home.py")

# %%
if reset_button:
    clear_cache_except_validation_df_master()
    st.rerun()
