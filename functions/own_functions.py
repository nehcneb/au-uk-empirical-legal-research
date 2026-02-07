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
#from dateutil.relativedelta import *
from datetime import timedelta
import sys
import pause
import os
import io
import math
from math import ceil
import traceback

#Conversion to text
import pymupdf
#import pymupdf4llm
from io import StringIO
from io import BytesIO
import pdf2image
from PIL import Image
import pytesseract
import mammoth

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
#import streamlit_ext as ste
from streamlit_extras.stylable_container import stylable_container

#OpenAI
import openai
import tiktoken

#aws
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb


# %%
#Import functions
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, str_to_int, str_to_int_page, save_input, send_notification_email, get_aws_s3, aws_df_get, aws_df_put
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, default_judgment_counter_bound, default_page_bound, truncation_note, spinner_text, search_error_display


# %%
#Page bound

default_page_bound = 100

print(f"\nThe maximum number of pages per file is {default_page_bound}.")

#if 'page_bound' not in st.session_state:
    #st.session_state['page_bound'] = default_page_bound

#Default file counter bound

default_file_counter_bound = default_judgment_counter_bound

#if 'file_counter_bound' not in st.session_state:
    #st.session_state['file_counter_bound'] = default_file_counter_bound

print(f"The default number of files to scrape per request is capped at {default_file_counter_bound}.\n")

# %% [markdown]
# # Functions for Own Files

# %%
file_error_note = 'This app was unable to scrape text from this file. This file was not sent to GPT.'

# %%
#File types and languages for processing
doc_types = ["pdf", "txt", 'docx', "xps", "epub", "mobi", 'cs', 'xml', 'html', 'json'] #"fb2", "cbz", "svg",
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
# Function to convert each uploaded file to file name, text

#@st.cache_data(show_spinner = False)
def doc_to_text(uploaded_doc, language, page_bound):
    file_triple = {'File name' : '', 'Language choice': language, 'Page length': '', 'extracted_text': ''} #

    try:
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
    
            #file_triple['Page length'] = 1

            file_triple['extracted_text'] = str(text_list)
            
        else:
             
            #pdf formats #If want to enable pymupdf4llm. Not useful in my experience.
            #if extension == 'pdf':
                #doc = pymupdf.open(stream=bytes_data)

                #max_doc_number=min(len(doc), page_bound)

                #md_text = pymupdf4llm.to_markdown(doc = doc, pages = range(0, max_doc_number), embed_images = True) #Add embed_images = True if want to include images
                
                #file_triple['extracted_text'] = str(md_text)

            #Other formats
            #else:
                
            #text formats
            if extension in ['txt', 'cs', 'xml', 'html', 'json']:
                doc = pymupdf.open(stream=bytes_data, filetype="txt")
    
            #Other formats
            else:
                doc = pymupdf.open(stream=bytes_data)
    
            max_doc_number=min(len(doc), page_bound)
            
            for page_index in list(range(0, max_doc_number)):
                page = doc.load_page(page_index)
                text_page = page.get_text() 
                text_list.append(text_page)
    
            file_triple['extracted_text'] = str(text_list)

            #Length of pages
            file_triple['Page length'] = len(doc)
        
    except Exception as e:
        print(f"{file_triple['File name']}: failed to get text")
        print(e)
    
    return file_triple


# %%
#Function for images to text

#@st.cache_data(show_spinner = False)
def image_to_text(uploaded_image, language, page_bound):
    file_triple = {'File name' : '', 'Language choice': language, 'Page length': '', 'extracted_text': ''}

    try:
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
    
        file_triple['extracted_text'] = str(text_list)
    
        #Length of pages
        file_triple['Page length'] = len(images)
    
    except Exception as e:
        print(f"{file_triple['File name']}: failed to get text")
        print(e)
        
    return file_triple


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, gpt_batch_input, engage_GPT_json, GPT_questions_check
#Import variables
from functions.gpt_functions import questions_check_system_instruction, basic_model#, flagship_model


# %%
#Define system role content for GPT
role_content_own = """You are a legal research assistant helping an academic researcher to answer questions about a file. The file may be a document or an image. You will be provided with the file. 
Please answer questions based only on information contained in the file. Where your answer comes from a part of the file, include a reference to that part of the file. 
If you cannot answer the questions based on the file, do not make up information, but instead write "answer not found"."""

#Respond in JSON form. In your response, produce as many keys as you need. 

#system_instruction = role_content_own

#intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#Obtain GPT output

@st.cache_data(show_spinner = False, ttl=300)
def run_own(df_master, uploaded_docs, uploaded_images):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
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
    
    #Create and export json file with search output
    json_individual = json.dumps(Files_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #GPT model

    #if df_master.loc[0, 'Use flagship version of GPT'] == True:
        #gpt_model = flagship_model
    #else:        
        #gpt_model = basic_model

    gpt_model = df_master.loc[0, 'gpt_model']

    temperature = df_master.loc[0, 'temperature']

    reasoning_effort = df_master.loc[0, 'reasoning_effort']
        
    #apply GPT_individual to each respondent's file spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Engage GPT    
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)

    if (pop_judgment() > 0) and ('extracted_text' in df_updated.columns):
        df_updated.pop('extracted_text')
    
    return df_updated



# %% [markdown]
# # For vision

# %%
#Import functions
from functions.gpt_functions import get_image_dims, calculate_image_token_cost, GPT_b64_json, engage_GPT_b64_json


# %%
#@st.cache_data(show_spinner = False)
def image_to_b64_own(uploaded_image, language, page_bound):
    file_triple = {'File name' : '', 'Language choice': language, 'b64_list': [], 'Dimensions (width, height)' : [],
                   'Page length': '', 
                   'tokens_raw': 0
                  }

    try:
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

        else:
    
            #file_triple['Page length'] = 1
        
            b64 = base64.b64encode(bytes_data).decode('utf-8')
        
            b64_to_attach = f"data:image/{extension};base64,{b64}"
            
            file_triple['b64_list'].append(b64_to_attach)
            
        for image_b64 in file_triple['b64_list']:
    
            #Get dimensions
            try:
    
                file_triple['Dimensions (width, height)'].append(get_image_dims(b64_to_attach))
            except Exception as e:
                print(f"Cannot obtain dimensions for {file_triple['File name']}, p {file_triple['b64_list'].index(image_b64)}.")
                print(e)
            
            file_triple['tokens_raw'] = file_triple['tokens_raw'] + calculate_image_token_cost(image_b64, detail="auto")
    except Exception as e:
        print(f"{file_triple['File name']}: failed to get text")
        print(e)
        
    return file_triple


# %%
#For vision

@st.cache_data(show_spinner = False, ttl=300)
def batch_b64_own(df_master, uploaded_images):

    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)

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
            file_triple = image_to_b64_own(uploaded_image, language, page_bound)
            Files_file.append(file_triple)
            file_counter += 1

    #Create and export json file with search output
    json_individual = json.dumps(Files_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #Instruct GPT

    GPT_activation = int(df_master.loc[0, 'Use GPT'])
    
    #GPT model

    #if df_master.loc[0, 'Use flagship version of GPT'] == True:
        #gpt_model = flagship_model
    #else:        
        #gpt_model = basic_model

    gpt_model = df_master.loc[0, 'gpt_model']

    temperature = df_master.loc[0, 'temperature']

    reasoning_effort = df_master.loc[0, 'reasoning_effort']
        
    #apply GPT_individual to each respondent's judgment spreadsheet

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #apply GPT_individual to each respondent's file spreadsheet    
    df_updated = engage_GPT_b64_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)
    
    #Remove redundant columns

    for column in ['tokens_raw', 'b64_list']:
        try:
            df_updated.pop(column)
        except:
            print(f"No {column} column.")

    return df_updated



# %%
#For vision

@st.cache_data(show_spinner = False, ttl=300)
def run_b64_own(df_master, uploaded_images):

    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)

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
            file_triple = image_to_b64_own(uploaded_image, language, page_bound)
            Files_file.append(file_triple)
            file_counter += 1

    #Create and export json file with search output
    json_individual = json.dumps(Files_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #Instruct GPT
    #GPT model

    #if df_master.loc[0, 'Use flagship version of GPT'] == True:
        #gpt_model = flagship_model
    #else:        
        #gpt_model = basic_model

    gpt_model = df_master.loc[0, 'gpt_model']

    temperature = df_master.loc[0, 'temperature']

    reasoning_effort = df_master.loc[0, 'reasoning_effort']
        
    #apply GPT_individual to each respondent's file spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']

    #apply GPT_individual to each respondent's file spreadsheet    
    df_updated = engage_GPT_b64_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)
    
    #Remove redundant columns

    for column in ['tokens_raw', 'b64_list']:
        try:
            df_updated.pop(column)
        except:
            print(f"No {column} column.")

    return df_updated


# %% [markdown]
# # Batch request

# %%
#Batch get GPT output

@st.cache_data(show_spinner = False, ttl=300)
def batch_own(df_master, uploaded_docs, uploaded_images):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create files file
    Files_file = []

    #Obtain bounds and language

    file_counter_bound = int(df_master.loc[0, 'Maximum number of files'])

    page_bound = int(df_master.loc[0,'Maximum number of pages per file'])

    #st.write(f"file_counter_bound == {file_counter_bound}, page_bound == {page_bound}")
    
    language = df_master.loc[0, 'Language choice']
    
    #Convert uploaded documents to text

    file_counter = 1

    #Decide whether to do b64
    if bool(df_master.loc[0, 'b64_enabled']) == False:
        
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

    else: #bool(df_master.loc[0, 'b64']) == True:
    
        #Convert images to b64, then send to GPT
        for uploaded_image in uploaded_images:
            if file_counter <= file_counter_bound:
                file_triple = image_to_b64_own(uploaded_image, language, page_bound)
                Files_file.append(file_triple)
                file_counter += 1
    
    #Create and export json file with search output
    json_individual = json.dumps(Files_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

    #GPT model

    #if df_master.loc[0, 'Use flagship version of GPT'] == True:
        #gpt_model = flagship_model
    #else:        
        #gpt_model = basic_model

    gpt_model = df_master.loc[0, 'gpt_model']

    temperature = df_master.loc[0, 'temperature']

    reasoning_effort = df_master.loc[0, 'reasoning_effort']
        
    #apply GPT_individual to each respondent's file spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
        
    #Engage GPT
    batch_record_df_individual = gpt_batch_input(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)

    #Remove before text before saving to aws
    if (pop_judgment() > 0) and ('extracted_text' in df_individual.columns):
        df_individual.pop('extracted_text')

    return batch_record_df_individual
    


# %%
#Batch function

@st.dialog("Requesting data")
def own_batch_request_function(df_master, uploaded_docs, uploaded_images):
     
    if ((st.session_state['df_master'].loc[0, 'Use own account'] == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                            
        if is_api_key_valid(st.session_state.df_master.loc[0, 'Your GPT API key']) == False:
            st.error('Your API key is not valid.')
            
            st.session_state["batch_ready_for_submission"] = False

            st.stop()

        else:
            
            st.session_state["batch_ready_for_submission"] = True
    else:
        st.session_state["batch_ready_for_submission"] = True

    
    #Check if valid email address entered
    if '@' not in st.session_state['df_master'].loc[0, 'Your email address']:
        
        st.session_state["batch_ready_for_submission"] = False

        st.write('Please enter a valid email address to receive your request data.')
        
        batch_email_entry = st.text_input(label = "Your email address (mandatory)", value =  st.session_state['df_master'].loc[0, 'Your email address'])

        if st.button(label = 'CONFIRM your email address', disabled = bool(st.session_state.batch_submitted)):
            
            st.session_state['df_master'].loc[0, 'Your email address'] = batch_email_entry

            if '@' not in st.session_state['df_master'].loc[0, 'Your email address']:
            
                st.error('You must enter a valid email address to receive your request data.')
                st.stop()
            else:
                st.session_state["batch_ready_for_submission"] = True

    if st.session_state["batch_ready_for_submission"] == True:
    
        with st.spinner(spinner_text):
            
            try:

                #Update df_master
                jurisdiction_page = st.session_state.jurisdiction_page

                df_master['jurisdiction_page'] = jurisdiction_page
                
                df_master['submission_time'] = str(datetime.now())

                #Activate user's own key or mine
                if st.session_state['df_master'].loc[0, 'Use own account'] == True:
                    
                    API_key = st.session_state.df_master.loc[0, 'Your GPT API key']
    
                else:
                    
                    #API_key = st.secrets["openai"]["gpt_api_key"]
                    
                    from functions.common_functions import API_key
                    
                    #Must keep the following to ensure that if not using own account, then judgment_counter_max is applied
                    st.session_state['df_master'].loc[0, 'Maximum number of files'] = st.session_state["judgment_counter_max"]

                #Check questions for potential privacy violation
                openai.api_key = API_key

                #if df_master.loc[0, 'Use flagship version of GPT'] == True:
                    #gpt_model = flagship_model
                #else:        
                    #gpt_model = basic_model

                gpt_model = df_master.loc[0, 'gpt_model']
                
                questions_checked_dict = GPT_questions_check(df_master.loc[0, 'Enter your questions for GPT'], gpt_model, questions_check_system_instruction)

                #Use checked questions
                df_master.loc[0, 'Enter your questions for GPT'] = questions_checked_dict['questions_string']
                
                #Get batch_record, df_individual as a list
                batch_record_df_individual = batch_own(df_master, uploaded_docs, uploaded_images)

                #print(f"batch_record_df_individual == {batch_record_df_individual}")
                
                df_individual = batch_record_df_individual['df_individual']
                
                batch_dict = batch_record_df_individual['batch_record'].to_dict()
                
                batch_id = batch_dict['id']
                input_file_id = batch_dict['input_file_id']
                status = batch_dict['status']
        
                #Add batch_record to df_master
                df_master['batch_id'] = batch_id
                df_master['input_file_id'] = input_file_id
                df_master['status'] = status

                #print(f"df_master == {df_master}")
                
                #Initiate aws s3
                s3_resource = get_aws_s3()
                #Get a list of all files on s3
                #bucket = s3_resource.Bucket('lawtodata')

                #Upload df_individual onto AWS
                aws_df_put(s3_resource, df_individual, f'{batch_id}.csv')

                #csv_buffer = StringIO()
                #df_individual.to_csv(csv_buffer)
                #s3_resource.Object('lawtodata', f'{batch_id}.csv').put(Body=csv_buffer.getvalue())
                                    
                #Get all_df_masters

                all_df_masters = aws_df_get(s3_resource, 'all_df_masters.csv')
                
                #for obj in bucket.objects.all():
                    #key = obj.key
                    #if key == 'all_df_masters.csv':
                        #body = obj.get()['Body'].read()
                        #all_df_masters = pd.read_csv(BytesIO(body), index_col=0)
                        #break

                #st.write(df_master)
                
                #Add df_master to all_df_masters 
                all_df_masters = pd.concat([all_df_masters, df_master], ignore_index=True)

                #Upload all_df_masters to aws
                aws_df_put(s3_resource, all_df_masters, 'all_df_masters.csv')
                
                #csv_buffer = StringIO()
                #all_df_masters.to_csv(csv_buffer)
                #s3_resource = boto3.resource('s3',region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"], aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"])
                #s3_resource.Object('lawtodata', 'all_df_masters.csv').put(Body=csv_buffer.getvalue())
                
                #Send me an email to let me know
                send_notification_email(ULTIMATE_RECIPIENT_NAME = st.session_state['df_master'].loc[0, 'Your name'], 
                                        ULTIMATE_RECIPIENT_EMAIL = st.session_state['df_master'].loc[0, 'Your email address'], 
                                        jurisdiction_page = st.session_state['df_master'].loc[0, 'jurisdiction_page']
                                       )

                #Change session states
                st.session_state['df_master'].loc[0, 'Maximum number of files'] = default_judgment_counter_bound                    
                st.session_state["batch_submitted"] = True
                st.session_state["batch_error"] == False
                st.session_state['error_msg'] = ''
                
                st.rerun()
            
            except Exception as e:

                #Change session states
                st.session_state['df_master'].loc[0, 'Maximum number of files'] = default_judgment_counter_bound                    
                st.session_state["batch_submitted"] = False
                st.session_state["batch_error"] = True

                st.error(search_error_display)
                                
                print(traceback.format_exc())

                st.session_state['error_msg'] = traceback.format_exc()

                st.rerun()


