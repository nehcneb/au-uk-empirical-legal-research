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
import urllib.request
#import pypdf
import io
from io import BytesIO
import traceback

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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg, search_error_display


# %% [markdown]
# # English Reports search engine

# %%
from functions.er_functions import er_methods_list, er_method_types, er_search, er_search_url, er_search_results_to_case_link_pairs, er_judgment_text, er_meta_judgment_dict, er_judgment_tokens_b64, er_meta_judgment_dict_b64, er_GPT_b64_json, er_engage_GPT_b64_json



# %%
from functions.common_functions import link


# %%
#function to create dataframe
def er_create_df():

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
    
    #Judgment counter bound
    try:
        judgments_counter_bound = judgments_counter_bound_entry
    except:
        print('judgments_counter_bound not entered')
        judgments_counter_bound = default_judgment_counter_bound

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
        gpt_questions = gpt_questions_entry[0: question_characters_bound]
    
    except:
        print('GPT questions not entered.')
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Enter search query': query_entry,
           'Find (method)': method_entry, 
          'Metadata inclusion': True, #Placeholder even though no metadata collected
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': gpt_questions, 
            'Use GPT': gpt_activation_status,
              'Use own account': own_account,
            'Use flagship version of GPT' : gpt_enhancement
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
        
    return df_master_new


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from functions.gpt_functions import question_characters_bound, default_msg, default_caption


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction



# %%
#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-4o-mini"
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

# %% [markdown]
# # Streamlit form, functions and parameters

# %%
#Import functions and variables
from functions.common_functions import open_page, clear_cache_except_validation_df_master, tips


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default values

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
    st.session_state['df_master'].loc[0, 'Metadata inclusion'] = True
    st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound
    st.session_state['df_master'].loc[0, 'Enter your questions for GPT'] = ''
    st.session_state['df_master'].loc[0, 'Use GPT'] = False
    st.session_state['df_master'].loc[0, 'Use own account'] = False
    st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    st.session_state['df_master'].loc[0, 'Example'] = ''

    #Jurisdiction specific
    st.session_state.df_master.loc[0, 'Enter search query'] = None
    st.session_state.df_master.loc[0, 'Find (method)'] = 'this Boolean query'

    #Generally applicable
    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %%
#if st.session_state.page_from != "pages/ER.py": #Need to add in order to avoid GPT page from showing form of previous page

#Create form

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[the English Reports]")

st.success(default_msg)

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [CommonLII](http://www.commonlii.org/form/search1.html?mask=uk/cases/EngR). This section mimics their search function.
""")

method_entry = st.selectbox(label = 'Find', options = er_methods_list, index= er_methods_list.index(st.session_state.df_master.loc[0, 'Find (method)']))

query_entry = st.text_input(label = 'Enter search query', value = st.session_state.df_master.loc[0, 'Enter search query'])
    
st.info("""You can preview the judgments returned by your search terms. You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
""")

with stylable_container(
    "purple",
    css_styles="""
    button {
        background-color: purple;
        color: white;
    }""",
):
    preview_button = st.button(label = 'PREVIEW on CommonLII (in a popped up window)')


# %% [markdown]
# ## Buttons

# %%
#Buttons

#col1, col2, col3, col4 = st.columns(4, gap = 'small')

#with col1:

    #reset_button = st.button(label='RESET', type = 'primary')

#with col4:
with stylable_container(
    "green",
    css_styles="""
    button {
        background-color: #00FF00;
        color: black;
    }""",
):
    next_button = st.button(label='NEXT')

keep_button = st.button('SAVE')


# %% [markdown]
# # Save and run

# %%
if preview_button:
    
    df_master = er_create_df()

    judgments_url = er_search_url(df_master)['results_url']

    open_page(judgments_url)


# %%
if keep_button:

    all_search_terms = str(query_entry)
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
                            
        df_master = er_create_df()

        save_input(df_master)
    
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

    df_master = er_create_df()

    save_input(df_master)

    st.session_state["page_from"] = 'pages/ER.py'

    st.switch_page("Home.py")

# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    all_search_terms = str(query_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
    
        df_master = er_create_df()

        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            try:
                er_soup = er_search_url(df_master)['soup']
                
                if 'Documents found:   0' in str(er_soup):
                    st.error(no_results_msg)
                    
                else:
    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/ER.py'
                    
                    st.switch_page('pages/GPT.py')

            except Exception as e:
                print(search_error_display)
                print(e)
                print(traceback.format_exc())
                st.error(search_error_display)
                st.error(e)
                st.error(traceback.format_exc())
