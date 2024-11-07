# ---
# jupyter:
#   jupytext:
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
from dateutil import parser
from dateutil.relativedelta import *
from datetime import datetime, timedelta
import sys
import pause
import requests
from bs4 import BeautifulSoup, SoupStrainer
import httplib2
from urllib.request import urlretrieve
import os
#import pypdf
import io
from io import BytesIO
from io import StringIO
import copy

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
#from streamlit.components.v1 import html
import streamlit_ext as ste
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
import openpyxl
from pyxlsb import open_workbook as open_xlsb

# %%
#Import functions
from functions.common_functions import own_account_allowed, batch_mode_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, str_to_int, pdf_judgment, streamlit_timezone, save_input, download_buttons, send_notification_email, open_page, clear_cache_except_validation_df_master, clear_cache, tips, link, uploaded_file_to_df

#Import variables
from functions.common_functions import today_in_nums, today, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, list_range_check, au_date, streamlit_cloud_date_format, spinner_text, search_error_display, own_gpt_headings

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between case scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of case text to process is {judgment_text_lower_bound} tokens.\n")


# %%
# Go back to home page if this page is the first page
if 'page_from' not in st.session_state:
    clear_cache()
    st.switch_page("Home.py")

# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json, gpt_run
#Import variables
from functions.gpt_functions import question_characters_bound, judgment_batch_cutoff, judgment_batch_max
#, intro_for_GPT


# %%
if batch_mode_allowed() > 0:
    print(f'By default, users are allowed to use batch mode. ')
else:
    print(f'By default, users are NOT allowed to use batch mode.')


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction

if check_questions_answers() > 0:
    print(f'By default, questions and answers are checked for potential privacy violation.')
else:
    print(f'By default, questions and answers are NOT checked for potential privacy violation.')

# %%
#Module, costs and upperbounds

#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-4o-mini"

#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

#if 'judgments_counter_bound' not in st.session_state:
    #st.session_state['judgments_counter_bound'] = default_judgment_counter_bound

# %% [markdown]
# # Streamlit form, functions and parameters

# %% [markdown]
# ## Initialize session states

# %%
#Only for return and run buttons

if st.session_state.page_from != 'pages/GPT.py':

    st.session_state['jurisdiction_page'] = st.session_state.page_from


# %%
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
    st.session_state['df_master'].loc[0, 'Metadata inclusion'] = True
    st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound
    st.session_state['df_master'].loc[0, 'Enter your questions for GPT'] = ''
    st.session_state['df_master'].loc[0, 'Use GPT'] = False
    st.session_state['df_master'].loc[0, 'Use own account'] = False
    st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    st.session_state['df_master'].loc[0, 'Example'] = ''
    
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

    if ((batch_mode_allowed() > 0) and (st.session_state.jurisdiction_page in ['pages/HCA.py', 'pages/FCA.py', 'pages/NSW.py',  'pages/US.py'])):

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
if 'df_example' not in st.session_state:
        st.session_state["df_example"] = ''


# %% [markdown]
# ## Form for AI and account

# %%
return_button = st.button('RETURN to the previous page')

#st.header("Use GPT as your research assistant")

st.header(":blue[Would you to ask GPT questions about the cases returned by your search terms?]")

st.markdown("""You can use this app without asking GPT any questions. For instance, you can extract metadata and get estimates of file length and GPT cost. 
""")

gpt_activation_entry = st.checkbox(label = 'Use GPT (free by default)', value = st.session_state['df_master'].loc[0, 'Use GPT'])

st.session_state['df_master'].loc[0, 'Use GPT'] = gpt_activation_entry

st.caption("Use of GPT is costly and funded by a grant. For the model used by default (gpt-4o-mini), Ben's own experience suggests that it costs approximately USD \$0.01 (excl GST) per case. The [exact cost](https://openai.com/pricing) depends on question length, case length, and answer length. You will be given cost estimates.")

st.subheader("Enter your questions for each case")

st.markdown("""Please enter one question **per line or per paragraph**. GPT will answer your questions for **each case** based only on information from the relevant file **itself**. """)

st.markdown("""GPT is instructed to avoid giving answers which cannot be obtained from the relevant file itself. This is to minimise the risk of giving incorrect information (ie hallucination).""")

#if st.toggle('See the instruction given to GPT'):
    #st.write(f"{intro_for_GPT[0]['content']}")

if st.toggle('Tips for using GPT'):
    tips()

gpt_questions_entry = st.text_area(label = f"You may enter at most {question_characters_bound} characters.", height= 200, max_chars=question_characters_bound, value = st.session_state['df_master'].loc[0, 'Enter your questions for GPT']) 

#if gpt_questions_entry:
    
st.session_state['df_master'].loc[0, 'Enter your questions for GPT'] = gpt_questions_entry

st.caption(f"By default, model gpt-4o-mini will answer your questions. Due to a technical limitation, this model will read up to approximately {round(tokens_cap('gpt-4o-mini')*3/4)} words from each case.")

if check_questions_answers() > 0:
    
    st.warning("Please do not try to obtain personally identifiable information. Your questions and GPT's answers will be checked for potential privacy violation.")

#Disable toggles while prompt is not entered or the same as the last processed prompt
if gpt_activation_entry:
    
    if gpt_questions_entry:
        
        st.session_state['disable_input'] = False
        
    else:
        
        st.session_state['disable_input'] = True
        
else:
    st.session_state['disable_input'] = False

#Upload example
st.markdown("""By default, this app will produce a spreadsheet with rows of judgments and columns of answers to your question(s). If you prefer a different column layout, please upload an example.""")

uploaded_file = st.file_uploader(label = "Supported formats: CSV, XLSX, JSON.", 
                                 type=['csv', 'xlsx', 'json'], 
                                 accept_multiple_files=False
                                )

if uploaded_file:

    try:
    
        df_example = uploaded_file_to_df(uploaded_file)
        
        indice = df_example.index.tolist()
    
        if len(indice) > 0:
    
            for index in indice [1: ]:
    
                df_example.drop(index, axis=0, inplace = True)

        columns = df_example.columns.tolist()

        for col in columns:
            
            for gpt_col in own_gpt_headings:
                
                if ((gpt_col.lower() in col.lower()) and (col in df_example.columns)):
                    
                    df_example.drop(col, axis=1, inplace = True)
        
        st.session_state.df_example = df_example.to_json(orient = 'split', compression = 'infer', default_handler=str)
                    
        st.session_state.df_master.loc[0, 'Example'] = json.dumps(st.session_state.df_example)
        
        st.success('GPT will *try* to follow this example and give the following as a typical row:')

        st.dataframe(df_example)

    except:
        st.error('Unfortunately, GPT is unable to follow this example.')
    
else:
    
    st.session_state['df_example'] = ''

    st.session_state.df_master.loc[0, 'Example'] = json.dumps(st.session_state.df_example)

#st.write(st.session_state.df_example)

if own_account_allowed() > 0:
    
    st.subheader(':orange[Enhance app capabilities]')
    
    st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or change the maximum nunber of cases to process? You can do so with your own GPT account.
""")
    
    own_account_entry = st.toggle(label = 'Use my own GPT account',  value = st.session_state['df_master'].loc[0, 'Use own account'])
    
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

        if gpt_enhancement_entry:

            st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = True
            st.session_state.gpt_model = "gpt-4o-2024-08-06"

        else:
            
            st.session_state.gpt_model = 'gpt-4o-mini'
            st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False

        st.write(f'**:green[You can change the maximum number of cases to process.]** The default maximum is {default_judgment_counter_bound}.')
        
        judgments_counter_bound_entry = st.number_input(label = f'Up to {st.session_state["judgment_counter_max"]}', min_value = 1, max_value = st.session_state["judgment_counter_max"], step = 1, value = str_to_int(st.session_state['df_master'].loc[0, 'Maximum number of judgments']))
        
        #if judgments_counter_bound_entry:
        
        st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = judgments_counter_bound_entry
    
        if judgments_counter_bound_entry > st.session_state["judgment_batch_cutoff"]:
    
            st.warning(f"Given more than {st.session_state['judgment_batch_cutoff']} cases need to be processes, this app will send your requested data to your nominated email address in about **2 business days**.")

        st.write(f"*GPT model {st.session_state.gpt_model} will answer any questions based on up to approximately {round(tokens_cap(st.session_state.gpt_model)*3/4)} words from each case, for up to {st.session_state['df_master'].loc[0, 'Maximum number of judgments']} case(s).*")
    
    else:
        
        st.session_state["own_account"] = False

        st.session_state['df_master'].loc[0, 'Use own account'] = False
    
        st.session_state.gpt_model = "gpt-4o-mini"

        st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    
        st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound

# %% [markdown]
# ## Consent

# %%
st.header("Consent")

st.markdown("""By using this app, you agree that the data and/or information this form provides will be temporarily stored on one or more remote servers for the purpose of producing data. Any such data and/or information may also be given to an artificial intelligence provider for the same purpose.""")

consent =  st.checkbox('Yes, I agree.', value = False, disabled = st.session_state.disable_input)

if consent:
    st.session_state['df_master'].loc[0, 'Consent'] = consent

st.markdown("""If you do not agree, then please feel free to close this app. """)


# %% [markdown]
# ## Save entries

# %%
gpt_keep_button = st.button(label = 'DOWNLOAD entries')

if gpt_keep_button:
    st.success('Scroll down to download your entries.')


# %% [markdown]
# ## Next steps

# %%
st.header("Next steps")

#Calculate estimating waiting time

estimated_waiting_secs = int(float(st.session_state['df_master'].loc[0, 'Maximum number of judgments']))*30

#Instructions
st.markdown(f"""You can now press :green[PRODUCE data] to obtain a spreadsheet which hopefully has the data you seek. This app will **immediately** process up to {min(st.session_state["judgment_batch_cutoff"], st.session_state['df_master'].loc[0, 'Maximum number of judgments'])} cases. The estimated waiting time is {estimated_waiting_secs/60} minute(s).
""")

if ((own_account_allowed() > 0) and (batch_mode_allowed() > 0) and (st.session_state.jurisdiction_page in ['pages/HCA.py', 'pages/FCA.py', 'pages/NSW.py',  'pages/US.py'])):
    st.markdown(f"""Alternatively, you can press :orange[REQUEST data] to process up to {st.session_state["judgment_counter_max"]} cases. Your requested data will be sent to your nominated email address in about **2 business days**. 
""")

#Warning
if st.session_state.gpt_model == 'gpt-4o-mini':
    st.warning('A low-cost GPT model will answer your questions. Please reach out to Ben Chen at ben.chen@sydney.edu.au if you would like to use the flagship model instead.')

if st.session_state.gpt_model == "gpt-4o-2024-08-06":
    st.warning('An expensive GPT model will answer your questions. Please be cautious.')

#Buttons

gpt_reset_button = st.button(label='REMOVE data', type = 'primary', disabled = not bool(st.session_state.need_resetting))

if ((own_account_allowed() > 0) and (batch_mode_allowed() > 0) and (st.session_state.jurisdiction_page in ['pages/HCA.py', 'pages/FCA.py', 'pages/NSW.py',  'pages/US.py'])):
    with stylable_container(
        "orange",
        css_styles="""
        button {
            background-color: #F9F500;
            color: black;
        }""",
    ):
        batch_button = st.button(label = 'REQUEST data')#, disabled = not bool(st.session_state['df_master'].loc[0, 'Maximum number of judgments'] > default_judgment_counter_bound))

with stylable_container(
    "green",
    css_styles="""
    button {
        background-color: #00FF00;
        color: black;
    }""",
):
    run_button = st.button(label = 'PRODUCE data', disabled = bool(st.session_state['df_master'].loc[0, 'Maximum number of judgments'] > st.session_state["judgment_batch_cutoff"]))

#Display need resetting message if necessary
if st.session_state.need_resetting == 1:
    if len(st.session_state.df_individual) > 0:
        st.warning('You must :red[REMOVE] the data previously produced before producing new data.')


# %% [markdown]
# ## ER only

# %%
#if st.session_state.gpt_model == "gpt-4o":
if ((st.session_state.own_account == True) and (st.session_state.jurisdiction_page == 'pages/ER.py')):
    
    st.markdown("""The English Reports are available as PDFs. By default, this app will use an Optical Character Recognition (OCR) engine to extract text from the relevant PDFs, and then send such text to GPT.
    
Alternatively, you can send the relevant PDFs to GPT as images. This alternative approach may produce better responses for "untidy" PDFs, but tends to be **slower** and **costlier** than the default approach.
""")
    
    #st.write('Not getting the best responses for your images? You can try a more costly')
    #b64_help_text = 'GPT will process images directly, instead of text first extracted from images by an Optical Character Recognition engine. This only works for PNG, JPEG, JPG, GIF images.'
    er_run_button_b64 = st.button(label = 'SEND PDFs to GPT as images')


# %% [markdown]
# ## Previous responses and outputs

# %%
#Create placeholder download buttons if previous entries and output in st.session_state:

if len(st.session_state.df_individual)>0:

    download_buttons(df_master = st.session_state.df_master, df_individual = st.session_state.df_individual, saving = False, previous = True)


# %% [markdown]
# # Run etc buttons

# %% [markdown]
# ## All jurisdictions except ER

# %%
if gpt_keep_button:
    
    download_buttons(df_master = st.session_state.df_master, df_individual = [], saving = True, previous = False)


# %%
if run_button:
    
    if int(consent) == 0:
        st.warning("You must tick 'Yes, I agree.' to use the app.")

    elif len(st.session_state.df_individual)>0:
        st.warning('You must :red[REMOVE] the last produced data before producing new data.')
            
    else:

        if ((st.session_state.own_account == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                
            if is_api_key_valid(gpt_api_key_entry) == False:
                st.error('Your API key is not valid.')
                st.stop()
                
        spinner_text += f'The estimated waiting time is {estimated_waiting_secs/60} minute(s).'

        with st.spinner(spinner_text):

            try:
    
                #Create spreadsheet of responses
                df_master = st.session_state.df_master

                #st.write(f"df_master.loc[0, 'Example'] == {df_master.loc[0, 'Example']}")
                
                #Activate user's own key or mine
                if st.session_state.own_account == True:
                    
                    API_key = df_master.loc[0, 'Your GPT API key']
    
                else:
                    API_key = st.secrets["openai"]["gpt_api_key"]
                
                openai.api_key = API_key
    
                #Produce data
                
                jurisdiction_page = st.session_state.jurisdiction_page
                
                df_individual = gpt_run(jurisdiction_page, df_master)
                                    
                #Keep data in session state
                st.session_state["df_individual"] = df_individual

                #Change session states
                st.session_state['need_resetting'] = 1
                st.session_state["page_from"] = 'pages/GPT.py'           

                #Download data
                download_buttons(df_master, df_individual)
                
            except Exception as e:
    
                st.error(search_error_display)
                
                st.error(e)

                print(e)
                


# %%
if return_button:
    
    st.session_state["page_from"] = 'pages/GPT.py'

    st.switch_page(st.session_state.jurisdiction_page)


# %%
if gpt_reset_button:

    st.session_state['df_individual'] = pd.DataFrame([])
    
    st.session_state['need_resetting'] = 0
    
    st.rerun()


# %% [markdown]
# ## ER

# %%
if ((st.session_state.own_account == True) and (st.session_state.jurisdiction_page == 'pages/ER.py')):

    if er_run_button_b64:
        
        if int(consent) == 0:
            st.warning("You must tick 'Yes, I agree.' to use the app.")
    
        elif len(st.session_state.df_individual)>0:
            st.warning('You must :red[REMOVE] the data already produced before producing new data.')
                
        else:
    
            if ((st.session_state.own_account == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                    
                if is_api_key_valid(gpt_api_key_entry) == False:
                    st.error('Your API key is not valid.')
                    st.stop()

            #Increase waiting time
            estimated_waiting_secs = estimated_waiting_secs*10
            
            spinner_text += f'The estimated waiting time is {estimated_waiting_secs/60} minute(s).'
    
            with st.spinner(spinner_text):

                try:

                    #Definitions and functions for ER
                    from functions.er_functions import er_run, er_run_b64, er_methods_list, er_method_types, er_search, er_search_results_to_case_link_pairs, er_judgment_text, er_meta_judgment_dict, role_content_er, er_judgment_tokens_b64, er_meta_judgment_dict_b64, er_GPT_b64_json, er_engage_GPT_b64_json

                    from functions.gpt_functions import get_image_dims, calculate_image_token_cost
                    
                    system_instruction = role_content_er

                    #Create spreadsheet of responses
                    df_master = st.session_state.df_master
    
                    #Activate user's own key or mine
                    if st.session_state.own_account == True:
                        
                        API_key = df_master.loc[0, 'Your GPT API key']
        
                    else:
                        API_key = st.secrets["openai"]["gpt_api_key"]
                    
                    openai.api_key = API_key
    
                    #Produce results
                        
                    df_individual = er_run_b64(df_master)
                        
                    #Keep data in session state
                    st.session_state["df_individual"] = df_individual
    
                    #Change session states
                    st.session_state['need_resetting'] = 1
                    st.session_state["page_from"] = 'pages/GPT.py'           
    
                    #Download data
                    download_buttons(df_master, df_individual)
                    
                except Exception as e:
                    
                    st.error(search_error_display)
                    
                    st.error(e)


# %% [markdown]
# ## Batching


# %%
if ((own_account_allowed() > 0) and (batch_mode_allowed() > 0) and (st.session_state.jurisdiction_page in ['pages/HCA.py', 'pages/FCA.py', 'pages/NSW.py',  'pages/US.py'])):
    
    if batch_button:
        
        if int(consent) == 0:
            st.warning("You must tick 'Yes, I agree.' to use the app.")
    
        elif len(st.session_state.df_individual)>0:
            st.warning('You must :red[REMOVE] the data already produced before producing new data.')

        elif st.session_state['df_master'].loc[0, 'Use GPT'] == False:
            st.error("You must tick 'Use GPT'.")
                
        else:

            if st.session_state.jurisdiction_page == 'pages/US.py':
                
                if len(str(st.session_state.df_master.loc[0, 'CourtListener API token'])) < 20:
                    st.error('Please return to the previous page and enter a valid CourtListener API token.')
                    st.stop()
                                    
            if ((st.session_state.own_account == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                    
                if is_api_key_valid(gpt_api_key_entry) == False:
                    st.error('Your API key is not valid.')
                    st.stop()

            #Check if valid email address entered
            if '@' not in st.session_state['df_master'].loc[0, 'Your email address']:
                st.error('You must enter a valid email address to receive your request data.')
                st.stop()
            
            else:
            
                with st.spinner(spinner_text):
                    
                    try:
        
                        #Create spreadsheet of responses
                        df_master = st.session_state.df_master

                        jurisdiction_page = st.session_state.jurisdiction_page
        
                        df_master['jurisdiction_page'] = jurisdiction_page
                        
                        df_master['status'] = 'to_process'
        
                        df_master['submission_time'] = str(datetime.now())

                        #Check questions for potential privacy violation
                        #Activate user's own key or mine
                        if st.session_state.own_account == True:
                            
                            API_key = df_master.loc[0, 'Your GPT API key']
            
                        else:
                            API_key = st.secrets["openai"]["gpt_api_key"]
                        
                        openai.api_key = API_key

                        if df_master.loc[0, 'Use flagship version of GPT'] == True:
                            gpt_model = "gpt-4o-2024-08-06"
                        else:        
                            gpt_model = "gpt-4o-mini"

                        questions_checked_dict = GPT_questions_check(df_master.loc[0, 'Enter your questions for GPT'], gpt_model, questions_check_system_instruction)

                        #Use checked questions
                        df_master.loc[0, 'Enter your questions for GPT'] = questions_checked_dict['questions_string']
                        
                        #Initiate aws s3
                        s3_resource = boto3.resource('s3',region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"], aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"])
                        
                        #Get a list of all files on s3
                        bucket = s3_resource.Bucket('lawtodata')
        
                        #Get all_df_masters
                        for obj in bucket.objects.all():
                            key = obj.key
                            if key == 'all_df_masters.csv':
                                body = obj.get()['Body'].read()
                                all_df_masters = pd.read_csv(BytesIO(body), index_col=0)
                                break
                                
                        #Add df_master to all_df_masters 
                        all_df_masters = pd.concat([all_df_masters, df_master], ignore_index=True)
        
                        #Upload all_df_masters to aws
                        csv_buffer = StringIO()
                        all_df_masters.to_csv(csv_buffer)
                        s3_resource = boto3.resource('s3',region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"], aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"])
                        s3_resource.Object('lawtodata', 'all_df_masters.csv').put(Body=csv_buffer.getvalue())
                                               
                        #Send me an email to let me know
                        send_notification_email(ULTIMATE_RECIPIENT_NAME = st.session_state['df_master'].loc[0, 'Your name'], 
                                                ULTIMATE_RECIPIENT_EMAIL = st.session_state['df_master'].loc[0, 'Your email address']
                                               )
                        
                        st.success('Your request has been submitted. This app will send your requested data to your nominated email address in about **2 business days**. Please feel free to close this app.')
                        
                    except Exception as e:

                        st.error(search_error_display)
                        
                        st.error(e)



