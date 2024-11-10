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
import pause
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
from functions.common_functions import convert_df_to_json, convert_df_to_csv, convert_df_to_excel, today_in_nums, spinner_text


# %% editable=true slideshow={"slide_type": ""}
#Title of webpage
st.set_page_config(
   page_title="LawtoData: An Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)


# %%
#Get all objects from aws s3

#@st.cache_resource(show_spinner = False)
def get_aws_s3():
    
    #Initiate aws s3
    s3_resource = boto3.resource('s3',region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"], aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"])

    return s3_resource

#Get all objects from aws s3

#@st.cache_data(show_spinner = False)
def get_aws_objects():
    
    #Get a list of all files on s3
    bucket = st.session_state.s3_resource.Bucket('lawtodata')
    
    aws_objects = []
    
    for obj in bucket.objects.all():
        key = obj.key
        body = obj.get()['Body'].read()
        key_body = {'key': key, 'body': body}
        aws_objects.append(key_body)

    return aws_objects
    


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
    st.session_state['df_master'].loc[0, 'status'] = ''
    st.session_state['df_master'].loc[0, 'batch_id'] = ''

if 'df_individual' not in st.session_state:

    st.session_state['df_individual'] = pd.DataFrame([])

if 'match_status' not in st.session_state:

    st.session_state['match_status'] = False


# %%
#Define function to check if email matches with batch_id

#@st.cache_data(show_spinner = False)
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
#For deleting data and record from aws
@st.dialog("Please confirm")
def delete_all():
    if not (batch_id_entry and email_entry):
        st.warning('Please enter your nominated email address and access code.')
        #quit()
        st.stop()
    else:        
        st.session_state['match_status'] = check_email_batch_id(st.session_state.all_df_masters, email_entry, batch_id_entry)

    if st.session_state['match_status'] == False:
        
        st.error('Your nominated email address or access code is not correct, or the requested data cannot be found.')
        st.stop()
        
    else:

        st.write(f"Are you sure you want to delete your data? If you do so, **there is no going back**. Your search terms, questions for GPT, and all other entries to obtain the data will also be deleted.")
        
        confirm_deletion_entry = st.text_input(label = "Type 'yes'")
        
        if st.button("CONFIRM"):

            with st.spinner('Deleting your data...'):

                if confirm_deletion_entry.lower() != 'yes':
    
                    st.warning("Please type 'yes' to confirm, or close this window if you do not want to delete the requested data.")
    
                else:
                    
                    #Get relevant df_individual
                    for key_body in st.session_state.aws_objects:
                        if key_body['key'] == f'{batch_id_entry}.csv':
                            df_individual = pd.read_csv(BytesIO(key_body['body']), index_col=0)
                            st.session_state.df_individual = df_individual.copy(deep = True)
                            print(f"Succesfully loaded {key_body['key']}.")
                            break
                
                    if (st.session_state.df_master.loc[0, 'status'] != 'deleted') and (len(st.session_state.df_individual) > 0):
            
                        st.session_state.df_individual = pd.DataFrame([])
                            
                        #Update df_individual on AWS
                        csv_buffer = StringIO()
                        st.session_state.df_individual.to_csv(csv_buffer)
                        #st.session_state.s3_resource.Object('lawtodata', f'{batch_id_entry}.csv').put(Body=csv_buffer.getvalue())
                        st.session_state.s3_resource.Object('lawtodata', f'{batch_id_entry}.csv').delete()
                        
                        print(f"Updated {batch_id_entry}.csv online." )
            
                        #Update all_df_master and df_master
                        batch_index = st.session_state.all_df_masters.index[st.session_state.all_df_masters['batch_id'] == batch_id_entry].tolist()[0]
            
                        for col in st.session_state.all_df_masters.columns:
                            if col not in ['submission_time', 'batch_id', 'input_file_id', 'output_file_id', 'sent_to_user']:
                                st.session_state.all_df_masters.loc[batch_index, col] = 'deleted'
            
                        #Update df_master on aws
                        csv_buffer = StringIO()
                        st.session_state.all_df_masters.to_csv(csv_buffer)
                        st.session_state.s3_resource.Object('lawtodata', 'all_df_masters.csv').put(Body=csv_buffer.getvalue())
                                        
                        print(f"Updated all_df_masters.csv online." )
    
                        #Update status of last retrived/deleted output
                        st.session_state.df_master.loc[0, 'status'] = 'deleted'
    
                        #pause.seconds(3)
                        st.rerun()                    
    


# %%
#Initiate aws_s3, and get all_df_masters

with st.spinner(spinner_text):
    
    if 's3_resource' not in st.session_state:
    
        st.session_state.s3_resource = get_aws_s3()
    
    if 'aws_objects' not in st.session_state:
        
        st.session_state.aws_objects = get_aws_objects()
        
    if 'all_df_masters' not in st.session_state:
    
        for key_body in st.session_state.aws_objects:
            if key_body['key'] == 'all_df_masters.csv':
                st.session_state['all_df_masters'] = pd.read_csv(BytesIO(key_body['body']), index_col=0)
                print(f"Succesfully loaded {key_body['key']}.")
                break


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

batch_id_entry = st.text_input(label = 'Access code', value = st.session_state['df_master'].loc[0, 'batch_id'])

#if batch_id_entry:
st.session_state['df_master'].loc[0, 'batch_id'] = batch_id_entry

#Retrive data button
with stylable_container(
    "green",
    css_styles="""
    button {
        background-color: #00FF00;
        color: black;
    }""",
):
    retrive_button = st.button(label = 'RETRIVE data')

#dete data button
if st.button(label = 'DELETE data', type = 'primary', disabled = bool(st.session_state.df_master.loc[0, 'status'] == 'deleted')):
    
    delete_all()

if st.session_state.df_master.loc[0, 'status'] == 'deleted':
    
    st.success('Your data has been deleted.')


# %% [markdown]
# # Retrieve

# %%
if retrive_button:
    if not (batch_id_entry and email_entry):
        st.warning('Please enter your nominated email address and access code.')
        #quit()
        st.stop()
    else:        
        st.session_state['match_status'] = check_email_batch_id(st.session_state.all_df_masters, email_entry, batch_id_entry)

    if st.session_state['match_status'] == False:
        
        st.error('Your nominated email address or access code is not correct, or the requested data cannot be found.')
        st.stop()
        
    else:
        try:
            #Get relevant df_individual
            for key_body in st.session_state.aws_objects:
                if key_body['key'] == f'{batch_id_entry}.csv':
                    df_individual = pd.read_csv(BytesIO(key_body['body']), index_col=0)
                    st.session_state.df_individual = df_individual.copy(deep = True)
                    print(f"Succesfully loaded {key_body['key']}.")

                    break
    
            #Update df_master
            batch_index = st.session_state.all_df_masters.index[st.session_state.all_df_masters['batch_id'] == batch_id_entry].tolist()[0]
            for col in st.session_state.all_df_masters.columns:
                st.session_state['df_master'].loc[0, col] = st.session_state.all_df_masters.loc[batch_index, col]

            if len(st.session_state.df_individual) > 0:
                st.rerun()
            
            else:
                st.error('Your nominated email address or access code is not correct, or the requested data cannot be found.')
                
        except Exception as e:
            
            st.error(f'The requested data cannot be retrieved due to the following error: {e}')


# %%
if (st.session_state.df_master.loc[0, 'status'] != 'deleted') and (len(st.session_state.df_individual) > 0):

    st.session_state["page_from"] = 'pages/BATCH.py'           

    #Write results
    st.success("Your data is now available for download. Thank you for using *LawtoData*!")

    #Button for downloading results
    output_name = str(st.session_state.df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_results'
        
    excel_xlsx = convert_df_to_excel(st.session_state.df_individual)
    
    ste.download_button(label='Download your data as an Excel spreadsheet (XLSX)',
                        data=excel_xlsx,
                        file_name= output_name + '.xlsx', 
                        mime='application/vnd.ms-excel',
                       )

    csv_output = convert_df_to_csv(st.session_state.df_individual)
    
    ste.download_button(
        label="Download your data as a CSV (for use in Excel etc)", 
        data = csv_output,
        file_name= output_name + '.csv', 
        mime= "text/csv", 
    )
    
    json_output = convert_df_to_json(st.session_state.df_individual)
    
    ste.download_button(
        label="Download your data as a JSON", 
        data = json_output,
        file_name= output_name + '.json', 
        mime= "application/json", 
    )

    st.page_link('pages/AI.py', label="Analyse your data with an AI", icon = '🤔')


