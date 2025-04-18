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
from functions.hca_functions import hca_collections, hca_search, hca_pdf_judgment, hca_meta_labels_droppable, hca_meta_judgment_dict, hca_meta_judgment_dict_alt, hca_mnc_to_link_browse, hca_citation_to_link, hca_mnc_to_link, hca_load_data, hca_data_url, hca_df, hca_judgment_to_exclude, hca_search_results_to_judgment_links_filtered_df, hca_search_url, hca_year_range, hca_judge_list, hca_party_list, hca_terms_to_add, hca_enhanced_search  
#hca_search_results_to_judgment_links


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

    #Can't figure out how to add the following based on the HCA's filtered search function
    #parties_include = parties_include_entry
    #parties_not_include = parties_not_include_entry
    #year_is = year_is_entry
    #year_is_not = year_is_not_entry
    #case_number = case_number_entry
    #judges_include = judges_include_entry
    #judges_not_include = judges_not_include_entry

    #The following are based on my own filter

    own_parties_include = ''

    try:
        own_parties_include = own_parties_include_entry
    
    except:
        
        print('Parties to include not entered.')

    own_parties_exclude = ''

    try:
        own_parties_exclude = own_parties_exclude_entry

    except:
        print('Parties to exclude not entered.')

    own_judges_include = ''

    try:
        own_judges_include = own_judges_include_entry
    
    except:
        print('judges to include not entered.')

    own_judges_exclude = ''

    try:
        own_judges_exclude = own_judges_exclude_entry

    except:
        print('judges to exclude not entered.')

    #Dates
    
    before_date = ''

    try:

        before_date = str(before_date_entry.strftime('%d')) + '-' + str(before_date_entry.strftime('%B'))[:3] + '-' + str(before_date_entry.strftime('%Y'))

    except:
        print('Decision date is before not entered')
        pass

    
    after_date = ''
    
    try:
        after_date = str(after_date_entry.strftime('%d'))  + '-' + str(after_date_entry.strftime('%B'))[:3]  + '-' + str(after_date_entry.strftime('%Y'))
        
    except:
        print('Decision date is after not entered')
    
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
            'Search for medium neutral citation': citation, 
             'Full text search': full_text, 
            #Can't figure out how to add the following based on the HCA's filtered search function
           #'Parties include': parties_include, 
            #'Parties do not include': parties_not_include, 
            #'Year is': year_is, 
            #'Year is not': year_is_not, 
            #'Case number': case_number, 
            #'Judges include': judges_include, 
            #'Judges do not include': judges_not_include, 
               #The following are based on my own filter
           'Parties include': own_parties_include, 
            'Parties do not include': own_parties_exclude, 
            #'Before this year': own_min_year, 
            #'After this year': own_max_year, 
           'Decision date is after': after_date,
            'Decision date is before': before_date, 
           #'Case numbers include': own_case_numbers_include, 
            #'Case numbers do not include': own_case_numbers_exclude, 
            'Judges include': own_judges_include, 
            'Judges do not include': own_judges_exclude, 
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
    st.session_state.df_master.loc[0, 'Search for medium neutral citation'] = None 
    st.session_state.df_master.loc[0, 'Parties include'] = None 
    st.session_state.df_master.loc[0, 'Parties do not include'] = None 
    st.session_state.df_master.loc[0, 'Decision date is after'] = None 
    st.session_state.df_master.loc[0, 'Decision date is before'] = None 
    #st.session_state.df_master.loc[0, 'Case numbers include'] = None 
    #st.session_state.df_master.loc[0, 'Case numbers do not include'] = None 
    st.session_state.df_master.loc[0, 'Judges include'] = None 
    st.session_state.df_master.loc[0, 'Judges do not include']  = None

    #Generally applicable
    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

# %%
#HCA specific session states

if (('court_filter_status' not in st.session_state) or ('df_master' not in st.session_state)):
    st.session_state["court_filter_status"] = False


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

st.markdown("""For search tips, please visit the [High Court Judgments Database](https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term=). This section largely mimics their judgments search function except the filter function.
""")

quick_search_entry = st.text_input(label = 'Quick search (search party names and catchwords)', value = st.session_state.df_master.loc[0, 'Quick search'])

citation_entry = st.text_input(label = 'Search for medium neutral citation (eg [2014] HCA 1)', value = st.session_state.df_master.loc[0, 'Search for medium neutral citation'])
st.caption('CLR or other citations may work only up to 2014.')

#if citation_entry:
    #if 'hca' not in citation_entry.lower():
        
        #st.error('Sorry, this free version only searches for medium neutral citation (eg [2014] HCA 1).')

if collection_entry != '1 CLR - 100 CLR (judgments 1903-1958)':

    full_text_entry = st.text_input(label = 'Full text search', value = st.session_state.df_master.loc[0, 'Full text search'])

else:
    full_text_entry = ''

st.subheader("Filter your search results")

filter_toggle = st.toggle(label = "Filter/unfilter", value = st.session_state.court_filter_status)

if filter_toggle:
    
    st.warning("Filtering your search results may *significantly* prolong the processing time.")

    st.session_state['court_filter_status'] = True
    
    own_parties_include_entry = st.text_input(label = 'Parties include (separate parties by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Parties include'])
    st.caption('If entered, then this app will only process cases that include at least one of the parties entered.')
    
    own_parties_exclude_entry = st.text_input(label = 'Parties do not include (separate parties by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Parties do not include'])
    st.caption('If entered, then this app will only process cases that do not include any of the parties entered.')

    #Get year range allowed

    year_start = 1903
    date_start = date(year_start, 1, 1)
    
    for year in ['2000', '1948', '1903']:
        if year in collection_entry:
            year_start = int(year)
            date_start = datetime(year_start, 1, 1)
            break
    
    year_end = datetime.now().year
    date_end = datetime.now()
    
    for year in ['1999', '1958']:
        if year in collection_entry:
            year_end = int(year)
            date_end = datetime(year_end, 12, 31)
            break


    
    after_date_entry = st.date_input(label = 'Decision date is after', value = date_range_check(date_start, date_end, date_parser(st.session_state.df_master.loc[0, 'Decision date is after'])), format="DD/MM/YYYY", min_value = date_start, max_value = date_end, help = "If you cannot change this date entry, please press :red[RESET] and try again.")
    
    before_date_entry = st.date_input(label = 'Decision date is before', value = date_range_check(date_start, date_end, date_parser(st.session_state.df_master.loc[0, 'Decision date is before'])), format="DD/MM/YYYY", min_value = date_start,  max_value = date_end,help = "If you cannot change this date entry, please press :red[RESET] and try again.")
    
    if collection_entry != '1 CLR - 100 CLR (judgments 1903-1958)':
    
        #own_case_numbers_include_entry = st.text_input(label = 'Case numbers include (separate case numbers by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Case numbers include']) 
        #st.caption('If entered, then this app will only process cases with at least one of the case numbers entered.')
    
        #own_case_numbers_exclude_entry = st.text_input(label = 'Case numbers do not include (separate case numbers by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Case numbers do not include']) 
        #st.caption('If entered, then this app will only process cases without any of the case numbers entered.')
    
        own_judges_include_entry = st.text_input(label = 'Judges include (separate judges by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Judges include'])
        st.caption('If entered, then this app will only process cases heared by at least one of the judges entered.')
        
        own_judges_exclude_entry = st.text_input(label = 'Judges do not include (separate judges by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Judges do not include'])
        st.caption('If entered, then this app will only process cases not heared by any of the judges entered.')
        
        #if ((own_judges_include_entry) or (own_judges_exclude_entry)):
            #st.session_state['filtering_message'] = True

        #else:
            #st.session_state['filtering_message'] = False
    
    #else:
        #own_case_numbers_include_entry = ''
        #own_case_numbers_exclude_entry = ''
        #own_judges_include_entry = ''
        #own_judges_exclude_entry = ''

else: #if filter_toggle == False

    st.success('Your search results will not be filtered.')
    
    st.session_state['court_filter_status'] = False

    st.session_state.df_master.loc[0, 'Parties include'] = None 
    st.session_state.df_master.loc[0, 'Parties do not include'] = None 
    st.session_state.df_master.loc[0, 'Decision date is after'] = None 
    st.session_state.df_master.loc[0, 'Decision date is before'] = None 
    #st.session_state.df_master.loc[0, 'Case numbers include'] = None 
    #st.session_state.df_master.loc[0, 'Case numbers do not include'] = None 
    st.session_state.df_master.loc[0, 'Judges include'] = None 
    st.session_state.df_master.loc[0, 'Judges do not include']  = None


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

    with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):

        df_master = hca_create_df()
        
        results_url_count = hca_search_url(df_master)
        
        results_url = results_url_count['results_url']
    
        results_count = int(float(results_url_count['results_count']))
    
        results_count_to_display = results_count
    
        #Conduct search
        judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
    
        case_infos = hca_enhanced_search(collection = df_master.loc[0, 'Collection'], 
                            quick_search = df_master.loc[0, 'Quick search'], 
                            full_text = df_master.loc[0, 'Full text search'],
                        judgments_counter_bound = judgments_counter_bound,
                        own_parties_include = df_master.loc[0, 'Parties include'], 
                        own_parties_exclude = df_master.loc[0, 'Parties do not include'], 
                        #own_min_year, 
                        #own_max_year, 
                        after_date = df_master.loc[0, 'Decision date is after'], 
                         before_date = df_master.loc[0, 'Decision date is before'], 
                        #own_case_numbers_include, 
                        #own_case_numbers_exclude, 
                        own_judges_include = df_master.loc[0, 'Judges include'], 
                        own_judges_exclude = df_master.loc[0, 'Judges do not include']
                        )
    
        results_count = min(len(case_infos), results_count)
    
        if results_count > 0:
            
            df_preview = pd.DataFrame(case_infos)
    
            #Get display settings
            display_df_dict = display_df(df_preview)
    
            df_preview = display_df_dict['df']
    
            link_heading_config = display_df_dict['link_heading_config']
    
            #Update results count for display
            if len(case_infos) < judgments_counter_bound:
                results_count_to_display = len(case_infos)
            
            #Display search results
            st.success(f'Your search terms returned up to {results_count_to_display} result(s). Please see below for the top {min(results_count, default_judgment_counter_bound)} result(s).')
                        
            st.dataframe(df_preview.head(default_judgment_counter_bound),  column_config=link_heading_config)
    
            #The HCA's search page does not reflect filters
            #st.page_link(results_url, label=f"SEE all search results (in a popped up window)", icon = "🌎")
    
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

    all_search_terms = str(quick_search_entry) + str(citation_entry) + str(full_text_entry)
    
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
    all_search_terms = str(quick_search_entry) + str(citation_entry) + str(full_text_entry)
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
    
        df_master = hca_create_df()
        
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            try:
                
                results_url_count = hca_search_url(df_master)
                                
                results_count = int(float(results_url_count['results_count']))

                if filter_toggle:
                    #Conduct actual search if filter is turned on
                    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                
                    case_infos = hca_enhanced_search(collection = df_master.loc[0, 'Collection'], 
                                        quick_search = df_master.loc[0, 'Quick search'], 
                                        full_text = df_master.loc[0, 'Full text search'],
                                    judgments_counter_bound = judgments_counter_bound,
                                    own_parties_include = df_master.loc[0, 'Parties include'], 
                                    own_parties_exclude = df_master.loc[0, 'Parties do not include'], 
                                    #own_min_year, 
                                    #own_max_year, 
                                    after_date = df_master.loc[0, 'Decision date is after'], 
                                     before_date = df_master.loc[0, 'Decision date is before'], 
                                    #own_case_numbers_include, 
                                    #own_case_numbers_exclude, 
                                    own_judges_include = df_master.loc[0, 'Judges include'], 
                                    own_judges_exclude = df_master.loc[0, 'Judges do not include']
                                    )

                    results_count = min(len(case_infos), results_count)
                    
                if  results_count == 0:
                    
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
