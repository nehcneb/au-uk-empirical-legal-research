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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, mnc_cleaner, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # High Court of Australia search engine

# %%
from functions.hca_functions import hca_collections, hca_search, hca_search_results_to_judgment_links, hca_pdf_judgment, hca_meta_labels_droppable, hca_meta_judgment_dict, hca_meta_judgment_dict_alt, hca_mnc_to_link_browse, hca_citation_to_link, hca_mnc_to_link, hca_load_data, hca_data_url, hca_df, hca_judgment_to_exclude, hca_search_results_to_judgment_links_filtered_df, hca_search_url


# %%
from functions.common_functions import link, is_date, list_value_check, au_date


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
from functions.gpt_functions import question_characters_bound, default_msg, default_caption


# %%
print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")
print(f"The default number of judgments to scrape per request is capped at {default_judgment_counter_bound}.\n")

# %%
#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction

if check_questions_answers() > 0:
    print(f'By default, questions and answers are checked for potential privacy violation.')
else:
    print(f'By default, questions and answers are NOT checked for potential privacy violation.')


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

st.header(f"Search :blue[judgments of the High Court of Australia]")

st.success(default_msg)

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
        
        #st.error('Sorry, this pilot app only searches for medium neutral citation (eg [2014] HCA 1).')

if collection_entry != '1 CLR - 100 CLR (judgments 1903-1958)':

    full_text_entry = st.text_input(label = 'Full text search', value = st.session_state.df_master.loc[0, 'Full text search'])

else:
    full_text_entry = ''

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

    preview_button = st.button(label = 'PREVIEW on the High Court Judgments Database (in a pop-up window)')

#if st.session_state.number_of_results != '0':

    #hca_results_num_button = st.button('DISPLAY the number of results')
    
    #if hca_results_num_button:

results_num_button = st.button(label = 'SHOW the number of judgments found', disabled = ('number_of_results' not in st.session_state), help = 'Press PREVIEW first.')

if results_num_button:

    if len(st.session_state.df_master) > 0:

        if int(st.session_state.number_of_results) == 0:

            st.error(f'There are {st.session_state.number_of_results} results. Please change your search terms.')

        elif int(st.session_state.number_of_results) == 1:
    
            st.success(f'There is {st.session_state.number_of_results} result.')
    
        else:
        
            st.success(f'There are {st.session_state.number_of_results} results.')

    else:

        st.warning('Please enter some search terms and press the PREVIEW button first.')
        
    #hca_results_num()

#The following filters are not based on HCA's filter at https://eresources.hcourt.gov.au/search?col=0&facets=&srch-Term=

st.subheader("Filter your search results")

filter_toggle = st.toggle(label = "Filter/unfilter", value = st.session_state.court_filter_status)

if filter_toggle:
    
    st.warning("Filtering your search results may *significantly* prolong the processing time. The PREVIEW and SHOW buttons will *not* reflect your search filters.")

    st.session_state['court_filter_status'] = True
    
    own_parties_include_entry = st.text_input(label = 'Parties include (separate parties by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Parties include'])
    st.caption('If entered, then this app will only process cases that include at least one of the parties entered.')
    
    own_parties_exclude_entry = st.text_input(label = 'Parties do not include (separate parties by comma or semi-colon)', value = st.session_state.df_master.loc[0, 'Parties do not include'])
    st.caption('If entered, then this app will only process cases that do not include any of the parties entered.')
    
    after_date_entry = st.date_input(label = 'Decision date is after', value = au_date(st.session_state.df_master.loc[0, 'Decision date is after']), format="DD/MM/YYYY", min_value = date(1903, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")
    
    before_date_entry = st.date_input(label = 'Decision date is before', value = au_date(st.session_state.df_master.loc[0, 'Decision date is before']), format="DD/MM/YYYY", min_value = date(1903, 1, 1),  max_value = datetime.now(),help = "If you cannot change this date entry, please press :red[RESET] and try again.")
    
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


st.subheader("Judgment metadata collection")

st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the decision date and so on. 

Case name and medium neutral citation are always included with your results.
""")

meta_data_entry = st.checkbox('Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])


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

    df_master = hca_create_df()

    st.session_state['df_master'] = df_master

    judgments_url_num = hca_search_url(df_master)
    
    judgments_url = judgments_url_num['url']

    judgments_num = judgments_url_num['results_num']

    st.session_state['number_of_results'] = judgments_num

    open_page(judgments_url)
    
    #st.rerun


# %%
if keep_button:

    #Check whether search terms entered

    all_search_terms = str(quick_search_entry) + str(citation_entry) + str(full_text_entry)
    
    if all_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
            
    else:
            
        df_master = hca_create_df()

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

            judgments_url_num = hca_search_url(df_master)
            judgments_num = judgments_url_num['results_num']
            if int(judgments_num) == 0:
                st.error(no_results_msg)

            else:
                
                save_input(df_master)
                
                st.session_state["page_from"] = 'pages/HCA.py'
                
                st.switch_page('pages/GPT.py')
