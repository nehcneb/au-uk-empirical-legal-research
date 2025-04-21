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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, save_input, display_df, download_buttons
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg, search_error_display


# %% [markdown]
# # High Court of Australia search engine

# %%
from functions.hca_functions import hca_collections, parties_include_categories, year_is_categories, judge_includes_categories, hca_search, hca_meta_labels_droppable, hca_meta_judgment_dict, hca_meta_judgment_dict_alt#, hca_mnc_to_link_browse, hca_citation_to_link, hca_mnc_to_link, hca_load_data, hca_data_url, hca_df, hca_judgment_to_exclude, hca_search_results_to_judgment_links_filtered_df, hca_search_url, hca_year_range, hca_judge_list, hca_party_list, hca_terms_to_add, hca_enhanced_search  
#hca_search_results_to_judgment_links, hca_pdf_judgment


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
    quick_search = quick_search_entry
    citation =  citation_entry

    full_text = ''
    try:
        full_text = full_text_entry

    except:
        print('Full text not entered.')

    parties_include = list(parties_include_categories.keys())[0]
    try:
        parties_include = parties_include_entry

    except:
        print('parties_include not entered.')

    parties = ''
    try:
        parties = parties_entry

    except:
        print('parties not entered.')

    year_is = list(year_is_categories.keys())[0]
    try:
        year_is = year_is_entry

    except:
        print('year_is not entered.')

    year = ''
    try:
        year = year_entry

    except:
        print('year not entered.')

    case_number = ''
    try:
        case_number = case_number_entry

    except:
        print('case_number not entered.')

    judge_is = list(judge_includes_categories.keys())[0]
    try:
        judge_is = judge_is_entry

    except:
        print('judge_is not entered.')

    judge = ''
    try:
        judge = judge_entry

    except:
        print('judge not entered.')
    
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
            'Quick search': quick_search, 
            'Search for citation': citation, 
             'Full text search': full_text, 
           'Parties include/do not include': parties_include, 
               'Parties': parties,
               'Year is/is not': year_is,
               'Year': year,
               'Case number': case_number,
               'Judge includes/does not include': judge_is,
               'Judge': judge,
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

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

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
    st.session_state['df_master'].loc[0, 'Use GPT'] = False
    st.session_state['df_master'].loc[0, 'Use own account'] = False
    st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    st.session_state['df_master'].loc[0, 'Example'] = ''

    #Jurisdiction specific
    st.session_state.df_master.loc[0, 'Collection'] = 'Judgments 2000-present' 
    st.session_state.df_master.loc[0, 'Quick search'] = None
    st.session_state.df_master.loc[0, 'Full text search'] = None 
    st.session_state.df_master.loc[0, 'Search for citation'] = None 
    st.session_state.df_master.loc[0, 'Parties include/do not include'] = list(parties_include_categories.keys())[0] 
    st.session_state.df_master.loc[0, 'Parties'] = None 
    st.session_state.df_master.loc[0, 'Year is/is not'] = list(year_is_categories.keys())[0] 
    st.session_state.df_master.loc[0, 'Year'] = None 
    st.session_state.df_master.loc[0, 'Case number'] = None 
    st.session_state.df_master.loc[0, 'Judge includes/does not include'] = list(judge_includes_categories.keys())[0] 
    st.session_state.df_master.loc[0, 'Judge']  = None

    #Generally applicable
    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

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

st.subheader("Judgment collection")

collection_entry = st.selectbox(label = 'Select one to search', options = hca_collections, index = list_value_check(hca_collections, st.session_state.df_master.loc[0, 'Collection']))

st.subheader("Your search terms")

st.markdown("""For search tips, please visit the [High Court Judgments Database](https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term=). This section mimics their judgments search function.
""")

quick_search_entry = st.text_input(label = 'Quick search (searches searches party names and the catchwords of the judgments)', 
                                   value = st.session_state.df_master.loc[0, 'Quick search']
                                  )

citation_entry = st.text_input(label = 'Search for citation', 
                               value = st.session_state.df_master.loc[0, 'Search for citation'],
                               help = 'Enter full citation eg [2013] HCA 1 or 249 CLR 435'
                              )

if collection_entry != hca_collections[-1]:

    full_text_entry = st.text_input(label = 'Full text search', 
                                    value = st.session_state.df_master.loc[0, 'Full text search'],
                                    help = 'Search the full text of the cases.'
                                   )

else:
    full_text_entry = ''

st.subheader("Filter search")

parties_col1, parties_col2 = st.columns(2)

with parties_col1:
    parties_include_entry = st.selectbox(label = 'Parties include/do not include', options = parties_include_categories, index = list_value_check(list(parties_include_categories.keys()), st.session_state.df_master.loc[0, 'Parties include/do not include']))
with parties_col2:
    parties_entry = st.text_input(label = 'Parties', value = st.session_state.df_master.loc[0, 'Parties'])

year_col1, year_col2 = st.columns(2)

with year_col1:
    year_is_entry = st.selectbox(label = 'Year is/is not', options = year_is_categories, index = list_value_check(list(year_is_categories.keys()), st.session_state.df_master.loc[0, 'Year is/is not']))
with year_col2:
    year_entry = st.text_input(label = 'Year', 
                               value = st.session_state.df_master.loc[0, 'Year'],
                              help = 'You can search a range e.g. 2003 TO 2004'
                              )

if collection_entry != hca_collections[-1]:

    case_number_entry = st.text_input(label = 'Case number', value = st.session_state.df_master.loc[0, 'Case number']) 

    judge_col1, judge_col2 = st.columns(2)
    
    with judge_col1:
        judge_includes_entry = st.selectbox(label = 'Judge includes/does not include', options = judge_includes_categories, index = list_value_check(list(judge_includes_categories.keys()), st.session_state.df_master.loc[0, 'Judge includes/does not include']))
    with judge_col2:
        judge_entry = st.text_input(label = 'Judge', value = st.session_state.df_master.loc[0, 'Judge'])

else:
    case_number_entry = ''
    judge_includes_entry = list(judge_includes_categories.keys())[0]
    judge_entry = ''

#st.subheader("Judgment metadata collection")

#st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the decision date and so on. 

#Case name and medium neutral citation are always included with your results.""")

#meta_data_entry = st.checkbox('Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])
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

    all_search_terms = str(quick_search_entry) + str(citation_entry) + str(full_text_entry) + str(parties_entry)  + str(year_entry)  + str(judge_entry) 
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
        
        with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):
    
            df_master = hca_create_df()
                
            #Conduct search    
            hca_search_dict = hca_search(collection = df_master.loc[0, 'Collection'], 
                           quick_search = df_master.loc[0, 'Quick search'],
                           citation = df_master.loc[0, 'Search for citation'], 
                            full_text = df_master.loc[0, 'Full text search'], 
                            parties_include = df_master.loc[0, 'Parties include/do not include'],
                            parties = df_master.loc[0, 'Parties'],
                            year_is = df_master.loc[0, 'Year is/is not'],
                            year = df_master.loc[0, 'Year'], 
                            case_number = df_master.loc[0, 'Case number'], 
                            judge_is = df_master.loc[0, 'Judge includes/does not include'],
                            judge = df_master.loc[0, 'Judge'],
                            judgment_counter_bound = default_judgment_counter_bound
                            )
            
            results_count = hca_search_dict['results_count']
    
            case_infos = hca_search_dict['case_infos']
        
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

    all_search_terms = str(quick_search_entry) + str(citation_entry) + str(full_text_entry) + str(parties_entry)  + str(year_entry)  + str(judge_entry) 
    
    if all_search_terms.replace('None', '') == "":

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
    all_search_terms = str(quick_search_entry) + str(citation_entry) + str(full_text_entry) + str(parties_entry)  + str(year_entry)  + str(judge_entry) 
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
    
        df_master = hca_create_df()
        
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            try:
                
                hca_search_dict = hca_search(collection = df_master.loc[0, 'Collection'], 
                               quick_search = df_master.loc[0, 'Quick search'],
                               citation = df_master.loc[0, 'Search for citation'], 
                                full_text = df_master.loc[0, 'Full text search'], 
                                parties_include = df_master.loc[0, 'Parties include/do not include'],
                                parties = df_master.loc[0, 'Parties'],
                                year_is = df_master.loc[0, 'Year is/is not'],
                                year = df_master.loc[0, 'Year'], 
                                case_number = df_master.loc[0, 'Case number'], 
                                judge_is = df_master.loc[0, 'Judge includes/does not include'],
                                judge = df_master.loc[0, 'Judge'],
                                judgment_counter_bound = default_judgment_counter_bound
                                )
                
                results_count = hca_search_dict['results_count']
                    
                if results_count == 0:
                    
                    st.error(no_results_msg)
    
                else:
                    
                    save_input(df_master)
                    
                    st.session_state["page_from"] = 'pages/HCA.py'
                    
                    st.switch_page('pages/GPT.py')
           
            except Exception as e:
                print(search_error_display)
                print(e)
                st.error(search_error_display)
                st.error(e)
