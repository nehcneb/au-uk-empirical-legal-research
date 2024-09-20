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
#import base64 
import json
import pandas as pd
#import shutil
import numpy as np
#import re
#import datetime
#from datetime import date
#from datetime import datetime
import sys
import pause
import os
import io
from io import BytesIO
from io import StringIO
#from dateutil import parser
#from dateutil.relativedelta import *
#from datetime import timedelta
#from PIL import Image
#import math
#from math import ceil
#import matplotlib.pyplot as plt
#import ast
#import copy

#OpenAI
import openai
#import tiktoken

#aws
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
#from streamlit.components.v1 import html
#import streamlit_ext as ste


# %%
#Import functions
from functions.gpt_functions import gpt_batch_input_submit, split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json, gpt_run

#For checking questions and answers
from functions.common_functions import check_questions_answers

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction, GPT_answers_check

if check_questions_answers() > 0:
    print(f'By default, questions and answers are checked for potential privacy violation.')
else:
    print(f'By default, questions and answers are NOT checked for potential privacy violation.')


# %%
#Title of webpage
st.set_page_config(
   page_title="LawtoData: An Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Initialise
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'pages/BATCH_GET.py'

# %%
st.title(":blue[LawtoData]")

st.subheader("An Empirical Legal Research Kickstarter")

st.markdown("""*LawtoData* is an [open-source](https://github.com/nehcneb/au-uk-empirical-legal-research) web app designed to help kickstart empirical projects involving judgments. It automates the most costly and time-consuming aspects of empirical research.""") 


# %%
#Generate current directory, just to check whether running on Github Actions or locally
current_dir = ''
try:
    current_dir = os.getcwd()
    print(current_dir)
except Exception as e:
    print(f"current_dir not generated.")
    print(e)

# %%
#Initiate aws s3 and ses

#If using Github Actions
if 'Users/Ben' not in current_dir:
    AWS_DEFAULT_REGION = os.environ['AWS_DEFAULT_REGION']
    AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
    AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
    
    SENDER = os.environ['EMAIL_SENDER']
    RECIPIENT = os.environ['EMAIL_RECEIVER_WORK']

else:#If using on streamlit

    AWS_DEFAULT_REGION=st.secrets["aws"]["AWS_DEFAULT_REGION"]
    AWS_ACCESS_KEY_ID=st.secrets["aws"]["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"]
    
    SENDER = st.secrets["email_notifications"]["email_sender"]
    RECIPIENT = st.secrets["email_notifications"]["email_receiver_work"]

s3_resource = boto3.resource('s3',region_name=AWS_DEFAULT_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
ses = boto3.client('ses',region_name=AWS_DEFAULT_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
#ses is based on the following upon substitutiong 'ses' for 's3', https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#guide-credentials


# %% [markdown]
# # Get all_df_masters and all df_individuals

# %%
st.subheader("Load records")

# %%
#Get a list of all files on s3
bucket = s3_resource.Bucket('lawtodata')

aws_objects = []

for obj in bucket.objects.all():
    key = obj.key
    body = obj.get()['Body'].read()
    key_body = {'key': key, 'body': body}
    aws_objects.append(key_body)

#Get all_df_masters

for key_body in aws_objects:
    if key_body['key'] == 'all_df_masters.csv':
        all_df_masters_current = pd.read_csv(BytesIO(key_body['body']), index_col=0)
        st.success(f"Succesfully loaded {key_body['key']}.")
        break

#Work on new copy of all_df_masters

all_df_masters = all_df_masters_current.copy()
        
#Alternative download file example
#NOT IN USE
#s3 = boto3.client('s3',region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"], aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"])
#s3.download_file('BUCKET_NAME', 'OBJECT_NAME', 'FILE_NAME')
#see https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-example-download-file.html
#'OBJECT_NAME' = 'FILE_NAME'
#eg s3.download_file('lawtodata', 'myfile.csv', 'myfile.csv')

# %%
#Obtain google spreadsheet for all df_masters      
#conn_all_df_masters = st.connection("gsheets_all_df_masters", type=GSheetsConnection, ttl=0)
#all_df_masters = conn_all_df_masters.read()
#all_df_masters = all_df_masters.fillna('')
#all_df_masters = all_df_masters[all_df_masters["submission_time"]!='']

# %%
#Tidy up all_df_masters

boolean_columns = ["Metadata inclusion", 'Use GPT', 'Use own account', 'Use flagship version of GPT']

for column in boolean_columns:
    if column in all_df_masters.columns:
        all_df_masters[column] = all_df_masters[column].replace({'True': 1, 'False':0, 'TRUE': 1, 'FALSE': 0})

#all_df_masters.reset_index(drop=True)

# %% [markdown]
# # Submit updated all_df_masters to GPT

# %%
st.subheader("Scrape judgments and submit batches to GPT")

# %%
#requests counter

batch_request_total = 0

for index in all_df_masters.index:

    current_status = str(all_df_masters.loc[index, 'status'])

    if current_status == 'to_process':
        batch_request_total += 1

if batch_request_total == 0:
    st.warning('No requests need to be submitted.')


# %%
#Generate batch input, submit to GPT and keep record online

#all_df_masters = all_df_masters[all_df_masters["status"]=='to_process']

batch_request_counter = 0

gpt_batch_input_list = []

for index in all_df_masters.index:

    current_status = str(all_df_masters.loc[index, 'status'])

    if current_status == 'to_process':
    
        api_key = all_df_masters.loc[index, 'Your GPT API key']
    
        openai.api_key = api_key
        
        df_dict = all_df_masters.loc[index].to_dict()
    
        df_master = pd.DataFrame.from_dict([df_dict], orient='columns')
    
        jurisdiction_page = df_master.loc[0, 'jurisdiction_page']
    
        gpt_batch_input = gpt_batch_input_submit(jurisdiction_page, df_master)

        gpt_batch_input_list.append(gpt_batch_input)
        
        #Get batch record
        batch_record = gpt_batch_input['batch_record']
        
        batch_dict = batch_record.to_dict()
        batch_id = batch_dict['id']
        input_file_id = batch_dict['input_file_id']
        status = batch_dict['status']

        #Update df_masters
        all_df_masters.loc[index, 'batch_id'] = batch_id
        all_df_masters.loc[index, 'input_file_id'] = input_file_id
        all_df_masters.loc[index, 'status'] = status

        #Update counter
        batch_request_counter += 1

        st.success(f'{batch_id} submitted to GPT. Done {batch_request_counter}/{batch_request_total}.')

    #Keep batching record on AWS
    #Upload all_df_masters to aws
    #csv_buffer = StringIO()
    #all_df_masters.to_csv(csv_buffer)
    #s3_resource.Object('lawtodata', 'all_df_masters.csv').put(Body=csv_buffer.getvalue())

    #Keep batch record on google sheet
    #conn_all_df_masters.update(worksheet="Sheet1", data=all_df_masters)


# %% [markdown]
# # Upload each submitted df_individual

# %%
st.subheader("Save scaped judgment data")

# %%
if len(gpt_batch_input_list) == 0:
    
    st.warning('No judgment data have been scraped.')


# %%
#Obtain all_df_individuals from google sheets
#conn_all_df_individuals = st.connection("gsheets_record_all_df_individuals", type=GSheetsConnection, ttl=0)

# %%
#Obtain all_df_individuals from aws
#Based on https://stackoverflow.com/questions/38154040/save-dataframe-to-csv-directly-to-s3-python

save_counter = 0

for gpt_batch_input in gpt_batch_input_list:

    #Get batch record
    batch_record = gpt_batch_input['batch_record']
    
    batch_dict = batch_record.to_dict()
    batch_id = batch_dict['id']
    #Sheet will be named by batch id
    
    df_individual = gpt_batch_input['df_individual']

    #Upload df_individual onto AWS
    csv_buffer = StringIO()
    df_individual.to_csv(csv_buffer)
    s3_resource.Object('lawtodata', f'{batch_id}.csv').put(Body=csv_buffer.getvalue())

    save_counter += 1

    #Keep all_df_individuals on google sheets
    #conn_all_df_individuals.create(worksheet=batch_id, data=df_individual)
    
    st.success(f"{batch_id} saved online. Done {save_counter}/{len(gpt_batch_input_list)}.")

#Alternative Uploading file example
#NOT IN USE
#s3 = boto3.client('s3')
#with open("FILE_NAME", "rb") as f:
    #s3.upload_fileobj(f, "BUCKET_NAME", "OBJECT_NAME")


# %% [markdown]
# # Retrive output from GPT

# %%
st.subheader("Retrive GPT output")

# %%
#Get max number of batches to retrieve

max_retrieve_counter = 0

for index in all_df_masters.index:

    current_status = all_df_masters.loc[index, "status"]

    if current_status == 'validating':

        max_retrieve_counter += 1

if max_retrieve_counter == 0:
    st.warning('No batches are pending retrival.')


# %%
df_batch_id_response_list = []

retrieve_counter = 0

for index in all_df_masters.index:

    current_status = all_df_masters.loc[index, "status"]

    if current_status == 'validating':
    
        api_key = all_df_masters.loc[index, 'Your GPT API key']
        
        openai.api_key = api_key
    
        batch_id = all_df_masters.loc[index, 'batch_id']
    
        gpt_model = "gpt-4o-mini"
        if all_df_masters.loc[index, 'Use flagship version of GPT'] == True:
            gpt_model = "gpt-4o-2024-08-06"
        else:        
            gpt_model = "gpt-4o-mini"
            
        #Get batch record
        batch_record = openai.batches.retrieve(batch_id)
    
        output_file_id = ''
    
        try:
    
            output_file_id = batch_record.output_file_id
    
        except:
    
            st.warning(f"{batch_id}: output_file_id not yet available.")
            
        status = batch_record.status

        #Print any status change
        st.info(f"{batch_id}: status == {status}.")
        print(f"{batch_id}: status == {status}.")
        
        if status == 'completed':
            
            batch_response = openai.files.content(output_file_id)
    
            df_batch_response = pd.read_json(batch_response.text, lines=True)
    
            batch_id_response = {'batch_id': batch_id, 'df_batch_response': df_batch_response, 'gpt_model': gpt_model}
    
            #Apppend gpt batch id and responses to list for adding to df_individual later
            
            df_batch_id_response_list.append(batch_id_response)

            #Update status and remove api key on all_df_masters
            all_df_masters.loc[index, 'status'] = status
            all_df_masters.loc[index, 'Your GPT API key'] = ''
    
            #Update all_df_masters on AWS
            #csv_buffer = StringIO()
            #all_df_masters.to_csv(csv_buffer)
            #s3_resource.Object('lawtodata', 'all_df_masters.csv').put(Body=csv_buffer.getvalue())

            #Update counter 
            retrieve_counter += 1
    
            #Update google sheet for all_df_masters
            #conn_all_df_masters.update(worksheet="Sheet1", data=all_df_masters)

            st.success(f"{batch_id}: status == {status}. Done {retrieve_counter}/{max_retrieve_counter}")


# %% [markdown]
# # Append retrieved output to df_individuals

# %%
st.subheader("Append GPT output to judgment data")

# %%
if len(df_batch_id_response_list) == 0:
    
    st.warning('No GPT output needs to be appended.')


# %%
#Get a list of all files on s3
bucket = s3_resource.Bucket('lawtodata')

aws_objects = []

for obj in bucket.objects.all():
    key = obj.key
    body = obj.get()['Body'].read()
    key_body = {'key': key, 'body': body}
    aws_objects.append(key_body)


# %%
# Attach add gpt response to df_individual

append_counter = 0

for df_batch_response in df_batch_id_response_list:

    batch_id = df_batch_response['batch_id']

    #Get df_individual from aws
    for key_body in aws_objects:
        if key_body['key'] == f'{batch_id}.csv':
            df_individual = pd.read_csv(BytesIO(key_body['body']), index_col=0)
            st.success(f"Succesfully loaded {key_body['key']} as df_individual.")
            break
    
    #Get df_individual from google sheets
    #conn_all_df_individuals = st.connection("gsheets_record_all_df_individuals", type=GSheetsConnection, ttl=0)
    #df_individual = conn_all_df_individuals.read(worksheet = batch_id)

    #Append gpt output to individual
    df_batch_response = df_batch_response['df_batch_response']

    for gpt_index in df_batch_response.index:

        #Get custom id of GPT case-specific response
        
        custom_id = df_batch_response.loc[gpt_index, 'custom_id']

        #Link GPT case-specific response to row in df_individual
        
        case_index_list = df_individual.index[df_individual['custom_id']==custom_id].tolist()

        if len(case_index_list) > 0:
            
            case_index = case_index_list[0]

            #Get gpt specific answers
            
            answers_dict = json.loads(df_batch_response.loc[gpt_index, 'response']['body']['choices'][0]['message']['content'])

            input_tokens = df_batch_response.loc[gpt_index, 'response']['body']['usage']['prompt_tokens']

            output_tokens = df_batch_response.loc[gpt_index, 'response']['body']['usage']['completion_tokens']

            #Check GPT answers
            if check_questions_answers() > 0:
                
                try:

                    #Get checked answers and tokens 
                    redacted_output = GPT_answers_check(answers_dict, gpt_model, answers_check_system_instruction)
            
                    redacted_answers_dict = redacted_output[0]
            
                    redacted_answers_output_tokens = redacted_output[1]
            
                    redacted_answers_prompt_tokens = redacted_output[2]

                    #Update to reflect checked answers

                    answers_dict = redacted_answers_dict
                    
                    input_tokens += redacted_answers_prompt_tokens

                    output_tokens += redacted_answers_output_tokens
                        
                except Exception as e:
        
                    print('Answers check failed.')
        
                    print(e)

            #Attach GPT answers to df_individual
            for gpt_question in answers_dict.keys():

                heading = 'GPT question: ' + gpt_question
                
                answer = answers_dict[gpt_question]

                df_individual.loc[case_index, heading] = answer

                df_individual.loc[case_index, 'GPT cost estimate (USD excl GST)'] = input_tokens*gpt_input_cost(gpt_model)/2 + output_tokens*gpt_output_cost(gpt_model)/2

        #Remove judgment column
        
        if 'judgment' in df_individual.columns:
            df_individual.pop('judgment')

        #Update df_individual on AWS
        csv_buffer = StringIO()
        df_individual.to_csv(csv_buffer)
        s3_resource.Object('lawtodata', f'{batch_id}.csv').put(Body=csv_buffer.getvalue())
        
        #Update df_individual on google sheet
        #conn_all_df_individuals.update(worksheet=batch_id, data=df_individual)                

    append_counter += 1
    
    st.success(f"{batch_id} GPT output appended to df_individual and saved online. Done {append_counter}/{len(df_batch_id_response_list)}.")


# %% [markdown]
# # Sending emails via AWS

# %%
st.subheader("Send notification emails")


# %%
#Define send email function

def send_email(ULTIMATE_RECIPIENT_NAME, ULTIMATE_RECIPIENT_EMAIL, ACCESS_LINK, BATCH_CODE):
    #Based on the following upon substituting various arguments, https://docs.aws.amazon.com/ses/latest/dg/send-an-email-using-sdk-programmatically.html
    
    # Replace sender@example.com with your "From" address.
    # This address must be verified with Amazon SES.
    #SENDER = "name <email>"

    # The subject line for the email.
    SUBJECT = f"{ULTIMATE_RECIPIENT_EMAIL}"
    
    # The email body for recipients with non-HTML email clients.

    #BODY_TEXT is not in used
    BODY_TEXT = (
    
    f"Dear {ULTIMATE_RECIPIENT_NAME}\r\n\r\n"
    
    "Thank you for using LawtoData. You can now view and download your requested data. To do so, please click on the following link:\r\n"
    f"{ACCESS_LINK}\r\n\r\n"
    
    f"Your access code is {BATCH_CODE}\r\n\r\n"
    
    "Lawtodata is partially funded by a University of Sydney Research Accelerator (SOAR) Prize. Please kindly acknowledge this if you use your requested data to produce any research output. \r\n\r\n"
    
    #There is no need to acknowledge me. 
    
    "Kind regards\r\n\r\n"
    
    "Ben\r\n\r\n"
    
    "Ben Chen | Senior Research Fellow and Senior Lecturer\r\n"
    "The University of Sydney Law School\r\n"
    " \r\n"
    "Email: ben.chen@sydney.edu.au | Phone: + 61 2 8627 6887 (by appointment)\r\n"
    "Webpage: https://www.sydney.edu.au/law/about/our-people/academic-staff/ben-chen.html\r\n"
    "Address: Room 431, New Law Building (F10), Eastern Ave, The University of Sydney, NSW 2006\r\n"
    )

    #<h1>LawtoData: an Empirical Legal Research Kickstarter</h1>

    
    # The HTML body of the email.
    BODY_HTML = f"""<html>
    <head></head>
    <body>
    <p>
    Dear {ULTIMATE_RECIPIENT_NAME}
    </p>
    <p>
    Thank you for using <em>LawtoData</em>. You can now view and download your requested data. To do so, please click on the following link:
    </p>
    <p>
    {ACCESS_LINK}
    </p>
    <p>
    Your access code is {BATCH_CODE}
    </p>     
    <p>
    <em>LawtoData</em> is partially funded by a University of Sydney Research Accelerator (SOAR) Prize. Please kindly acknowledge this if you use your requested data to produce any research output.
    </p>    
    <p>
    Please don't hesitate to reach out if I could be of assistance.
    </p> 
    <p>
    Kind regards
    </p> 
    <p>
    Ben
    </p>   
    <p>
    <b>Ben Chen</b> | Senior Research Fellow and Senior Lecturer
    <p>
    The University of Sydney Law School
    </p>
    <p>
    Email: ben.chen@sydney.edu.au | Phone: + 61 2 8627 6887 (by appointment)
    </p>
    <p>
    Webpage: https://www.sydney.edu.au/law/about/our-people/academic-staff/ben-chen.html
    </p>
    <p>
    Address: Room 431, New Law Building (F10), Eastern Ave, The University of Sydney, NSW 2006
    </p> 
    </body>
    </html>
    """              
    
    # The character encoding for the email.
    CHARSET = "UTF-8"
    
    # Create a new SES resource and specify a region.
    #client = boto3.client('ses',region_name=AWS_REGION)
    
    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = ses.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
                #'CcAddresses': [
                    #CC_RECIPIENT,
                #]
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    #'Text': {
                        #'Charset': CHARSET,
                        #'Data': BODY_TEXT,
                    #},
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
            # If you are not using a configuration set, comment or delete the
            # following line
            #ConfigurationSetName=CONFIGURATION_SET,
        )
    # Display an error if something goes wrong.	
    
    except ClientError as e:
        st.error(e.response['Error']['Message'])
        print(e.response['Error']['Message'])
        
    else:
        st.success(f"Email sent! Message ID: {response['MessageId']}.")        
        print(f"Email sent! Message ID: {response['MessageId']}.")        


# %%
#Get number of notification emails to send
all_df_masters.fillna('')

emails_counter_total = 0

for index in all_df_masters.index:
    
    sent_to_user = all_df_masters.loc[index, 'sent_to_user']

    status = all_df_masters.loc[index, 'status']

    if ((status == 'completed') and (sent_to_user not in [True, 1, 'yes', 'Yes', '1'])):
        emails_counter_total += 1

# %%
#Send emails
#all_df_masters.fillna('')

email_sent_counter = 0

for index in all_df_masters.index:
    
    sent_to_user = all_df_masters.loc[index, 'sent_to_user']

    status = all_df_masters.loc[index, 'status']

    if ((status == 'completed') and (sent_to_user not in [True, 1, 'yes', 'Yes', '1'])):
        
        batch_id = str(all_df_masters.loc[index, 'batch_id'])
        name = str(all_df_masters.loc[index, 'Your name'])
        email = str(all_df_masters.loc[index, 'Your email address'])

        link = 'https://lawtodata.streamlit.app/BATCH'

        try:
            send_email(ULTIMATE_RECIPIENT_NAME = name, 
                       ULTIMATE_RECIPIENT_EMAIL = email, 
                       ACCESS_LINK = link , 
                       BATCH_CODE = batch_id
                      )

            all_df_masters.loc[index, 'sent_to_user'] = 1

            email_sent_counter += 1
            
            st.success(f'{batch_id} for user {name} at {email} successfully emailed. Done {email_sent_counter}/{emails_counter_total}.')
            print(f'{batch_id} for user {name} at {email} successfully emailed. Done {email_sent_counter}/{emails_counter_total}.')

        except Exception as e:
            st.error(f"{batch_id} not emailed to user {name} at {email}.")
            print(f"{batch_id} not emailed to user {name} at {email}.")

            st.error(f"{e}")
            print(f"{e}")

            


# %% [markdown]
# # Finish

# %%
st.subheader("Finish")

# %%
#Upload all_df_masters to aws if needed

all_df_masters_needs_update = False

for index in all_df_masters.index:
    if all_df_masters.loc[index, 'status'] != all_df_masters_current.loc[index, 'status']:
        all_df_masters_needs_update = True
        break

if all_df_masters_needs_update == True:
    
    csv_buffer = StringIO()
    all_df_masters.to_csv(csv_buffer)
    s3_resource.Object('lawtodata', 'all_df_masters.csv').put(Body=csv_buffer.getvalue())

    st.success(f"Updated all_df_masters.csv online." )
    print(f"Updated all_df_masters.csv online." )

else:
    st.warning(f"No need to update all_df_masters.csv online." )
    print(f"No need to update all_df_masters.csv online." )

#Update google sheet for all_df_masters
#conn_all_df_masters.update(worksheet="Sheet1", data=all_df_masters)
