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
from io import BytesIO
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
# # BAILII search engine

# %%
from functions.bailii_functions import bailii_sort_dict, bailii_highlight_dict, bailii_courts_default_list, bailii_courts_list, bailii_search_tool, bailii_search_url


# %%
#function to create dataframe
def bailii_create_df():

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
            
    #Textual entries text

    citation = citation_entry
    
    case_name = case_name_entry

    all_of_these_words = all_of_these_words_entry
        
    exact_phrase = exact_phrase_entry
    
    any_of_these_words = any_of_these_words_entry
    
    advanced_query = advanced_query_entry
    
    #dates        
    from_date = from_date_entry
    
    to_date = to_date_entry
    
    sortby = sortby_entry
    
    highlight = highlight_entry
    
    #Courts
    courts_list = courts_entry

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

    meta_data_choice = meta_data_entry
    
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Citation': citation,
            'Case name': case_name,
            'All of these words': all_of_these_words,
            'Exact phrase': exact_phrase,
            'Any of these words': any_of_these_words,
            'Advanced query': advanced_query,
            'From date': from_date,
            'To date': to_date,
            'Sort results by': sortby,
            'Highlight search terms in result': highlight,
            'Courts' : courts_list, 
            'Metadata inclusion' : meta_data_choice,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': gpt_questions, 
            'Use GPT': gpt_activation_status, 
          'Use own account': own_account,
            'Use flagship version of GPT' : gpt_enhancement
          }

    df_master_new = pd.DataFrame([new_row])

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

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])
    
#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

if 'df_master' not in st.session_state:

    #Generally applicable
    df_master_dict = {'Your name' : '', 
    'Your email address' : '', 
    'Your GPT API key' : '', 
    'Metadata inclusion' : True, 
    'Maximum number of judgments' : default_judgment_counter_bound, 
    'Enter your questions for GPT' : '', 
    'Use GPT' : False, 
    'Use own account' : False, 
    'Use flagship version of GPT' : False,
    'Example' : ''
    }

    #Jurisdiction specific
    jurisdiction_specific_dict = {
    'Citation': None,
    'Case name': None,
    'All of these words': None,
    'Exact phrase': None,
    'Any of these words': None,
    'Advanced query': None,
    'From date': None,
    'To date': None,
    'Sort results by': list(bailii_sort_dict.keys())[0],
    'Highlight search terms in result': True,
    'Courts': []
    }

    #Make into  df
    df_master_dict.update(jurisdiction_specific_dict)
    
    st.session_state['df_master'] = pd.DataFrame([df_master_dict])

#Initialise jurisdiction_page
if 'jurisdiction_page' not in st.session_state:
    st.session_state['jurisdiction_page'] = 'pages/BAILII.py'

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
#if st.session_state.page_from != "pages/BAILII.py": #Need to add in order to avoid GPT page from showing form of previous page

#Create form for court selection

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[cases of the England and Wales courts from BAILII]")

st.success(default_msg)

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Courts to cover")

default_on = st.button('ADD the House of Lords, the Supreme Court, the Privy Council, the Court of Appeal & the High Court', help = 'You may need to press :red[RESET] to add these courts.')

if default_on:
    
    if isinstance(st.session_state['df_master'].loc[0, 'Courts'], list):
        for court in bailii_courts_default_list:
            if court not in st.session_state['df_master'].loc[0, 'Courts']:
                st.session_state['df_master'].loc[0, 'Courts'].append(court)
    else:
        st.session_state['df_master']['Courts'] = st.session_state['df_master']['Courts'].astype('object')
        st.session_state['df_master'].at[0, 'Courts'] = bailii_courts_default_list

courts_entry = st.multiselect(label = 'Select or type in the courts to search', options = bailii_courts_list, default = st.session_state['df_master'].loc[0, 'Courts'])

#st.caption("All courts and tribunals listed in this menu will be covered if left blank.")

#Search terms

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [BAILII](https://www.bailii.org/form/search_cases.html). This section mimics their case law search function.
""")

citation_entry = st.text_input(label = 'Citation', value = st.session_state.df_master.loc[0, 'Citation'], help = 'e.g. [2000] 1 AC 360')

case_name_entry = st.text_input(label = 'Case name', value = st.session_state.df_master.loc[0, 'Case name'], help = 'e.g. barber v somerset')

all_of_these_words_entry = st.text_input(label = 'All of these words', value = st.session_state.df_master.loc[0, 'All of these words'], help = 'e.g. breach fiduciary duty')

exact_phrase_entry = st.text_input(label = 'Exact phrase', value = st.session_state.df_master.loc[0, 'Exact phrase'], help = 'e.g. parliamentary sovereignty')

any_of_these_words_entry = st.text_input(label = 'Any of these words', value = st.session_state.df_master.loc[0, 'Any of these words'], help = 'e.g. waste pollution radiation')

advanced_query_entry = st.text_input(label = 'Advanced query [(help)](https://www.bailii.org/bailii/help/advanced_query.html)', value = st.session_state.df_master.loc[0, 'Advanced query'], help = 'e.g. pollut* and (nuclear or radioactiv*)')
#st.write('')

date_col1, date_col2 = st.columns(2)

with date_col1:

    from_date_entry = st.date_input('From date', value = date_parser(st.session_state.df_master.loc[0, 'From date']), format="DD/MM/YYYY", min_value = date(1900, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

with date_col2:

    to_date_entry = st.date_input('To date', value = date_parser(st.session_state.df_master.loc[0, 'To date']), format="DD/MM/YYYY", min_value = date(1900, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

sortby_entry = st.selectbox(label = 'Sort results by', 
                                      options = [*bailii_sort_dict.keys()], 
                                    index = list_value_check([*bailii_sort_dict.keys()], st.session_state['df_master'].loc[0, "Sort results by"]), 
                                    )

highlight_entry = st.checkbox(label = 'Highlight search terms in result', value = st.session_state['df_master'].loc[0, "Highlight search terms in result"])

st.subheader("Judgment metadata collection")

st.markdown("""Would you like to obtain judgment metadata? Such data include the judge(s), the parties and so on. 

You will always obtain case names and medium neutral citations.
""")

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
    
    all_search_terms = str(citation_entry) + str(case_name_entry) + str(all_of_these_words_entry) + str(exact_phrase_entry) + str(any_of_these_words_entry) + str(advanced_query_entry) + str(from_date_entry) + str(to_date_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif len(courts_entry) == 0:
        
        st.warning('Please select at least one court to cover.')
    
    else:
        
        with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):

            try:
                
                df_master = bailii_create_df()
                
                search_results_w_count = bailii_search_url(df_master)
                
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

    all_search_terms = str(citation_entry) + str(case_name_entry) + str(all_of_these_words_entry) + str(exact_phrase_entry) + str(any_of_these_words_entry) + str(advanced_query_entry) + str(from_date_entry) + str(to_date_entry)
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif len(courts_entry) == 0:
        
        st.warning('Please select at least one court to cover.')
            
    else:
                            
        df_master = bailii_create_df()
        
        save_input(df_master)
    
        download_buttons(df_master = df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:

    df_master = bailii_create_df()
    
    save_input(df_master)

    st.session_state["page_from"] = 'pages/BAILII.py'

    st.switch_page("Home.py")

# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    all_search_terms = str(citation_entry) + str(case_name_entry) + str(all_of_these_words_entry) + str(exact_phrase_entry) + str(any_of_these_words_entry) + str(advanced_query_entry) + str(from_date_entry) + str(to_date_entry)
        
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif len(courts_entry) == 0:
        
        st.warning('Please select at least one court to cover.')
    
    else:

        df_master = bailii_create_df()
        
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):
            
            try:
    
                search_results_w_count = bailii_search_url(df_master)
                
                results_count = search_results_w_count['results_count']
                
                if results_count == 0:
                    st.error(no_results_msg)
    
                else:
    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/BAILII.py'
                    
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

