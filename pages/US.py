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


#OpenAI
import openai
import tiktoken

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb

# %%
test = pd.DataFrame([])

# %%
#Import functions
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, clear_cache, list_value_check, list_range_check, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # US search engine

# %%
from functions.us_functions import us_search_tool, us_search_preview, us_court_choice_to_list, us_court_choice_clean, us_order_by, us_precedential_status, us_fed_app_courts, us_fed_dist_courts, us_fed_hist_courts, us_bankr_courts, us_state_courts, us_more_courts, all_us_jurisdictions, us_date
#us_court_choice_to_string


# %%
from functions.common_functions import link, hide_own_token, reverse_link


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

    if st.session_state.court_filter_status:

        fed_app_courts = fed_app_courts_entry
        
        fed_dist_courts = fed_dist_courts_entry
    
        fed_hist_courts = fed_hist_courts_entry
    
        bankr_courts = bankr_courts_entry
    
        state_courts = state_courts_entry
    
        more_courts = more_courts_entry

    else:

        fed_app_courts = ['All']
        
        fed_dist_courts = ['All']
    
        fed_hist_courts = ['All']
    
        bankr_courts = ['All']
    
        state_courts = ['All']
    
        more_courts = ['All']
        
    q = q_entry

    order_by = order_by_entry

    precedential_status = precedential_status_entry    

    case_name = case_name_entry

    judge = judge_entry
    
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

    #Entries contonue

    cited_gt = cited_gt_entry

    cited_lt = cited_lt_entry

    citation = citation_entry

    neutral_cite = neutral_cite_entry

    docket_number = docket_number_entry

    token = token_entry
    
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
            'Federal Appellate Courts': fed_app_courts, 
           'Federal District Courts': fed_dist_courts, 
           'Federal Historical Courts': fed_hist_courts, 
           'Bankruptcy Courts': bankr_courts, 
           'State and Territory Courts': state_courts, 
           'More Courts': more_courts, 
            'Search': q_entry, 
            'Search results order': order_by, 
            'Precedential status': precedential_status, 
            'Case Name': case_name,
            'Judge': judge, 
            'Filed after': filed_after,
            'Filed before': filed_before,
               'Min cites': cited_gt, 
           'Max cites': cited_lt, 
            'Citation': citation,
            'Neutral citation': neutral_cite, 
            'Docket number': docket_number,
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
from functions.gpt_functions import question_characters_bound, default_msg


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

    #Jurisdiction specific
    st.session_state['df_master'].loc[0, 'Federal Appellate Courts'] = ['All'] 
    st.session_state['df_master'].loc[0, 'Federal District Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Federal Historical Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Bankruptcy Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'State and Territory Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'More Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Search'] = None
    st.session_state['df_master'].loc[0, 'Search results order'] = list(us_order_by.keys())[0] 
    st.session_state['df_master'].loc[0, 'Precedential status'] = [list(us_precedential_status.keys())[0]]
    st.session_state['df_master'].loc[0, 'Case Name'] = None
    st.session_state['df_master'].loc[0, 'Judge'] = None 
    st.session_state['df_master'].loc[0, 'Filed after'] = None
    st.session_state['df_master'].loc[0, 'Filed before'] = None
    st.session_state['df_master'].loc[0, 'Min cites'] = None
    st.session_state['df_master'].loc[0, 'Max cites'] = None
    st.session_state['df_master'].loc[0, 'Citation'] = None
    st.session_state['df_master'].loc[0, 'Neutral citation'] = None
    st.session_state['df_master'].loc[0, 'Docket number'] = None
    st.session_state['df_master'].loc[0, 'CourtListener API token'] = st.secrets["courtlistener"]["token"]

    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})
    
if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True


# %%
#US specific session states

if (('court_filter_status' not in st.session_state) or ('df_master' not in st.session_state)):
    st.session_state["court_filter_status"] = False


# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %%
#if st.session_state.page_from != "pages/US.py": #Need to add in order to avoid GPT page from showing form of previous page

#Create form

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[judgments of United States courts]")

st.success(f"**Please enter your search terms.** {default_msg}")

st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more judgments, courts, or tribunals.')

reset_button = st.button(label='RESET', type = 'primary')

st.subheader("Courts to cover")

jurisdiction_toggle = st.toggle(label = 'Select/unselect courts', value = st.session_state.court_filter_status)

if jurisdiction_toggle:

    st.warning('Please select the courts to cover.')

    st.session_state['court_filter_status'] = True
        
    st.markdown("**:blue[Federal Appellate Courts]**")

    fed_app_courts_entry = st.multiselect(label = 'Select or type in Federal Appellate Courts to cover', 
                                          options = list(us_fed_app_courts.keys()), 
                                          default = us_court_choice_to_list(st.session_state['df_master'].loc[0, 'Federal Appellate Courts'])
                                         )

    #st.session_state['df_master'].loc[0, 'Federal Appellate Courts'] = us_court_choice_to_string(fed_app_courts_entry)
    
    st.markdown("**:blue[Federal District Courts]**")

    fed_dist_courts_entry = st.multiselect(label = 'Select or type in Federal District Courts to cover', 
                                          options = list(us_fed_dist_courts.keys()), 
                                          default = us_court_choice_to_list(st.session_state['df_master'].loc[0, 'Federal District Courts'])
                                         )
    
    #st.session_state['df_master'].loc[0, 'Federal District Courts'] = us_court_choice_to_string(fed_dist_courts_entry)

    st.markdown("**:blue[Federal Historical Courts]**")
    
    fed_hist_courts_entry = st.multiselect(label = 'Select or type in Federal Historical Courts to cover', 
                                          options = list(us_fed_hist_courts.keys()), 
                                          default = us_court_choice_to_list(st.session_state['df_master'].loc[0, 'Federal Historical Courts'])
                                         )
    
    #st.session_state['df_master'].loc[0, 'Federal Historical Courts'] = us_court_choice_to_string(fed_hist_courts_entry)
    
    st.markdown("**:blue[Bankruptcy Courts]**")

    bankr_courts_entry = st.multiselect(label = 'Select or type in Bankruptcy Courts to cover', 
                                          options = list(us_bankr_courts.keys()), 
                                          default = us_court_choice_to_list(st.session_state['df_master'].loc[0, "Bankruptcy Courts"])
                                         )
    
    #st.session_state['df_master'].loc[0, "Bankruptcy Courts"] = us_court_choice_to_string(bankr_courts_entry)

    st.markdown("**:blue[State and Territory Courts]**")

    state_courts_entry = st.multiselect(label = 'Select or type in State and Territory Courts to cover', 
                                          options = list(us_state_courts.keys()), 
                                          default = us_court_choice_to_list(st.session_state['df_master'].loc[0, "State and Territory Courts"])
                                         )
    
    #st.session_state['df_master'].loc[0, "State and Territory Courts"] = us_court_choice_to_string(state_courts_entry)

    st.markdown("**:blue[More Courts]**")

    more_courts_entry = st.multiselect(label = 'Select or type in more Courts to cover', 
                                          options = list(us_more_courts.keys()), 
                                          default = us_court_choice_to_list(st.session_state['df_master'].loc[0, "More Courts"])
                                         )
    
    #st.session_state['df_master'].loc[0, "More Courts"] = us_court_choice_to_string(more_courts_entry)

else: #if jurisdiction_toggle == False
    
    st.success('All courts will be covered.')
    
    st.session_state['court_filter_status'] = False
    st.session_state['df_master'].loc[0, 'Federal Appellate Courts'] = ['All'] 
    st.session_state['df_master'].loc[0, 'Federal District Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Federal Historical Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'Bankruptcy Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'State and Territory Courts'] = ['All']
    st.session_state['df_master'].loc[0, 'More Courts'] = ['All']

#Enable to see what courts are covered
#for jurisdiction in all_us_jurisdictions.keys():

    #st.write(f"Covered for {jurisdiction}: {st.session_state['df_master'].loc[0, jurisdiction]}")

st.subheader("Your search terms")

st.markdown("""For search tips, please visit [CourtListener](https://www.courtlistener.com/help/search-operators/). This section largely mimics their advanced search function.
""")

q_entry = st.text_input(label = 'Search', value = st.session_state['df_master'].loc[0, 'Search'])

order_by_entry = st.selectbox(label = "Search results order ", options = list(us_order_by.keys()), index = list(us_order_by.keys()).index(st.session_state['df_master'].loc[0, 'Search results order']))

precedential_status_entry = st.multiselect(label = 'Precedential status', 
                                           options = list(us_precedential_status.keys()), 
                                           default = st.session_state['df_master'].loc[0, 'Precedential status'])

case_name_entry = st.text_input(label = 'Case name', value = st.session_state['df_master'].loc[0, 'Case Name'])

judge_entry = st.text_input(label = 'Judge', value = st.session_state['df_master'].loc[0, 'Judge'])

filed_after_entry = st.date_input(label = 'Filed after (month first)', value = us_date(st.session_state['df_master'].loc[0, 'Filed after']), format="MM/DD/YYYY", min_value = date(1658, 7, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

filed_before_entry = st.date_input(label = 'Filed before (month first)', value = us_date(st.session_state['df_master'].loc[0, 'Filed before']), format="MM/DD/YYYY", min_value = date(1658, 7, 1), max_value = datetime.now(), help = "If you cannot change this date entry, please press :red[RESET] and try again.")

cited_gt_entry = st.text_input(label = 'Min cites', value = st.session_state['df_master'].loc[0, 'Min cites'])

cited_lt_entry = st.text_input(label = 'Max cites', value = st.session_state['df_master'].loc[0, 'Max cites'])

citation_entry = st.text_input(label = 'Citation', value = st.session_state['df_master'].loc[0, 'Citation'])

neutral_cite_entry = st.text_input(label = 'Neutral citation', value = st.session_state['df_master'].loc[0, 'Neutral citation'])

docket_number_entry = st.text_input(label = 'Docket number', value = st.session_state['df_master'].loc[0, 'Docket number'])

st.subheader("Your CourtListener API token")

token_entry = st.text_input(label = 'Optional', value = hide_own_token(user_token = st.session_state['df_master'].loc[0, 'CourtListener API token'], own_token = st.secrets["courtlistener"]["token"]))

if token_entry:
    st.session_state['df_master'].loc[0, 'CourtListener API token'] = token_entry

#st.write(st.session_state['df_master'].loc[0, 'CourtListener API token'])

st.write('By default, this app will process up to 500 queries per day. If that limit is exceeded, you can still use this app with your own CourtListen API token (click [here](https://www.courtlistener.com/sign-in/) to sign up for one).')

st.info("""You can preview the judgments returned by your search terms.""")

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
    
    #Check whether search terms entered

    us_search_terms = str(st.session_state['df_master'].loc[0, 'Federal Appellate Courts'])  + str(st.session_state['df_master'].loc[0, 'Federal District Courts']) + str(st.session_state['df_master'].loc[0, 'Federal Historical Courts']) + str(st.session_state['df_master'].loc[0, 'Bankruptcy Courts']) + str(st.session_state['df_master'].loc[0, 'State and Territory Courts']) + str(st.session_state['df_master'].loc[0, 'More Courts']) + str(q_entry) + str(case_name_entry) + str(judge_entry) + str(filed_after_entry) + str(filed_before_entry) + str(cited_gt_entry) + str(cited_lt_entry) + str(citation_entry) + str(neutral_cite_entry) + str(docket_number_entry)
    
    if us_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')

    else:

        df_master = us_create_df()

        results_count = us_search_preview(df_master)['results_count']

        search_results = us_search_preview(df_master)['results_to_show']
            
        if results_count > 0:

            df_preview = pd.DataFrame(search_results)

            df_preview['Hyperlink to CourtListener'] = df_preview['Hyperlink to CourtListener'].apply(reverse_link)
            
            link_heading_config = {} 
      
            link_heading_config['Hyperlink to CourtListener'] = st.column_config.LinkColumn(display_text = 'Click')
    
            st.success(f'Your search terms returned {results_count} result(s). Please see below for the top {min(results_count, default_judgment_counter_bound)} result(s).')
                        
            st.dataframe(df_preview.head(default_judgment_counter_bound),  column_config=link_heading_config)
    
        else:
            st.error('Your search terms returned 0 results. Please change your search terms or enter a CourtListener API token, and try again.')


# %% [markdown]
# ## Metadata choice

# %%
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
if keep_button:

    #Check whether search terms entered

    us_search_terms = str(st.session_state['df_master'].loc[0, 'Federal Appellate Courts'])  + str(st.session_state['df_master'].loc[0, 'Federal District Courts']) + str(st.session_state['df_master'].loc[0, 'Federal Historical Courts']) + str(st.session_state['df_master'].loc[0, 'Bankruptcy Courts']) + str(st.session_state['df_master'].loc[0, 'State and Territory Courts']) + str(st.session_state['df_master'].loc[0, 'More Courts']) + str(q_entry) + str(case_name_entry) + str(judge_entry) + str(filed_after_entry) + str(filed_before_entry) + str(cited_gt_entry) + str(cited_lt_entry) + str(citation_entry) + str(neutral_cite_entry) + str(docket_number_entry)
    
    if us_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = us_create_df()

        #st.dataframe(df_master)

        #st.write(df_master.loc[0, 'Federal Appellate Courts'])

        #st.write(type(df_master.loc[0, 'Federal Appellate Courts']))

        if 'CourtListener API token' in df_master.columns:
            df_master.pop('CourtListener API token')

        save_input(df_master)

        st.write('**You can download a copy of your entries.**')
    
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

    us_search_terms = str(st.session_state['df_master'].loc[0, 'Federal Appellate Courts'])  + str(st.session_state['df_master'].loc[0, 'Federal District Courts']) + str(st.session_state['df_master'].loc[0, 'Federal Historical Courts']) + str(st.session_state['df_master'].loc[0, 'Bankruptcy Courts']) + str(st.session_state['df_master'].loc[0, 'State and Territory Courts']) + str(st.session_state['df_master'].loc[0, 'More Courts']) + str(q_entry) + str(case_name_entry) + str(judge_entry) + str(filed_after_entry) + str(filed_before_entry) + str(cited_gt_entry) + str(cited_lt_entry) + str(citation_entry) + str(neutral_cite_entry) + str(docket_number_entry)
    
    if us_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
    
    else:
            
        df_master = us_create_df()
    
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):

            us_search_preview_dict = us_search_preview(df_master)
            
            if us_search_preview_dict['results_count'] == 0:
                
                st.error(no_results_msg)
            
            else:
                
                save_input(df_master)

                st.session_state["page_from"] = 'pages/US.py'
                
                st.switch_page('pages/GPT.py')

