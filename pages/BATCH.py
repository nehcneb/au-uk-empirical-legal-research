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
#from dateutil.relativedelta import *
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
#import streamlit_ext as ste
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
#Title of webpage
st.set_page_config(
   page_title="LawtoData: An Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Import functions and variables
from functions.common_functions import convert_df_to_json, convert_df_to_csv, convert_df_to_excel, today_in_nums, spinner_text, download_buttons, get_aws_s3, aws_df_get, aws_df_put


# %%
#Testing aws_df_get
#aws_df_get('all_df_masters.csv')

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
        
        confirm_deletion_entry = st.text_input(label = "Type 'yes' in lower case to delete your data.")
        
        if st.button("CONFIRM"):

            with st.spinner('Deleting your data...'):

                if confirm_deletion_entry.lower() != 'yes':
    
                    st.warning("Please type 'yes' to confirm, or close this window if you do not want to delete the requested data.")
    
                else:
                    
                    #Get relevant df_individual
                    st.session_state.df_individual = aws_df_get(s3_resource, f"{batch_id_entry}.csv")
                
                    if (st.session_state.df_master.loc[0, 'status'] != 'deleted') and (len(st.session_state.df_individual) > 0):
            
                            
                        #Delete df_individual on AWS
                        s3_resource.Object('lawtodata', f'{batch_id_entry}.csv').delete()

                        #csv_buffer = StringIO()
                        #st.session_state.df_individual = pd.DataFrame([])
                        #st.session_state.df_individual.to_csv(csv_buffer)
                        #s3_resource.Object('lawtodata', f'{batch_id_entry}.csv').put(Body=csv_buffer.getvalue())
                        
                        
                        print(f"Deleted {batch_id_entry}.csv online." )
            
                        #Get latest all_df_master
                        st.session_state['all_df_masters'] = aws_df_get(s3_resource, 'all_df_masters.csv')

                        #Identify index in all_df_masters of batch to be deleted
                        batch_index = st.session_state.all_df_masters.index[st.session_state.all_df_masters['batch_id'] == batch_id_entry].tolist()[0]

                        #Modify all_df_master
                        for col in st.session_state.all_df_masters.columns:
                            if col not in ['submission_time', 'batch_id', 'input_file_id', 'output_file_id', 'sent_to_user']:
                                st.session_state.all_df_masters.loc[batch_index, col] = ''
                        
                        st.session_state.df_master.loc[batch_index, 'status'] = 'deleted'
                        
                        #Update df_master on aws
                        aws_df_put(s3_resource, all_df_masters, f'all_df_masters.csv')

                        #csv_buffer = StringIO()
                        #st.session_state.all_df_masters.to_csv(csv_buffer)
                        #s3_resource.Object('lawtodata', 'all_df_masters.csv').put(Body=csv_buffer.getvalue())
                                        
                        print(f"Updated all_df_masters.csv online." )
    
                        #Update status of last retrived/deleted output
                        st.session_state.df_master.loc[0, 'status'] = 'deleted'
    
                        #pause.seconds(3)
                        st.rerun()
    

# %%
#Initiate aws_s3, and get all_df_masters

s3_resource = get_aws_s3()

with st.spinner(spinner_text):
    
    #if 's3_resource' not in st.session_state:
    
        #s3_resource = get_aws_s3()
    
    if 'all_df_masters' not in st.session_state:

        st.session_state['all_df_masters'] = aws_df_get(s3_resource, 'all_df_masters.csv')


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
    
    st.info('Your data has been deleted.')


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
        with st.spinner('Retrieving your data...'):

            #pause.seconds(3)
            
            try:
                #Get relevant df_individual
                st.session_state.df_individual = aws_df_get(s3_resource, f'{batch_id_entry}.csv')
        
                #Update df_master
                batch_index = st.session_state.all_df_masters.index[st.session_state.all_df_masters['batch_id'] == batch_id_entry].tolist()[0]
                for col in st.session_state.all_df_masters.columns:
                    st.session_state['df_master'].loc[0, col] = st.session_state.all_df_masters.loc[batch_index, col]
    
                if len(st.session_state.df_individual) > 0:

                    #State the status of this df_individual
                    st.session_state.df_master.loc[0, 'status'] = st.session_state.all_df_masters.loc[batch_index, 'status']

                    #st.write(f"st.session_state.df_master.loc[0, 'status'] == {st.session_state.df_master.loc[0, 'status']}")

                    #pause.seconds(3)
                    
                    st.rerun()
                
                else:
                    st.error('Your nominated email address or access code is not correct, or the requested data cannot be found.')
                    
            except Exception as e:
                
                st.error(f'The requested data cannot be retrieved due to the following error: {e}')


# %%
if (st.session_state.df_master.loc[0, 'status'] != 'deleted') and (len(st.session_state.df_individual) > 0):

    st.session_state["page_from"] = 'pages/BATCH.py'           

    #Download data
    download_buttons(df_master = st.session_state.df_master, df_individual = st.session_state.df_individual)


