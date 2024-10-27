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

# %% editable=true slideshow={"slide_type": ""}
#streamlit run Dropbox/Python/GitHub/au-uk-empirical-legal-research-unlimited/BATCH.py

# %% [markdown] editable=true slideshow={"slide_type": ""}
# # Preliminaries

# %% editable=true slideshow={"slide_type": ""}
#Preliminary modules
#import base64 
import json
import pandas as pd
#import shutil
import numpy as np
import re
import datetime
from datetime import date
from dateutil import parser
from dateutil.relativedelta import *
from datetime import datetime, timedelta
#import sys
#import pause
#import requests
#from bs4 import BeautifulSoup, SoupStrainer
#import httplib2
#from urllib.request import urlretrieve
import os
#import pypdf
import io
from io import BytesIO
from io import StringIO
#import copy

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
#from streamlit.components.v1 import html
import streamlit_ext as ste
from streamlit_extras.stylable_container import stylable_container

#OpenAI
#import openai
#import tiktoken

#aws
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb


# %%
#Import functions and variables
from functions.common_functions import convert_df_to_json, convert_df_to_csv, convert_df_to_excel, today_in_nums



# %% editable=true slideshow={"slide_type": ""}
#Title of webpage
st.set_page_config(
   page_title="LawtoData: An Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Initiate aws s3
s3_resource = boto3.resource('s3',region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"], aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"])

#Get a list of all files on s3
bucket = s3_resource.Bucket('lawtodata')

aws_objects = []

for obj in bucket.objects.all():
    key = obj.key
    body = obj.get()['Body'].read()
    key_body = {'key': key, 'body': body}
    aws_objects.append(key_body)

# %%
#Get all_df_masters

for key_body in aws_objects:
    if key_body['key'] == 'all_df_masters.csv':
        all_df_masters = pd.read_csv(BytesIO(key_body['body']), index_col=0)
        print(f"Succesfully loaded {key_body['key']}.")
        break


# %%
#Define function to check if email matches with batch_id

def check_email_batch_id(df, email, batch_id):
    
    value = False
    
    try:
        batch_index = df.index[df['batch_id'] == batch_id].tolist()[0]
        correct_email = df.loc[batch_index, 'Your email address']
        if email.lower() == correct_email.lower():
            value = True
    except:
        print(f'Email does not match with batch_id.')

    return value



# %%
#Initialise 

if 'df_master' not in st.session_state:

    #Generally applicable
    st.session_state['df_master'] = pd.DataFrame([])
    st.session_state['df_master'].loc[0, 'Your name'] = ''
    st.session_state['df_master'].loc[0, 'Your email address'] = ''
    st.session_state['df_master'].loc[0, 'Your GPT API key'] = ''
    st.session_state['df_master'].loc[0, 'Use own account'] = False
    st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    st.session_state['df_master'].loc[0, 'batch_id'] = ''

if 'df_individual' not in st.session_state:

    st.session_state['df_individual'] = pd.DataFrame([])

if 'match_status' not in st.session_state:

    st.session_state['match_status'] = False


# %% [markdown]
# # Streamlit page

# %%
st.title(":blue[LawtoData]")

st.subheader("An Empirical Legal Research Kickstarter")

st.write('Thank you for using *LawtoData*! Please enter your nominated email address and access code to retrieve your requested data.')

st.write('Your access code can be found in the email notifying you of the availability of your requested data.')

email_entry = st.text_input(label = 'Email address', value = st.session_state['df_master'].loc[0, 'Your email address'])

#if email_entry:
st.session_state['df_master'].loc[0, 'Your email address'] = email_entry

batch_code_entry = st.text_input(label = 'Access code', value = st.session_state['df_master'].loc[0, 'batch_id'])

#if batch_code_entry:
st.session_state['df_master'].loc[0, 'batch_id'] = batch_code_entry

with stylable_container(
    "green",
    css_styles="""
    button {
        background-color: #00FF00;
        color: black;
    }""",
):
    retrive_button = st.button(label = 'RETRIVE data')


# %% [markdown]
# # Retrieve

# %%
if retrive_button:
    if not (batch_code_entry and email_entry):
        st.warning('Please enter your nominated email address and access code.')
        #quit()
        st.stop()
    else:        
        st.session_state['match_status'] = check_email_batch_id(all_df_masters, email_entry, batch_code_entry)

    if st.session_state['match_status'] == False:
        
        st.error('Your nominated email address or access code is not correct.')
        st.stop()
        
    else:
        #Get relevant df_individual
        for key_body in aws_objects:
            if key_body['key'] == f'{batch_code_entry}.csv':
                df_individual = pd.read_csv(BytesIO(key_body['body']), index_col=0)
                st.session_state.df_individual = df_individual
                print(f"Succesfully loaded {key_body['key']}.")
                break
    
        if len(st.session_state.df_individual) > 0:
        
            st.session_state["page_from"] = 'pages/BATCH.py'           
        
            #Write results
        
            st.success("Your data is now available for download. Thank you for using *LawtoData*!")
        
            batch_index = all_df_masters.index[all_df_masters['batch_id'] == batch_code_entry].tolist()[0]
            
            #Button for downloading results
            output_name = str(all_df_masters.loc[batch_index, 'Your name']) + '_' + str(today_in_nums) + '_results'
                
            excel_xlsx = convert_df_to_excel(df_individual)
            
            ste.download_button(label='Download your data as an Excel spreadsheet (XLSX)',
                                data=excel_xlsx,
                                file_name= output_name + '.xlsx', 
                                mime='application/vnd.ms-excel',
                               )

            csv_output = convert_df_to_csv(df_individual)
            
            ste.download_button(
                label="Download your data as a CSV (for use in Excel etc)", 
                data = csv_output,
                file_name= output_name + '.csv', 
                mime= "text/csv", 
            )
            
            json_output = convert_df_to_json(df_individual)
            
            ste.download_button(
                label="Download your data as a JSON", 
                data = json_output,
                file_name= output_name + '.json', 
                mime= "application/json", 
            )
        
            st.page_link('pages/AI.py', label="Analyse your data with an AI", icon = '🤔')        

# %%

