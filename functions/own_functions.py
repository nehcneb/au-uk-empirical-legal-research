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
from datetime import timedelta
import sys
import pause
import os
import io
import math
from math import ceil

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
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste
from streamlit_extras.stylable_container import stylable_container

#OpenAI
import openai
import tiktoken

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb


# %%
#Import functions
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, str_to_int, str_to_int_page, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, default_judgment_counter_bound, default_page_bound, truncation_note


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

@st.cache_data(show_spinner = False)
def doc_to_text(uploaded_doc, language, page_bound):
    file_triple = {'File name' : '', 'Language choice': language, 'Page length': '', 'Extracted text': ''}

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
    
            file_triple['Page length'] = 1
            
        else:
            #text formats
            if extension in ['txt', 'cs', 'xml', 'html', 'json']:
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
    except Exception as e:
        print(f"{file_triple['File name']}: failed to get text")
        print(e)
    
    return file_triple


# %%
#Function for images to text

@st.cache_data(show_spinner = False)
def image_to_text(uploaded_image, language, page_bound):
    file_triple = {'File name' : '', 'Language choice': language, 'Page length': '', 'Extracted text': ''}

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
    
        file_triple['Extracted text'] = str(text_list)
    
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
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string  
#Import variables
from functions.gpt_functions import question_characters_bound


# %%
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
role_content_own = 'You are a legal research assistant helping an academic researcher to answer questions about a file. The file may be a document or an image. You will be provided with the file. Please answer questions based only on information contained in the file. Where your answer comes from a part of the file, include a reference to that part of the file. If you cannot answer the questions based on the file, do not make up information, but instead write "answer not found".'

system_instruction = role_content_own

intro_for_GPT = [{"role": "system", "content": system_instruction}]


# %%
#Define GPT answer function for answers in json form, YES TOKENS
#IN USE

@st.cache_data(show_spinner = False)
def GPT_json_own(questions_json, df_example, file_triple, gpt_model, system_instruction):
    #'question_json' variable is a json of questions to GPT

    file_for_GPT = [{"role": "user", "content": file_prompt(file_triple, gpt_model)}]

    json_direction = [{"role": "user", "content": 'You will be given questions to answer in JSON form.'}]

    #Create answer format
    answers_json = {}

    #st.write(f"df_example == {df_example}")
    
    #st.write(f"len(df_example) == {len(df_example)}")

    if len(df_example.replace('"', '')) > 0:

        #st.write(f"df_example == {df_example}")

        #st.write(type(df_example))

        try:
            
            if isinstance(df_example, str):
                
                answers_json = json.loads(df_example)

            if isinstance(df_example, dict):
                
                answers_json = df_example

        except Exception as e:
            print(f"Example provided but can't produce json to send to GPT.")
            print(e)
    
    #st.write(f"answers_json == {answers_json}")

    #Check if answers format succesfully created by following any example uploaded
    q_keys = [*questions_json]
    
    if len(answers_json) == 0:
        q_counter = 1
        for q_index in q_keys:
            answers_json.update({f'GPT question {q_counter}: {questions_json[q_index]}': f'Your answer. (The paragraphs, pages or sections from which you obtained your answer)'})
            q_counter += 1

    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": json.dumps(questions_json) + ' \n Respond in the following JSON form: ' + json.dumps(answers_json)}]
    
    #Create messages in one prompt for GPT
    language_content = f"The file is written in {file_triple['Language choice']}."

    intro_for_GPT = [{"role": "system", "content": system_instruction + language_content}] 

    messages_for_GPT = intro_for_GPT + file_for_GPT + json_direction + question_for_GPT
    
#   return messages_for_GPT

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model=gpt_model,
            messages=messages_for_GPT, 
            response_format={"type": "json_object"}, 
            max_tokens = max_output(gpt_model, messages_for_GPT), 
            temperature = 0.1, 
            #top_p = 0.1
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        answers_dict = json.loads(completion.choices[0].message.content)
        
        #Obtain tokens
        output_tokens = completion.usage.completion_tokens
        
        prompt_tokens = completion.usage.prompt_tokens
        
        return [answers_dict, output_tokens, prompt_tokens]

    except Exception as error:
        
        print('GPT failed to produce answers.')
        
        for q_index in q_keys:
            
            answers_json.update({q_index: error})
        
        return [answers_json, 0, 0]



# %%
#Define GPT function for each respondent's dataframe, index by file then question, with input and output tokens given by GPT itself
#IN USE

#The following function DOES NOT check for existence of questions for GPT
    # To so check, active line marked as #*

@st.cache_data(show_spinner = False)
def engage_GPT_json_own(questions_json, df_example, df_individual, GPT_activation, gpt_model, system_instruction):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # f"Length of first 10 pages in tokens (up to {tokens_cap(gpt_model)} given to GPT)"
        # 'GPT cost estimate (USD excl GST)'
        # 'GPT time estimate (seconds)'
        # GPT questions/answers

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()
    
    for file_index in df_individual.index:
        
        file_triple = df_individual.to_dict('index')[file_index]

        #Check wither error in getting the full text
        text_error = False
        if 'Extracted text' in file_triple.keys():
            if len(file_triple['Extracted text']) == 0:
                text_error = True
                df_individual.loc[file_index, 'Note'] = search_error_note
                print(f"File indexed {file_index} not sent to GPT given full text was not scrapped.")
        
        #Calculate and append number of tokens of file, regardless of whether given to GPT
        file_tokens = num_tokens_from_string(str(file_triple), "cl100k_base")
        df_individual.loc[file_index, f"Length of first {st.session_state['df_master'].loc[0,'Maximum number of pages per file']} pages in tokens (up to {tokens_cap(gpt_model)} given to GPT)"] = file_tokens       

        #Indicate whether file truncated
        if file_tokens > tokens_cap(gpt_model):
            df_individual.loc[file_index, 'Note'] = truncation_note

        #Create columns for respondent's GPT cost, time
        df_individual.loc[file_index, 'GPT cost estimate (USD excl GST)'] = ''
        df_individual.loc[file_index, 'GPT time estimate (seconds)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each file, gives answers as a string containing a dictionary

        if ((int(GPT_activation) > 0) and (text_error == False)):
            GPT_file_triple = GPT_json_own(questions_json, df_example, file_triple, gpt_model, system_instruction) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_file_triple[0]

            #Calculate and append GPT finish time and time difference to individual df
            GPT_finish_time = datetime.now()
            
            GPT_time_difference = GPT_finish_time - GPT_start_time
    
            df_individual.loc[file_index, 'GPT time estimate (seconds)'] = GPT_time_difference.total_seconds()

        else:
            answers_dict = {}    
            
            question_keys = [*questions_json]

            for q_index in question_keys:
                #Increases file index by 2 to ensure consistency with Excel spreadsheet
                answer = ''
                answers_dict.update({questions_json[q_index]: answer})
            
            #Own calculation of GPT costs for mock answers

            #Calculate capped file tokens

            file_capped_tokens = num_tokens_from_string(file_prompt(file_triple, gpt_model), "cl100k_base")

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(json.dumps(questions_json), "cl100k_base")

            #Calculate other instructions' tokens

            other_instructions = system_instruction + 'The file is written in some language' + 'you will be given questions to answer in JSON form.' + ' \n Respond in the following JSON form: '

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. State specific page numbers or sections of the file.", "cl100k_base")

            #Calculate number of tokens of answers
            answers_output_tokens = num_tokens_from_string(str(answers_dict), "cl100k_base")

            answers_input_tokens = file_capped_tokens + questions_tokens + other_tokens
            
            GPT_file_triple = [answers_dict, answers_output_tokens, answers_input_tokens]

        #Create GPT question headings and append answers to individual spreadsheets
        for answer_index in answers_dict.keys():

            #Check any errors
            answer_string = str(answers_dict[answer_index]).lower()
            
            if ((answer_string.startswith('your answer.')) or (answer_string.startswith('your response.'))):
                
                answers_dict[answer_index] = 'Error. Please try a different question or GPT model.'

            #Append answer to spreadsheet

            answer_header = answer_index

            try:
            
                df_individual.loc[file_index, answer_header] = answers_dict[answer_index]

            except:

                df_individual.loc[file_index, answer_header] = str(answers_dict[answer_index])
            
        #Calculate GPT costs

        GPT_cost = GPT_file_triple[1]*gpt_output_cost(gpt_model) + GPT_file_triple[2]*gpt_input_cost(gpt_model)

        #Calculate and append GPT cost to individual df
        df_individual.loc[file_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual



# %%
#Obtain parameters

@st.cache_data(show_spinner = False)
def run_own(df_master, uploaded_docs, uploaded_images):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
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

    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o-2024-08-06"
    else:        
        gpt_model = "gpt-4o-mini"
        
    #apply GPT_individual to each respondent's file spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
        
    #Engage GPT    
    df_updated = engage_GPT_json_own(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    if 'Extracted text' in df_updated.columns:
        df_updated.pop('Extracted text')
    
    return df_updated
    


# %% [markdown]
# # For vision, own file only

# %%
#Import functions
from functions.gpt_functions import get_image_dims, calculate_image_token_cost


# %%
@st.cache_data(show_spinner = False)
def image_to_b64_own(uploaded_image, language, page_bound):
    file_triple = {'File name' : '', 'Language choice': language, 'b64_list': [], 'Dimensions (width, height)' : [],
                   'Page length': '', 'tokens_raw': 0
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
    
            file_triple['Page length'] = 1
        
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
#Define GPT answer function for answers in json form, YES TOKENS
#For gpt-4o vision

@st.cache_data(show_spinner = False)
def GPT_b64_json_own(questions_json, df_example, file_triple, gpt_model, system_instruction):
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
    answers_json = {}

    #st.write(f"df_example == {df_example}")
    
    #st.write(f"len(df_example) == {len(df_example)}")

    if len(df_example.replace('"', '')) > 0:

        #st.write(f"df_example == {df_example}")

        #st.write(type(df_example))

        try:
            
            if isinstance(df_example, str):
                
                answers_json = json.loads(df_example)

            if isinstance(df_example, dict):
                
                answers_json = df_example

        except Exception as e:
            print(f"Example provided but can't produce json to send to GPT.")
            print(e)
    
    #st.write(f"answers_json == {answers_json}")

    #Check if answers format succesfully created by following any example uploaded
    q_keys = [*questions_json]
    
    if len(answers_json) == 0:
        q_counter = 1
        for q_index in q_keys:
            answers_json.update({f'GPT question {q_counter}: {questions_json[q_index]}': f'Your answer. (The paragraphs, pages or sections from which you obtained your answer)'})
            q_counter += 1

    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": json.dumps(questions_json) + ' \n Respond in the following JSON form: ' + json.dumps(answers_json)}]
    
    #Create messages in one prompt for GPT
    language_content = f"The file is written in {file_triple['Language choice']}."

    intro_for_GPT = [{"role": "system", "content": system_instruction + language_content}] 

    messages_for_GPT = intro_for_GPT + file_for_GPT + question_for_GPT
    
#   return messages_for_GPT

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model=gpt_model,
            messages=messages_for_GPT, 
            response_format={"type": "json_object"}, 
            temperature = 0.1, 
            #top_p = 0.1
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        answers_dict = json.loads(completion.choices[0].message.content)
        
        #Obtain tokens
        output_tokens = completion.usage.completion_tokens
        
        prompt_tokens = completion.usage.prompt_tokens
        
        return [answers_dict, output_tokens, prompt_tokens]

    except Exception as error:
        
        print('GPT failed to produce answers.')
        
        for q_index in q_keys:
            
            answers_json.update({q_index: error})
        
        return [answers_json, 0, 0]



# %%
#Define GPT function for each respondent's dataframe, index by file then question, with input and output tokens given by GPT itself
#For gpt-4o vision

#The following function DOES NOT check for existence of questions for GPT
    # To so check, active line marked as #*

@st.cache_data(show_spinner = False)
def engage_GPT_b64_json_own(questions_json, df_example, df_individual, GPT_activation, gpt_model, system_instruction):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # f"Length of first 10 pages in tokens (up to {tokens_cap(gpt_model)} given to GPT)"
        # 'GPT cost estimate (USD excl GST)'
        # 'GPT time estimate (seconds)'
        # GPT questions/answers

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()
        
    for file_index in df_individual.index:
        
        file_triple = df_individual.to_dict('index')[file_index]

        #Check wither error in getting the full text
        text_error = False
        if 'Extracted text' in file_triple.keys():
            if len(file_triple['Extracted text']) == 0:
                text_error = True
                df_individual.loc[file_index, 'Note'] = search_error_note
                print(f"File indexed {file_index} not sent to GPT given full text was not scrapped.")
        
        #Calculate and append number of tokens of file, regardless of whether given to GPT
        df_individual.loc[file_index, f"Tokens (up to {tokens_cap(gpt_model)} given to GPT)"] = file_triple['tokens_raw']

        #Create columns for respondent's GPT cost, time
        df_individual.loc[file_index, 'GPT cost estimate (USD excl GST)'] = ''
        df_individual.loc[file_index, 'GPT time estimate (seconds)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each file, gives answers as a string containing a dictionary

        if ((int(GPT_activation) > 0) and (text_error == False)):
            GPT_file_triple = GPT_b64_json_own(questions_json, df_example, file_triple, gpt_model, system_instruction) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_file_triple[0]

            #Calculate and append GPT finish time and time difference to individual df
            GPT_finish_time = datetime.now()
            
            GPT_time_difference = GPT_finish_time - GPT_start_time
    
            df_individual.loc[file_index, 'GPT time estimate (seconds)'] = GPT_time_difference.total_seconds()
        
        else:
            answers_dict = {}    
            
            question_keys = [*questions_json]

            for q_index in question_keys:
                #Increases file index by 2 to ensure consistency with Excel spreadsheet
                answer = ''
                answers_dict.update({questions_json[q_index]: answer})
            
            #Calculate capped file tokens

            file_capped_tokens = min(file_triple['tokens_raw'], tokens_cap(gpt_model))

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(json.dumps(questions_json), "cl100k_base")

            #Calculate other instructions' tokens

            other_instructions = system_instruction + 'The file is written in some language' + 'you will be given questions to answer in JSON form.' + ' \n Respond in the following JSON form: '

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. State specific page numbers or sections of the file.", "cl100k_base")

            #Calculate number of tokens of answers
            answers_output_tokens = num_tokens_from_string(str(answers_dict), "cl100k_base")

            answers_input_tokens = file_capped_tokens + questions_tokens + other_tokens
            
            GPT_file_triple = [answers_dict, answers_output_tokens, answers_input_tokens]

        #Create GPT question headings and append answers to individual spreadsheets
        for answer_index in answers_dict.keys():

            #Check any errors
            answer_string = str(answers_dict[answer_index]).lower()
            
            if ((answer_string.startswith('your answer.')) or (answer_string.startswith('your response.'))):
                
                answers_dict[answer_index] = 'Error. Please try a different question or GPT model.'

            #Append answer to spreadsheet

            answer_header = answer_index

            try:
            
                df_individual.loc[file_index, answer_header] = answers_dict[answer_index]

            except:

                df_individual.loc[file_index, answer_header] = str(answers_dict[answer_index])
                
        #Calculate GPT costs

        GPT_cost = GPT_file_triple[1]*gpt_output_cost(gpt_model) + GPT_file_triple[2]*gpt_input_cost(gpt_model)

        #Calculate and append GPT cost to individual df
        df_individual.loc[file_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual



# %%
#For gpt-4o vision

@st.cache_data(show_spinner = False)
def run_b64_own(df_master, uploaded_images):

    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
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

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o-2024-08-06"
    else:        
        gpt_model = "gpt-4o-mini"
        
    #apply GPT_individual to each respondent's judgment spreadsheet

    questions_json = df_master.loc[0, 'questions_json']

    #apply GPT_individual to each respondent's file spreadsheet    
    df_updated = engage_GPT_b64_json_own(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, system_instruction = system_instruction)

    #Remove redundant columns

    for column in ['tokens_raw', 'b64_list']:
        try:
            df_updated.pop(column)
        except:
            print(f"No {column} column.")

    return df_updated


