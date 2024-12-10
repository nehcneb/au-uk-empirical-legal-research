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

#NSWCaseLaw
from nswcaselaw.search import Search

#OpenAI
import openai
import tiktoken

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb


# %%
#Import functions
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, au_date, save_input, download_buttons, display_df
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg, search_error_display, no_results_msg

# %% [markdown]
# # CaseLaw NSW functions and parameters

# %%
from functions.nsw_functions import nsw_courts, nsw_default_courts, nsw_tribunals, nsw_search_preview, nsw_link


# %%
#function to create dataframe
def nsw_create_df():

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

    gpt_api_key = ''
    try:
        gpt_api_key = gpt_api_key_entry
        #This is the user's entered API key whether valid or invalid, not necessarily the one used to produce outputs
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
    
    #NSW court choices

    courts = courts_entry
    
    #NSW tribunals choices    
    tribunals = tribunals_entry

    #Search terms
    
    body = body_entry
    title = title_entry
    before = before_entry
    catchwords = catchwords_entry
    party = party_entry
    mnc = mnc_entry

    startDate = ''

    try:

        startDate = startDate_entry.strftime('%d/%m/%Y')

    except:
        print('startDate not entered')
        
    endDate = ''
        
    try:
        endDate = endDate_entry.strftime('%d/%m/%Y')
        
    except:
        print('endDate not entered')
    
    fileNumber = fileNumber_entry
    legislationCited = legislationCited_entry
    casesCited = casesCited_entry

    #metadata choice

    meta_data_choice = meta_data_entry
    
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

    #Create row
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
           'Courts': courts,
           'Tribunals': tribunals, 
           'Free text': body, 
           'Case name': title, 
           'Before' : before, 
           'Catchwords' : catchwords, 
           'Party names' : party, 
           'Medium neutral citation': mnc, 
           'Decision date from': startDate, 
           'Decision date to': endDate, 
           'File number': fileNumber, 
           'Legislation cited': legislationCited,
           'Cases cited': casesCited, 
#           'Information to Collect from Judgment Headnotes': headnotes,
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
from functions.gpt_functions import question_characters_bound, default_msg, default_caption
#For batch mode
from functions.gpt_functions import gpt_get_custom_id, gpt_batch_input_id_line, gpt_batch_input


# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction



# %%
#Module, costs and upperbounds

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
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %%
#Initialize default values

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
    jurisdiction_specific_dict = {'Courts' : [],
    'Tribunals' : [],
    'Free text'  : None,
    'Case name'  : None,
    'Before'  : None,
    'Catchwords'  : None,
    'Party names'  : None,
    'Medium neutral citation'  : None,
    'Decision date from'  : None,
    'Decision date to'  : None,
    'File number'  : None,
    'Legislation cited'  : None,
    'Cases cited'  : None
    }

    #Make into  df
    df_master_dict.update(jurisdiction_specific_dict)
    
    st.session_state['df_master'] = pd.DataFrame([df_master_dict])


# %%
#NSW-specific session_states

#if 'dafault_courts_status' not in st.session_state:
    #st.session_state['dafault_courts_status'] = False


# %% [markdown]
# ## Form before AI

# %%
#Create form

#if st.session_state.page_from != "pages/NSW.py": #Need to add in order to avoid GPT page from showing form of previous page

return_button = st.button('RETURN to first page')

st.header("Search :blue[cases of the New South Wales courts and tribunals]")

st.success(default_msg)

st.write(f'This app uses [an open-source Python module](https://github.com/Sydney-Informatics-Hub/nswcaselaw) developed by Mike Lynch and Xinwei Luo of Sydney Informatics Hub to search for and collect cases from [NSW Caselaw](https://www.caselaw.nsw.gov.au/search/advanced). It also sources cases from the [Open Australian Legal Corpus](https://huggingface.co/datasets/umarbutler/open-australian-legal-corpus) compiled by Umar Butler.')

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Courts and tribunals to cover")

default_on_courts = st.checkbox(label = 'Prefill the Court of Appeal, the Court of Criminal Appeal, and the Supreme Court')#, value = st.session_state.dafault_courts_status)

if default_on_courts:
    st.session_state['df_master']['Courts'] = st.session_state['df_master']['Courts'].astype('object')
    st.session_state['df_master'].at[0, 'Courts'] = nsw_default_courts

courts_entry = st.multiselect(label = 'Courts', options = nsw_courts, default = st.session_state['df_master'].loc[0, 'Courts'])

tribunals_entry = st.multiselect(label = 'Tribunals', options = nsw_tribunals, default = st.session_state['df_master'].loc[0, 'Tribunals'])

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [NSW Caselaw](https://www.caselaw.nsw.gov.au/search/advanced). This section mimics their Advanced Search function.""")

catchwords_entry = st.text_input(label = "Catchwords", value = st.session_state['df_master'].loc[0, 'Catchwords'])

body_entry = st.text_input(label = "Free text (searches the entire judgment)", value = st.session_state['df_master'].loc[0, 'Free text']) 

title_entry = st.text_input(label = "Case name", value = st.session_state['df_master'].loc[0, 'Case name'])

before_entry = st.text_input(label = "Before", value = st.session_state['df_master'].loc[0, 'Before'])

st.caption("Name of judge, commissioner, magistrate, member, registrar or assessor")

party_entry = st.text_input(label = "Party names", value = st.session_state['df_master'].loc[0, 'Party names'])

mnc_entry = st.text_input(label = "Medium neutral citation", value = st.session_state['df_master'].loc[0, 'Medium neutral citation'])

st.caption("Must include square brackets eg [2022] NSWSC 922")

startDate_entry = st.date_input(label = "Decision date from", value = au_date(st.session_state['df_master'].loc[0, 'Decision date from']), format="DD/MM/YYYY", min_value = date(1900, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

st.caption("Pre-1999 decisions are usually [not available](https://www.caselaw.nsw.gov.au/about) from NSW Caselaw and will unlikely to be collected.")

endDate_entry = st.date_input(label = "Decision date to", value = au_date(st.session_state['df_master'].loc[0, 'Decision date to']),  format="DD/MM/YYYY", min_value = date(1900, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

fileNumber_entry = st.text_input(label = "File number", value = st.session_state['df_master'].loc[0, 'File number'])

legislationCited_entry = st.text_input(label = "Legislation cited", value = st.session_state['df_master'].loc[0, 'Legislation cited'])

casesCited_entry = st.text_input(label = "Cases cited", value = st.session_state['df_master'].loc[0, 'Cases cited'] )

#    headnotes_entry = st.multiselect("Please select", headnotes_choices)

#st.subheader("Judgment metadata collection")

#st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the decision date and so on. 

#Case name and medium neutral citation are always included with your results.
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
    
    all_search_terms = str(catchwords_entry) + str(body_entry) + str(title_entry) + str(before_entry) + str(party_entry) + str(mnc_entry) + str(startDate_entry) + str(endDate_entry) + str(fileNumber_entry) + str(legislationCited_entry) + str(casesCited_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif (len(courts_entry) == 0) and (len(tribunals_entry) == 0):
        st.warning('Please select at least one court or tribunal to cover.')
    
    else:
        with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):
        
            df_master = nsw_create_df()
    
            search_results_w_count = nsw_search_preview(df_master)
            
            results_count = search_results_w_count['results_count']
    
            results_to_show = search_results_w_count['results_to_show']
    
            results_url = search_results_w_count['results_url']
                
            if results_count > 0:
    
                df_preview = pd.DataFrame(results_to_show)
    
                #Clean df for display
                df_preview['uri'] = df_preview['uri'].apply(nsw_link)
    
                rename_columns_dict = {'title': 'Title', 'uri': 'Hyperlink to NSW Caselaw', 'before': 'Before', 'decisionDate': 'Decision date', 'catchwords': 'Catchwords'}
    
                df_preview.rename(columns=rename_columns_dict, inplace=True)
    
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

    all_search_terms = str(catchwords_entry) + str(body_entry) + str(title_entry) + str(before_entry) + str(party_entry) + str(mnc_entry) + str(startDate_entry) + str(endDate_entry) + str(fileNumber_entry) + str(legislationCited_entry) + str(casesCited_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif (len(courts_entry) == 0) and (len(tribunals_entry) == 0):
        st.warning('Please select at least one court or tribunal to cover.')
            
    else:
        
        df_master = nsw_create_df()
        
        save_input(df_master)

        download_buttons(df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:

    df_master = nsw_create_df()
    
    save_input(df_master)

    st.session_state["page_from"] = 'pages/NSW.py'

    st.switch_page("Home.py")


# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    all_search_terms = str(catchwords_entry) + str(body_entry) + str(title_entry) + str(before_entry) + str(party_entry) + str(mnc_entry) + str(startDate_entry) + str(endDate_entry) + str(fileNumber_entry) + str(legislationCited_entry) + str(casesCited_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    elif (len(courts_entry) == 0) and (len(tribunals_entry) == 0):
        st.warning('Please select at least one court or tribunal to cover.')
    
    else:
    
        df_master = nsw_create_df()
        
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):
            try:
                search_results_w_count = nsw_search_preview(df_master)
                results_count = search_results_w_count['results_count']
                
                if results_count == 0:
                    
                    st.error(no_results_msg)
    
                else:
                    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/NSW.py'
                    
                    st.switch_page('pages/GPT.py')
        
            except Exception as e:
                print(search_error_display)
                print(e)
                st.error(search_error_display)
                st.error(e)


