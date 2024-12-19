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
#import pypdf
import io
from io import BytesIO

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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input, display_df, download_buttons
#Import variables
from functions.common_functions import today_in_nums, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg, search_error_display


# %% [markdown]
# # UKPO search engine

# %%
from functions.ukpo_functions import ukpo_search_tool, ukpo_search_function, ukpo_search_preview, ukpo_outcomes_dict, ukpo_topics_dict, ukpo_types_dict, ukpo_sortby_dict


# %%
from functions.common_functions import link, reverse_link


# %%
#function to create dataframe
def ukpo_create_df():

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

    #Entries

    keyword = ''
    
    if keyword_entry:
        
        keyword = keyword_entry

    outcomes_list = []
    
    if outcomes_list_entry:
        
        outcomes_list = outcomes_list_entry

    topics_list = []

    if topics_list_entry:

        topics_list = topics_list_entry

    types_list = []

    if types_list_entry:

        types_list = types_list_entry

    sortby = list(ukpo_sortby_dict.keys())[-1]

    if sortby_entry:

        sortby = sortby_entry
    #Entries common to all jurisdictions
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

    #metadata choice
    meta_data_choice = True
        
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Keyword search': keyword, 
            'Select outcome': outcomes_list,
            'Select complaint topic': topics_list,
            'Select type': types_list, 
            'Sort by': sortby, 
            'Metadata inclusion': meta_data_choice,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': gpt_questions, 
            'Use GPT': gpt_activation_status,
           'Use own account': own_account,
            'Use flagship version of GPT': gpt_enhancement
          }

    df_master_new = pd.DataFrame([new_row])#, index = [0])
    
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
from functions.common_functions import open_page, tips, clear_cache, list_value_check


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default values

if 'own_account' not in st.session_state:
    st.session_state['own_account'] = False

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

    #Jurisdiction specific
    jurisdiction_specific_dict = {'Keyword search': '',
    'Select outcome': [],
    'Select complaint topic': [],
    'Select type': [],
    'Sort by': list(ukpo_sortby_dict.keys())[-1],
    }

    #Make into  df
    df_master_dict.update(jurisdiction_specific_dict)
    
    st.session_state['df_master'] = pd.DataFrame([df_master_dict])

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
#Create form

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[cases of the Pensions Ombudsman]")

st.success(default_msg)

st.write(f'This app sources cases from [the Pensions Ombudsman](https://www.pensions-ombudsman.org.uk/decisions).')

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [the Pensions Ombudsman](https://www.pensions-ombudsman.org.uk/decisions). This section mimics their search function.
""")

keyword_entry = st.text_input(label = 'Keyword search', value = st.session_state['df_master'].loc[0, 'Keyword search'])


outcomes_list_entry = st.multiselect(label = 'Select outcome', 
                                      options = list(ukpo_outcomes_dict.keys()), 
                                      default = st.session_state['df_master'].loc[0, "Select outcome"]
                                         )

topics_list_entry = st.multiselect(label = 'Select complaint topic', 
                                      options = list(ukpo_topics_dict.keys()), 
                                      default = st.session_state['df_master'].loc[0, "Select complaint topic"]
                                         )

types_list_entry = st.multiselect(label = 'Select type', 
                                      options = list(ukpo_types_dict.keys()), 
                                      default = st.session_state['df_master'].loc[0, "Select type"]
                                         )

sortby_entry = st.selectbox(label = "Sort by", options = list(ukpo_sortby_dict.keys()), index = list(ukpo_sortby_dict.keys()).index(st.session_state['df_master'].loc[0, 'Sort by']))

#st.subheader("Case metadata collection")

#st.markdown("""Would you like to obtain case metadata? Such data include the judge(s), the filing date and so on. 

#You will always obtain case names and citations.
#""")

#meta_data_entry = st.checkbox(label = 'Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])

meta_data_entry = True

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


# %% [markdown]
# ## Preview

# %%
if preview_button:
    
    ukpo_search_terms = str(keyword_entry) + str(outcomes_list_entry) + str(topics_list_entry) + str(types_list_entry)
    
    if ukpo_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
        with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):
            
            df_master = ukpo_create_df()
    
            search_results_w_count = ukpo_search_preview(df_master)
            
            results_count = search_results_w_count['results_count']
    
            results_to_show = search_results_w_count['results_to_show']
    
            results_url = search_results_w_count['results_url']
    
            if results_count > 0:
    
                df_preview = pd.DataFrame(results_to_show)
    
                #Get display settings
                display_df_dict = display_df(df_preview)
    
                df_preview = display_df_dict['df']
    
                link_heading_config = display_df_dict['link_heading_config']
    
                #Display search results
                st.success(f'Your search terms returned {results_count} result(s). Please see below for the top {min(results_count, default_judgment_counter_bound)} result(s).')
                            
                st.dataframe(df_preview.head(default_judgment_counter_bound),  column_config=link_heading_config)
    
                st.page_link(results_url, label=f"SEE all search results (in a popped up window)", icon = "🌎")
        
            else:
                st.error(no_results_msg)


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

    #Check whether search terms entered

    ukpo_search_terms = str(keyword_entry) + str(outcomes_list_entry) + str(topics_list_entry) + str(types_list_entry)
    
    if ukpo_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = ukpo_create_df()

        save_input(df_master)

        download_buttons(df_master = df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:

    df_master = ukpo_create_df()

    save_input(df_master)
    
    st.session_state["page_from"] = 'pages/UKPO.py'

    st.switch_page("Home.py")

# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    ukpo_search_terms = str(keyword_entry) + str(outcomes_list_entry) + str(topics_list_entry) + str(types_list_entry)
    
    if ukpo_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = ukpo_create_df()
    
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            try:

                search_results_w_count = ukpo_search_preview(df_master)
                
                results_count = search_results_w_count['results_count']
                
                if results_count == 0:
                    
                    st.error(no_results_msg)
    
                else:
                    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/UKPO.py'
                    
                    st.switch_page('pages/GPT.py')

            except Exception as e:
                print(search_error_display)
                print(e)
                st.error(search_error_display)
                st.error(e)

