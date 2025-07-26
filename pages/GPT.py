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
#from dateutil.relativedelta import *
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
import traceback

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
#from streamlit.components.v1 import html
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
import openpyxl
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
from functions.common_functions import own_account_allowed, batch_mode_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, str_to_int, streamlit_timezone, save_input, download_buttons, send_notification_email, open_page, clear_cache_except_validation_df_master, clear_cache, tips, link, uploaded_file_to_df, streamlit_timezone, report_error

#Import variables
from functions.common_functions import judgment_batch_cutoff, judgment_batch_max, today_in_nums, today, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, list_range_check, date_parser, streamlit_cloud_date_format, own_gpt_headings, gpt_cost_msg, search_error_display


# %%
# Go back to home page if this page is the first page
if 'page_from' not in st.session_state:
    clear_cache()
    st.switch_page("Home.py")

# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, gpt_run, batch_request_function #GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import question_characters_bound, system_characters_bound, default_caption, basic_model, flagship_model, role_content, gpt_system_msg, pages_w_batch
#, intro_for_GPT


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction


# %%
#Module, costs and upperbounds

#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = basic_model

#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

#if 'judgments_counter_bound' not in st.session_state:
    #st.session_state['judgments_counter_bound'] = default_judgment_counter_bound


# %% [markdown]
# # Streamlit form, functions and parameters

# %% [markdown]
# ### Function for saving entries for own account

# %%
#Function for saving entries for own account:

def own_account_entries_function():

    if own_account_allowed() > 0:

        st.session_state['df_master'].loc[0, 'Use own account'] = own_account_entry

        if st.session_state['df_master'].loc[0, 'Use own account']:
            
            st.session_state['df_master'].loc[0, 'Your name'] = name_entry
    
            st.session_state['df_master'].loc[0, 'Your email address'] = email_entry
    
            st.session_state['df_master'].loc[0, 'Your GPT API key'] = gpt_api_key_entry
    
            st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = gpt_enhancement_entry
    
            if st.session_state['df_master'].loc[0, 'Use flagship version of GPT']:
            
                st.session_state.gpt_model = flagship_model
    
            else:
                
                st.session_state.gpt_model = basic_model
    
            st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = judgments_counter_bound_entry
    
        else:
            
            st.session_state['df_master'].loc[0, 'Use own account'] = False
            
            st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False

            st.session_state.gpt_model = basic_model

            st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound #st.session_state["judgment_batch_cutoff"]
    
    #else:

        #st.session_state['df_master'].loc[0, 'Use own account'] = False
    
        #st.session_state.gpt_model = basic_model

        #st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    
        #st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound

    st.session_state.estimated_waiting_secs = min(st.session_state["judgment_batch_cutoff"], st.session_state['df_master'].loc[0, 'Maximum number of judgments'])*30



# %% [markdown]
# ## Run functions

# %%
#For all jurisdictions

@st.dialog("Producing data")
def gpt_run_function():
    
    if int(consent_entry) == 0:
        st.warning("You must tick 'Yes, I agree.' to use the app.")

    elif len(st.session_state.df_individual) > 0:
        
        st.warning('You must :red[REMOVE] the last produced data before producing new data.')
            
    else:

        own_account_entries_function()
        
        if ((own_account_entry) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                
            if is_api_key_valid(gpt_api_key_entry) == False:
                st.error('Your API key is not valid.')
                st.stop()
                
        spinner_text = f'The estimated waiting time is {st.session_state.estimated_waiting_secs/60} minute(s).'

        with st.spinner(spinner_text):

            try:
                
                #Warning
                if gpt_activation_entry:
                    if st.session_state.gpt_model == basic_model:
                        st.warning('A low-cost GPT model is in use. Please be cautious.')
                        st.caption(f'Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more cases or use a better model.')
                    
                    #if st.session_state.gpt_model == flagship_model:
                        #st.warning('An expensive GPT model will process the cases found. Please be cautious.')
                            
                #Create spreadsheet of responses
                df_master = st.session_state.df_master

                #st.write(f"df_master.loc[0, 'Example'] == {df_master.loc[0, 'Example']}")
                
                #Activate user's own key or mine
                if own_account_entry:
                    
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
                #download_buttons(df_master, df_individual)

                #Clear any error
                st.session_state["batch_error"] = False
                st.session_state['error_msg'] = ''
                
                st.rerun()
            
            except Exception as e:

                #Clear output
                st.session_state["df_individual"] = pd.DataFrame([])
                
                st.error(search_error_display)
                                
                print(traceback.format_exc())

                st.session_state['error_msg'] = traceback.format_exc()
                


# %%
#For ER only

@st.dialog("Producing data")
def er_run_b64_function():

    if int(consent_entry) == 0:
        st.warning("You must tick 'Yes, I agree.' to use the app.")

    elif len(st.session_state.df_individual)>0:
        st.warning('You must :red[REMOVE] the data already produced before producing new data.')
            
    else:

        own_account_entries_function()
        
        if ((own_account_entry) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                
            if is_api_key_valid(gpt_api_key_entry) == False:
                st.error('Your API key is not valid.')
                st.stop()
        #Increase waiting time
        st.session_state.estimated_waiting_secs = st.session_state.estimated_waiting_secs*10
        
        spinner_text = f'The estimated waiting time is {st.session_state.estimated_waiting_secs/60} minute(s).'

        with st.spinner(spinner_text):

            try:

                #Warning
                if gpt_activation_entry:
                    if st.session_state.gpt_model == basic_model:
                        st.warning('A low-cost GPT model is in use. Please be cautious.')
                        st.caption(f'Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more cases or use a better model.')
                    
                    #if st.session_state.gpt_model == flagship_model:
                        #st.warning('An expensive GPT model will process the cases found. Please be cautious.')
                
                #Definitions and functions for ER
                from functions.er_functions import er_run_b64#, role_content_er#, er_run, er_methods_list, er_method_types, er_search, er_search_results_to_case_link_pairs, er_judgment_text, er_meta_judgment_dict, er_judgment_tokens_b64, er_meta_judgment_dict_b64, er_GPT_b64_json, er_engage_GPT_b64_json

                #from functions.gpt_functions import get_image_dims, calculate_image_token_cost
                
                #system_instruction = role_content_er

                #Create spreadsheet of responses
                df_master = st.session_state.df_master

                #Activate user's own key or mine
                if own_account_entry:
                    
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
                #download_buttons(df_master, df_individual)

                #Clear any error
                st.session_state["batch_error"] = False
                st.session_state['error_msg'] = ''
                
                st.rerun()
            
            except Exception as e:

                #Clear output
                st.session_state["df_individual"] = pd.DataFrame([])
                
                st.error(search_error_display)
                                
                print(traceback.format_exc())

                st.session_state['error_msg'] = traceback.format_exc()
                    


# %% [markdown]
# ## Initialize session states

# %%
#Only for return and run buttons

if st.session_state.page_from != 'pages/GPT.py':

    st.session_state['jurisdiction_page'] = st.session_state.page_from


# %%
#if 'own_account' not in st.session_state:
    #st.session_state['own_account'] = False

if 'need_resetting' not in st.session_state:
        
    st.session_state['need_resetting'] = 0

if 'df_master' not in st.session_state:

    #Generally applicable
    df_master_dict = {'Your name': '',
    'Your email address': '',
    'Your GPT API key': '',
    'Metadata inclusion': True,
    'Maximum number of judgments': default_judgment_counter_bound,
    'Enter your questions for GPT': '',
    'Use GPT': False,
    'Use own account': False,
    'Use flagship version of GPT': False,
    'Example': ''
    }
    
    st.session_state['df_master'] = pd.DataFrame([df_master_dict])

if 'System instruction' not in st.session_state.df_master.columns:

    if st.session_state.jurisdiction_page == 'pages/HK.py':

        from functions.hk_functions import role_content_hk
    
        st.session_state['df_master'].loc[0, 'System instruction'] = role_content_hk

    elif st.session_state.jurisdiction_page == 'pages/HKLII.py':

        from functions.hklii_functions import role_content_hklii
    
        st.session_state['df_master'].loc[0, 'System instruction'] = role_content_hklii
    
    elif st.session_state.jurisdiction_page == 'pages/ER.py':

        from functions.er_functions import role_content_er
    
        st.session_state['df_master'].loc[0, 'System instruction'] = role_content_er

    else:
        
        st.session_state['df_master'].loc[0, 'System instruction'] = role_content

if 'Example' not in st.session_state.df_master.columns:
    st.session_state['df_master'].loc[0, 'Example'] = ''

if 'Consent' not in st.session_state.df_master.columns:
    st.session_state['df_master'].loc[0, 'Consent'] = False

if 'df_individual' not in st.session_state:

    st.session_state['df_individual'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

#default_judgment_counter_bound < judgment_batch_cutoff < judgment_batch_max/2

#Instant mode max/batch mode threshold
if "judgment_batch_cutoff" not in st.session_state:
#if own_account_allowed() > 0:
    st.session_state["judgment_batch_cutoff"] = judgment_batch_cutoff
#else:
    #st.session_state["judgment_batch_cutoff"] = default_judgment_counter_bound

#Maximum number of judgments to process under any mode
if "judgment_counter_max" not in st.session_state:

    st.session_state["judgment_counter_max"] = judgment_batch_cutoff

if ((batch_mode_allowed() > 0) and (st.session_state.jurisdiction_page in pages_w_batch)):
        
    st.session_state["judgment_counter_max"] = judgment_batch_max

#Initalize for the purpuse of disabling multiple submissions of batch requests
if "batch_submitted" not in st.session_state:
    st.session_state["batch_submitted"] = False

if "batch_error" not in st.session_state:
    st.session_state["batch_error"] = False

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
# ## Form for AI

# %%
return_button = st.button('RETURN to the previous page')

#st.header("Use GPT as your research assistant")

st.header(":blue[Would you like GPT to get data or information from the cases found?]")

st.markdown("""You don't have to use GPT. This app can extract metadata and get estimates of file length and GPT cost without using GPT. 
""")

gpt_activation_entry = st.checkbox(label = 'Use GPT (free for users by default)', value = st.session_state['df_master'].loc[0, 'Use GPT'])

st.session_state['df_master'].loc[0, 'Use GPT'] = gpt_activation_entry

st.caption(f"{gpt_cost_msg}")

st.subheader("Tell GPT what to get from each case")

st.success("""In question form, please tell GPT what to get from each case. **Enter one question per paragraph**. """)

st.markdown("""For each case, GPT will respond based only on information from the case itself. This is to minimise the risk of giving incorrect information (ie hallucination).
GPT will also provide references for its responses.
""")

gpt_questions_entry = st.text_area(label = f"Your questions (up to {question_characters_bound} characters)", height= 250, max_chars=question_characters_bound, value = st.session_state['df_master'].loc[0, 'Enter your questions for GPT']) 

st.session_state['df_master'].loc[0, 'Enter your questions for GPT'] = gpt_questions_entry

st.caption(f"This app uses model {basic_model} by default. This model will read up to approximately {round(tokens_cap(basic_model)*3/4)} words from each case.")

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

st.markdown("""This app will produce a spreadsheet with rows of cases and columns of answers to your questions. If you have a preferred layout, please feel free to upload an example for GPT to follow.""")

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
        
        st.error(f'Sorry, this app is unable to follow the selected example.')

        print(traceback.format_exc())

        st.session_state['error_msg'] = traceback.format_exc()
        
if len(st.session_state.df_example_to_show) > 0:
        
    st.success('For each case, GPT will *try* to produce something like the following:')

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
    
    st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or change the maximum number of cases to process? You can do so with your own GPT account.
""")
    
    own_account_entry = st.toggle(label = 'Use my own GPT account',  value = st.session_state['df_master'].loc[0, 'Use own account'])
    
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

        #if gpt_enhancement_entry:

            #st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = True
            
            #st.session_state.gpt_model = flagship_model

        #else:
            
            #st.session_state.gpt_model = basic_model
            #st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False

        st.write(f'**:green[You can change the maximum number of cases to process.]**')
        
        judgments_counter_bound_entry = st.slider(label = f'Up to {st.session_state["judgment_counter_max"]}', min_value = 1, max_value = st.session_state["judgment_counter_max"], step = 1, value = str_to_int(st.session_state['df_master'].loc[0, 'Maximum number of judgments']))
        
        if judgments_counter_bound_entry > st.session_state["judgment_batch_cutoff"]:
    
            st.warning(f"Given more than {st.session_state['judgment_batch_cutoff']} cases may need to be processes, this app will send your requested data to your nominated email address in about **2 business days**.")



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

#estimated_waiting_secs = int(float(min(st.session_state["judgment_batch_cutoff"], st.session_state['df_master'].loc[0, 'Maximum number of judgments'])))*30

#Instructions
st.markdown(f"""You can now press :green[PRODUCE data] to obtain a spreadsheet which hopefully has the data you seek. This app will immediately process up to {int(min(st.session_state['judgment_batch_cutoff'], st.session_state['df_master'].loc[0, 'Maximum number of judgments']))} cases. The estimated waiting time is **{min(st.session_state["judgment_batch_cutoff"], st.session_state['df_master'].loc[0, 'Maximum number of judgments'])*30/60} minute(s)**.
""")

#st.markdown(f"""You can now press :green[PRODUCE data] to obtain a spreadsheet which hopefully has the data you seek. This app will immediately process up to {min(st.session_state["judgment_batch_cutoff"], st.session_state['df_master'].loc[0, 'Maximum number of judgments'])} cases. The estimated waiting time is **{estimated_waiting_secs/60} minute(s)**.""")

if ((batch_mode_allowed() > 0) and (st.session_state.jurisdiction_page in pages_w_batch)):
    st.markdown(f"""Alternatively, you can press :orange[REQUEST data] to process up to {st.session_state["judgment_counter_max"]} cases. Your requested data will be sent to your nominated email address in about **2 business days**. 
""")


#Buttons

gpt_reset_button = st.button(label='REMOVE data', type = 'primary', disabled = not bool(st.session_state.need_resetting))

if ((batch_mode_allowed() > 0) and (st.session_state.jurisdiction_page in pages_w_batch)):
    with stylable_container(
        "orange",
        css_styles="""
        button {
            background-color: #F9F500;
            color: black;
        }""",
    ):
        batch_button = st.button(label = f"REQUEST data (up to {st.session_state['judgment_counter_max']} cases)", 
                                 help = 'You can only :orange[REQUEST] data once per session.', 
                                 disabled = bool((st.session_state.batch_submitted) or (st.session_state.disable_input))
                                )#, disabled = not bool(st.session_state['df_master'].loc[0, 'Maximum number of judgments'] > default_judgment_counter_bound))

with stylable_container(
    "green",
    css_styles="""
    button {
        background-color: #00FF00;
        color: black;
    }""",
):
    run_button = st.button(label = f"PRODUCE data now (up to {int(min(st.session_state['judgment_batch_cutoff'], st.session_state['df_master'].loc[0, 'Maximum number of judgments']))} cases)", 
                           help = 'You must :red[REMOVE] any data previously produced before producing new data.', 
                           disabled = bool((st.session_state.need_resetting) or (st.session_state.disable_input) or (bool(st.session_state['df_master'].loc[0, 'Maximum number of judgments'] > st.session_state["judgment_batch_cutoff"])))
                          )

#Display need resetting message if necessary
#if st.session_state.need_resetting == 1:
    #if len(st.session_state.df_individual) > 0:
        #st.warning('You must :red[REMOVE] the data previously produced before producing new data.')


# %% [markdown]
# ## ER only

# %%
#if st.session_state.gpt_model == flagship_model:
if ((own_account_entry) and (st.session_state.jurisdiction_page == 'pages/ER.py')):
    
    st.markdown("""The English Reports are available as PDFs. By default, this app will use an Optical Character Recognition (OCR) engine to extract text from the relevant PDFs, and then send such text to GPT.
    
Alternatively, you can send the relevant PDFs to GPT as images. This alternative approach may produce better responses for "untidy" PDFs, but tends to be **slower** and **costlier** than the default approach.
""")
    
    #st.write('Not getting the best responses for your images? You can try a more costly')
    #b64_help_text = 'GPT will process images directly, instead of text first extracted from images by an Optical Character Recognition engine. This only works for PNG, JPEG, JPG, GIF images.'
    er_run_button_b64 = st.button(label = 'SEND PDFs to GPT as images',
                             help = 'You must :red[REMOVE] any data previously produced before producing new data.', 
                           disabled = bool((st.session_state.need_resetting) or (st.session_state.disable_input) or (bool(st.session_state['df_master'].loc[0, 'Maximum number of judgments'] > st.session_state["judgment_batch_cutoff"])))
                                 )


# %% [markdown]
# ## Download entries and and outputs

# %%
#Create placeholder download buttons if previous entries and output in st.session_state:

if len(st.session_state.df_individual) > 0:

    #Current output
    if st.session_state["page_from"] == 'pages/GPT.py':

        download_buttons(df_master = st.session_state.df_master, df_individual = st.session_state.df_individual)

    #Previous entries and output
    else:
        download_buttons(df_master = st.session_state.df_master, df_individual = st.session_state.df_individual, saving = False, previous = True)


# %% [markdown]
# # Run etc buttons

# %% [markdown]
# ## All jurisdictions except ER

# %%
if gpt_keep_button:
    
    own_account_entries_function()
    
    download_buttons(df_master = st.session_state.df_master, df_individual = [], saving = True, previous = False)


# %%
if run_button:

    gpt_run_function()


# %%
if return_button:

    own_account_entries_function()
    
    st.session_state["page_from"] = 'pages/GPT.py'

    st.switch_page(st.session_state.jurisdiction_page)


# %%
if gpt_reset_button:
    
    st.session_state['df_individual'] = pd.DataFrame([])
    
    st.session_state['need_resetting'] = 0

    st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound
    
    st.rerun()


# %% [markdown]
# ## ER

# %%
if ((own_account_entry) and (st.session_state.jurisdiction_page == 'pages/ER.py')):

    if er_run_button_b64:

        er_run_b64_function()


# %% [markdown]
# ## Batch


# %%
if ((batch_mode_allowed() > 0) and (st.session_state.jurisdiction_page in pages_w_batch)):
    
    if batch_button:
        
        own_account_entries_function()
        
        batch_request_function()
    
    if st.session_state.batch_submitted and st.session_state.need_resetting and (st.session_state.batch_error == False):
        
        st.success('Your data request has been submitted. This app will send your requested data to your nominated email address in about **2 business days**. Feel free to close this app.')

        #Warning
        if gpt_activation_entry:
            if st.session_state.gpt_model == basic_model:
                st.warning('A low-cost GPT model is in use. Please be cautious.')
                st.caption(f'Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more cases or use a better model.')
            
            #if st.session_state.gpt_model == flagship_model:
                #st.warning('An expensive GPT model will process the cases found. Please be cautious.')

    if (st.session_state.batch_error) and (len(st.session_state.error_msg) > 0):

        st.error(search_error_display)



# %% [markdown]
# # Report error

# %%
if len(st.session_state.error_msg) > 0:

    report_error_button = st.button(label = 'REPORT the error', type = 'primary', help = 'Send your entries and a report of the error to the developer.')

    if report_error_button:

        st.session_state.error_msg = report_error(error_msg = st.session_state.error_msg, jurisdiction_page = st.session_state.jurisdiction_page, df_master = st.session_state.df_master)


