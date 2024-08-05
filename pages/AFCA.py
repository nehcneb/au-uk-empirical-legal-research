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
from dateutil.relativedelta import *
from datetime import datetime, timedelta
import sys
import pause
import requests
from bs4 import BeautifulSoup, SoupStrainer
import httplib2
from urllib.request import urlretrieve
import os
import PyPDF2
import io
from io import BytesIO

#Streamlit
import streamlit as st
from streamlit_gsheets import GSheetsConnection
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
from common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, mnc_cleaner, au_date, list_value_check
#Import variables
from common_functions import today_in_nums, today, errors_list, scraper_pause_mean, judgment_text_lower_bound

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %% [markdown]
# # afca search engine

# %%
#Scrape javascript

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.support import expected_conditions as EC

options = Options()
options.add_argument("--disable-gpu")
options.add_argument("--headless")
options.add_argument('--no-sandbox')  
options.add_argument('--disable-dev-shm-usage')  

@st.cache_resource
def get_driver():
    return webdriver.Chrome(
        #service=Service(
            #ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        #),
        options=options,
    )

browser = get_driver()

browser.implicitly_wait(10)
browser.set_page_load_timeout(10)

# %%
from common_functions import link


# %% [markdown]
# ## [NOT WORKING] Pre 14 June 2024

# %% [markdown]
# ## Post 14 June 2024

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
    judgments_counter_bound = st.session_state.judgments_counter_bound

    #GPT enhancement
    gpt_enhancement = st.session_state.gpt_enhancement_entry

    #Input
    #Template
    new_row = {'Processed': '',
           'Timestamp': '',
           'Your name': '', 
           'Your email address': '', 
           'Your GPT API key': '', 
            'Search for published decisions': '', 
               'Search for a financial firm': '', 
            'Product line': '', 
            'Product category': '', 
            'Product name': '', 
            'Issue type': '', 
            'Issue': '', 
            'Date from': '01/01/1900',
            'Date to': today,
            'Metadata inclusion' : False,
           'Maximum number of judgments': judgments_counter_bound, 
           'Enter your questions for GPT': '', 
            'Use GPT': False,
           'Use own account': False,
            'Use flagship version of GPT' : False
          }
    
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
        gpt_questions = gpt_questions_entry[0: 1000]
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
# ### Definitions of menu items

# %%
#Example of code used to generate dropdown menu options

#issue_options = {}
#pair_raw = pair_raw = {"value": "a1149d98-3fc2-ed11-b597-00224892f51a", "text": "Total & Permanent Disability"}
#text = pair_raw['text']
#counter = 0
#for key in issue_options.keys():
	#if text in key:
		#counter += 1
#if counter == 0:
	#issue_options[text] = pair_raw
	#issue_options[text].pop('text')
#else:
	#new_text = f"{text} {counter}"
	#issue_options[new_text] = pair_raw
	#issue_options[new_text].pop('text')

# %%
#'Product line'

product_line_options = {'Credit': {'value': '719de0b0-93c1-ed11-b597-00224892f893'},
 'Deposit Taking': {'value': '779de0b0-93c1-ed11-b597-00224892f893'},
 'General Insurance': {'value': '739de0b0-93c1-ed11-b597-00224892f893'},
 'Investments': {'value': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Life Insurance': {'value': '7f9de0b0-93c1-ed11-b597-00224892f893'},
 'Non rules': {'value': '7b9de0b0-93c1-ed11-b597-00224892f893'},
 'Payment Systems': {'value': '799de0b0-93c1-ed11-b597-00224892f893'},
 'Superannuation': {'value': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Traditional Trustee Services': {'value': '819de0b0-93c1-ed11-b597-00224892f893'}}


# %%
#'Product category'

#Data parents are values of product lines
product_category_options = {'Annuity Policy': {'value': '78c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Approved Deposit Fund': {'value': '7ac2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Business Finance': {'value': '52c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '719de0b0-93c1-ed11-b597-00224892f893'},
 'Consumer Credit': {'value': '54c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '719de0b0-93c1-ed11-b597-00224892f893'},
 'Corporate Fund': {'value': '7cc2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Current Accounts': {'value': '6cc2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '779de0b0-93c1-ed11-b597-00224892f893'},
 'Derivatives/hedging': {'value': '64c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Direct Transfer': {'value': '70c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '799de0b0-93c1-ed11-b597-00224892f893'},
 'Domestic Insurance': {'value': '5ac2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '739de0b0-93c1-ed11-b597-00224892f893'},
 'Estate Management': {'value': '8ec2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '819de0b0-93c1-ed11-b597-00224892f893'},
 'Estate Planning': {'value': '90c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '819de0b0-93c1-ed11-b597-00224892f893'},
 'Extended Warranty': {'value': '5ec2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '739de0b0-93c1-ed11-b597-00224892f893'},
 'Guarantees': {'value': '50c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '719de0b0-93c1-ed11-b597-00224892f893'},
 'Income Stream Risk': {'value': '8cc2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7f9de0b0-93c1-ed11-b597-00224892f893'},
 'Industry Fund': {'value': '7ec2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Life Policy Fund': {'value': '80c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Managed Investments': {'value': '60c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Margin Loans': {'value': '56c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '719de0b0-93c1-ed11-b597-00224892f893'},
 'Non rules': {'value': '74c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '799de0b0-93c1-ed11-b597-00224892f893'},
 'Non-Cash': {'value': '72c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '799de0b0-93c1-ed11-b597-00224892f893'},
 'Non-Income Stream Risk': {'value': 'dd439989-cfc6-ed11-b597-00224811ec4e',
  'data-parent': '7f9de0b0-93c1-ed11-b597-00224892f893'},
 'Professional Indemnity Insurance': {'value': '5cc2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '739de0b0-93c1-ed11-b597-00224892f893'},
 'Public Sector Fund': {'value': '82c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Real Property': {'value': '68c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Retail Fund': {'value': '84c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Retirement Savings Account': {'value': '86c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Safe Custody': {'value': '6ec2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '779de0b0-93c1-ed11-b597-00224892f893'},
 'Savings Accounts': {'value': '6ac2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '779de0b0-93c1-ed11-b597-00224892f893'},
 'Securities': {'value': '62c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Small APRA Fund': {'value': '88c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Small Business/Farm Insurance': {'value': '58c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '739de0b0-93c1-ed11-b597-00224892f893'},
 'Superannuation - Non Trustee Related': {'value': '66c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '759de0b0-93c1-ed11-b597-00224892f893'},
 'Superannuation Fund': {'value': '76c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '7d9de0b0-93c1-ed11-b597-00224892f893'},
 'Trusts': {'value': '92c2a0cb-93c1-ed11-b597-00224892f893',
  'data-parent': '819de0b0-93c1-ed11-b597-00224892f893'}}

# %%
#'Product name'

product_name_options = {'Annuities': {'value': '87139d98-3fc2-ed11-b597-00224892f51a'},
 'Annuity Policy': {'value': '89139d98-3fc2-ed11-b597-00224892f51a'},
 'Another type of credit': {'value': 'ba1adf72-fde3-ed11-8847-000d3a6ad49b'},
 'Another type of general insurance': {'value': 'e1957fbb-5ee6-ed11-8848-000d3a6a9642'},
 'Approved Deposit Fund': {'value': '8b139d98-3fc2-ed11-b597-00224892f51a'},
 'ATM': {'value': '8d139d98-3fc2-ed11-b597-00224892f51a'},
 'Australian Equity Funds': {'value': '8f139d98-3fc2-ed11-b597-00224892f51a'},
 'Bank Bills': {'value': '91139d98-3fc2-ed11-b597-00224892f51a'},
 'Bank Drafts': {'value': '93139d98-3fc2-ed11-b597-00224892f51a'},
 'Bank Guarantee': {'value': '95139d98-3fc2-ed11-b597-00224892f51a'},
 'Beneficiary': {'value': '97139d98-3fc2-ed11-b597-00224892f51a'},
 'Bills of Exchange': {'value': '99139d98-3fc2-ed11-b597-00224892f51a'},
 'Bonds': {'value': '9b139d98-3fc2-ed11-b597-00224892f51a'},
 'Brown Goods': {'value': '9d139d98-3fc2-ed11-b597-00224892f51a'},
 'Builder’s warranty': {'value': 'f45b7989-00e9-ed11-8848-000d3a6a9642'},
 'Business Credit Card': {'value': '9f139d98-3fc2-ed11-b597-00224892f51a'},
 'Business Guarantee': {'value': 'a1139d98-3fc2-ed11-b597-00224892f51a'},
 'Business Loans': {'value': 'a3139d98-3fc2-ed11-b597-00224892f51a'},
 'Business or farm': {'value': 'bd685caf-5ee6-ed11-8848-000d3a6a9642'},
 'Business Transaction Accounts': {'value': 'a5139d98-3fc2-ed11-b597-00224892f51a'},
 'Buy Now, Pay Later': {'value': 'a7139d98-3fc2-ed11-b597-00224892f51a'},
 'Cash Management Accounts': {'value': '5e897c0a-d053-ee11-be6f-000d3a6ad35b'},
 'Cash Management Accounts 1': {'value': 'a9139d98-3fc2-ed11-b597-00224892f51a'},
 'Cash Management Accounts 2': {'value': '8cfd2556-258e-ee11-be36-6045bde4aa06'},
 'Charitable/ Educational Schemes': {'value': 'ab139d98-3fc2-ed11-b597-00224892f51a'},
 'Cheques': {'value': 'ad139d98-3fc2-ed11-b597-00224892f51a'},
 'Commercial bills': {'value': 'af139d98-3fc2-ed11-b597-00224892f51a'},
 'Commercial Property': {'value': 'b1139d98-3fc2-ed11-b597-00224892f51a'},
 'Commercial Vehicles': {'value': 'b3139d98-3fc2-ed11-b597-00224892f51a'},
 'Computer & Electronic Breakdown': {'value': 'b5139d98-3fc2-ed11-b597-00224892f51a'},
 'Construction Loans': {'value': 'b7139d98-3fc2-ed11-b597-00224892f51a'},
 'Consumer Credit Insurance': {'value': 'b9139d98-3fc2-ed11-b597-00224892f51a'},
 'Consumer Credit Insurance 1': {'value': '3218b47b-268e-ee11-be36-6045bde4aa06'},
 'Consumer Guarantee': {'value': 'bb139d98-3fc2-ed11-b597-00224892f51a'},
 'Contractors All Risk': {'value': 'bd139d98-3fc2-ed11-b597-00224892f51a'},
 'Contracts for Difference': {'value': 'bf139d98-3fc2-ed11-b597-00224892f51a'},
 'Counter Transactions': {'value': 'c3139d98-3fc2-ed11-b597-00224892f51a'},
 'Credit Cards': {'value': 'c5139d98-3fc2-ed11-b597-00224892f51a'},
 'Cryptocurrency': {'value': 'c7139d98-3fc2-ed11-b597-00224892f51a'},
 'Cyber': {'value': 'c9139d98-3fc2-ed11-b597-00224892f51a'},
 'Death Benefit': {'value': 'cb139d98-3fc2-ed11-b597-00224892f51a'},
 'Death Benefit 1': {'value': '717416f2-278e-ee11-be36-6045bde4a41a'},
 'Death Benefit 2': {'value': 'b38c09d9-2a8e-ee11-be36-6045bde4a41a'},
 'Death Benefit 3': {'value': '7d68c7ec-2c8e-ee11-be36-6045bde4a41a'},
 'Death Benefit 4': {'value': '322f228d-2d8e-ee11-be36-6045bde4a41a'},
 'Death Benefit 5': {'value': 'f5a921e1-cd9f-ee11-be37-6045bde6f4e7'},
 'Debentures': {'value': 'cd139d98-3fc2-ed11-b597-00224892f51a'},
 'Debt Agreement': {'value': 'cf139d98-3fc2-ed11-b597-00224892f51a'},
 'Debt management/credit repair': {'value': 'd1139d98-3fc2-ed11-b597-00224892f51a'},
 'Direct Debits': {'value': 'd3139d98-3fc2-ed11-b597-00224892f51a'},
 'EFTPOS': {'value': 'd5139d98-3fc2-ed11-b597-00224892f51a'},
 'Electronic Banking': {'value': 'd7139d98-3fc2-ed11-b597-00224892f51a'},
 'Endowments': {'value': 'd9139d98-3fc2-ed11-b597-00224892f51a'},
 'Enduring Powers of Attorney': {'value': 'db139d98-3fc2-ed11-b597-00224892f51a'},
 'Equity Release': {'value': 'dd139d98-3fc2-ed11-b597-00224892f51a'},
 'Estate Management': {'value': 'df139d98-3fc2-ed11-b597-00224892f51a'},
 'Exchange Traded Funds': {'value': 'e1139d98-3fc2-ed11-b597-00224892f51a'},
 'Film Schemes': {'value': 'e3139d98-3fc2-ed11-b597-00224892f51a'},
 'Fire or accidental damage': {'value': 'e5139d98-3fc2-ed11-b597-00224892f51a'},
 'First Home Buyer Accounts': {'value': 'e7139d98-3fc2-ed11-b597-00224892f51a'},
 'Foreign Currency Accounts': {'value': 'e9139d98-3fc2-ed11-b597-00224892f51a'},
 'Foreign Currency Transfers': {'value': 'eb139d98-3fc2-ed11-b597-00224892f51a'},
 'Foreign Exchange': {'value': 'ed139d98-3fc2-ed11-b597-00224892f51a'},
 'Forwards': {'value': 'ef139d98-3fc2-ed11-b597-00224892f51a'},
 'Funeral Plans': {'value': 'f1139d98-3fc2-ed11-b597-00224892f51a'},
 'Futures': {'value': 'f3139d98-3fc2-ed11-b597-00224892f51a'},
 'Glass': {'value': 'f5139d98-3fc2-ed11-b597-00224892f51a'},
 'Hire purchase/lease': {'value': 'f7139d98-3fc2-ed11-b597-00224892f51a'},
 'Hire purchase/lease 1': {'value': 'e3abf1be-218e-ee11-be36-6045bde4aa06'},
 'Home Building': {'value': 'f9139d98-3fc2-ed11-b597-00224892f51a'},
 'Home Contents': {'value': 'fb139d98-3fc2-ed11-b597-00224892f51a'},
 'Home Loans': {'value': 'fd139d98-3fc2-ed11-b597-00224892f51a'},
 'Horse Schemes': {'value': 'ff139d98-3fc2-ed11-b597-00224892f51a'},
 'Income Protection': {'value': 'faf79a05-c953-ee11-be6f-000d3a6ad35b'},
 'Income Protection 1': {'value': '01149d98-3fc2-ed11-b597-00224892f51a'},
 'Industrial Special Risk': {'value': '03149d98-3fc2-ed11-b597-00224892f51a'},
 'Interest free finance': {'value': '07149d98-3fc2-ed11-b597-00224892f51a'},
 'International Equity Funds': {'value': '09149d98-3fc2-ed11-b597-00224892f51a'},
 'Investment Property Loans': {'value': '0b149d98-3fc2-ed11-b597-00224892f51a'},
 'Investor Direct Portfolio Services': {'value': '0d149d98-3fc2-ed11-b597-00224892f51a'},
 'Land Transit': {'value': '0f149d98-3fc2-ed11-b597-00224892f51a'},
 'Landlords Insurance': {'value': '11149d98-3fc2-ed11-b597-00224892f51a'},
 'Letter of credit': {'value': '13149d98-3fc2-ed11-b597-00224892f51a'},
 'Life Policy Fund': {'value': '15149d98-3fc2-ed11-b597-00224892f51a'},
 'Line of credit/overdraft': {'value': '17149d98-3fc2-ed11-b597-00224892f51a'},
 'Line of credit/overdraft 1': {'value': 'cbd06226-218e-ee11-be36-6045bde4aa06'},
 'Litigation Funding Scheme': {'value': '19149d98-3fc2-ed11-b597-00224892f51a'},
 'Livestock': {'value': '1b149d98-3fc2-ed11-b597-00224892f51a'},
 'Loss of Profits/ Business Interruption': {'value': '1d149d98-3fc2-ed11-b597-00224892f51a'},
 'Loyalty Programs': {'value': '1f149d98-3fc2-ed11-b597-00224892f51a'},
 'Machinery breakdowns': {'value': '21149d98-3fc2-ed11-b597-00224892f51a'},
 'Managed Discretionary Accounts': {'value': '23149d98-3fc2-ed11-b597-00224892f51a'},
 'Managed Strata Title Schemes': {'value': '25149d98-3fc2-ed11-b597-00224892f51a'},
 'Margin Loans': {'value': '27149d98-3fc2-ed11-b597-00224892f51a'},
 'Marine': {'value': 'a8b3cdd8-00e9-ed11-8848-000d3a6a9642'},
 'Medical Indemnity': {'value': '29149d98-3fc2-ed11-b597-00224892f51a'},
 'Merchant Facilities': {'value': '2b149d98-3fc2-ed11-b597-00224892f51a'},
 'Mixed Asset Fund/s': {'value': '2d149d98-3fc2-ed11-b597-00224892f51a'},
 'Money': {'value': '2f149d98-3fc2-ed11-b597-00224892f51a'},
 'Mortgage Offset Accounts': {'value': '31149d98-3fc2-ed11-b597-00224892f51a'},
 'Mortgage Schemes': {'value': '33149d98-3fc2-ed11-b597-00224892f51a'},
 'Motor Vehicle': {'value': '3d149d98-3fc2-ed11-b597-00224892f51a'},
 'Motor Vehicle- Comprehensive': {'value': '35149d98-3fc2-ed11-b597-00224892f51a'},
 'Motor Vehicle- Third Party': {'value': '37149d98-3fc2-ed11-b597-00224892f51a'},
 'Motor Vehicle- Third Party Fire and Theft': {'value': '39149d98-3fc2-ed11-b597-00224892f51a'},
 'Motor Vehicle- Uninsured Third Party': {'value': '3b149d98-3fc2-ed11-b597-00224892f51a'},
 'Non FF Debt': {'value': '3f149d98-3fc2-ed11-b597-00224892f51a'},
 'Non FF debt/Non-financial product deb': {'value': '41149d98-3fc2-ed11-b597-00224892f51a'},
 'Non rules': {'value': '43149d98-3fc2-ed11-b597-00224892f51a'},
 'Non-Cash Systems': {'value': '45149d98-3fc2-ed11-b597-00224892f51a'},
 'Online Accounts': {'value': '47149d98-3fc2-ed11-b597-00224892f51a'},
 'Options ': {'value': '49149d98-3fc2-ed11-b597-00224892f51a'},
 'Other Complaint': {'value': '9bd97ba8-c753-ee11-be6f-000d3a6ad35b'},
 'Other Complaint 1': {'value': '3e17d79f-c853-ee11-be6f-000d3a6ad35b'},
 'Other Complaint 2': {'value': 'bc92fcc5-ce53-ee11-be6f-000d3a6ad35b'},
 'Other Complaint 3': {'value': 'f60b61a8-00e4-ed11-8847-000d3a6ad49b'},
 'Other Professional Indemnity': {'value': '4b149d98-3fc2-ed11-b597-00224892f51a'},
 'Other superannuation fund complaint': {'value': '2a187c25-6fe7-ed11-8848-000d3a6ad49b'},
 'Passbook Accounts': {'value': '4d149d98-3fc2-ed11-b597-00224892f51a'},
 'Pension': {'value': '4f149d98-3fc2-ed11-b597-00224892f51a'},
 'Pension 1': {'value': 'b98e7d7c-278e-ee11-be36-6045bde4a41a'},
 'Pension 2': {'value': '58dfd680-2d8e-ee11-be36-6045bde4a41a'},
 'Personal and Domestic Property- Caravan': {'value': '51149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Domestic Pet': {'value': '53149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Horse': {'value': '55149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Mobile Phone': {'value': '57149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Moveables': {'value': '59149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Pleasure Craft': {'value': '5b149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Trailer': {'value': '5d149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal and Domestic Property- Valuables': {'value': '5f149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal Loans': {'value': '61149d98-3fc2-ed11-b597-00224892f51a'},
 'Personal Transaction Accounts': {'value': '63149d98-3fc2-ed11-b597-00224892f51a'},
 'Pooled Superannuation Trust': {'value': '65149d98-3fc2-ed11-b597-00224892f51a'},
 'Primary Production Schemes': {'value': '67149d98-3fc2-ed11-b597-00224892f51a'},
 'Private health': {'value': 'd66672c0-00e9-ed11-8848-000d3a6a9642'},
 'Promissory Notes': {'value': '69149d98-3fc2-ed11-b597-00224892f51a'},
 'Property Funds': {'value': '6b149d98-3fc2-ed11-b597-00224892f51a'},
 'Public Liability': {'value': '6d149d98-3fc2-ed11-b597-00224892f51a'},
 'Real Property': {'value': '71149d98-3fc2-ed11-b597-00224892f51a'},
 'Residential Strata Title': {'value': '73149d98-3fc2-ed11-b597-00224892f51a'},
 'Retirement Savings Account': {'value': '77149d98-3fc2-ed11-b597-00224892f51a'},
 'Safe Custody': {'value': '79149d98-3fc2-ed11-b597-00224892f51a'},
 'Scholarship Funds': {'value': '7b149d98-3fc2-ed11-b597-00224892f51a'},
 'Self-managed Superannuation Fund': {'value': '7d149d98-3fc2-ed11-b597-00224892f51a'},
 'Shares': {'value': '7f149d98-3fc2-ed11-b597-00224892f51a'},
 'Short term finance': {'value': '81149d98-3fc2-ed11-b597-00224892f51a'},
 'Sickness and Accident Insurance': {'value': '83149d98-3fc2-ed11-b597-00224892f51a'},
 'Small APRA Fund': {'value': '85149d98-3fc2-ed11-b597-00224892f51a'},
 'Specific purpose': {'value': '87149d98-3fc2-ed11-b597-00224892f51a'},
 'Stored Value Cards': {'value': '89149d98-3fc2-ed11-b597-00224892f51a'},
 'Superannuation Account': {'value': '8b149d98-3fc2-ed11-b597-00224892f51a'},
 'Superannuation Account 1': {'value': 'b0f7d146-2b8e-ee11-be36-6045bde4a41a'},
 'Superannuation Account 2': {'value': '8928f16d-2d8e-ee11-be36-6045bde4a41a'},
 'Superannuation Account 3': {'value': '4b542808-2e8e-ee11-be36-6045bde4a41a'},
 'Superannuation Account 4': {'value': 'f87e4611-cf9f-ee11-be37-6045bde6f4e7'},
 'Superannuation Fund 1': {'value': '8d149d98-3fc2-ed11-b597-00224892f51a'},
 'Swaps': {'value': '8f149d98-3fc2-ed11-b597-00224892f51a'},
 'Telegraphic Transfers': {'value': '91149d98-3fc2-ed11-b597-00224892f51a'},
 'Term Deposits': {'value': '93149d98-3fc2-ed11-b597-00224892f51a'},
 'Term Life': {'value': '95149d98-3fc2-ed11-b597-00224892f51a'},
 'Terminal Illness': {'value': '97149d98-3fc2-ed11-b597-00224892f51a'},
 'Terminal Illness 1': {'value': 'd1e580f1-2a8e-ee11-be36-6045bde4a41a'},
 'Terminal Illness 2': {'value': '5ba3aaff-2c8e-ee11-be36-6045bde4a41a'},
 'Terminal Illness 3': {'value': '065900b9-2d8e-ee11-be36-6045bde4a41a'},
 'Terminal Illness 4': {'value': '38b92f12-ce9f-ee11-be37-6045bde6f4e7'},
 'Theft 1': {'value': '99149d98-3fc2-ed11-b597-00224892f51a'},
 'Ticket Insurance': {'value': '9b149d98-3fc2-ed11-b597-00224892f51a'},
 'Timeshare Schemes': {'value': '9d149d98-3fc2-ed11-b597-00224892f51a'},
 'Title Insurance': {'value': '9f149d98-3fc2-ed11-b597-00224892f51a'},
 'Total & Permanent Disability': {'value': '48c5503c-c953-ee11-be6f-000d3a6ad35b'},
 'Total & Permanent Disability 1': {'value': 'a1149d98-3fc2-ed11-b597-00224892f51a'},
 'Total & Permanent Disability 2': {'value': '3697d553-298e-ee11-be36-6045bde4a41a'},
 'Total & Permanent Disability 3': {'value': '4b393410-2b8e-ee11-be36-6045bde4a41a'},
 'Total & Permanent Disability 4': {'value': 'bb19b324-2d8e-ee11-be36-6045bde4a41a'},
 'Total & Permanent Disability 5': {'value': '4ac09bdd-2d8e-ee11-be36-6045bde4a41a'},
 'Total & Permanent Disability 6': {'value': '3f986a59-ce9f-ee11-be37-6045bde6f4e7'},
 'Total & Temporary Disability': {'value': 'afc19083-288e-ee11-be36-6045bde4a41a'},
 'Total & Temporary Disability 1': {'value': 'df854728-2b8e-ee11-be36-6045bde4a41a'},
 'Total & Temporary Disability 2': {'value': '68d0dc61-2d8e-ee11-be36-6045bde4a41a'},
 'Total & Temporary Disability 3': {'value': 'd545c8f5-2d8e-ee11-be36-6045bde4a41a'},
 'Trauma': {'value': 'a5149d98-3fc2-ed11-b597-00224892f51a'},
 'Travel': {'value': 'a7149d98-3fc2-ed11-b597-00224892f51a'},
 "Travellers' Cheques": {'value': 'a9149d98-3fc2-ed11-b597-00224892f51a'},
 'Trust Bond': {'value': 'ab149d98-3fc2-ed11-b597-00224892f51a'},
 'Trustee Common Funds': {'value': 'ad149d98-3fc2-ed11-b597-00224892f51a'},
 'Trusts': {'value': 'c66d7c30-6be7-ed11-8848-000d3a6ad5b3'},
 'Warrants': {'value': 'af149d98-3fc2-ed11-b597-00224892f51a'},
 'White Goods': {'value': 'b1149d98-3fc2-ed11-b597-00224892f51a'},
 'Whole of Life ': {'value': 'b3149d98-3fc2-ed11-b597-00224892f51a'},
 'Wills': {'value': 'b5149d98-3fc2-ed11-b597-00224892f51a'},
 'Worker’s compensation': {'value': 'd39e8da1-00e9-ed11-8848-000d3a6a9642'}}


# %%
#'Issue type'

issue_type_options = {'Accessibility': {'value': '3a35d144-0116-ee11-9cbe-000d3a6a9642'},
 'Advice': {'value': '80e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'afca Engagement': {'value': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Authorisation/Instructions': {'value': '84e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Charges': {'value': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Charges, Fees, Interest or Premiums': {'value': '86e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Claims Handling': {'value': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Communication': {'value': '6fd45e57-0116-ee11-9cbe-000d3a6a9642'},
 'Conduct': {'value': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Consumer Data Right': {'value': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Consumer Data Rights': {'value': '8ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Credit Reporting': {'value': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Disclosure': {'value': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'Disclosure and Document Distribution': {'value': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Efficiency & Effectiveness': {'value': 'a0535f51-0116-ee11-9cbe-000d3a6a9642'},
 'Fairness & Impartiality': {'value': 'e72a054b-0116-ee11-9cbe-000d3a6a9642'},
 'FF Decision': {'value': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Financial Difficulty': {'value': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Financial Difficulty/Hardship': {'value': '90e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Instructions': {'value': 'a8e3b749-afc1-ed11-83fe-000d3a6ad49b'},
 'Internal Dispute Resolution': {'value': '92e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Lending and Recovery Practice': {'value': '94e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Non rules': {'value': 'fe41fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Observations': {'value': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'Other Complaint': {'value': '4e60feb6-20e8-ed11-8848-000d3a6ad5b3'},
 'OTR': {'value': '5f21aa63-0116-ee11-9cbe-000d3a6a9642'},
 'Privacy & Confidentiality': {'value': '32ff8356-afc1-ed11-83fe-000d3a6ad49b'},
 'Privacy and Credit Reporting': {'value': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Records Management': {'value': '98e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Sales Practices': {'value': '9ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Service': {'value': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Source': {'value': 'a7c5c437-0116-ee11-9cbe-000d3a6a9642'},
 'Transactions': {'value': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Transactions and Processing': {'value': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'}}

# %%
#'Issue'

#Data parents are values of issue types

issue_options = {'A fee or charge - eg premiums, excesses': {'value': '49170f1f-f805-ee11-8f6e-000d3a6ad5b3',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Account administration error': {'value': 'ef32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Account balance': {'value': 'e1f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Account closure': {'value': 'e3f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Account closure 1': {'value': '4d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Account operations and features': {'value': 'e5f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Account restriction': {'value': '53f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Account switching process': {'value': '55f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Accounting for reduced input tax credit': {'value': '89f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '86e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Accuracy of credit file enquiry': {'value': '2ff81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Accuracy of default listing': {'value': '31f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Accuracy of FHA reporting': {'value': '33f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Accuracy of liability listing': {'value': '35f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Accuracy of reporting (CRB)': {'value': '37f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Accuracy of RHI reporting': {'value': '39f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'afca approach to terms of settlement/settlement requiring investigation': {'value': '63f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Age discrimination': {'value': '8539554a-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '3a35d144-0116-ee11-9cbe-000d3a6a9642'},
 'Allocation of rewards points': {'value': '57f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Applicant rejects FSP decision': {'value': '4133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Application for early super release declined': {'value': '4f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Application of discount': {'value': '8bf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '86e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Application of legislation': {'value': '9bf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Application of policy/interpretation': {'value': '9df71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Application/calculation of charge': {'value': '8ff71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '86e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Application/calculation of fee': {'value': '91f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '86e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Application/calculation of interest': {'value': '93f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '86e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Application/calculation of premium': {'value': '8df71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '86e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Application/calculation of stamp duty': {'value': '95f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '86e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Appropriate lending': {'value': '1df81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '94e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Appropriate Lending': {'value': '5133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Appropriateness of advice': {'value': '5d68fb20-400f-ee11-8f6e-00224892f893',
  'data-parent': '80e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Avoidance of policies': {'value': '9ff71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Balance transfer systems': {'value': '59f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Bias': {'value': 'd640425d-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'e72a054b-0116-ee11-9cbe-000d3a6a9642'},
 'Break costs': {'value': '1b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Break costs disclosure': {'value': '2b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'Cancellation of policy': {'value': '5333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Cancellation of refund': {'value': '5533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Cancellation/reduction of facility': {'value': '1ff81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '94e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'CFD disclosure': {'value': 'e7f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Charge disclosure': {'value': 'e9f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Chargebacks - declined (consumer)': {'value': '0b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Chargebacks - delayed (consumer)': {'value': '0d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Chargebacks - merchant': {'value': '0f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Claim amount': {'value': '5733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Claim assessment': {'value': 'a1f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Claim denial: full': {'value': 'a3f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Claim denial: partial': {'value': 'a5f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Client qualification: Contracts for difference': {'value': '5f68fb20-400f-ee11-8f6e-00224892f893',
  'data-parent': '80e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Collection activity during open EDR case': {'value': '65f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Collection/recovery action': {'value': '21f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '94e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Commercial credit reporting': {'value': '5933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Compliance with afca Engagement Charter': {'value': '67f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with afca preliminary assessment/recommendation': {'value': '69f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with afca timeframes': {'value': '6bf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with APPs': {'value': '3bf81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with best interest obligations': {'value': '6168fb20-400f-ee11-8f6e-00224892f893',
  'data-parent': '80e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with CR Code (other)': {'value': '3df81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with customer mandate': {'value': '77f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '84e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with director duties': {'value': 'b1f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with duty of utmost good faith': {'value': 'bff71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with enforceable undertakings': {'value': 'b3f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with know your client obligations': {'value': '6368fb20-400f-ee11-8f6e-00224892f893',
  'data-parent': '80e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with management agreement': {'value': 'b5f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Compliance with settlement agreement': {'value': 'b7f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Conduct of assessor/contractor': {'value': 'bbf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Conduct of employees/authorised representatives': {'value': 'b9f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Conduct of investigator': {'value': 'bdf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Conflict of Interest': {'value': '7734b783-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'e72a054b-0116-ee11-9cbe-000d3a6a9642'},
 'Consent to disclose': {'value': '3ff81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Consent to electronic delivery': {'value': 'ebf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Content of siginificant event notice': {'value': 'edf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Contract/policy delivery': {'value': 'eff71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Co-operating with afca': {'value': '6df71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'CR Code Complaints Management': {'value': '0ff81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '92e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Credit Enquiry': {'value': '9533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Credit file corrections': {'value': '41f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Credit reporting': {'value': '0333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '32ff8356-afc1-ed11-83fe-000d3a6ad49b'},
 'Credit Score': {'value': '9733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Dealing with vulnerable consumers': {'value': 'c1f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Death benefit distribution': {'value': '5b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Death benefit distributions': {'value': '5bf81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Decline of Financial Difficulty Request': {'value': '4333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Deductible or excess': {'value': '1d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Default judgment obtained': {'value': '4533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Default Listing': {'value': '9933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Default Notice': {'value': '4733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Delay': {'value': 'e932d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a8e3b749-afc1-ed11-83fe-000d3a6ad49b'},
 'Delay in claim handling': {'value': 'f132d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Delay in complaint handling': {'value': 'f332d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Delay/error in superannuation rollovers': {'value': '5df81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Delays in claim handling': {'value': 'a7f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Denial of application or variation request': {'value': '5d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim': {'value': '5f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-complainant non-disclosure': {'value': '6133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-DUI': {'value': '6333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-Exclusion/ condition': {'value': '6533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-Fraudulent claim': {'value': '6733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-No policy or contract': {'value': '6933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of claim-No proof of loss': {'value': '6b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Denial of variation request': {'value': '6d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Design, pricing and distribution ': {'value': 'f1f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Did not comply with Rules, OGs or other policy': {'value': '7c29eb76-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'e72a054b-0116-ee11-9cbe-000d3a6a9642'},
 'Did not comply with Rules, OGs or other policy 1': {'value': 'b766fc34-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'Did not understand complaint': {'value': 'd150bff4-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '6fd45e57-0116-ee11-9cbe-000d3a6a9642'},
 'Direct debits': {'value': '5ff81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Disability discrimination': {'value': 'ed254143-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '3a35d144-0116-ee11-9cbe-000d3a6a9642'},
 'Discharge of Loans': {'value': '23f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '94e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Discourteous communication': {'value': '94ed19e2-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '6fd45e57-0116-ee11-9cbe-000d3a6a9642'},
 'Dishonoured transactions': {'value': '1133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Documentation missing from file': {'value': 'b3a61e47-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'Duplicate transactions': {'value': '61f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Early access to superannuation advice': {'value': '6568fb20-400f-ee11-8f6e-00224892f893',
  'data-parent': '80e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Early repayment fee/cost': {'value': '97f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '86e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Elder abuse': {'value': '79f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '84e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Engagement charter issue': {'value': '510f025a-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'Error in debt collection': {'value': '6f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Errors in Determination': {'value': 'ebf6407f-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'Failed to address key issues/concerns in decision': {'value': 'c15d6196-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'a0535f51-0116-ee11-9cbe-000d3a6a9642'},
 'Failed to follow process': {'value': 'ce0089b5-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'a0535f51-0116-ee11-9cbe-000d3a6a9642'},
 "Failure to act in client's best interests": {'value': '3533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Failure to exchange information': {'value': '7bf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '84e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Failure to follow instructions/agreement': {'value': 'eb32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a8e3b749-afc1-ed11-83fe-000d3a6ad49b'},
 'Failure to give effect to afca determination': {'value': '6ff71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Failure to prioritise clients interests': {'value': '3733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Failure to provide advice': {'value': '3933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Failure to provide special needs assistance': {'value': 'f532d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Failure/ refusal to provide access': {'value': '0533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '32ff8356-afc1-ed11-83fe-000d3a6ad49b'},
 'Family law division of super benefit': {'value': '7133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Family Violence/co-debtor hardship': {'value': '01f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '90e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Family violence/co-debtor policies': {'value': '25f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '94e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Fee disclosure': {'value': 'f3f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Fee Disclosure': {'value': '2d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'FF complaint handling': {'value': 'b9161118-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'a7c5c437-0116-ee11-9cbe-000d3a6a9642'},
 'FF failure to respond to request for assistance': {'value': '4933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'FF process took too long': {'value': '053cc09c-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'a0535f51-0116-ee11-9cbe-000d3a6a9642'},
 'Financial advice provided by my trustee': {'value': '222fb630-0fe8-ed11-8848-000d3a6ad5b3',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Financial difficulty policy': {'value': '03f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '90e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Flood claim': {'value': 'a9f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'General advice warnings': {'value': '6768fb20-400f-ee11-8f6e-00224892f893',
  'data-parent': '80e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Guarantee requirements': {'value': 'f5f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Guarantor financial difficulty': {'value': '05f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '90e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'High conflict complainant': {'value': 'dc90e353-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'I believe the fee has been incorrectly charged to me': {'value': 'c1bd198d-1b01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'I believe the fee has been incorrectly charged to me 1': {'value': 'c580a80a-1c01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'I cannot afford my repayments': {'value': 'ffec1c3b-f4e8-ed11-8848-000d3a6b1bd3',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'I was provided with incorrect fee information': {'value': 'cb01b180-1b01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'I was provided with incorrect fee information 1': {'value': '3087fefc-1b01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'IA process took too long': {'value': '80aa52af-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'a0535f51-0116-ee11-9cbe-000d3a6a9642'},
 'Identification procedures': {'value': '81f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '84e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Inadequate assistance provided': {'value': '8fb6b12a-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '3a35d144-0116-ee11-9cbe-000d3a6a9642'},
 'Inadequate documentation/phone notes': {'value': 'a5280041-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'Inadequate response to calls or correspondence': {'value': '468a54c8-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '6fd45e57-0116-ee11-9cbe-000d3a6a9642'},
 'Inadequate response to questions/information requests': {'value': '61c18cd4-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '6fd45e57-0116-ee11-9cbe-000d3a6a9642'},
 'Inappropriate advice': {'value': '3b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Inappropriate debt collection action': {'value': '7333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Inappropriate margin call notice and/or investment': {'value': '7533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Inappropriate portfolio liquidation': {'value': 'f732d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Inapproriate collection activity': {'value': '07f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '90e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Incorrect  payment': {'value': '3d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect advice': {'value': '1f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect assessment of fact/law': {'value': 'ef903b1b-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '5f21aa63-0116-ee11-9cbe-000d3a6a9642'},
 'Incorrect commissions': {'value': '2133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect fees/ costs': {'value': 'f932d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect Fees/Charges EXAMPLE CONFIRM': {'value': '03faa0de-67e9-ed11-8848-000d3a6b1bd3',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect financial information provided': {'value': '2333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect interest added': {'value': '1333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect premiums': {'value': '2533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect product/service information': {'value': '2f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect tax': {'value': '2733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect/inappropriate advice': {'value': 'd5f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Incorrect/inappropriate advice 1': {'value': '8733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect/inappropriate data collection': {'value': 'd7f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Incorrect/inappropriate data collection 1': {'value': '8933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect/inappropriate data correction': {'value': '8b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect/inappropriate data maintenance': {'value': 'd9f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Incorrect/inappropriate data maintenance 1': {'value': '8d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrect/inappropriate data use or disclosure': {'value': 'dbf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Incorrect/inappropriate data use or disclosure 1': {'value': '8f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Incorrectly processed instructions': {'value': 'ed32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a8e3b749-afc1-ed11-83fe-000d3a6ad49b'},
 'Insufficient product/service information': {'value': '3133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'Interpretation of Policy Terms and Conditions': {'value': '7733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Interpretation of product terms and conditions': {'value': '7933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Investment scam': {'value': '6968fb20-400f-ee11-8f6e-00224892f893',
  'data-parent': '80e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Issues with referral to IA': {'value': '50eee936-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '3a35d144-0116-ee11-9cbe-000d3a6a9642'},
 'Joint loan benefit': {'value': '27f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '94e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Jurisdictional reviews': {'value': '1e33a272-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'Lack of procedural fairness': {'value': 'f164a556-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'e72a054b-0116-ee11-9cbe-000d3a6a9642'},
 'Lack of update': {'value': 'e5b3b689-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'a0535f51-0116-ee11-9cbe-000d3a6a9642'},
 'Level of expertise': {'value': 'c3f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Liability Disputed': {'value': '7b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Limitation of account (third-party use)': {'value': '7df71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '84e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Loss of documents/ personal property': {'value': 'fb32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Management of a systemic issue/ Code breaches': {'value': 'e4ccda21-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '5f21aa63-0116-ee11-9cbe-000d3a6a9642'},
 'Management of complainant details': {'value': 'fd32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Market manipulation': {'value': 'c5f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Membership or complaint fees': {'value': '3b9b0a01-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '5f21aa63-0116-ee11-9cbe-000d3a6a9642'},
 'Merging superannuation accounts': {'value': '63f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Merging superannuation funds': {'value': '65f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Merits - case decision': {'value': '889a0715-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '5f21aa63-0116-ee11-9cbe-000d3a6a9642'},
 'Merits - jurisdictional decision': {'value': '0ce75107-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '5f21aa63-0116-ee11-9cbe-000d3a6a9642'},
 'Miselading conduct/information: social media': {'value': 'cdf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Misleading conduct': {'value': 'c7f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Misleading conduct: high risk product': {'value': 'cbf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Misleading conduct: sustainable finance': {'value': 'c9f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Misleading product/service information': {'value': '3333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'f5e14f63-afc1-ed11-83fe-000d3a6ad49b'},
 'Misrepresentation: information about EDR': {'value': '71f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Mistaken internet payment': {'value': '67f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Mistaken Internet Payment': {'value': '1533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Mortgagee sale': {'value': '29f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '94e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Mortgagee sale 1': {'value': '7d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'My application for credit was declined': {'value': 'd189a235-f9e8-ed11-8848-000d3a6b1bd3',
  'data-parent': ''},
 'My complaint involves a scam': {'value': '70e6a978-f9e8-ed11-8848-000d3a6b1bd3',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'My complaint is with another driver’s insurer': {'value': '1f501d02-fff5-ed11-8849-000d3a6ad49b',
  'data-parent': ''},
 'No claim bonus': {'value': '2933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'a379125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Non rules': {'value': '8533d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'fe41fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Non ToR': {'value': '3f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b3b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Notice of change': {'value': 'fff71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Other': {'value': 'fa766b2e-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '5f21aa63-0116-ee11-9cbe-000d3a6a9642'},
 'Other 1': {'value': '9b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Other CDR issue': {'value': 'ddf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Other CDR issue 1': {'value': '9133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Other Complaint': {'value': '92365f86-0fe8-ed11-8848-000d3a6ad5b3',
  'data-parent': ''},
 'Other discrimination': {'value': '51995950-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '3a35d144-0116-ee11-9cbe-000d3a6a9642'},
 'Other privacy breaches': {'value': '0733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '32ff8356-afc1-ed11-83fe-000d3a6ad49b'},
 'Other reason / not sure': {'value': '41aee1c9-1609-ee11-8f6e-000d3a6ad49b',
  'data-parent': ''},
 'Other reason for disputing the fee / not sure': {'value': '9514719f-1b01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'Other reason for disputing the fee / not sure 1': {'value': '0c92d01c-1c01-ee11-8f6d-000d3a6ad35b',
  'data-parent': ''},
 'Other type of scam': {'value': '54b1e51a-42df-ed11-a7c7-000d3a6ad49b',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Policy interpretation': {'value': 'abf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Poor quality information /advice provided': {'value': '1c200cdc-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '6fd45e57-0116-ee11-9cbe-000d3a6a9642'},
 'Post determination communication': {'value': 'b67b2b6c-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'Post recommendation communication': {'value': 'bafa2b66-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'Premium disclosure': {'value': 'f7f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Premium increase': {'value': '99f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '86e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Pressure to accept a decision or settle the complaint': {'value': '01be7f63-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'e72a054b-0116-ee11-9cbe-000d3a6a9642'},
 'Privacy access request': {'value': '45f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Privacy/confidentiality breach': {'value': 'c5fb9c70-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'e72a054b-0116-ee11-9cbe-000d3a6a9642'},
 'Privacy/confidentiality breach 1': {'value': '43f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '96e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Providing information to afca': {'value': '73f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Quantum of loss': {'value': 'adf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Racial discrimination': {'value': 'cf08443d-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '3a35d144-0116-ee11-9cbe-000d3a6a9642'},
 'Re-allocation issues': {'value': '2ff4bcbb-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'a0535f51-0116-ee11-9cbe-000d3a6a9642'},
 'Recognition of authorised representative/trustee/POA/guardian': {'value': '7ff71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '84e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Recording customer address': {'value': '83f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '84e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Recording information/data': {'value': '47f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '98e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Recovery of EDR costs': {'value': '75f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '82e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Reduction in benefit': {'value': 'aff71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '88e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Release of securities': {'value': '2bf81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '94e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Repayment History Information': {'value': '9d33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '33b6f37b-afc1-ed11-83fe-000d3a6ad49b'},
 'Request to close account': {'value': '85f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '84e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Request to open account': {'value': '87f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '84e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Request to Suspend Enforcement Proceedings': {'value': '4b33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'b9b1f969-afc1-ed11-83fe-000d3a6ad49b'},
 'Responsible lending': {'value': '2df81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '94e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Responsible lending 1': {'value': '7f33d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Retaining information/data': {'value': '49f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '98e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'RG 271 Part A- afca Membership': {'value': '11f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '92e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'RG 271 Part B- Complaint and complaint definition': {'value': '13f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '92e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'RG 271 Part C- IDR response standards': {'value': '15f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '92e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'RG 271 Part C- IDR Timeframes': {'value': '17f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '92e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'RG 271 Part D- Systemic issues': {'value': '19f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '92e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'RG 271 Part E- IDR standards': {'value': '1bf81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '92e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Sale of add-on insurance': {'value': '4bf81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Sale of funeral insurance': {'value': '4df81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Sale to vulnerable consumer': {'value': '51f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'SC complaint handling': {'value': '87ada824-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'a7c5c437-0116-ee11-9cbe-000d3a6a9642'},
 'SC process took too long': {'value': 'ca2ff4a2-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': 'a0535f51-0116-ee11-9cbe-000d3a6a9642'},
 'Scam - MasterCard Prepaid': {'value': '1733d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Scam - phishing/ spoofing': {'value': '0fed3e7e-5cd8-ed11-a7c7-000d3a6ad5b3',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Scam - remote access': {'value': 'ab6930b4-5cd8-ed11-a7c7-000d3a6ad5b3',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Scam transactions': {'value': '6bf81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Security and destruction/de-identification': {'value': 'dff71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Security and Destruction/De-identification': {'value': '9333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '0f42fb75-afc1-ed11-83fe-000d3a6ad49b'},
 'Serious contravention of law': {'value': 'cff71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Service issue': {'value': 'b8dc2e5b-0fe8-ed11-8848-000d3a6ad5b3',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Service quality': {'value': 'ff32d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Settlement delay': {'value': '69f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Small business financial difficulty': {'value': '09f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '90e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Special needs not addressed': {'value': 'f0a04785-0316-ee11-9cbe-000d3a6a9642',
  'data-parent': '482bb369-0116-ee11-9cbe-000d3a6a9642'},
 'Statement delivery': {'value': 'f9f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Statement of advice': {'value': '6b68fb20-400f-ee11-8f6e-00224892f893',
  'data-parent': '80e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Successor fund transfer systems': {'value': '6df81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Suitability of product': {'value': '6d68fb20-400f-ee11-8f6e-00224892f893',
  'data-parent': '80e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Supervision of sales conduct/authorised representative': {'value': '4ff81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Technical communication issue': {'value': 'ae9b29ee-0216-ee11-9cbe-000d3a6a9642',
  'data-parent': '6fd45e57-0116-ee11-9cbe-000d3a6a9642'},
 'Technical Problems': {'value': '0133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '59056350-afc1-ed11-83fe-000d3a6ad49b'},
 'Terms and conditions\xa0delivery': {'value': 'fbf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Terms of hardship agreement/contract variation': {'value': '0bf81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '90e98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Transaction failure': {'value': '6ff81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Transfer of unclaimed monies': {'value': '71f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Unauthorised conduct': {'value': 'd1f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Unauthorised information disclosed': {'value': '0933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '32ff8356-afc1-ed11-83fe-000d3a6ad49b'},
 'Unauthorised transactions': {'value': '73f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Unauthorised transactions 1': {'value': '1933d755-94c1-ed11-b597-00224892f51a',
  'data-parent': '9579125d-afc1-ed11-83fe-000d3a6ad49b'},
 'Unclaimed money': {'value': '75f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Unclear funds': {'value': '77f81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '9ce98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Unconscionable conduct': {'value': '8133d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Unfair contract term': {'value': 'd3f71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ae98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Unfair contract terms': {'value': '8333d755-94c1-ed11-b597-00224892f51a',
  'data-parent': 'd4d6fb6f-afc1-ed11-83fe-000d3a6ad49b'},
 'Unit pricing disclosure': {'value': 'fdf71b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '8ee98e3d-3d0f-ee11-8f6e-002248927eb4'},
 'Unregulated contract financial difficulty': {'value': '0df81b3f-3f0f-ee11-8f6e-00224811ec4e',
  'data-parent': '90e98e3d-3d0f-ee11-8f6e-002248927eb4'}}


# %% [markdown]
# ### Obtain search results

# %%
#Define search boxes

def afca_search(keywordsearch_input, #= '', 
                ffsearch_input, #= '', 
                product_line_input, #= '', 
                product_category_input, #= '', 
                product_name_input, #= '', 
                issue_type_input, #= '', 
                issue_input, #= '', 
                date_from_input, #= '01/01/1900', 
                date_to_input #= today
                ):

    #Open browser
    browser.get('https://my.afca.org.au/searchpublisheddecisions/')
    browser.delete_all_cookies()
    browser.refresh()

    #Obtaina and input elements
    
    #'Search for published decisions'
    keywordsearch = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'keywordsearch')))

    #'Search for a financial firm'
    ffsearch = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'ffsearch')))
    
    #'Product line'
    product_line = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'plsearch')))
    dropdown_product_line = Select(product_line)

    #'Product category'
    product_category = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'pcsearch')))
    dropdown_product_category = Select(product_category)

    #'Product cate'
    product_name = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'pnsearch')))
    dropdown_product_name = Select(product_name)

    #'Issue type'
    issue_type = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'itsearch')))
    dropdown_issue_type = Select(issue_type)

    #'Issue'
    issue = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'issearch')))
    dropdown_issue = Select(issue)

    #'Date from'
    #date_from = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'date_from')))
    date_from = Wait(browser,  20).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='date_from']")))

    #data-date-format="DD/MM/YYYY"
    #eg date_input.send_keys("07/07/2023")
    
    #'Date to'
    #date_to = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'date_to')))
    date_to = Wait(browser,  20).until(EC.visibility_of_element_located((By.XPATH, "//input[@id='date_to']")))

    #Buttons
    submit_button = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'submitsearch')))
    clear_button = Wait(browser,  20).until(EC.visibility_of_element_located((By.ID, 'clearsearch')))
    
    #Enter input
    clear_button.click()

    if ((keywordsearch_input != None) and (keywordsearch_input != '')):
        keywordsearch.send_keys(keywordsearch_input)

    if ((ffsearch_input != None) and (ffsearch_input != '')):
        ffsearch.send_keys(ffsearch_input)

    if ((product_line_input != None) and (product_line_input != '')):
        product_line_value = product_line_options[product_line_input]["value"]
        dropdown_product_line.select_by_value(product_line_value)

    if ((product_category_input != None) and (product_category_input != '')):

        product_category_value = product_category_options[product_category_input]["value"]
        dropdown_product_category.select_by_value(product_category_value)
        #If parent value not automatically updated
        #for key in product_line_options:
            #if product_category_options[product_category_input]["data-parent"] == product_line_options[key]["value"]:
                #product_line_value = product_line_options[product_line_input]["value"]
                #product_line_value = product_line_options[product_line_input]["value"]
    
    if ((product_name_input != None) and (product_name_input != '')):

        product_name_value = product_name_options[product_name_input]["value"]
        dropdown_product_name.select_by_value(product_name_value)

    if ((issue_type_input != None) and (issue_type_input != '')):

        issue_type_value = issue_type_options[issue_type_input]["value"]
        dropdown_issue_type.select_by_value(issue_type_value)

    if ((issue_input != None) and (issue_input != '')):

        issue_value = issue_options[issue_input]["value"]
        dropdown_issue.select_by_value(issue_value)
        #If parent value not automatically updated
        #for key in issue_type_options:
            #if issue_options[issue_input]["data-parent"] == issue_type_options[key]["value"]:
                #issue_type_value = issue_type_options[issue_type_input]["value"]
                #issue_type_value = issue_type_options[issue_type_input]["value"]

    if date_from_input != '01/01/1900':
        date_from.send_keys(date_from_input)

    if date_to_input != today:
        date_to.send_keys(date_to_input)
    
    #Get search results
    submit_button.click()

    case_list = [] #For preview

    urls = [] #For actual scraping

    raw_cases = [] #Placeholder

    try:
        raw_cases = Wait(browser, 20).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='kb_record panel panel-default container']")))
            
        for raw_case in raw_cases:
            case_name = raw_case.text.split('\n')[0]
            case_number = raw_case.text.split('\n')[1].replace('Case number: ', '').replace('Case Number: ', '')
            firm = raw_case.text.split('\n')[2].replace('Financial Firm: ', '').replace('Financial firm: ', '')
            date = raw_case.text.split('\n')[3].replace('Date: ', '')

            inner_html = raw_case.get_attribute('innerHTML')
            soup_case = BeautifulSoup(inner_html, "lxml")            
            url = 'https://my.afca.org.au' + soup_case.find_all('a', href=True)[0]['href']
            
            case_meta = {#'Case name': case_name, #Bijective function between case name and number
                'Case number': case_number, 'Financial firm': firm, 'Date': date, 'Hyperlink to afca portal': url}
            case_list.append(case_meta)
            urls.append(url)
                    
    except Exception as e:
        print('Search terms returned no results.')
        print(e)

    #Alternative method of getting cases
    #try:
        #raw_cases= Wait(browser, 20).until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='kb_record panel panel-default container']")))
    
        #raw_links = Wait(browser, 20).until(EC.presence_of_all_elements_located((By.XPATH, "//*[contains(@href, 'searchpublisheddecisions/kb-article/')]")))
        
        #The above gets twice as many raw links as cases, in an ordered way.
        #for raw_case in raw_cases:
            #raw_case_index = raw_cases.index(raw_case)
            #raw_link_index = int(raw_case_index)*2 #There are twice as many raw links as cases, in an ordered way.
            #case_name = raw_case.text.split('\n')[0]
            #case_number = raw_case.text.split('\n')[1].replace('Case number: ', '').replace('Case Number: ', '')
            #firm = raw_case.text.split('\n')[2].replace('Financial Firm: ', '').replace('Financial firm: ', '')
            #date = raw_case.text.split('\n')[3].replace('Date: ', '')
            #url = raw_links[raw_link_index].get_attribute("href")
            #case_meta = {#'Case name': case_name, #Bijective function between case name and number
                #'Case number': case_number, 'Financial firm': firm, 'Date': date, 'Hyperlink to afca portal': url}
            #case_list.append(case_meta)
            #urls.append(url)
    #except Exception as e:
        #print('Search terms returned no results.')
        #print(e)

    return {'case_sum': len(case_list), 'case_list': case_list, 'urls': urls}



# %%
def afca_meta_judgment_dict(judgment_url):

    headers = {'User-Agent': 'whatever'}
    page = requests.get(judgment_url, headers=headers)
    soup = BeautifulSoup(page.content, "lxml")
    
    judgment_dict = {'Case name': '', 'Hyperlink to afca portal': link(judgment_url), 'Case number': '', 'Financial firm': '', 'Date': '', 'judgment': ''}

    #Attach 

    case_name = soup.find('li', attrs={'class': 'active'}).text
    
    if case_name[0]== ' ':
        case_name = case_name[1:]

    judgment_dict['Case name'] = case_name  
    
    judgment_text = soup.get_text(separator="\n", strip=True)

    judgment_dict['judgment'] = judgment_text  

    try:
        if 'Case number\n' in judgment_text:
            case_number = judgment_text.split('Case number\n')[1].split('\n')[0]
        elif 'Case numbers\n' in judgment_text:
            case_number = judgment_text.split('Case numbers\n')[1].split('\n')[0]
        elif 'Determination For Case ' in case_name:
            case_number = case_name.split('Determination For Case ')[1]
        else:
            case_number = ''
            
        judgment_dict['Case number'] = case_number
        
    except:
        print('Case number not found.')

    try:
        judgment_dict['Financial firm'] = judgment_text.split('Financial firm\n')[1].split('\n')[0]
    except:
        print('Case number not found.')

    try:
        judgment_dict['Date'] = judgment_text.split(f'{case_number}\n')[3].split('\n')[0]
    except:
        print('Date not found.')
    
    return judgment_dict


# %%
afca_meta_labels_droppable = ["Case number", "Financial firm", 'Date']

# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from gpt_functions import question_characters_bound, default_judgment_counter_bound, role_content#, intro_for_GPT


# %%
print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")
print(f"The default number of judgments to scrape per request is capped at {default_judgment_counter_bound}.\n")

# %%
#Jurisdiction specific instruction
system_instruction = role_content

intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-4o-mini"
    
#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

#Upperbound on number of judgments to scrape
if 'judgments_counter_bound' not in st.session_state:
    st.session_state['judgments_counter_bound'] = default_judgment_counter_bound


# %%
#Obtain parameters

def afca_run(df_master):
    
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your questions for GPT'] = df_master['Enter your questions for GPT'][0: question_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    search_results = afca_search(keywordsearch_input = df_master.loc[0, 'Search for published decisions'], 
                ffsearch_input = df_master.loc[0, 'Search for a financial firm'], 
                product_line_input = df_master.loc[0, 'Product line'], 
                product_category_input = df_master.loc[0, 'Product category'], 
                product_name_input = df_master.loc[0, 'Product name'], 
                issue_type_input = df_master.loc[0, 'Issue type'], 
                issue_input = df_master.loc[0, 'Issue'], 
                date_from_input = df_master.loc[0, 'Date from'], 
                date_to_input = df_master.loc[0, 'Date to'])

    #Create list of judgment links
    judgments_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    #judgments_links = []

    counter = 0

    #for link in judgments_links:
    for link in search_results['urls']:
        if counter < judgments_counter_bound:

            judgment_dict = afca_meta_judgment_dict(link)
    
            judgments_file.append(judgment_dict)

            counter += 1
            
            pause.seconds(np.random.randint(5, 15))
        else:
            break
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)

#    df_individual = pd.DataFrame(judgments_file)
    
    df_individual = pd.read_json(json_individual)
    
    #Rename column titles
    
#    try:
#        df_individual['Hyperlink (double click)'] = df_individual['Hyperlink'].apply(link)
#        df_individual.pop('Hyperlink')
#    except:
#        pass
                    
    #Instruct GPT
    
    #GPT model

    if df_master.loc[0, 'Use flagship version of GPT'] == True:
        gpt_model = "gpt-4o"
    else:        
        #gpt_model = "gpt-4o-mini"
        gpt_model = "gpt-4o-mini"
        
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json(questions_json, df_individual, GPT_activation, gpt_model, system_instruction)

    df_updated.pop('judgment')


    #Drop metadata if not wanted

    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in afca_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
                
    return df_updated

# %% [markdown]
# # Streamlit form, functions and parameters

# %%
#Import functions and variables
from common_functions import open_page, clear_cache_except_validation_df_master, tips


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default values

if 'gpt_enhancement_entry' not in st.session_state:
    st.session_state['gpt_enhancement_entry'] = False

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
    st.session_state.df_master.loc[0, 'Search for published decisions'] = None 
    st.session_state.df_master.loc[0, 'Search for a financial firm'] = None 
    st.session_state.df_master.loc[0, 'Product line'] = None 
    st.session_state.df_master.loc[0, 'Product category'] = None 
    st.session_state.df_master.loc[0, 'Product name'] = None 
    st.session_state.df_master.loc[0, 'Issue type'] = None 
    st.session_state.df_master.loc[0, 'Issue'] = None 
    st.session_state.df_master.loc[0, 'Date from'] = None 
    st.session_state.df_master.loc[0, 'Date to'] = None

    #Generally applicable
    st.session_state['df_master'] = st.session_state['df_master'].replace({np.nan: None})

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True

# %%
#Try to carry over previously entered personal details    
try:
    st.session_state['gpt_api_key_entry'] = st.session_state.df_master.loc[0, 'Your GPT API key']
except:
    st.session_state['gpt_api_key_entry'] = ''

try:
    st.session_state['name_entry'] = st.session_state.df_master.loc[0, 'Your name']
except:
    st.session_state['name_entry'] = ''

try:
    st.session_state['email_entry'] = st.session_state.df_master.loc[0, 'Your email address']
    
except:
    st.session_state['email_entry'] = ''

# %%
#If landing page is not home
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

# %% [markdown]
# ## Form before AI

# %%
if st.session_state.page_from != "pages/AFCA.py": #Need to add in order to avoid GPT page from showing form of previous page

    #Create form
    
    return_button = st.button('RETURN to first page')
    
    st.header(f"You have selected to study :blue[decisions of the Australian Financial Complaints Authority].")
    
    #    st.header("Judgment Search Criteria")
    
    st.markdown("""**:green[Please enter your search terms.]** This program will collect (ie scrape) the first 10 judgments returned by your search terms.
""")
    
    st.caption('During the pilot stage, the number of judgments to scrape is capped. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more judgments, courts, or tribunals.')
    
    st.subheader("Your search terms")
    
    st.markdown("""For search tips, please visit [the afca Portal](https://my.afca.org.au/searchpublisheddecisions/). This section mimics their search function.
""")
    
    keywordsearch_entry = st.text_input(label = 'Search for published decisions', value = st.session_state.df_master.loc[0, 'Search for published decisions'])
    
    ffsearch_entry = st.text_input(label = 'Search for a financial firm', value = st.session_state.df_master.loc[0, 'Search for a financial firm'])
    
    product_line_entry = st.selectbox(label = 'Product line', options = list(product_line_options.keys()), index = list_value_check(list(product_line_options.keys()), st.session_state.df_master.loc[0, 'Product line']))
    
    product_category_entry = st.selectbox(label = 'Product category', options = list(product_category_options.keys()), index = list_value_check(list(product_category_options.keys()), st.session_state.df_master.loc[0, 'Product category']))
    
    product_name_entry = st.selectbox(label = 'Product name', options = list(product_name_options.keys()), index = list_value_check(list(product_name_options.keys()), st.session_state.df_master.loc[0, 'Product name']))
    
    issue_type_entry = st.selectbox(label = 'Issue type', options = list(issue_type_options.keys()), index = list_value_check(list(issue_type_options.keys()), st.session_state.df_master.loc[0, 'Issue type']))
    
    issue_entry = st.selectbox(label = 'Issue type', options = list(issue_options.keys()), index = list_value_check(list(issue_options.keys()), st.session_state.df_master.loc[0, 'Issue']))
            
    date_from_entry = st.date_input('Date from (may not work)', value = au_date(st.session_state.df_master.loc[0, 'Date from']), format="DD/MM/YYYY", min_value = date(2000, 1, 1), max_value = datetime.now())
    
    date_to_entry = st.date_input('Date to (may not work)', value = au_date(st.session_state.df_master.loc[0, 'Date to']), format="DD/MM/YYYY", min_value = date(2000, 1, 1), max_value = datetime.now())
     
    st.markdown("""You can preview the judgments returned by your search terms after you have entered some search terms.
""")
    #You may have to unblock a popped up window, refresh this page, and re-enter your search terms.
    
    preview_button = st.button(label = 'PREVIEW', type = 'primary')


    # %%
    if preview_button:
    
        df_master = afca_create_df()
    
        afca_search_terms = str(keywordsearch_entry) + str(ffsearch_entry) + str(product_line_entry) + str(product_category_entry) + str(product_name_entry) + str(issue_type_entry) + str(issue_entry) + str(date_from_entry) + str(date_to_entry)
        
        if afca_search_terms.replace('None', '') == "":
    
            st.warning('You must enter some search terms.')
            #quit()
    
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
          
                link_heading_config['Hyperlink to afca portal'] = st.column_config.LinkColumn(display_text = 'Click')
        
                st.success(f'Your search terms returned {search_results["case_sum"]} result(s). Please see below for the top {min(search_results["case_sum"], 10)} result(s).')
                            
                st.dataframe(df_preview.head(10),  column_config=link_heading_config)
        
            else:
                st.warning('Your search terms returned 0 results. Please change your search terms and try again.')

    # %%
    st.subheader("Judgment metadata collection")
    
    st.markdown("""Would you like to obtain judgment metadata? Such data include the case number, the financial firm involved, and the decision date. 
    
Case name and hyperlinks to the afca portal are always included with your results.
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
    
        afca_search_terms = str(keywordsearch_entry) + str(ffsearch_entry) + str(product_line_entry) + str(product_category_entry) + str(product_name_entry) + str(issue_type_entry) + str(issue_entry) + str(date_from_entry) + str(date_to_entry)
        
        if afca_search_terms.replace('None', '') == "":
    
            st.warning('You must enter some search terms.')
                
        else:
                
            df_master = afca_create_df()

            st.session_state['df_master'] = df_master
        
            df_master.pop("Your GPT API key")
        
            df_master.pop("Processed")
        
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
    
        st.switch_page("Home.py")

    # %%
    #if reset_button:
        #clear_cache_except_validation_df_master()
        #st.rerun()

    # %%
    if next_button:
    
        afca_search_terms = str(keywordsearch_entry) + str(ffsearch_entry) + str(product_line_entry) + str(product_category_entry) + str(product_name_entry) + str(issue_type_entry) + str(issue_entry) + str(date_from_entry) + str(date_to_entry)
        
        if afca_search_terms.replace('None', '') == "":
    
            st.warning('You must enter some search terms.')
        
        else:
        
            df_master = afca_create_df()
            
            st.session_state['df_master'] = df_master
                        
            st.session_state["page_from"] = 'pages/AFCA.py'
            
            st.switch_page('pages/GPT.py')
