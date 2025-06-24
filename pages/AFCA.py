# ---
# jupyter:
#   jupytext:
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
from functions.common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, date_parser, list_value_check, streamlit_cloud_date_format, streamlit_timezone, save_input, download_buttons
#Import variables
from functions.common_functions import today_in_nums, today, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg, search_error_display


# %% [markdown]
# # AFCA search engine

# %%
from functions.afca_functions import browser, collection_options, product_line_options, product_category_options, product_name_options, issue_type_options, issue_options, afca_search, afca_meta_judgment_dict,  afca_meta_labels_droppable, afca_old_pdf_judgment, afca_old_element_meta, afca_old_search, afca_old_meta_labels_droppable, afca_meta_labels_droppable

if streamlit_timezone() == True:
    from functions.afca_functions import browser_old


# %%
from functions.common_functions import link


# %%
#function to create dataframe
def afca_create_df():

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

    #Input
    #Template
    new_row = {'Processed': '',
           'Timestamp': '',
           'Your name': '', 
           'Your email address': '', 
           'Your GPT API key': '', 
            'Collection': '', 
              #Post 14 June 2024 search terms 
            'Search for published decisions': '', 
            'Search for a financial firm': '', 
           'Product line': '', 
            'Product category': '', 
            'Product name': '', 
            'Issue type': '', 
            'Issue': '', 
          #Pre 14 June 2024 search terms
            'Include decisions made under earlier Terms of Reference': False, 
            'All these words': '', 
           'This exact wording or phrase': '', 
            'One or more of these words - 1': '', 
            'One or more of these words - 2': '', 
            'One or more of these words - 3': '', 
            'Any of these unwanted words': '', 
            'Case number': '', 
            #'Days back from now': '',
            #'Months back from now': '',
            #'Years back from now': '',
            #'Date of decision from': '', 
            #'Date of decision to': '', 
            #General
            'Date from': '', #'DD/MM/YYYY',
            'Date to': '', #'DD/MM/YYYY', 
            'Metadata inclusion' : False,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': '', 
            'Use GPT': False,
           'Use own account': False,
            'Use flagship version of GPT' : False
          }

    #Collection

    try:
        new_row['Collection'] = collection_entry

    except:
        print('Collection not selected.')
        
    #Post June 2024 input
    try:
        new_row['Search for published decisions'] = keywordsearch_entry
    except:
        print('Search for published decisions not entered.')
    
    try:
        new_row['Search for a financial firm'] = ffsearch_entry
    except:
        print('Search for a financial firm not entered.')
    
    try:
        new_row['Product line'] = product_line_entry
    except:
        print('Product line not entered.')
    
    try:
        new_row['Product category'] = product_category_entry
    except:
        print('Product category not entered.')
    
    try:
        new_row['Product name'] = product_name_entry
    except:
        print('Product name not entered.')
    
    try:
        new_row['Issue type'] = issue_type_entry
    except:
        print('Issue type not entered.')
    
    try:
        new_row['Issue'] = issue_entry
    except:
        print('Issue not entered.')


    #Pre June 2024 input

    try:
        new_row['Include decisions made under earlier Terms of Reference'] = early_t_o_r_entry
    except:
        new_row['Include decisions made under earlier Terms of Reference'] = False
        print('Whether to Include decisions made under earlier Terms of Reference not entered.')

    try:
        new_row['All these words'] = all_these_words_entry
    except:
        print('All these words not entered.')

    try:
        new_row['This exact wording or phrase'] = this_exact_wording_phrase_entry
    except:
        print('This exact wording or phrase not entered.')

    try:
        new_row['Any of these unwanted words'] = any_of_these_unwanted_words_entry
    except:
        print('Any of these unwanted words not entered.')

    try:
        new_row['One or more of these words - 1'] = one_or_more_of_these_words_1_entry
    except:
        print('One or more of these words - 1 not entered.')

    try:
        new_row['One or more of these words - 2'] = one_or_more_of_these_words_2_entry
    except:
        print('One or more of these words - 2 not entered.')

    try:
        new_row['One or more of these words - 3'] = one_or_more_of_these_words_3_entry
    except:
        print('One or more of these words - 3 not entered.')

    try:
        new_row['Case number'] = case_number_entry
    except:
        print('Case number not entered.')
    
    #dates
            
    try:
        new_row['Date from'] = date_from_entry.strftime("%d/%m/%Y")

    except:
        print('Date from not entered.')

    try:

        new_row['Date to'] = date_to_entry.strftime("%d/%m/%Y")
        
    except:
        print('Date to not entered.')

    #GPT choice and entry
    try:
        gpt_activation_status = gpt_activation_entry
        new_row['Use GPT'] = gpt_activation_status
    except:
        print('GPT activation status not entered.')

    try:
        gpt_questions = gpt_questions_entry[0: question_characters_bound]
        new_row['Enter your questions for GPT'] = gpt_questions
    
    except:
        print('GPT questions not entered.')

    #metadata choice
    try:
        meta_data_choice = meta_data_entry
        new_row['Metadata inclusion'] = meta_data_choice
    
    except:
        print('Metadata choice not entered.')

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
print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")
print(f"The default number of judgments to scrape per request is capped at {default_judgment_counter_bound}.\n")

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
    st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = ''

    #Jurisdiction specific

    st.session_state.df_master.loc[0, 'Collection'] = 'Decisions published from 14 June 2024'
    
    st.session_state.df_master.loc[0, 'Date from'] = None 
    st.session_state.df_master.loc[0, 'Date to'] = None

    #Post June 2024
    st.session_state.df_master.loc[0, 'Search for published decisions'] = None 
    st.session_state.df_master.loc[0, 'Search for a financial firm'] = None 
    st.session_state.df_master.loc[0, 'Product line'] = None 
    st.session_state.df_master.loc[0, 'Product category'] = None 
    st.session_state.df_master.loc[0, 'Product name'] = None 
    st.session_state.df_master.loc[0, 'Issue type'] = None 
    st.session_state.df_master.loc[0, 'Issue'] = None 

    #Pre June 2024
    st.session_state.df_master.loc[0, 'Include decisions made under earlier Terms of Reference'] = False
    st.session_state.df_master.loc[0, 'All these words'] = None
    st.session_state.df_master.loc[0, 'This exact wording or phrase'] = None
    st.session_state.df_master.loc[0, 'One or more of these words - 1'] = None
    st.session_state.df_master.loc[0, 'One or more of these words - 2'] = None
    st.session_state.df_master.loc[0, 'One or more of these words - 3'] = None
    st.session_state.df_master.loc[0, 'Any of these unwanted words'] = None
    st.session_state.df_master.loc[0, 'Case number'] = None

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
#if st.session_state.page_from != "pages/AFCA.py": #Need to add in order to avoid GPT page from showing form of previous page

return_button = st.button('RETURN to first page')

st.header(f"Search :blue[cases of the Australian Financial Complaints Authority]")

st.success(default_msg)

st.caption(default_caption)

if streamlit_timezone() == True:
    st.warning('One or more Chrome window may have been launched. It must be kept open.')

reset_button = st.button(label='RESET', type = 'primary')

st.subheader('Case collection')

collection_entry = st.selectbox(label = 'Select one to search', options = collection_options, index = collection_options.index(st.session_state.df_master.loc[0, 'Collection']))

st.subheader("Your search terms")

if collection_entry:
    
    st.session_state.df_master.loc[0, 'Collection'] = collection_entry
    
if st.session_state.df_master.loc[0, 'Collection'] == 'Decisions published from 14 June 2024':

    st.markdown("""For search tips, please visit the [AFCA Portal](https://my.afca.org.au/searchpublisheddecisions/). This section mimics their search function.
""")
    
    keywordsearch_entry = st.text_input(label = 'Search for published decisions', value = st.session_state.df_master.loc[0, 'Search for published decisions'])
    
    ffsearch_entry = st.text_input(label = 'Search for a financial firm', value = st.session_state.df_master.loc[0, 'Search for a financial firm'])
    
    product_line_entry = st.selectbox(label = 'Product line', options = list(product_line_options.keys()), index = list_value_check(list(product_line_options.keys()), st.session_state.df_master.loc[0, 'Product line']))
    
    product_category_entry = st.selectbox(label = 'Product category', options = list(product_category_options.keys()), index = list_value_check(list(product_category_options.keys()), st.session_state.df_master.loc[0, 'Product category']))
    
    product_name_entry = st.selectbox(label = 'Product name', options = list(product_name_options.keys()), index = list_value_check(list(product_name_options.keys()), st.session_state.df_master.loc[0, 'Product name']))
    
    issue_type_entry = st.selectbox(label = 'Issue type', options = list(issue_type_options.keys()), index = list_value_check(list(issue_type_options.keys()), st.session_state.df_master.loc[0, 'Issue type']))
    
    issue_entry = st.selectbox(label = 'Issue', options = list(issue_options.keys()), index = list_value_check(list(issue_options.keys()), st.session_state.df_master.loc[0, 'Issue']))

else:
    
    st.markdown("""For search tips, please visit [AFCA's website](https://www.afca.org.au/what-to-expect/search-published-decisions). This section largely mimics their advanced keyword search function.
""")
    early_t_o_r_entry = st.checkbox(label = 'Include decisions made under earlier Terms of Reference', value = st.session_state['df_master'].loc[0, 'Include decisions made under earlier Terms of Reference'])

    st.write('Find decisions that have...')
    
    all_these_words_entry = st.text_input(label = 'all these words', value = st.session_state.df_master.loc[0, 'All these words'])

    this_exact_wording_phrase_entry = st.text_input(label = 'this exact wording or phrase', value = st.session_state.df_master.loc[0, 'This exact wording or phrase'])
    
    one_or_more_of_these_words_1_entry = st.text_input(label = 'one or more of these words', value = st.session_state.df_master.loc[0, 'One or more of these words - 1'])

    one_or_more_of_these_words_2_entry = st.text_input(label = 'Word - 2', value = st.session_state.df_master.loc[0, 'One or more of these words - 2'], label_visibility="collapsed")

    one_or_more_of_these_words_3_entry = st.text_input(label = 'Word - 3', value = st.session_state.df_master.loc[0, 'One or more of these words - 3'], label_visibility="collapsed")
    
    any_of_these_unwanted_words_entry = st.text_input(label = "But don't show decisions that have any of these unwanted words", value = st.session_state.df_master.loc[0, 'Any of these unwanted words'])

    case_number_entry = st.text_input(label = 'Case number', value = st.session_state.df_master.loc[0, 'Case number'])

#Dates are applicable to both collections

date_col1, date_col2 = st.columns(2)

with date_col1:
    
    date_from_entry = st.date_input('Date from', value = date_parser(st.session_state.df_master.loc[0, 'Date from']), format="DD/MM/YYYY", help = "If you cannot change this date entry, please press :red[RESET] and try again.")
    
with date_col2:

    date_to_entry = st.date_input('Date to', value = date_parser(st.session_state.df_master.loc[0, 'Date to']), format="DD/MM/YYYY", help = "If you cannot change this date entry, please press :red[RESET] and try again.")


#st.subheader("Case metadata collection")

#st.markdown("""Would you like to obtain case metadata? Such data include the case number, the financial firm involved, and the decision date. 

#Case name and hyperlinks to AFCA's website are always included with your results.
#""")

#meta_data_entry = st.checkbox(label = 'Include metadata', value = st.session_state['df_master'].loc[0, 'Metadata inclusion'])
meta_data_entry = True

st.info("""You can preview the cases returned by your search terms.""")

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

    if st.session_state.df_master.loc[0, 'Collection'] == 'Decisions published before 14 June 2024':
        
        afca_search_terms = str(all_these_words_entry) + str(this_exact_wording_phrase_entry) + str(one_or_more_of_these_words_1_entry) + str(one_or_more_of_these_words_2_entry) + str(one_or_more_of_these_words_3_entry) + str(case_number_entry)
    else:
    
        afca_search_terms = str(keywordsearch_entry) + str(ffsearch_entry) + str(product_line_entry) + str(product_category_entry) + str(product_name_entry) + str(issue_type_entry) + str(issue_entry) + str(date_from_entry) + str(date_to_entry)
        
    if afca_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
        #quit()

    else:

        with st.spinner(r"$\textsf{\normalsize Getting your search results...}$"):
            
            df_master = afca_create_df()
    
            if st.session_state.df_master.loc[0, 'Collection'] == 'Decisions published before 14 June 2024':
                search_results = afca_old_search(earlier_t_o_r_input = df_master.loc[0, 'Include decisions made under earlier Terms of Reference'], 
                                                    all_these_words_input = df_master.loc[0, 'All these words'], 
                                                    this_exact_wording_or_phrase_input = df_master.loc[0, 'This exact wording or phrase'], 
                                                    one_or_more_of_these_words_1_input = df_master.loc[0, 'One or more of these words - 1'], 
                                                    one_or_more_of_these_words_2_input = df_master.loc[0, 'One or more of these words - 2'], 
                                                    one_or_more_of_these_words_3_input = df_master.loc[0, 'One or more of these words - 3'], 
                                                    any_of_these_unwanted_words_input = df_master.loc[0, 'Any of these unwanted words'], 
                                                    case_number_input = df_master.loc[0, 'Case number'], 
                                                    date_from_input = df_master.loc[0, 'Date from'], 
                                                    date_to_input = df_master.loc[0, 'Date to'], 
                                                    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                                                )
    
            else:
                search_results = afca_search(keywordsearch_input = df_master.loc[0, 'Search for published decisions'], 
                            ffsearch_input = df_master.loc[0, 'Search for a financial firm'], 
                            product_line_input = df_master.loc[0, 'Product line'], 
                            product_category_input = df_master.loc[0, 'Product category'], 
                            product_name_input = df_master.loc[0, 'Product name'], 
                            issue_type_input = df_master.loc[0, 'Issue type'], 
                            issue_input = df_master.loc[0, 'Issue'], 
                            date_from_input = df_master.loc[0, 'Date from'], 
                            date_to_input = df_master.loc[0, 'Date to'])
            
            if search_results['case_sum'] > 0:
    
                df_preview = pd.DataFrame(search_results['case_list'])
                
                link_heading_config = {} 
          
                link_heading_config['Hyperlink to AFCA Portal'] = st.column_config.LinkColumn(display_text = 'Click')
        
                st.success(f'Your search terms returned {search_results["case_sum"]} result(s). Please see below for the top {min(search_results["case_sum"], default_judgment_counter_bound)} result(s).')
                            
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

    if st.session_state.df_master.loc[0, 'Collection'] == 'Decisions published before 14 June 2024':
        
        afca_search_terms = str(all_these_words_entry) + str(this_exact_wording_phrase_entry) + str(one_or_more_of_these_words_1_entry) + str(one_or_more_of_these_words_2_entry) + str(one_or_more_of_these_words_3_entry) + str(case_number_entry)
    else:
    
        afca_search_terms = str(keywordsearch_entry) + str(ffsearch_entry) + str(product_line_entry) + str(product_category_entry) + str(product_name_entry) + str(issue_type_entry) + str(issue_entry) + str(date_from_entry) + str(date_to_entry)
        
    if afca_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
        #quit()
            
    else:
            
        df_master = afca_create_df()

        save_input(df_master)
    
        download_buttons(df_master = df_master, df_individual = [], saving = True, previous = False)


# %%
if return_button:

    df_master = afca_create_df()

    save_input(df_master)        

    st.session_state["page_from"] = 'pages/AFCA.py'

    st.switch_page("Home.py")

# %%
if reset_button:
    
    st.session_state.pop('df_master')

    #clear_cache()
    st.rerun()

# %%
if next_button:

    if st.session_state.df_master.loc[0, 'Collection'] == 'Decisions published before 14 June 2024':
        
        afca_search_terms = str(all_these_words_entry) + str(this_exact_wording_phrase_entry) + str(one_or_more_of_these_words_1_entry) + str(one_or_more_of_these_words_2_entry) + str(one_or_more_of_these_words_3_entry) + str(case_number_entry)
    else:
    
        afca_search_terms = str(keywordsearch_entry) + str(ffsearch_entry) + str(product_line_entry) + str(product_category_entry) + str(product_name_entry) + str(issue_type_entry) + str(issue_entry) + str(date_from_entry) + str(date_to_entry)
        
    if afca_search_terms.replace('None', '') == "":

        st.warning('You must enter some search terms.')
        #quit()
    
    else:
    
        df_master = afca_create_df()
                    
        #Check search results
        with st.spinner(r"$\textsf{\normalsize Checking your search terms...}$"):
            try:
                if st.session_state.df_master.loc[0, 'Collection'] == 'Decisions published before 14 June 2024':
                    search_results = afca_old_search(earlier_t_o_r_input = df_master.loc[0, 'Include decisions made under earlier Terms of Reference'], 
                                                        all_these_words_input = df_master.loc[0, 'All these words'], 
                                                        this_exact_wording_or_phrase_input = df_master.loc[0, 'This exact wording or phrase'], 
                                                        one_or_more_of_these_words_1_input = df_master.loc[0, 'One or more of these words - 1'], 
                                                        one_or_more_of_these_words_2_input = df_master.loc[0, 'One or more of these words - 2'], 
                                                        one_or_more_of_these_words_3_input = df_master.loc[0, 'One or more of these words - 3'], 
                                                        any_of_these_unwanted_words_input = df_master.loc[0, 'Any of these unwanted words'], 
                                                        case_number_input = df_master.loc[0, 'Case number'], 
                                                        date_from_input = df_master.loc[0, 'Date from'], 
                                                        date_to_input = df_master.loc[0, 'Date to'], 
                                                        judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])
                                                    )
    
                else:
                    search_results = afca_search(keywordsearch_input = df_master.loc[0, 'Search for published decisions'], 
                                ffsearch_input = df_master.loc[0, 'Search for a financial firm'], 
                                product_line_input = df_master.loc[0, 'Product line'], 
                                product_category_input = df_master.loc[0, 'Product category'], 
                                product_name_input = df_master.loc[0, 'Product name'], 
                                issue_type_input = df_master.loc[0, 'Issue type'], 
                                issue_input = df_master.loc[0, 'Issue'], 
                                date_from_input = df_master.loc[0, 'Date from'], 
                                date_to_input = df_master.loc[0, 'Date to'])
                
                if search_results['case_sum'] == 0:
                    
                    st.error(no_results_msg)
    
                else:
    
                    save_input(df_master)
    
                    st.session_state["page_from"] = 'pages/AFCA.py'
                    
                    st.switch_page('pages/GPT.py')
            
            except Exception as e:
                print(search_error_display)
                print(e)
                st.error(search_error_display)
                st.error(e)

