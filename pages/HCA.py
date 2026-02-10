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
from dateutil.parser import parse
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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, save_input, display_df, download_buttons, report_error
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg, search_error_display


# %% [markdown]
# # High Court of Australia search engine

# %%
from functions.hca_functions import hca_collections, hca_collections_years_dict, hca_collections_judges_dict, hca_search_methods_dict, hca_clr_volumns, hca_search_preview, hca_meta_labels_droppable



# %%
from functions.common_functions import link, is_date, list_value_check, date_parser


# %%
#function to create dataframe
def hca_create_df():

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
        
    #Other entries
    collection = collection_entry
    method = method_entry


    keywords = ''
    
    try:
        
        keywords = keywords_entry

    except:
        print(f'keywords not entered')

    citation = ''
    
    try:
        
        citation = citation_entry

    except:
        print(f'citation not entered')

    case_number = ''
    
    try:
        
        case_number = case_number_entry

    except:
        print(f'case_number not entered')
        

    judge = None
    try:
        judge = judge_entry

    except:
        print('judge not entered.')

    clr = None
    try:
        clr = str(clr_entry)

    except:
        print('CLR not entered.')
    
    year = None
    try:
        year = str(year_entry)

    except:
        print('year not entered.')

    #GPT choice and entry
    gpt_activation_status = False
   
    try:
        gpt_activation_status = gpt_activation_entry

    except:
        print('GPT activation status not entered.')
    
    gpt_questions = ''
    
    try:
        gpt_questions = gpt_questions_entry[0: question_characters_bound]
    
    except:
        print('GPT questions not entered.')

    #metadata choice

    meta_data_choice = True

    try:

        meta_data_choice = meta_data_entry
    
    except:
        print('Metadata choice not entered.')        
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Collection' : collection, 
            'Search method': method,
            'Keyword search': keywords, 
            'Medium neutral citation': citation, 
               'Case number': case_number,
               'Justices': judge,
               'Filter by CLR volume': clr,
              'Year': year,

               #The following are common to all pages
            'Metadata inclusion' : meta_data_choice,
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
from functions.common_functions import open_page, clear_cache_except_validation_df_master, tips, date_range_check


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
    st.session_state['df_master'].loc[0, 'Use GPT'] = True
    st.session_state['df_master'].loc[0, 'Use own account'] = False
    st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    st.session_state['df_master'].loc[0, 'Example'] = ''

    #Jurisdiction specific
    st.session_state.df_master.loc[0, 'Collection'] = hca_collections[0]
    st.session_state.df_master.loc[0, 'Search method'] = hca_search_methods_dict[hca_collections[0]][0]
    st.session_state.df_master.loc[0, 'Keyword search'] = None
    st.session_state.df_master.loc[0, 'Case number'] = None 
    st.session_state.df_master.loc[0, 'Justices']  = None
    st.session_state.df_master.loc[0, 'Filter by CLR volume'] = None
    st.session_state.df_master.loc[0, 'Year'] = None 

    st.session_state.df_master.loc[0, 'Medium neutral citation'] = None 
    
    #Generally applicable
    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

#Initialise jurisdiction_page
if 'jurisdiction_page' not in st.session_state:
    st.session_state['jurisdiction_page'] = 'pages/HCA.py'

#Initialise error reporting status
if 'error_msg' not in st.session_state:
    st.session_state['error_msg'] = ''

# %%
#HCA specific session states

#if (('court_filter_status' not in st.session_state) or ('df_master' not in st.session_state)):
    #st.session_state["court_filter_status"] = False


# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %%
#if st.session_state.page_from != "pages/HCA.py": #Need to add in order to avoid GPT page from showing form of previous page

#Create form

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[cases of the High Court of Australia]")

st.success(default_msg)

st.write(f'This app sources cases from the [High Court Judgments Database](https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term=)  and the [Open Australian Legal Corpus](https://huggingface.co/datasets/umarbutler/open-australian-legal-corpus) compiled by Umar Butler.')

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Judgments collection")

collection_entry = st.selectbox(label = 'Select a judgments collection to search', options = hca_collections, index = list_value_check(hca_collections, st.session_state.df_master.loc[0, 'Collection']))

if collection_entry != st.session_state.df_master.loc[0, 'Collection']:

    st.session_state['df_master'].loc[0, 'Justices'] = None

    st.session_state['df_master'].loc[0, 'Filter by CLR volume'] = None
    
    st.session_state['df_master'].loc[0, 'Year'] = None

#method_entry = st.selectbox(label = 'Select a search method', options = hca_search_methods_dict[collection_entry], index = list_value_check(hca_search_methods_dict[collection_entry], st.session_state.df_master.loc[0, 'Search method']))

method_entry = hca_search_methods_dict[collection_entry][0]

last_entry = None

st.subheader("Your search terms")

st.markdown("""For search tips, please visit the [High Court Judgments Database](https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term=). This section largely mimics their judgments search function.
""")

if method_entry:

    if 'Keyword' in method_entry:
            
        keywords_entry = st.text_input(label = 'Keyword search', 
                                           value = st.session_state.df_master.loc[0, 'Keyword search'],
                                          help = "")
        
        st.caption('Also searches case name and party names')

        if keywords_entry:

            last_entry = keywords_entry
    
    if 'case number' in method_entry:
        
        case_number_entry = st.text_input(label = 'Case number', 
                                          value = st.session_state.df_master.loc[0, 'Case number'],
                                         )

        if case_number_entry:

            last_entry = case_number_entry
        
    if 'Justices' in method_entry:
        
        judge_entry = st.selectbox(label = 'Justices', 
                                    options = hca_collections_judges_dict[collection_entry],
                                    index = list_value_check(hca_collections_judges_dict[collection_entry], st.session_state.df_master.loc[0, 'Justices']),
                                     help = "If you cannot change this entry, please press :red[RESET] and try again."
                                    )

        if judge_entry:

            last_entry = judge_entry

    if 'year' in method_entry:
        
        year_entry = st.selectbox(label = 'Year', 
                                        options = hca_collections_years_dict[collection_entry],
                                        index = list_value_check(hca_collections_years_dict[collection_entry], st.session_state.df_master.loc[0, 'Year']),
                                     help = "If you cannot change this entry, please press :red[RESET] and try again."
                                        )

        if year_entry:

            last_entry = year_entry
    
    if 'CLR' in method_entry:
        
        clr_entry = st.selectbox(label = 'Filter by CLR volume', 
                                 options = hca_clr_volumns,
                                 index = list_value_check(hca_clr_volumns, st.session_state.df_master.loc[0, 'Filter by CLR volume']),
                                  help = "If you cannot change this entry, please press :red[RESET] and try again."
                                )

        if clr_entry:

            last_entry = clr_entry

    if 'Citation' in method_entry:
        
        citation_entry = st.text_input(label = 'Medium neutral citation', 
                                   value = st.session_state.df_master.loc[0, 'Medium neutral citation'],
                                  )

        if method_entry:

            last_entry = method_entry
        

st.subheader("Judgment metadata collection")

st.markdown("""Would you like to obtain judgment metadata? Such data include the judge(s), the decision date and so on. 

Case name and medium neutral citation are always included with your results.""")

meta_data_entry = st.checkbox('Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])

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

    hca_search_terms = str(last_entry) 
    
    if hca_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
        
        with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):

            try:
            
                df_master = hca_create_df()
        
                search_results_w_count = hca_search_preview(df_master)
                
                results_count = search_results_w_count['results_count']
        
                case_infos = search_results_w_count['case_infos']
        
                results_url = search_results_w_count['results_url']
        
                if results_count > 0:
        
                    df_preview = pd.DataFrame(case_infos)
        
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

    #Check whether search terms entered

    hca_search_terms = str(last_entry) 
    
    if hca_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
            
    else:
            
        df_master = hca_create_df()

        save_input(df_master)
    
        download_buttons(df_master = df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:

    df_master = hca_create_df()

    save_input(df_master)

    st.session_state["page_from"] = 'pages/HCA.py'

    st.switch_page("Home.py")

# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:
    
    hca_search_terms = str(last_entry) 
        
    if hca_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
    
        df_master = hca_create_df()
        
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            try:

                search_results_w_count = hca_search_preview(df_master)
                
                results_count = search_results_w_count['results_count']
                
                if results_count == 0:
                    
                    st.error(no_results_msg)
    
                else:
                    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/HCA.py'
                    
                    st.switch_page('pages/GPT.py')

            except Exception as e:

                st.error(search_error_display)
                
                print(traceback.format_exc())

                st.session_state['error_msg'] = traceback.format_exc()


# %% [markdown]
# # Report error

# %%
if len(st.session_state.error_msg) > 0:

    report_error_button = st.button(label = 'REPORT the error', type = 'primary', help = 'Send your entries and a report of the error to the developer.')

    if report_error_button:

        st.session_state.error_msg = report_error(error_msg = st.session_state.error_msg, jurisdiction_page = st.session_state.jurisdiction_page, df_master = st.session_state.df_master)

