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
#import pypdf
import io
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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input, display_df, download_buttons, report_error
#Import variables
from functions.common_functions import today_in_nums, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg, search_error_display


# %% [markdown]
# # US search engine

# %%
from functions.us_functions import us_search_tool, us_search_function, us_search_preview, us_order_by, us_pacer_order_by, us_precedential_status, us_fed_app_courts, us_fed_dist_courts, us_fed_hist_courts, us_bankr_courts, us_state_courts, us_more_courts, all_us_jurisdictions, us_date, us_collections, us_pacer_fed_app_courts, us_pacer_fed_dist_courts, us_pacer_bankr_courts, us_pacer_more_courts, all_us_pacer_jurisdictions


# %%
from functions.common_functions import link, reverse_link


# %%
#function to create dataframe
def us_create_df():

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

    collection = list(us_collections.keys())[0]
    
    if collection_entry:
        
        collection = collection_entry

    #Set default court entries:
        fed_app_courts = ['All']
        
        fed_dist_courts = ['All']
    
        fed_hist_courts = ['All']
    
        bankr_courts = ['All']
    
        state_courts = ['All']
    
        more_courts = ['All']

    filtered_by_court = False
    
    if filtered_by_court_toggle:
        filtered_by_court = filtered_by_court_toggle
    
    if ((collection_entry ==  list(us_collections.keys())[0]) and (filtered_by_court)):

        fed_app_courts = fed_app_courts_entry
        
        fed_dist_courts = fed_dist_courts_entry
    
        fed_hist_courts = fed_hist_courts_entry
    
        bankr_courts = bankr_courts_entry
    
        state_courts = state_courts_entry
    
        more_courts = more_courts_entry

    if ((collection_entry ==  list(us_collections.keys())[1]) and (filtered_by_court)):
        
        fed_app_courts = fed_app_courts_entry
        
        fed_dist_courts = fed_dist_courts_entry
        
        bankr_courts = bankr_courts_entry
        
        more_courts = more_courts_entry

    #Entries common to both opinions and PACER records
    q = q_entry

    order_by = order_by_entry

    case_name = case_name_entry

    filed_after = ''

    if filed_after_entry != 'None':
        
        try:
            filed_after = filed_after_entry.strftime("%m/%d/%Y")
            
        except:
            pass

    filed_before = ''

    if filed_before_entry != 'None':

        try:

            filed_before = filed_before_entry.strftime("%m/%d/%Y")
            
        except:
            
            pass

    docket_number = docket_number_entry

    token = token_entry

    #Initialise source specific values
    precedential_status = [list(us_precedential_status.keys())[0]]
    judge = None
    cited_gt = None
    cited_lt = None
    citation = None
    neutral_cite = None
    
    description = None
    description=None 
    document_number=None
    attachment_number=None
    assigned_to=None
    referred_to=None
    nature_of_suit=None
    party_name=None
    atty_name=None
    available_only= True

    #Opinions specific entries
    if collection_entry ==  list(us_collections.keys())[0]:
        precedential_status = precedential_status_entry    
    
        judge = judge_entry
        
        cited_gt = cited_gt_entry
    
        cited_lt = cited_lt_entry
    
        citation = citation_entry
    
        neutral_cite = neutral_cite_entry

    else: #PACER records specific entries
        description=description_entry 
        document_number=document_number_entry
        attachment_number=attachment_number_entry
        assigned_to=assigned_to_entry
        referred_to=referred_to_entry
        nature_of_suit=nature_of_suit_entry
        party_name=party_name_entry
        atty_name=atty_name_entry
        available_only=available_only_entry

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
    try:
        meta_data_choice = meta_data_entry
    except:
        print('Metadata choice not entered.')
        
    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
               'Collection': collection, 
           'Filtered by court': filtered_by_court, 
            'Federal Appellate Courts': fed_app_courts, 
           'Federal District Courts': fed_dist_courts, 
           'Federal Historical Courts': fed_hist_courts, 
           'Bankruptcy Courts': bankr_courts, 
           'State and Territory Courts': state_courts, 
           'More Courts': more_courts, 
            'Search': q_entry, 
            'Search results order': order_by, 
            'Case name': case_name,
           'Docket number': docket_number,
            'Filed after': filed_after,
            'Filed before': filed_before,
           'Judge': judge, 
           'Precedential status': precedential_status, 
               'Min cites': cited_gt, 
           'Max cites': cited_lt, 
            'Citation': citation,
            'Neutral citation': neutral_cite, 
               'Document description': description, 
               'Document number': document_number, 
                'Attachment number': attachment_number, 
               'Assigned to judge': assigned_to, 
               'Referred to judge': referred_to, 
               'Nature of suit': nature_of_suit, 
                'Party name': party_name, 
               'Attorney name': atty_name,
               'Only show results with PDFs': available_only, 
            'CourtListener API token': token, 
            'Metadata inclusion' : meta_data_choice,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': gpt_questions, 
            'Use GPT': gpt_activation_status,
           'Use own account': own_account,
            'Use flagship version of GPT' : gpt_enhancement
          }

    df_master_new = pd.DataFrame([new_row])#, index = [0])
            
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
    st.session_state['df_master'].loc[0, 'Collection'] =  list(us_collections.keys())[0]
    st.session_state['df_master'].loc[0, 'Filtered by court'] =  False
    st.session_state['df_master'].loc[0, 'Federal Appellate Courts'] = ['All'] 
    st.session_state['df_master'].loc[0, 'Federal District Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Federal Historical Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Bankruptcy Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'State and Territory Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'More Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Search'] = None
    st.session_state['df_master'].loc[0, 'Search results order'] = list(us_order_by.keys())[0] 
    st.session_state['df_master'].loc[0, 'Precedential status'] = [list(us_precedential_status.keys())[0]]
    st.session_state['df_master'].loc[0, 'Case name'] = None
    st.session_state['df_master'].loc[0, 'Judge'] = None 
    st.session_state['df_master'].loc[0, 'Filed after'] = None
    st.session_state['df_master'].loc[0, 'Filed before'] = None
    st.session_state['df_master'].loc[0, 'Min cites'] = None
    st.session_state['df_master'].loc[0, 'Max cites'] = None
    st.session_state['df_master'].loc[0, 'Citation'] = None
    st.session_state['df_master'].loc[0, 'Neutral citation'] = None
    st.session_state['df_master'].loc[0, 'Docket number'] = None
    st.session_state['df_master'].loc[0, 'Document description'] = None 
    st.session_state['df_master'].loc[0, 'Document number'] = None
    st.session_state['df_master'].loc[0, 'Attachment number'] = None
    st.session_state['df_master'].loc[0, 'Assigned to judge'] = None
    st.session_state['df_master'].loc[0, 'Referred to judge'] = None
    st.session_state['df_master'].loc[0, 'Nature of suit'] = None
    st.session_state['df_master'].loc[0, 'Party name'] = None
    st.session_state['df_master'].loc[0, 'Attorney name'] = None
    st.session_state['df_master'].loc[0, 'Only show results with PDFs'] = True
    st.session_state['df_master'].loc[0, 'CourtListener API token'] = None

    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})
    
if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

#Initialise jurisdiction_page
if 'jurisdiction_page' not in st.session_state:
    st.session_state['jurisdiction_page'] = 'pages/US.py'

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
#Create form

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[cases of the United States courts]")

st.success(default_msg)

st.write(f'This app sources cases from [CourtListener](https://www.courtlistener.com).')

st.caption(default_caption)

reset_button = st.button(label='RESET', type = 'primary')

st.subheader('Case collection')

collection_entry = st.selectbox(label = 'Select one to search', options = list(us_collections.keys()), index = list_value_check(list(us_collections.keys()), st.session_state.df_master.loc[0, 'Collection']))

if collection_entry != st.session_state['df_master'].loc[0, 'Collection']:
    st.session_state['df_master'].loc[0, 'Federal Appellate Courts'] = ['All'] 
    st.session_state['df_master'].loc[0, 'Federal District Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Federal Historical Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Bankruptcy Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'State and Territory Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'More Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Search results order'] = list(us_order_by.keys())[0]

#st.subheader('Courts to cover')

#If opinions chosen
if collection_entry ==  list(us_collections.keys())[0]:

    st.write(f"For information about case coverage, please visit [CourtListener](https://www.courtlistener.com/help/coverage/opinions/).")

    filtered_by_court_toggle = st.toggle(label = 'Select/unselect courts', value = st.session_state['df_master'].loc[0, 'Filtered by court'])
    
    if filtered_by_court_toggle:
    
        st.warning('Please select courts to cover.')
    
        #st.session_state['court_filter_status'] = True
                
        fed_app_courts_entry = st.multiselect(label = 'Federal Appellate Courts', 
                                              options = list(us_fed_app_courts.keys()), 
                                              default = st.session_state['df_master'].loc[0, 'Federal Appellate Courts']
                                             )
                
        fed_dist_courts_entry = st.multiselect(label = 'Federal District Courts', 
                                              options = list(us_fed_dist_courts.keys()), 
                                              default = st.session_state['df_master'].loc[0, 'Federal District Courts']
                                             )
                    
        fed_hist_courts_entry = st.multiselect(label = 'Federal Historical Courts', 
                                              options = list(us_fed_hist_courts.keys()), 
                                              default = st.session_state['df_master'].loc[0, 'Federal Historical Courts']
                                             )
                    
        bankr_courts_entry = st.multiselect(label = 'Bankruptcy Courts', 
                                              options = list(us_bankr_courts.keys()), 
                                              default = st.session_state['df_master'].loc[0, "Bankruptcy Courts"]
                                             )
                
        state_courts_entry = st.multiselect(label = 'State and Territory Courts', 
                                              options = list(us_state_courts.keys()), 
                                              default = st.session_state['df_master'].loc[0, "State and Territory Courts"]
                                             )
                
        more_courts_entry = st.multiselect(label = 'More Courts', 
                                              options = list(us_more_courts.keys()), 
                                              default = st.session_state['df_master'].loc[0, "More Courts"]
                                             )
            
    else: #if filtered_by_court_toggle == False
        
        st.info('All courts will be covered.')
        
        #st.session_state['court_filter_status'] = False
        #st.session_state['df_master'].loc[0, 'Federal Appellate Courts'] = ['All'] 
        #st.session_state['df_master'].loc[0, 'Federal District Courts'] = ['All']
        #st.session_state['df_master'].loc[0, 'Federal Historical Courts'] = ['All']
        #st.session_state['df_master'].loc[0, 'Bankruptcy Courts'] = ['All']
        #st.session_state['df_master'].loc[0, 'State and Territory Courts'] = ['All']
        #st.session_state['df_master'].loc[0, 'More Courts'] = ['All']

else: #If pacer records chosen

    st.write(f"For information about case coverage, please visit [CourtListener](https://free.law/2017/08/15/we-have-all-free-pacer).")
    
    filtered_by_court_toggle = st.toggle(label = 'Select/unselect courts', value = st.session_state['df_master'].loc[0, 'Filtered by court'])
    
    if filtered_by_court_toggle:
    
        st.warning('Please select courts to cover.')
    
        #st.session_state['court_pacer_filter_status'] = True
                
        fed_app_courts_entry = st.multiselect(label = 'Federal Appellate Courts', 
                                              options = list(us_pacer_fed_app_courts.keys()), 
                                              default = st.session_state['df_master'].loc[0, 'Federal Appellate Courts']
                                             )
                
        fed_dist_courts_entry = st.multiselect(label = 'Federal District Courts', 
                                              options = list(us_pacer_fed_dist_courts.keys()), 
                                              default = st.session_state['df_master'].loc[0, 'Federal District Courts']
                                             )
                        
        bankr_courts_entry = st.multiselect(label = 'Bankruptcy Courts', 
                                              options = list(us_pacer_bankr_courts.keys()), 
                                              default = st.session_state['df_master'].loc[0, "Bankruptcy Courts"]
                                             )
                
        more_courts_entry = st.multiselect(label = 'More Courts', 
                                              options = list(us_pacer_more_courts.keys()), 
                                              default = st.session_state['df_master'].loc[0, "More Courts"]
                                             )
            
    else: #if filtered_by_court_toggle == False
        
        st.info('All courts will be covered.')
        
        #st.session_state['court_pacer_filter_status'] = False
        #st.session_state['df_master'].loc[0, 'Federal Appellate Courts'] = ['All'] 
        #st.session_state['df_master'].loc[0, 'Federal District Courts'] = ['All']
        #st.session_state['df_master'].loc[0, 'Bankruptcy Courts'] = ['All']
        #st.session_state['df_master'].loc[0, 'More Courts'] = ['All']

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [CourtListener](https://www.courtlistener.com/help/search-operators/). This section largely mimics their advanced search function.
""")

q_entry = st.text_input(label = 'Search', value = st.session_state['df_master'].loc[0, 'Search'])

case_name_entry = st.text_input(label = 'Case name', value = st.session_state['df_master'].loc[0, 'Case name'])

docket_number_entry = st.text_input(label = 'Docket number', value = st.session_state['df_master'].loc[0, 'Docket number'])

date_col1, date_col2 = st.columns(2)

with date_col1:

    filed_after_entry = st.date_input(label = 'Filed after (month first)', value = us_date(st.session_state['df_master'].loc[0, 'Filed after']), format="MM/DD/YYYY", min_value = date(1658, 7, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

with date_col2:

    filed_before_entry = st.date_input(label = 'Filed before (month first)', value = us_date(st.session_state['df_master'].loc[0, 'Filed before']), format="MM/DD/YYYY", min_value = date(1658, 7, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

#If opinions chosen
if collection_entry ==  list(us_collections.keys())[0]:

    judge_entry = st.text_input(label = 'Judge', value = st.session_state['df_master'].loc[0, 'Judge'])
    
    precedential_status_entry = st.multiselect(label = 'Precedential status', 
                                               options = list(us_precedential_status.keys()), 
                                               default = st.session_state['df_master'].loc[0, 'Precedential status'])
    
    
    cited_gt_entry = st.text_input(label = 'Min cites', value = st.session_state['df_master'].loc[0, 'Min cites'])
    
    cited_lt_entry = st.text_input(label = 'Max cites', value = st.session_state['df_master'].loc[0, 'Max cites'])
    
    citation_entry = st.text_input(label = 'Citation', value = st.session_state['df_master'].loc[0, 'Citation'])
    
    neutral_cite_entry = st.text_input(label = 'Neutral citation', value = st.session_state['df_master'].loc[0, 'Neutral citation'])

    order_by_entry = st.selectbox(label = "Search results order ", options = list(us_order_by.keys()), index = list(us_order_by.keys()).index(st.session_state['df_master'].loc[0, 'Search results order']))

else: #If PACER records chosen
    description_entry = st.text_input(label = 'Document description', value = st.session_state['df_master'].loc[0, 'Document description'])
    document_number_entry = st.text_input(label = 'Document number', value = st.session_state['df_master'].loc[0, 'Document number'])
    attachment_number_entry = st.text_input(label = 'Attachment number', value = st.session_state['df_master'].loc[0, 'Attachment number'])
    assigned_to_entry = st.text_input(label = 'Assigned to judge', value = st.session_state['df_master'].loc[0, 'Assigned to judge'])
    referred_to_entry = st.text_input(label = 'Referred to judge', value = st.session_state['df_master'].loc[0, 'Referred to judge'])
    nature_of_suit_entry = st.text_input(label = 'Nature of suit', value = st.session_state['df_master'].loc[0, 'Nature of suit'])
    party_name_entry = st.text_input(label = 'Party name', value = st.session_state['df_master'].loc[0, 'Party name'])
    atty_name_entry = st.text_input(label = 'Attorney name', value = st.session_state['df_master'].loc[0, 'Attorney name'])
    available_only_entry = st.checkbox(label = 'Only show results with PDFs (up to 3 will be processed)', value = bool(float(st.session_state['df_master'].loc[0, 'Only show results with PDFs'])))
    order_by_entry = st.selectbox(label = "Search results order", options = list(us_pacer_order_by.keys()), index = list(us_pacer_order_by.keys()).index(st.session_state['df_master'].loc[0, 'Search results order']))

st.subheader("Your CourtListener API token")

token_entry = st.text_input(label = 'Optional unless otherwise stated', value = st.session_state['df_master'].loc[0, 'CourtListener API token'])

st.write('By default, this app will process up to 500 queries per day. If that limit is exceeded, you can still use this app with your own CourtListen API token (click [here](https://www.courtlistener.com/sign-in/) to sign up for one).')

st.subheader("Case metadata collection")

st.markdown("""Would you like to obtain case metadata? Such data include the judge(s), the filing date and so on. 

You will always obtain case names and citations.
""")

meta_data_entry = st.checkbox(label = 'Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])

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
    
    #If opinions chosen
    if collection_entry ==  list(us_collections.keys())[0]:

        us_search_terms = str(q_entry) + str(case_name_entry) + str(docket_number_entry) + str(filed_after_entry) + str(filed_before_entry) + str(judge_entry)

    else: #if pacer docs chosen
        
        us_search_terms = str(q_entry) + str(case_name_entry) + str(docket_number_entry) + str(filed_after_entry) + str(filed_before_entry) + str(description_entry) + str(document_number_entry) + str(attachment_number_entry) + str(assigned_to_entry) + str(referred_to_entry) + str(nature_of_suit_entry) + str(party_name_entry) + str(atty_name_entry)
    
    if us_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:
        with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):

            try:
                
                df_master = us_create_df()
        
                search_results_w_count = us_search_preview(df_master)
                
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
                    st.success(f'Your search terms returned about {results_count} result(s). Please see below for the top {min(results_count, default_judgment_counter_bound)} result(s).')
                                
                    st.dataframe(df_preview.head(default_judgment_counter_bound),  column_config=link_heading_config)
        
                    st.page_link(results_url, label=f"SEE all search results (in a popped up window)", icon = "🌎")
            
                else:
                    st.error(no_results_msg)
                    
                    #US-specific
                    st.error('Alternatively, please enter your own CourtListener API token and try again.')
                
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

    #If opinions chosen
    if collection_entry ==  list(us_collections.keys())[0]:

        us_search_terms = str(q_entry) + str(case_name_entry) + str(docket_number_entry) + str(filed_after_entry) + str(filed_before_entry) + str(judge_entry)

    else: #if pacer docs chosen
        
        us_search_terms = str(q_entry) + str(case_name_entry) + str(docket_number_entry) + str(filed_after_entry) + str(filed_before_entry) + str(description_entry) + str(document_number_entry) + str(attachment_number_entry) + str(assigned_to_entry) + str(referred_to_entry) + str(nature_of_suit_entry) + str(party_name_entry) + str(atty_name_entry)
    
    if us_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = us_create_df()

        if 'CourtListener API token' in df_master.columns:
            df_master.pop('CourtListener API token')

        save_input(df_master)

        download_buttons(df_master = df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:

    df_master = us_create_df()

    save_input(df_master)
    
    st.session_state["page_from"] = 'pages/US.py'

    st.switch_page("Home.py")

# %%
if reset_button:
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    #If opinions chosen
    if collection_entry ==  list(us_collections.keys())[0]:

        us_search_terms = str(q_entry) + str(case_name_entry) + str(docket_number_entry) + str(filed_after_entry) + str(filed_before_entry) + str(judge_entry)

    else: #if pacer docs chosen
        
        us_search_terms = str(q_entry) + str(case_name_entry) + str(docket_number_entry) + str(filed_after_entry) + str(filed_before_entry) + str(description_entry) + str(document_number_entry) + str(attachment_number_entry) + str(assigned_to_entry) + str(referred_to_entry) + str(nature_of_suit_entry) + str(party_name_entry) + str(atty_name_entry)
    
    if us_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = us_create_df()
    
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            try:

                search_results_w_count = us_search_preview(df_master)
                
                results_count = search_results_w_count['results_count']
                
                if results_count == 0:
                    
                    st.error(no_results_msg)
    
                    #US-specific
                    st.error('Alternatively, please enter your own CourtListener API token and try again.')
                
                else:
                    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/US.py'
                    
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

