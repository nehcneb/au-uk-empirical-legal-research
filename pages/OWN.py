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
#import fitz
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

#aws
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

#OpenAI
import openai
import tiktoken

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb



# %%
#Title of webpage
st.set_page_config(
   page_title="LawtoData: An Empirical Legal Research Automator",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Import functions
from functions.common_functions import own_account_allowed, batch_mode_allowed, immediate_b64, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, str_to_int, str_to_int_page, save_input, download_buttons, uploaded_file_to_df, send_notification_email, report_error_email

#Import variables
from functions.common_functions import judgment_batch_cutoff, judgment_batch_max, today_in_nums, errors_list, scraper_pause_mean, default_judgment_counter_bound, default_page_bound, own_gpt_headings, check_questions_answers, gpt_cost_msg

default_file_counter_bound = default_judgment_counter_bound

# %% [markdown]
# # Functions for Own Files

# %%
from functions.own_functions import doc_types, image_types, languages_dict, languages_list, doc_to_text, image_to_text, role_content_own, run_own, own_batch_request_function


# %%
#function to create dataframe
#@st.cache_data
def own_create_df():

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
    except:
        print('API key not entered')

    #Own account status
    try:
        own_account = own_account_entry
    except:
        own_account = False
        print('Own account not selected')
    
    #file counter bound
    #file_counter_bound = st.session_state['df_master'].loc[0, 'Maximum number of files']
    try:
        file_counter_bound = file_counter_bound_entry
    except:
        print('File counter bound not entered')
        file_counter_bound = default_file_counter_bound

    #Page counter bound
    #page_bound = st.session_state['df_master'].loc[0,'Maximum number of pages per file']
    try:
        page_bound = page_bound_entry
    except:
        print('Page bound not entered')
        page_bound = default_page_bound
    
    #GPT enhancement
    try:
        gpt_enhancement = gpt_enhancement_entry
    except:
        print('GPT enhancement not entered')
        gpt_enhancement = False

    if gpt_enhancement:
        st.session_state.gpt_model = flagship_model
    else:
        st.session_state.gpt_model = basic_model
        
    #GPT choice and entry
    try:
        gpt_activation_status = gpt_activation_entry
    except:
        gpt_activation_status = False

    gpt_questions = ''
    
    try:
        gpt_questions = gpt_questions_entry
    
    except:
        print('GPT questions not entered.')

    #Get uploaded file names

    file_names_list = []

    for uploaded_doc in uploaded_docs:
        file_names_list.append(uploaded_doc.name)

    for uploaded_image in uploaded_images:
        file_names_list.append(uploaded_image.name)

    #Language choice

    language = language_entry


    #System instruction
    try:
        system_instruction = st.session_state['df_master'].loc[0, 'System instruction']
    except:
        system_instruction = role_content_own
    
    #Example
    try:
        df_example = st.session_state['df_master'].loc[0, 'Example']
    except:
        df_example = ''

    #Consent
    try:
        consent = consent_entry
    except:
        print('Consent not entered')
        consent = True
    
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
           'Enter your questions for GPT': gpt_questions, 
            'Use own account': own_account,
            'Use flagship version of GPT': gpt_enhancement,
            'System instruction': system_instruction,
            'Example': df_example, 
            'Consent': consent
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
    
    return df_master_new



# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string  
#Import variables
from functions.gpt_functions import question_characters_bound, system_characters_bound, basic_model, flagship_model, gpt_system_msg


# %%
#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = basic_model
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

# %%
#Define system role content for GPT
#system_instruction = role_content_own

#intro_for_GPT = [{"role": "system", "content": system_instruction}]


# %%
#Import functions for vision, own file only
from functions.gpt_functions import get_image_dims, calculate_image_token_cost
from functions.own_functions import image_to_b64_own, run_b64_own#, #GPT_b64_json_own, engage_GPT_b64_json_own

# %% [markdown]
# # Streamlit form, functions and parameters

# %%
#Import functions and variables
from functions.common_functions import open_page, clear_cache_except_validation_df_master, tips


# %% [markdown]
# ## Run functions

# %%
@st.dialog("Producing data")
def own_run_function():
    
    if ((len(uploaded_docs) == 0) and (len(uploaded_images) == 0)):

        st.warning('You must upload some file(s).')

    elif ((st.session_state['df_master'].loc[0, 'Use GPT'] == False) or (len(gpt_questions_entry) < 5)):

        st.warning("You must tick 'Use GPT' and enter some questions.")
        
    elif int(consent_entry) == 0:
        
        st.warning("You must tick 'Yes, I agree.' to use the app.")
    
    elif len(st.session_state.df_individual)>0:
        
        st.warning('You must :red[REMOVE] the last produced data before producing new data.')

    else:

        if ((own_account_entry) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                
            if is_api_key_valid(gpt_api_key_entry) == False:
                st.error('Your API key is not valid.')
                st.stop()

        spinner_text = "In progress..."
        
        with st.spinner(spinner_text):

            try:
                #Warning
                if gpt_activation_entry:
                    if st.session_state.gpt_model == basic_model:
                        st.warning('A low-cost GPT model is in use. Please be cautious.')
                        st.caption(f'Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more files or use a better model.')
                    
                    #if st.session_state.gpt_model == flagship_model:
                        #st.warning('An expensive GPT model will process your files. Please be cautious.')
                      
                #Create spreadsheet of responses
                df_master = own_create_df()
                
                #Activate user's own key or mine
                if own_account_entry:
                    
                    API_key = df_master.loc[0, 'Your GPT API key']
    
                else:
                    
                    API_key = st.secrets["openai"]["gpt_api_key"]
    
                openai.api_key = API_key
                
                df_individual = run_own(df_master, uploaded_docs, uploaded_images)
        
                #Keep entries in session state
                st.session_state["df_master"] = df_master
    
                #Change session states
                st.session_state['need_resetting'] = 1
                st.session_state["page_from"] = 'pages/OWN.py'
                
                #Keep data in session state
                st.session_state["df_individual"] = df_individual

                #Download data
                #download_buttons(df_master, df_individual)

                #Clear any error
                st.session_state['error_msg'] = ''
                
                st.rerun()
            
            except Exception as e:

                #Clear output
                st.session_state["df_individual"] = pd.DataFrame([])
                
                st.error('Sorry, an error has occurred. Please change your questions or wait a few hours, and try again.')
                
                st.error(e)
                
                #st.error(traceback.format_exc())

                print(e)

                #print(traceback.format_exc())

                st.session_state['error_msg'] = traceback.format_exc()

                st.rerun()

                

# %%
@st.dialog("Producing data")
def run_b64_function():         

    if len(uploaded_images) == 0:

        st.warning('You must upload some image(s).')

    elif ((st.session_state['df_master'].loc[0, 'Use GPT'] == False) or (len(gpt_questions_entry) < 5)):

        st.warning("You must tick 'Use GPT' and enter some questions.")

    elif int(consent_entry) == 0:
        st.warning("You must tick 'Yes, I agree.' to use the app.")
    
    elif len(st.session_state.df_individual)>0:
        st.warning('You must :red[REMOVE] the data already produced before producing new data.')

    else:

        if ((own_account_entry) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                
            if is_api_key_valid(gpt_api_key_entry) == False:
                st.error('Your API key is not valid.')
                st.stop()
                
        #st.write('Your results should be available for download soon. The estimated waiting time is 3-5 minutes per 10 judgments.')
        #st.write('If this app produces an error or an unexpected spreadsheet, please double-check your search terms and try again.')

        spinner_text = "In progress..."

        with st.spinner(spinner_text):

            try:                    
                #Create spreadsheet of responses
                df_master = own_create_df()

                #Check for non-supported file types
                if '.bmp' in str(df_master['Your uploaded files']).lower():
                    st.error('Sorry, this app does not support BMP images.')
                    st.stop()
                    
                if '.tiff' in str(df_master['Your uploaded files']).lower():
                    st.error('Sorry, this app does not support TIFF images.')
                    st.stop()
                
                #Activate user's own key or mine
                if own_account_entry:
                    
                    API_key = df_master.loc[0, 'Your GPT API key']
    
                else:
                    
                    API_key = st.secrets["openai"]["gpt_api_key"]
    
                openai.api_key = API_key
                
                df_individual = run_b64_own(df_master, uploaded_images)

                #Keep entries in session state    
                st.session_state["df_master"] = df_master
            
                #Change session states
                st.session_state['need_resetting'] = 1
                st.session_state["page_from"] = 'pages/OWN.py'
                
                #Keep data in session state
                st.session_state["df_individual"] = df_individual

                #Download data
                #download_buttons(df_master, df_individual)
                
                #if df_master.loc[0, 'Language choice'] != 'English':
        
                    #st.warning("If your spreadsheet reader does not display non-English text properly, please change the encoding to UTF-8 Unicode.")

                #Clear any error
                st.session_state['error_msg'] = ''
                
                st.rerun()
            
            except Exception as e:

                #Clear output
                st.session_state["df_individual"] = pd.DataFrame([])
                
                st.error('Sorry, an error has occurred. Please change your questions or wait a few hours, and try again.')
                
                st.error(e)
                
                #st.error(traceback.format_exc())

                print(e)

                #print(traceback.format_exc())

                st.session_state['error_msg'] = traceback.format_exc()

                st.rerun()



# %% [markdown]
# ## Initialize session states

# %%
#Initialize default values

#if 'jurisdiction_page' not in st.session_state:
st.session_state['jurisdiction_page'] = 'pages/OWN.py'

if 'gpt_api_key_validity' not in st.session_state:
    st.session_state['gpt_api_key_validity'] = False

#if 'own_account' not in st.session_state:
    #st.session_state['own_account'] = False

if 'need_resetting' not in st.session_state:
        
    st.session_state['need_resetting'] = 0

if 'df_master' not in st.session_state:

    df_master_dict = {'Your name': '',
    'Your email address': '',
    'Your GPT API key': '',
    'Maximum number of files': default_file_counter_bound,
    'Maximum number of pages per file': default_page_bound,
    'Language choice': 'English',
    'Enter your questions for GPT': '',
    'Use GPT': False,
    'Use own account': False,
    'Use flagship version of GPT': False,
    'System instruction': role_content_own,
    'Example': '', 
    'b64_enabled': False
    }
    
    st.session_state['df_master'] = pd.DataFrame([df_master_dict])

if 'System instruction' not in st.session_state.df_master.columns:
        
    st.session_state['df_master'].loc[0, 'System instruction'] = role_content_own

if 'System instruction' not in st.session_state.df_master.columns:
        
    st.session_state['df_master'].loc[0, 'Example'] = ''

if 'Consent' not in st.session_state.df_master.columns:
    st.session_state['df_master'].loc[0, 'Consent'] = False

if 'df_individual' not in st.session_state:

    st.session_state['df_individual'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

#default_judgment_counter_bound < judgment_batch_cutoff < judgment_batch_max

#Instant mode max/batch mode threshold
if own_account_allowed() > 0:
    st.session_state["judgment_batch_cutoff"] = judgment_batch_cutoff
else:
    st.session_state["judgment_batch_cutoff"] = default_judgment_counter_bound

#Maximum number of judgments to process under any mode
if "judgment_counter_max" not in st.session_state:

    st.session_state["judgment_counter_max"] = judgment_batch_cutoff

if batch_mode_allowed() > 0:

    st.session_state["judgment_counter_max"] = int(round(judgment_batch_max))

#Initalize for the purpuse of disabling multiple submissions of batch requests
if "batch_submitted" not in st.session_state:
    st.session_state["batch_submitted"] = False

if "batch_ready_for_submission" not in st.session_state:
    st.session_state["batch_ready_for_submission"] = False

#For example df
if 'df_example_to_show' not in st.session_state:
    st.session_state["df_example_to_show"] = pd.DataFrame([])

#Initalize df_example_key for the purpose of removing uploaded spreadsheets programatically
if "df_example_key" not in st.session_state:
    st.session_state["df_example_key"] = 0

#Initialise waiting time
if 'estimated_waiting_secs' not in st.session_state:
    
    st.session_state['estimated_waiting_secs'] = int(float(st.session_state["judgment_batch_cutoff"]))*30

#Initialise error reporting status
if 'error_msg' not in st.session_state:
    st.session_state['error_msg'] = ''

# %% [markdown]
# ## Form before AI

# %%
#Create form

return_button = st.button('RETURN to first page')

st.header(f"Research :blue[your own files]")
    
st.success(f'Please upload your documents or images.')

st.caption(f'By default, this app will extract text from up to {default_file_counter_bound} files, and process up to approximately {round(tokens_cap(basic_model)*3/4)} words from the first {default_page_bound} pages of each file. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more files or more pages per file.')

st.warning('This app works only if the text from your file(s) is displayed horizontally and neatly.')

st.subheader('Upload documents')

st.markdown("""Supported document formats: **searchable PDF**, **DOCX**, **TXT**, **JSON**, CS,  EPUB, MOBI, XML, HTML, XPS.
""")

uploaded_docs = st.file_uploader("Please choose your document(s).", type = doc_types, accept_multiple_files=True)

st.caption('DOC is not yet supported. Microsoft Word or a similar software can convert a DOC file to a DOCX file.')

st.subheader('Upload images')

st.markdown("""Supported image formats: **non-searchable PDF**, **JPG**, **JPEG**, **PNG**, BMP, GIF, TIFF.
""")

uploaded_images = st.file_uploader("Please choose your image(s).", type = image_types, accept_multiple_files=True)

st.caption("By default, [Python-tesseract](https://pypi.org/project/pytesseract/) will extract text from images. This tool is based on [Google’s Tesseract-OCR Engine](https://github.com/tesseract-ocr/tesseract).")

st.subheader('Language of uploaded files')

st.markdown("""In what language is the text from your uploaded file(s) written?""")
    
language_entry = st.selectbox("Please choose a language.", languages_list, index=0)

st.caption('Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to choose a language which is not available under this menu.')


# %% [markdown]
# ## Form for AI

# %%
st.header(":blue[Would you like GPT to get data or information from your files?]")

gpt_activation_entry = st.checkbox(label = 'Use GPT (free for users by default)', value = st.session_state['df_master'].loc[0, 'Use GPT'])

#if gpt_activation_entry:
    
st.session_state['df_master'].loc[0, 'Use GPT'] = gpt_activation_entry
    
st.caption(f"{gpt_cost_msg}")

st.subheader("Tell GPT what to get from each file")

st.success("""In question form, please tell GPT what to get from each file. **Enter one question per paragraph**. """)

st.markdown("""For each file, GPT will respond based only on information from the file itself. This is to minimise the risk of giving incorrect information (ie hallucination).
GPT will also provide references for its responses.
""")

gpt_questions_entry = st.text_area(label = f"Your questions (up to {question_characters_bound} characters)", height= 250, max_chars=question_characters_bound, value = st.session_state['df_master'].loc[0, 'Enter your questions for GPT']) 

st.caption(f"By default, this app will use model {basic_model}. This model will read up to approximately {round(tokens_cap(basic_model)*3/4)} words from each file.")

#if st.toggle('See tips for using GPT'):
with st.expander("See tips for using GPT"):
    tips()

#if st.toggle('See/edit the system instruction for GPT (advanced users only)'):
with st.expander("See/edit the system instruction for GPT (advanced users only)"):

    st.warning(gpt_system_msg)

    if st.button(label = 'RESET the system instruction', type="primary"):

        if 'System instruction' in st.session_state.df_master.columns:
    
            st.session_state.df_master.pop('System instruction')
    
        st.rerun()
    
    gpt_system_entry = st.text_area(label = f"System instruction (up to {system_characters_bound} characters)", height= 250, max_chars=system_characters_bound, value = st.session_state['df_master'].loc[0, 'System instruction']) 

    st.session_state['df_master'].loc[0, 'System instruction'] = gpt_system_entry

if check_questions_answers() > 0:
    
    st.warning("Please do not try to obtain personally identifiable information. Your questions/instructions and GPT's answers will be checked for potential privacy violation.")

#if gpt_questions_entry:
    
st.session_state['df_master'].loc[0, 'Enter your questions for GPT'] = gpt_questions_entry

#Disable toggles while prompt is not entered or the same as the last processed prompt

if gpt_activation_entry:
    
    if gpt_questions_entry:
        st.session_state['disable_input'] = False
        
    else:
        st.session_state['disable_input'] = True
else:
    st.session_state['disable_input'] = False
    
#Upload example
st.subheader("Share an exemplar (optional)")

st.markdown("""This app will produce a spreadsheet with rows of files and columns of answers to your questions. If you have a preferred layout, please feel free to upload an example for GPT to follow.""")

uploaded_file = st.file_uploader(label = "Upload an example", 
                                 type=['csv', 'xlsx', 'json'], 
                                 accept_multiple_files=False, 
                                  key = st.session_state["df_example_key"]
                                )

if uploaded_file:

    try:
    
        df_example_to_show = uploaded_file_to_df(uploaded_file)
        
        indice = df_example_to_show.index.tolist()
    
        if len(indice) > 0:
    
            for index in indice [1: ]:
    
                df_example_to_show.drop(index, axis=0, inplace = True)

        #Create copy to show before dropping GPT stats headings
        st.session_state.df_example_to_show = df_example_to_show.copy(deep = True)

        #Drop any GPT stats headings and add example to df_master as a string of a json
        columns = df_example_to_show.columns.tolist()

        for col in columns:
            
            for gpt_col in own_gpt_headings:
                
                if ((gpt_col.lower() in col.lower()) and (col in df_example_to_show.columns)):
                    
                    df_example_to_show.drop(col, axis=1, inplace = True)
                            
        st.session_state.df_master.loc[0, 'Example'] = json.dumps(df_example_to_show.loc[0].to_json(default_handler=str))
        
    except Exception as e:
        
        st.error(f'Sorry, this app is unable to follow this example due to this error: {e}')

if len(st.session_state.df_example_to_show) > 0:
        
    st.success('For each file, GPT will *try* to produce something like the following:')

    st.dataframe(st.session_state.df_example_to_show)

    #Button for removing example
    if st.button(label = 'REMOVE the uploaded example', type = 'primary'):
    
        st.session_state.df_example_key += 1
    
        st.session_state.df_example_to_show = pd.DataFrame([])
    
        st.session_state.df_master.loc[0, 'Example'] = ''
    
        st.rerun()


# %% [markdown]
# ## Own account

# %%
if own_account_allowed() == 0:
    
    own_account_entry = False

else:
    
#if own_account_allowed() > 0:
    
    st.header(':orange[Enhance app capabilities]')
    
    st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or increase the maximum number of files to process? You can do so with your own GPT account.
    """)
    
    own_account_entry = st.toggle(label = 'Use my own GPT account',  disabled = st.session_state.disable_input, value = st.session_state['df_master'].loc[0, 'Use own account'])
    
    if own_account_entry:
    
        #st.session_state['df_master'].loc[0, 'Use own account'] = own_account_entry
        
        #st.session_state["own_account"] = True
    
        st.markdown("""**:green[Please enter your name, email address and API key.]** You can sign up for a GPT account and pay for your own usage [here](https://platform.openai.com/signup). You can then create and find your API key [here](https://platform.openai.com/api-keys).
    """)
        
        name_entry = st.text_input(label = "Your name", value = st.session_state['df_master'].loc[0, 'Your name'])

        #if name_entry:
            
        #st.session_state['df_master'].loc[0, 'Your name'] = name_entry
        
        email_entry = st.text_input(label = "Your email address", value =  st.session_state['df_master'].loc[0, 'Your email address'])

        #if email_entry:
            
        #st.session_state['df_master'].loc[0, 'Your email address'] = email_entry
        
        gpt_api_key_entry = st.text_input(label = "Your GPT API key (mandatory)", value = st.session_state['df_master'].loc[0, 'Your GPT API key'])
        
        if gpt_api_key_entry:
            
            #st.session_state['df_master'].loc[0, 'Your GPT API key'] = gpt_api_key_entry

            if ((len(gpt_api_key_entry) < 40) or (gpt_api_key_entry[0:2] != 'sk')):
                
                st.warning('This key is not valid.')
                
        st.markdown(f"""**:green[You can use the flagship GPT model ({flagship_model}),]** which is :red[significantly more expensive] than the default model ({basic_model}).""")  
        
        gpt_enhancement_entry = st.checkbox('Use the flagship GPT model', value = st.session_state['df_master'].loc[0, 'Use flagship version of GPT'])
        
        st.caption('Click [here](https://openai.com/api/pricing) for pricing information on different GPT models.')

        #if gpt_enhancement_entry == True:
        
            #st.session_state.gpt_model = flagship_model
            #st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = True

        #else:
            
            #st.session_state.gpt_model = basic_model
            #st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
        
        st.write(f'**:green[You can change the maximum number of files to process.]**')

        file_counter_bound_entry = st.slider(label = f'Up to {st.session_state["judgment_counter_max"]} files', min_value = 1, max_value = st.session_state["judgment_counter_max"], step = 1, value = str_to_int(st.session_state['df_master'].loc[0, 'Maximum number of files']))

        #if file_counter_bound_entry:
            
        #st.session_state['df_master'].loc[0, 'Maximum number of files'] = file_counter_bound_entry
        
        if file_counter_bound_entry > st.session_state["judgment_batch_cutoff"]:
    
            st.warning(f"Given more than {st.session_state['judgment_batch_cutoff']} files may need to be processes, this app will send your requested data to your nominated email address in about **2 business days**.")

        st.write(f'**:orange[You can change the maximum number of pages per file to process.]**')
        
        page_bound_entry = st.slider(label = f'Up to {default_page_bound} pages', min_value = 1, max_value = default_page_bound, step = 1, value = str_to_int_page(st.session_state['df_master'].loc[0, 'Maximum number of pages per file']))

        #if page_bound_entry:
            
        #st.session_state['df_master'].loc[0, 'Maximum number of pages per file'] = page_bound_entry
        
        #st.write(f"*GPT model {st.session_state.gpt_model} will answer any questions based on up to approximately {int(round(tokens_cap(st.session_state.gpt_model)*3/4))} words from the first  {int(st.session_state['df_master'].loc[0,'Maximum number of pages per file'])} page(s) of each file, for up to {int(st.session_state['df_master'].loc[0, 'Maximum number of files'])} file(s).*")
    
    else:
        
        #st.session_state["own_account"] = False

        st.session_state['df_master'].loc[0, 'Use own account'] = False
    
        st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    
        #st.session_state.gpt_model = basic_model

        st.session_state['df_master'].loc[0, 'Maximum number of files'] = default_judgment_counter_bound #st.session_state["judgment_batch_cutoff"]

        st.session_state['df_master'].loc[0,'Maximum number of pages per file'] = default_page_bound


# %% [markdown]
# ## Save entries

# %%
keep_button = st.button(label = 'DOWNLOAD entries')

if keep_button:
    
    st.success('Scroll down to download your entries.')

# %% [markdown]
# ## Consent

# %%
st.header("Consent")

st.markdown("""By using this app, you agree that the data and/or information you and/or this app provide will be temporarily stored on one or more remote servers. Any such data and/or information may also be given to an artificial intelligence provider. Any such data and/or information [will not be used to train any artificial intelligence model.](https://platform.openai.com/docs/models/how-we-use-your-data#how-we-use-your-data) 
""")

consent_entry =  st.checkbox('Yes, I agree.', value = bool(st.session_state['df_master'].loc[0, 'Consent']), disabled = st.session_state.disable_input)

st.session_state['df_master'].loc[0, 'Consent'] = consent_entry

st.markdown("""If you do not agree, then please feel free to close this app. """)


# %% [markdown]
# ## Next steps

# %%
st.header("Next steps")

#Calculate estimating waiting time

#Instructions
st.markdown(f"""You can now press :green[PRODUCE data] to obtain a spreadsheet which hopefully has the data you seek. This app will immediately process up to {int(min(st.session_state["judgment_batch_cutoff"], st.session_state['df_master'].loc[0, 'Maximum number of files']))} cases. The estimated waiting time is **{min(st.session_state["judgment_batch_cutoff"], st.session_state['df_master'].loc[0, 'Maximum number of files'])*30/60} minute(s)**.
""")

if batch_mode_allowed() > 0:
    st.markdown(f"""Alternatively, you can press :orange[REQUEST data] to process up to {st.session_state["judgment_counter_max"]} files. Your requested data will be sent to your nominated email address in about **2 business days**. 
""")

reset_button = st.button(label='REMOVE data', type = 'primary', disabled = not bool(st.session_state.need_resetting))

if batch_mode_allowed() > 0:
    with stylable_container(
        "orange",
        css_styles="""
        button {
            background-color: #F9F500;
            color: black;
        }""",
    ):
        batch_button = st.button(label = f"REQUEST data (up to {st.session_state['judgment_counter_max']} files)", 
                                  help = 'You can only :orange[REQUEST] data once per session.', 
                                 disabled = bool((st.session_state.batch_submitted) or (st.session_state.disable_input))
                                )
        
with stylable_container(
    "green",
    css_styles="""
    button {
        background-color: #00FF00;
        color: black;
    }""",
):

    run_button = st.button(label = f"PRODUCE data now (up to {int(min(st.session_state['judgment_batch_cutoff'], st.session_state['df_master'].loc[0, 'Maximum number of files']))} files)", 
                          help = 'You must :red[REMOVE] any data previously produced before producing new data.', 
                           disabled = bool((st.session_state.need_resetting) or (st.session_state.disable_input) or (bool(st.session_state['df_master'].loc[0, 'Maximum number of files'] > st.session_state["judgment_batch_cutoff"])))
                          )

if ((own_account_entry == True) and (uploaded_images)):

    if immediate_b64() > 0:
    
        st.markdown("""By default, this app will use an Optical Character Recognition (OCR) engine to extract text from images, and then send such text to GPT.
        
Alternatively, you can send images directly to GPT. This alternative approach may produce better responses for "untidy" images, but tends to be slower and costlier than the default approach.
""")
    
        run_button_b64 = st.button(label = f"SEND images to GPT directly now (up to {min(st.session_state['judgment_batch_cutoff'], st.session_state['df_master'].loc[0, 'Maximum number of files'])} files)", 
                                  help = 'You must :red[REMOVE] any data previously produced before producing new data.', 
                                   disabled = bool((st.session_state.need_resetting) or (st.session_state.disable_input) or (bool(st.session_state['df_master'].loc[0, 'Maximum number of files'] > st.session_state["judgment_batch_cutoff"])))
                                  )
    
    else:

        st.markdown("""By default, this app will use an Optical Character Recognition (OCR) engine to extract text from images, and then send such text to GPT.
        
Alternatively, you can request to send images directly to GPT. This alternative approach may produce better responses for "untidy" images, but tends to be slower and costlier than the default approach. Your request data will be sent to your nominated email address in about **2 business days**.
""")
        
        batch_button_b64 = st.button(label = f"REQUEST to send images to GPT directly (up to {st.session_state['judgment_counter_max']} files)", 
                                       help = 'You can only :orange[REQUEST] data once per session.', 
                                 disabled = bool((st.session_state.batch_submitted) or (st.session_state.disable_input))
                                    )

#test_button = st.button('Test')

#Display need resetting message if necessary
#if st.session_state.need_resetting == 1:
    #if ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual) > 0)):
        #st.warning('You must :red[REMOVE] the data previously produced before producing new data.')
        #st.warning('You must :red[RESET] the app before producing new data. Please press the :red[RESET] button above.')

# %% [markdown]
# ## Download entries and and outputs

# %%
#Create placeholder download buttons if previous entries and output in st.session_state:

if len(st.session_state.df_individual) > 0:

    #Current output
    if st.session_state["page_from"] == 'pages/OWN.py':

        download_buttons(df_master = st.session_state.df_master, df_individual = st.session_state.df_individual)

    #Previous entries and output
    else:

        download_buttons(df_master = st.session_state.df_master, df_individual = st.session_state.df_individual, saving = False, previous = True)


# %% [markdown]
# # Buttons

# %%
#b64 batch
if (batch_mode_allowed() > 0) and ((own_account_entry) and (uploaded_images)):

    if batch_button_b64:
    
        if len(uploaded_images) == 0:
    
            st.warning('You must upload some image(s).')
    
        elif ((st.session_state['df_master'].loc[0, 'Use GPT'] == False) or (len(gpt_questions_entry) < 5)):
    
            st.warning("You must tick 'Use GPT' and enter some questions.")
            
        elif int(consent_entry) == 0:
            
            st.warning("You must tick 'Yes, I agree.' to use the app.")
        
        elif len(st.session_state.df_individual)>0:
            
            st.warning('You must :red[REMOVE] the last produced data before producing new data.')

        else:

            #Create spreadsheet of responses
            df_master = own_create_df()

            #Check for non-supported file types
            if '.bmp' in str(df_master['Your uploaded files']).lower():
                st.error('Sorry, this app does not support BMP images.')
                st.stop()
                
            if '.tiff' in str(df_master['Your uploaded files']).lower():
                st.error('Sorry, this app does not support TIFF images.')
                st.stop()

            #Ensure b64 is turned on
            df_master.loc[0, 'b64_enabled'] = True
            
            #Keep entries in session state    
            st.session_state["df_master"] = df_master
            
            own_batch_request_function(df_master, uploaded_docs, uploaded_images)

    #if st.session_state.batch_submitted == True:
        
        #st.success('Your data request has been submitted. This app will send your requested data to your nominated email address in about **2 business days**. Feel free to close this app.')

# %% [markdown]
# ## Save and run etc

# %%
if run_button:

    own_run_function()


# %%
#NOT IN USE

if immediate_b64() > 0:
    
    if ((own_account_entry) and (uploaded_images)):
        
        if run_button_b64:

            run_b64_function()
        


# %%
if keep_button:

    if ((len(uploaded_docs) == 0) and (len(uploaded_images) == 0)):

        st.warning('You must upload some file(s).')

    elif len(gpt_questions_entry) < 5:

        st.warning('You must enter some questions for GPT.')
            
    else:

        df_master = own_create_df()
    
        st.session_state["df_master"] = df_master

        download_buttons(df_master = st.session_state.df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:

    try:

        df_master = own_create_df()
    
        save_input(df_master)
        
    except:
        print('df_master not created.')

    st.session_state["page_from"] = 'pages/OWN.py'

    st.switch_page("Home.py")


# %%
if reset_button:

    st.session_state['df_individual'] = pd.DataFrame([])
    
    st.session_state['need_resetting'] = 0
    
    st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound
    
    st.rerun()

# %% [markdown]
# ## Batch

# %%
#Regular batch
if batch_mode_allowed() > 0:
    
    if batch_button:

        if ((len(uploaded_docs) == 0) and (len(uploaded_images) == 0)):
    
            st.warning('You must upload some file(s).')
    
        elif ((st.session_state['df_master'].loc[0, 'Use GPT'] == False) or (len(gpt_questions_entry) < 5)):
    
            st.warning("You must tick 'Use GPT' and enter some questions.")
            
        elif int(consent_entry) == 0:
            
            st.warning("You must tick 'Yes, I agree.' to use the app.")
        
        elif len(st.session_state.df_individual)>0:
            
            st.warning('You must :red[REMOVE] the last produced data before producing new data.')

        else:

            try:
                #Create spreadsheet of responses
                df_master = own_create_df()
    
                #Ensure b64 is turned off
                df_master.loc[0, 'b64_enabled'] = False
                
                #Keep entries in session state    
                st.session_state["df_master"] = df_master
                
                own_batch_request_function(df_master, uploaded_docs, uploaded_images)

                #Don't clear any error
                #st.session_state['error_msg'] = ''
                            
            except Exception as e:
    
                #Clear output
                st.session_state["df_individual"] = pd.DataFrame([])
                
                st.error('Sorry, an error has occurred. Please change your questions or wait a few hours, and try again.')
                
                st.error(e)
                
                #st.error(traceback.format_exc())
    
                print(e)
    
                #print(traceback.format_exc())
    
                st.session_state['error_msg'] = traceback.format_exc()

                st.rerun()

    if st.session_state.batch_submitted and st.session_state.need_resetting:
        
        st.success('Your data request has been submitted. This app will send your requested data to your nominated email address in about **2 business days**. Feel free to close this app.')

        #Warning
        if gpt_activation_entry:
            if st.session_state.gpt_model == basic_model:
                st.warning('A low-cost GPT model is in use. Please be cautious.')
                st.caption(f'Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more cases or use a better model.')


# %% [markdown]
# ## Report error

# %%
if len(st.session_state.error_msg) > 0:

    st.error('Sorry, an error has occurred. Please change your questions or wait a few hours, and try again.')

    st.error(st.session_state.error_msg)
        
    report_error_button = st.button(label = 'REPORT the error', help = 'Send your entries and a report of the error to the developer.')

    if report_error_button:

        #Send me an email to let me know
        report_error_email(ULTIMATE_RECIPIENT_NAME = st.session_state['df_master'].loc[0, 'Your name'], 
                                ULTIMATE_RECIPIENT_EMAIL = st.session_state['df_master'].loc[0, 'Your email address'],
                           jurisdiction_page = st.session_state.jurisdiction_page,
                           df_master = st.session_state['df_master'], 
                           error_msg = st.session_state.error_msg
                               )

        #Clear any error
        st.session_state['error_msg'] = ''

        st.success("Thank you for reporting the error. We will look at your report as soon as possible.")

