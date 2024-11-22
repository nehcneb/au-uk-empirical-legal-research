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
import traceback

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
from functions.common_functions import own_account_allowed, batch_mode_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, str_to_int, str_to_int_page, save_input, download_buttons, uploaded_file_to_df

#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, default_judgment_counter_bound, default_page_bound, spinner_text, own_gpt_headings



# %%
#Default file counter bound

default_file_counter_bound = default_judgment_counter_bound

#if 'file_counter_bound' not in st.session_state:
    #st.session_state['file_counter_bound'] = default_file_counter_bound


# %% [markdown]
# # Functions for Own Files

# %%
from functions.own_functions import doc_types, image_types, languages_dict, languages_list, doc_to_text, image_to_text, file_prompt, role_content_own, GPT_json_own, engage_GPT_json_own, run_own


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
    own_account = st.session_state.own_account
    
    #file counter bound
    file_counter_bound = st.session_state['df_master'].loc[0, 'Maximum number of files']

    #Page counter bound

    page_bound = st.session_state['df_master'].loc[0,'Maximum number of pages per file']
    
    #GPT enhancement
    try:
        gpt_enhancement = gpt_enhancement_entry
    except:
        print('GPT enhancement not entered')
        gpt_enhancement = False

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

    #Example
    try:
        df_example = st.session_state['df_master'].loc[0, 'Example']
    except:
        df_example = ''
    
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
            'Example': df_example
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
        
    return df_master_new



# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string  
#Import variables
from functions.gpt_functions import question_characters_bound, judgment_batch_cutoff, judgment_batch_max


# %%
#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-4o-mini"
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

# %%
#Define system role content for GPT
system_instruction = role_content_own

intro_for_GPT = [{"role": "system", "content": system_instruction}]


# %%
#Import functions for vision, own file only
from functions.gpt_functions import get_image_dims, calculate_image_token_cost
from functions.own_functions import image_to_b64_own, GPT_b64_json_own, run_b64_own, engage_GPT_b64_json_own

# %% [markdown]
# # Streamlit form, functions and parameters

# %%
#Import functions and variables
from functions.common_functions import open_page, clear_cache_except_validation_df_master, tips


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default values

if 'jurisdiction_page' not in st.session_state:

    st.session_state['jurisdiction_page'] = 'pages/OWN.py'

if 'gpt_api_key_validity' not in st.session_state:
    st.session_state['gpt_api_key_validity'] = False

if 'own_account' not in st.session_state:
    st.session_state['own_account'] = False

if 'need_resetting' not in st.session_state:
        
    st.session_state['need_resetting'] = 0

if 'df_master' not in st.session_state:

    #Generally applicable
    st.session_state['df_master'] = pd.DataFrame([])
    st.session_state['df_master'].loc[0, 'Your name'] = ''
    st.session_state['df_master'].loc[0, 'Your email address'] = ''
    st.session_state['df_master'].loc[0, 'Your GPT API key'] = ''
    st.session_state['df_master'].loc[0, 'Maximum number of files'] = default_judgment_counter_bound
    st.session_state['df_master'].loc[0, 'Maximum number of pages per file'] = default_page_bound
    st.session_state['df_master'].loc[0, 'Language choice'] = 'English'
    st.session_state['df_master'].loc[0, 'Enter your questions for GPT'] = ''
    st.session_state['df_master'].loc[0, 'Use GPT'] = False
    st.session_state['df_master'].loc[0, 'Use own account'] = False
    st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
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
if 'judgment_batch_cutoff' not in st.session_state:
    if own_account_allowed() > 0:
        st.session_state["judgment_batch_cutoff"] = judgment_batch_cutoff
    else:
        st.session_state["judgment_batch_cutoff"] = default_judgment_counter_bound

#Maximum number of judgments to process under any mode
if "judgment_counter_max" not in st.session_state:

    if ((batch_mode_allowed() > 0) and (st.session_state.jurisdiction_page in ['pages/HCA.py', 'pages/FCA.py', 'pages/NSW.py'])):

        if own_account_allowed() > 0:
            st.session_state["judgment_counter_max"] = judgment_batch_max
        
        else:
            st.session_state["judgment_counter_max"] = judgment_batch_cutoff
            
    else:
        
        if own_account_allowed() > 0:
            st.session_state["judgment_counter_max"] = judgment_batch_cutoff
        
        else:
            st.session_state["judgment_counter_max"] = default_judgment_counter_bound
            
#For example df
if 'df_example_to_show' not in st.session_state:
    st.session_state["df_example_to_show"] = pd.DataFrame([])

#Initalize df_example_key for the purpose of removing uploaded spreadsheets programatically
if "df_example_key" not in st.session_state:
    st.session_state["df_example_key"] = 0

# %% [markdown]
# ## Form before AI

# %%
#Create form

return_button = st.button('RETURN to first page')

st.header(f"Upload :blue[your own files]")
    
st.success(f'**Please upload your documents or images**. By default, this app will extract text from up to {default_file_counter_bound} files, and process up to approximately {round(tokens_cap("gpt-4o-mini")*3/4)} words from the first {default_page_bound} pages of each file.')

st.caption('Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more files or more pages per file.')

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
st.header(":blue[Would you like to ask GPT questions about your files?]")

gpt_activation_entry = st.checkbox(label = 'Use GPT (free by default)', value = st.session_state['df_master'].loc[0, 'Use GPT'])

#if gpt_activation_entry:
    
st.session_state['df_master'].loc[0, 'Use GPT'] = gpt_activation_entry
    
st.caption("Use of GPT is costly and funded by a grant. For the model used by default (gpt-4o-mini), Ben's own experience suggests that it costs approximately USD \$0.01 (excl GST) per file. The [exact cost](https://openai.com/pricing) for answering a question about a file depends on the length of the question, the length of the file, and the length of the answer produced. You will be given ex-post cost estimates.")

st.subheader("Enter your questions for each file")

st.warning("""Please enter **one question per line or paragraph**. For **each file**, GPT will answer your questions based **only** on information from the file **itself**. """)

st.markdown("""To minimise the risk of giving incorrect information (ie hallucination), GPT will be instructed to avoid giving answers which cannot be obtained from the relevant file itself.""")

#if st.toggle('See the instruction given to GPT'):
    #st.write(f"{intro_for_GPT[0]['content']}")

if st.toggle('Tips for using GPT'):
    tips()

gpt_questions_entry = st.text_area(label = f"You may enter at most {question_characters_bound} characters.", height= 200, max_chars=question_characters_bound, value = st.session_state['df_master'].loc[0, 'Enter your questions for GPT']) 

st.caption(f"By default, model gpt-4o-mini will answer your questions. Due to a technical limitation, this model will read up to approximately {round(tokens_cap('gpt-4o-mini')*3/4)} words from each file.")

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


if own_account_allowed() > 0:
    
    st.header(':orange[Enhance app capabilities]')
    
    st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or increase the maximum number of files to process? You can do so with your own GPT account.
    """)
    
    own_account_entry = st.toggle(label = 'Use my own GPT account',  disabled = st.session_state.disable_input, value = st.session_state['df_master'].loc[0, 'Use own account'])
    
    if own_account_entry:
    
        st.session_state['df_master'].loc[0, 'Use own account'] = own_account_entry
        
        st.session_state["own_account"] = True
    
        st.markdown("""**:green[Please enter your name, email address and API key.]** You can sign up for a GPT account and pay for your own usage [here](https://platform.openai.com/signup). You can then create and find your API key [here](https://platform.openai.com/api-keys).
    """)
        
        name_entry = st.text_input(label = "Your name", value = st.session_state['df_master'].loc[0, 'Your name'])

        #if name_entry:
            
        st.session_state['df_master'].loc[0, 'Your name'] = name_entry
        
        email_entry = st.text_input(label = "Your email address", value =  st.session_state['df_master'].loc[0, 'Your email address'])

        #if email_entry:
            
        st.session_state['df_master'].loc[0, 'Your email address'] = email_entry
        
        gpt_api_key_entry = st.text_input(label = "Your GPT API key (mandatory)", value = st.session_state['df_master'].loc[0, 'Your GPT API key'])
        
        if gpt_api_key_entry:
            
            st.session_state['df_master'].loc[0, 'Your GPT API key'] = gpt_api_key_entry

            if ((len(gpt_api_key_entry) < 40) or (gpt_api_key_entry[0:2] != 'sk')):
                
                st.warning('This key is not valid.')
                
        st.markdown("""**:green[You can use the flagship version of GPT (model gpt-4o),]** which is :red[significantly more expensive] than the default model (gpt-4o-mini) which you can use for free.""")  
        
        gpt_enhancement_entry = st.checkbox('Use the flagship GPT model', value = st.session_state['df_master'].loc[0, 'Use flagship version of GPT'])
        
        st.caption('Click [here](https://openai.com/api/pricing) for pricing information on different GPT models.')

        if gpt_enhancement_entry == True:
        
            st.session_state.gpt_model = "gpt-4o-2024-08-06"
            st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = True

        else:
            
            st.session_state.gpt_model = 'gpt-4o-mini'
            st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
        
        st.write(f'**:green[You can increase the maximum number of files to process.]** The default maximum is {default_file_counter_bound}.')

        file_counter_bound_entry = st.number_input(label = f'Up to {st.session_state["judgment_counter_max"]}', min_value = 1, max_value = st.session_state["judgment_counter_max"], step = 1, value = str_to_int(st.session_state['df_master'].loc[0, 'Maximum number of files']))

        #if file_counter_bound_entry:
            
        st.session_state['df_master'].loc[0, 'Maximum number of files'] = file_counter_bound_entry
        
        st.write(f'**:orange[You can increase the maximum number of pages per file to process.]** The default maximum is {default_page_bound}.')
        
        page_bound_entry = st.number_input(label = f'Enter a number between 1 and {default_page_bound}', min_value = 1, max_value = default_page_bound, step = 1, value = str_to_int_page(st.session_state['df_master'].loc[0, 'Maximum number of pages per file']))

        #if page_bound_entry:
            
        st.session_state['df_master'].loc[0, 'Maximum number of pages per file'] = page_bound_entry
        
        st.write(f"*GPT model {st.session_state.gpt_model} will answer any questions based on up to approximately {int(round(tokens_cap(st.session_state.gpt_model)*3/4))} words from the first  {int(st.session_state['df_master'].loc[0,'Maximum number of pages per file'])} page(s) of each file, for up to {int(st.session_state['df_master'].loc[0, 'Maximum number of files'])} file(s).*")
    
    else:
        
        st.session_state["own_account"] = False

        st.session_state['df_master'].loc[0, 'Use own account'] = False
    
        st.session_state.gpt_model = "gpt-4o-mini"

        st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    
        st.session_state['df_master'].loc[0, 'Maximum number of files'] = default_file_counter_bound

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

consent =  st.checkbox('Yes, I agree.', value = bool(st.session_state['df_master'].loc[0, 'Consent']), disabled = st.session_state.disable_input)

st.session_state['df_master'].loc[0, 'Consent'] = consent

st.markdown("""If you do not agree, then please feel free to close this app. """)


# %% [markdown]
# ## Next steps

# %%

st.header("Next steps")

st.markdown("""You can now press :green[PRODUCE data] to obtain a spreadsheet which hopefully has the data you seek.
""")

#Warning
if gpt_activation_entry:
    if st.session_state.gpt_model == 'gpt-4o-mini':
        st.warning('A low-cost GPT model will answer your questions. Please be cautious.')
        st.caption(f'Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more files or use a better model.')
    
    if st.session_state.gpt_model == "gpt-4o-2024-08-06":
        st.warning('An expensive GPT model will answer your questions. Please be cautious.')

reset_button = st.button(label='REMOVE data', type = 'primary', disabled = not bool(st.session_state.need_resetting))

with stylable_container(
    "green",
    css_styles="""
    button {
        background-color: #00FF00;
        color: black;
    }""",
):

    run_button = st.button(label = 'PRODUCE data', disabled = bool((st.session_state.need_resetting) or (st.session_state.disable_input)))
    
if ((st.session_state.own_account == True) and (uploaded_images)):

    st.markdown("""By default, this app will use an Optical Character Recognition (OCR) engine to extract text from images, and then send such text to GPT.

Alternatively, you can send images directly to GPT. This alternative approach may produce better responses for "untidy" images, but tends to be slower and costlier than the default approach.
""")
    
    #st.write('Not getting the best responses for your images? You can try a more costly')
    #b64_help_text = 'GPT will process images directly, instead of text first extracted from images by an Optical Character Recognition engine. This only works for PNG, JPEG, JPG, GIF images.'
    run_button_b64 = st.button(label = 'SEND images to GPT directly')

#test_button = st.button('Test')

#Display need resetting message if necessary
if st.session_state.need_resetting == 1:
    if ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual) > 0)):
        st.warning('You must :red[REMOVE] the data previously produced before producing new data.')
        #st.warning('You must :red[RESET] the app before producing new data. Please press the :red[RESET] button above.')

# %% [markdown]
# ## Previous responses and outputs

# %%
#Create placeholder download buttons if previous entries and output in st.session_state:

#if ((len(st.session_state.df_master) > 0) and (len(st.session_state.df_individual)>0)):

if len(st.session_state.df_individual) >0:

    download_buttons(df_master = st.session_state.df_master, df_individual = st.session_state.df_individual, saving = False, previous = True)


# %% [markdown]
# # Save and run

# %%
if run_button:

    if ((len(uploaded_docs) == 0) and (len(uploaded_images) == 0)):

        st.warning('You must upload some file(s).')

    elif ((st.session_state['df_master'].loc[0, 'Use GPT'] == False) or (len(gpt_questions_entry) < 5)):

        st.warning("You must tick 'Use GPT' and enter some questions.")
        
    elif int(consent) == 0:
        
        st.warning("You must tick 'Yes, I agree.' to use the app.")
    
    elif len(st.session_state.df_individual)>0:
        
        st.warning('You must :red[REMOVE] the last produced data before producing new data.')

    else:

        if ((st.session_state.own_account == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                
            if is_api_key_valid(gpt_api_key_entry) == False:
                st.error('Your API key is not valid.')
                st.stop()
                
        with st.spinner(spinner_text):

            try:
                #Create spreadsheet of responses
                df_master = own_create_df()
                
                #Activate user's own key or mine
                if st.session_state.own_account == True:
                    
                    API_key = df_master.loc[0, 'Your GPT API key']
    
                else:
                    
                    API_key = st.secrets["openai"]["gpt_api_key"]
    
                openai.api_key = API_key
                
                df_individual = run_own(df_master, uploaded_docs, uploaded_images)
        
                #Keep output in session state
                st.session_state["df_individual"] = df_individual
        
                st.session_state["df_master"] = df_master
    
                #Change session states
                st.session_state['need_resetting'] = 1
                st.session_state["page_from"] = 'pages/OWN.py'
                
                #Keep data in session state
                st.session_state["df_individual"] = df_individual

                #Download data
                download_buttons(df_master, df_individual)
            
            except Exception as e:

                st.error('Sorry, an error has occurred. Please change your questions or wait a few hours, and try again.')
                
                st.error(e)
                
                st.error(traceback.format_exc())

                print(e)

                print(traceback.format_exc())



# %%
if ((st.session_state.own_account == True) and (uploaded_images)):
    
    if run_button_b64:
    
        if len(uploaded_images) == 0:
    
            st.warning('You must upload some image(s).')
    
        elif ((st.session_state['df_master'].loc[0, 'Use GPT'] == False) or (len(gpt_questions_entry) < 5)):
    
            st.warning("You must tick 'Use GPT' and enter some questions.")
    
        elif int(consent) == 0:
            st.warning("You must tick 'Yes, I agree.' to use the app.")
        
        elif len(st.session_state.df_individual)>0:
            st.warning('You must :red[REMOVE] the data already produced before producing new data.')
    
        else:
    
            if ((st.session_state.own_account == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                    
                if is_api_key_valid(gpt_api_key_entry) == False:
                    st.error('Your API key is not valid.')
                    st.stop()
                    
            #st.write('Your results should be available for download soon. The estimated waiting time is 3-5 minutes per 10 judgments.')
            #st.write('If this app produces an error or an unexpected spreadsheet, please double-check your search terms and try again.')

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
                    if st.session_state.own_account == True:
                        
                        API_key = df_master.loc[0, 'Your GPT API key']
        
                    else:
                        
                        API_key = st.secrets["openai"]["gpt_api_key"]
        
                    openai.api_key = API_key
                    
                    df_individual = run_b64_own(df_master, uploaded_images)

                    #Keep output in session state
    
                    st.session_state["df_individual"] = df_individual
            
                    st.session_state["df_master"] = df_master
                
                    #Change session states
                    st.session_state['need_resetting'] = 1
                    st.session_state["page_from"] = 'pages/OWN.py'
                    
                    #Keep data in session state
                    st.session_state["df_individual"] = df_individual
    
                    #Download data
                    download_buttons(df_master, df_individual)
                    
                    if df_master.loc[0, 'Language choice'] != 'English':
            
                        st.warning("If your spreadsheet reader does not display non-English text properly, please change the encoding to UTF-8 Unicode.")
                
                except Exception as e:
        
                    st.error('Sorry, an error has occurred. Please change your questions or wait a few hours, and try again.')
                    
                    st.error(e)
                    
                    st.error(traceback.format_exc())
    
                    print(e)
    
                    print(traceback.format_exc())



# %%
if keep_button:

    if ((len(uploaded_docs) == 0) and (len(uploaded_images) == 0)):

        st.warning('You must upload some file(s).')

    elif len(gpt_questions_entry) < 5:

        st.warning('You must enter some questions for GPT.')
            
    else:

        st.subheader('Your entries are now available for download.')

        df_master = own_create_df()

        #st.session_state["df_master"] = df_master.copy(deep=True)

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
    
    st.rerun()
