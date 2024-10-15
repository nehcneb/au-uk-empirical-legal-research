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
import streamlit_ext as ste
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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_range_check, au_date, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # CaseLaw NSW functions and parameters

# %%
from functions.nsw_functions import nsw_meta_labels_droppable, nsw_courts, nsw_courts_positioning, nsw_default_courts, nsw_tribunals, nsw_tribunals_positioning, nsw_court_choice, nsw_tribunal_choice, nsw_date, nsw_link, nsw_short_judgment, nsw_tidying_up, nsw_tidying_up_prebatch, nsw_search_url


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

    courts_list = courts_entry

    courts = ', '.join(courts_list)
    
    #NSW tribunals choices
    
    tribunals_list = tribunals_entry

    tribunals = ', '.join(tribunals_list)

    #Search terms
    
    body = body_entry
    title = title_entry
    before = before_entry
    catchwords = catchwords_entry
    party = party_entry
    mnc = mnc_entry

    startDate = ''

    if startDate_entry != 'None':

        try:

            startDate = startDate_entry.strftime('%d/%m/%Y')

        except:
            pass
        
    endDate = ''

    if endDate_entry != 'None':
        
        try:
            endDate = endDate_entry.strftime('%d/%m/%Y')
            
        except:
            pass
    
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
    
    df_master_new = pd.DataFrame(new_row, index = [0])
        
    return df_master_new



# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json
#Import variables
from functions.gpt_functions import question_characters_bound, default_msg
#For batch mode
from functions.gpt_functions import gpt_get_custom_id, gpt_batch_input_id_line, gpt_batch_input



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
#Initialize default values

if 'default_courts' not in st.session_state:
    st.session_state['default_courts'] = []

if 'dafault_courts_status' not in st.session_state:
    st.session_state['dafault_courts_status'] = False

#if 'default_tribunals' not in st.session_state:
    #st.session_state['default_tribunals'] = []

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
    st.session_state['df_master'].loc[0, 'Courts'] = ''
    st.session_state['df_master'].loc[0, 'Tribunals'] = ''
    st.session_state['df_master'].loc[0, 'Free text']  = None
    st.session_state['df_master'].loc[0, 'Case name']  = None
    st.session_state['df_master'].loc[0, 'Before']  = None
    st.session_state['df_master'].loc[0, 'Catchwords']  = None
    st.session_state['df_master'].loc[0, 'Party names']  = None
    st.session_state['df_master'].loc[0, 'Medium neutral citation']  = None
    st.session_state['df_master'].loc[0, 'Decision date from']  = None
    st.session_state['df_master'].loc[0, 'Decision date to']  = None
    st.session_state['df_master'].loc[0, 'File number']  = None
    st.session_state['df_master'].loc[0, 'Legislation cited']  = None
    st.session_state['df_master'].loc[0, 'Cases cited']  = None

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
#Create form

#if st.session_state.page_from != "pages/NSW.py": #Need to add in order to avoid GPT page from showing form of previous page

return_button = st.button('RETURN to first page')

st.header("Search :blue[judgments of the New South Wales courts and tribunals]")

st.success(f"**Please enter your search terms.** {default_msg}")

st.write(f'To collect judgments, this app uses [an open-source Python module](https://github.com/Sydney-Informatics-Hub/nswcaselaw) developed by Mike Lynch and Xinwei Luo of Sydney Informatics Hub.')

st.caption("During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au if you'd like to cover more judgments.")

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Courts and tribunals to cover")

default_on_courts = st.checkbox(label = 'Prefill the Court of Appeal, the Court of Criminal Appeal, and the Supreme Court', value = st.session_state.dafault_courts_status)

if default_on_courts:

    st.session_state.default_courts = nsw_default_courts

else:
    #st.session_state.default_courts = []
    st.session_state.default_courts = list_range_check(nsw_courts, st.session_state['df_master'].loc[0, 'Courts'])

courts_entry = st.multiselect(label = 'Select or type in the courts to cover', options = nsw_courts, default = st.session_state.default_courts)

tribunals_entry = st.multiselect(label = 'Select or type in the tribunals to cover', options = nsw_tribunals, default = list_range_check(nsw_tribunals, st.session_state['df_master'].loc[0, 'Tribunals']))

#st.caption(f"All courts and tribunals listed in these menus will be covered if left blank.")

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

startDate_entry = st.date_input(label = "Decision date from (01/01/1999 the earliest)", value = au_date(st.session_state['df_master'].loc[0, 'Decision date from']), format="DD/MM/YYYY", min_value = date(1900, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

st.caption("Pre-1999 decisions are usually [not available](https://www.caselaw.nsw.gov.au/about) from NSW Caselaw and will unlikely to be collected.")

endDate_entry = st.date_input(label = "Decision date to", value = au_date(st.session_state['df_master'].loc[0, 'Decision date to']),  format="DD/MM/YYYY", min_value = date(1900, 1, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

fileNumber_entry = st.text_input(label = "File number", value = st.session_state['df_master'].loc[0, 'File number'])

legislationCited_entry = st.text_input(label = "Legislation cited", value = st.session_state['df_master'].loc[0, 'Legislation cited'])

casesCited_entry = st.text_input(label = "Cases cited", value = st.session_state['df_master'].loc[0, 'Cases cited'] )

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
    preview_button = st.button(label = 'PREVIEW on NSW Caselaw (in a popped up window)')

#    headnotes_entry = st.multiselect("Please select", headnotes_choices)

st.subheader("Judgment metadata collection")

st.markdown("""Would you like to obtain judgment metadata? Such data include the name of the judge, the decision date and so on. 

Case name and medium neutral citation are always included with your results.
""")

meta_data_entry = st.checkbox(label = 'Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])


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
    
    df_master = nsw_create_df()

    judgments_url = nsw_search_url(df_master)

    open_page(judgments_url)


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

        #Create outputs
    
        responses_output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_responses'
    
        #Buttons for downloading responses
    
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

            nsw_url_to_check = nsw_search_url(df_master)
            nsw_html = requests.get(nsw_url_to_check)
            nsw_soup = BeautifulSoup(nsw_html.content, "lxml")
            if 'totalElements' not in str(nsw_soup):
                
                st.error(no_results_msg)

            else:
                
                save_input(df_master)

                st.session_state["page_from"] = 'pages/NSW.py'
                
                st.switch_page('pages/GPT.py')

