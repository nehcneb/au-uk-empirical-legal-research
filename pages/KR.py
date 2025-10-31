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
#from dateutil.relativedelta import *
from datetime import datetime, timedelta
import sys
import pause
import requests
from bs4 import BeautifulSoup, SoupStrainer
import httplib2
from urllib.request import urlretrieve
import os
import urllib.request
import io
from io import BytesIO
import string
import traceback

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
#import streamlit_ext as ste
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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, date_parser, save_input, search_error_display, display_df, download_buttons, list_value_check, report_error
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # Kercher Reports search engine

# %%
from functions.kr_functions import kr_search_tool, kr_search_url #kr_methods_list, kr_method_types, kr_search, kr_search_results_to_case_link_pairs, kr_judgment_text, kr_meta_judgment_dict,


# %%
from functions.common_functions import link


# %%
#function to create dataframe
def kr_create_df():

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

    query = ''
    try:
        query = query_entry
    except:
        print('query not entered')
        
    year = ''
    try:
        year = year_entry
    except:
        print('year not entered')

    letter = ''
    try:
        letter = letter_entry
    except:
        print('letter not entered')
    
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
            'Search query': query,
           'Specific year': year,
           'Decision begins with': letter,
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
from functions.gpt_functions import question_characters_bound, default_msg, default_caption, basic_model, flagship_model


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction



# %%
#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = basic_model
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    from functions.common_functions import API_key

    st.session_state['gpt_api_key'] = API_key
    

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
    st.session_state.df_master.loc[0, 'Search query'] = None
    st.session_state.df_master.loc[0, 'Specific year'] = None
    st.session_state.df_master.loc[0, 'Decision begins with'] = None

    #Generally applicable
    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

#Initialise jurisdiction_page
if 'jurisdiction_page' not in st.session_state:
    st.session_state['jurisdiction_page'] = 'pages/KR.py'

#Initialise error reporting status
if 'error_msg' not in st.session_state:
    st.session_state['error_msg'] = ''

# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %%
#if st.session_state.page_from != "pages/KR.py": #Need to add in order to avoid GPT page from showing form of previous page

#Create form

return_button = st.button('RETURN to first page')

st.header(f"Search the :blue[Kercher Reports]")

st.success(default_msg)

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [AustLII](https://www.austlii.edu.au/cgi-bin/viewdb/au/cases/nsw/NSWSupC/). This section mimics their search function.
""")

#method_entry = st.selectbox(label = 'Find', options = kr_methods_list, index = kr_methods_list.index(st.session_state.df_master.loc[0, 'Find (method)']))

st.info('Please enter only *one* of the following search terms.')

year_entry = st.number_input(label = 'Specific year (1788-1899)', min_value = 1788, max_value = 1899,  value = st.session_state.df_master.loc[0, 'Specific year'])

letter_entry = st.selectbox(label = 'Decision begins with', options = list(string.ascii_uppercase), index =  list_value_check(list(string.ascii_uppercase), st.session_state.df_master.loc[0, 'Decision begins with']))

query_entry = st.text_input(label = 'Search query', value = st.session_state.df_master.loc[0, 'Search query'])

if (year_entry and letter_entry) or (year_entry and query_entry) or (letter_entry and query_entry):

    st.warning('This app will use only one search term. It will first use specific year, then decision begins with, then search query.')

st.info("""You can preview the results returned by your search terms.""")

with stylable_container(
    "purple",
    css_styles="""
    button {
        background-color: purple;
        color: white;
    }""",
):
    preview_button = st.button(label = 'PREVIEW')


# %%

# %% [markdown]
# ## Preview

# %%
if preview_button:
    
    all_search_terms = str(year_entry) + str(letter_entry) + str(query_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
        
        with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):

            try:

                df_master = kr_create_df()
                
                search_results_w_count = kr_search_url(df_master)
                
                results_count = search_results_w_count['results_count']
            
                results_url = search_results_w_count['results_url']
        
                case_infos = search_results_w_count['case_infos']
            
                if results_count > 0:
                
                    df_preview = pd.DataFrame(case_infos)
            
                    #Get display settings
                    display_df_dict = display_df(df_preview)
            
                    df_preview = display_df_dict['df']
            
                    link_heading_config = display_df_dict['link_heading_config']
                        
                    #Display search results
                    st.success(f'Your search terms returned {results_count} result(s). Please see below for the top {min(results_count, default_judgment_counter_bound)} result(s).')
                                
                    st.dataframe(df_preview.head(default_judgment_counter_bound),  column_config=link_heading_config)
                
                else:
        
                    st.error(no_results_msg)

            except Exception as e:

                st.error(search_error_display)
                
                print(traceback.format_exc())

                st.session_state['error_msg'] = traceback.format_exc()



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
if keep_button:

    all_search_terms = str(year_entry) + str(letter_entry) + str(query_entry)
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:

        df_master = kr_create_df()

        save_input(df_master)
        
        download_buttons(df_master = df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:
    
    df_master = kr_create_df()

    save_input(df_master)

    st.session_state["page_from"] = 'pages/KR.py'

    st.switch_page("Home.py")

# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    all_search_terms = str(year_entry) + str(letter_entry) + str(query_entry)
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
    
        df_master = kr_create_df()

        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):
            
            try:
    
                search_results_w_count = kr_search_url(df_master)
                
                results_count = search_results_w_count['results_count']
                
                if results_count == 0:
                    st.error(no_results_msg)
    
                else:
    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/KR.py'
                    
                    st.switch_page('pages/GPT.py')

            except Exception as e:

                st.error(search_error_display)
                
                print(traceback.format_exc())

                st.session_state['error_msg'] = traceback.format_exc()


# %%

# %% [markdown]
# # Report error

# %%
if len(st.session_state.error_msg) > 0:

    report_error_button = st.button(label = 'REPORT the error', type = 'primary', help = 'Send your entries and a report of the error to the developer.')

    if report_error_button:

        st.session_state.error_msg = report_error(error_msg = st.session_state.error_msg, jurisdiction_page = st.session_state.jurisdiction_page, df_master = st.session_state.df_master)

