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
import sys
import pause
import os
import io
from io import BytesIO
from io import StringIO
import datetime
from datetime import date
from datetime import datetime
from dateutil import parser
from dateutil.relativedelta import *
from datetime import timedelta
#from PIL import Image
#import math
#from math import ceil
#import matplotlib.pyplot as plt
import ast
#import copy
import traceback


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

#For checking questions and answers, acknowledgment
from functions.common_functions import check_questions_answers, pop_judgment, funder_msg, date_parser

from functions.gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction, GPT_answers_check


# %%
#Title of webpage
st.set_page_config(
   page_title="LawtoData: An Empirical Legal Research Automator",
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

st.subheader("An Empirical Legal Research Automator")

st.markdown("""*LawtoData* is an [open-source](https://github.com/nehcneb/au-uk-empirical-legal-research) web app designed to help kickstart empirical projects involving judgments. It automates the most costly and time-consuming aspects of empirical research.""") 


# %%
#Initiate aws s3 and ses

#If running on Github Actions, then '/home/runner/' in current_dir

#Try local or streamlit first

try:
    API_key = st.secrets["openai"]["gpt_api_key"]
    
    AWS_DEFAULT_REGION=st.secrets["aws"]["AWS_DEFAULT_REGION"]
    AWS_ACCESS_KEY_ID=st.secrets["aws"]["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"]
    
    SENDER = st.secrets["email_notifications"]["email_sender"]
    RECIPIENT = st.secrets["email_notifications"]["email_receiver_work"]
        
    print('Running locally or on Streamlit')
    
except:
    API_key = os.environ['GPT_API_KEY']
    
    AWS_DEFAULT_REGION = os.environ['AWS_DEFAULT_REGION']
    AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
    AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
    
    SENDER = os.environ['EMAIL_SENDER']
    RECIPIENT = os.environ['EMAIL_RECEIVER_WORK']

    print('Running on GitHub Actions or HuggingFace')



# %%
#Function for getting df from aws
def get_aws_df(df_name):
#df_name is a string of the file name of the relevant df to get from aws, WITH the extension (ie csv)
#Returns the relevant df as Pandas object if found, or an empty Pandas object if not found or other error

    #Initialise s3_resource if not already
    if 's3_resource' not in st.session_state:

        st.session_state.s3_resource = get_aws_s3()
    
    try:

        #Get relevant df from aws
        obj = st.session_state.s3_resource.Object('lawtodata', df_name).get()
        body = obj['Body'].read()

        df = pd.read_csv(BytesIO(body), index_col=0)
        
        print(f"Sucessfully loaded {df_name} from aws.")

    except Exception as e:

        print(f"Failed to load {df_name} from aws due to error: {e}.")

        df = pd.DataFrame([])
        
    return df
    


# %%
#Function for getting all objects from aws s3

def get_aws_s3():
    
    #Initiate aws s3
    s3_resource = boto3.resource('s3',region_name=AWS_DEFAULT_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

    return s3_resource



# %%
#Get all objects from aws s3
#NOT IN USE

def get_aws_objects():
    
    #Get a list of all files on s3
    bucket = s3_resource.Bucket('lawtodata')
    
    aws_objects = []
    
    for obj in bucket.objects.all():
        key = obj.key
        body = obj.get()['Body'].read()
        key_body = {'key': key, 'body': body}
        aws_objects.append(key_body)

    return aws_objects
    


# %%
#Function for using aws ses for sending emails
def get_aws_ses():
    ses = boto3.client('ses',region_name=AWS_DEFAULT_REGION, aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    #ses is based on the following upon substitutiong 'ses' for 's3', https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#guide-credentials
    return ses


# %% [markdown]
# # Get all_df_masters and all df_individuals

# %%
st.subheader("Load records")

# %%
#Initiate aws_s3, and get all_df_masters
s3_resource = get_aws_s3()

all_df_masters_current =  get_aws_df('all_df_masters.csv')

#Work on new copy of all_df_masters, which enables comparison with current version on aws
all_df_masters = all_df_masters_current.copy(deep = True)

#Old method which involves loading all objects from aws first 
#aws_objects = get_aws_objects()

#for key_body in aws_objects:
    #if key_body['key'] == 'all_df_masters.csv':
        #all_df_masters_current = pd.read_csv(BytesIO(key_body['body']), index_col=0)
        #print(f"Succesfully loaded {key_body['key']}.")
        #break

#all_df_masters = all_df_masters.fillna('')

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
# # Get df_individuals and submit to GPT

# %%
st.subheader("Scrape judgments and submit as batches to GPT")

# %%
#requests counter

batch_request_total = 0

for index in all_df_masters.index:

    current_status = str(all_df_masters.loc[index, 'status'])

    if current_status == 'to_process':
        batch_request_total += 1

if batch_request_total == 0:
    st.warning('No requests need to be submitted.')
    print('No requests need to be submitted.')


# %%
#Generate batch input, submit to GPT and keep record online

#all_df_masters = all_df_masters[all_df_masters["status"]=='to_process']

batch_request_counter = 0

gpt_batch_input_list = []

for index in all_df_masters.index:

    current_status = str(all_df_masters.loc[index, 'status'])

    if current_status == 'to_process':

        try:
            
            #Use user's own api key if entered
            if bool(all_df_masters.loc[index, 'Use own account']) == True:
    
                if len(str(all_df_masters.loc[index, 'Your GPT API key'])) > 40:

                     API_key = all_df_masters.loc[index, 'Your GPT API key']
        
            openai.api_key = API_key
            
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

            print(f'{batch_id} submitted to GPT. Done {batch_request_counter}/{batch_request_total}.')
            st.success(f'{batch_id} submitted to GPT. Done {batch_request_counter}/{batch_request_total}.')

        except Exception as e:

            status = 'error'
            all_df_masters.loc[index, 'status'] = status
            
            print(traceback.format_exc())
            print(f'{index} error: {e}')
            st.write(f'{index} error: {e}')

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
    print('No judgment data have been scraped.')


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

    print(f"{batch_id} saved online. Done {save_counter}/{len(gpt_batch_input_list)}.")
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

    if current_status in ['validating', 'in_progress']:

        max_retrieve_counter += 1

if max_retrieve_counter == 0:
    st.warning('No batches are pending retrival.')
    print('No batches are pending retrival.')


# %%
df_batch_id_response_list = []

retrieve_counter = 0

for index in all_df_masters.index:

    current_status = all_df_masters.loc[index, "status"]

    if current_status in ['validating', 'in_progress']:

        try:
        
            #Use user's own api key if entered
            if bool(all_df_masters.loc[index, 'Use own account']) == True:
    
                if len(str(all_df_masters.loc[index, 'Your GPT API key'])) > 40:

                     API_key = all_df_masters.loc[index, 'Your GPT API key']
                    
            openai.api_key = API_key
        
            batch_id = all_df_masters.loc[index, 'batch_id']
        
            gpt_model = "gpt-4o-mini"
            if all_df_masters.loc[index, 'Use flagship version of GPT'] == True:
                gpt_model = "gpt-4o"
            else:        
                gpt_model = "gpt-4o-mini"
                
            #Get batch record
            batch_record = openai.batches.retrieve(batch_id)

            #st.write(f"{batch_id}: batch_record == {batch_record}")
            
            output_file_id = ''
        
            try:
        
                output_file_id = batch_record.output_file_id
        
            except:
        
                st.warning(f"{batch_id}: output_file_id not yet available.")
                
            status = batch_record.status
    
            #Print current status change
            st.info(f"{batch_id}: status == {status}.")
            print(f"{batch_id}: status == {status}.")

            #Update status etc on all_df_masters
            all_df_masters.loc[index, 'status'] = status
            all_df_masters.loc[index, 'output_file_id'] = output_file_id

            #st.write(f"all_df_masters.loc[index] == {all_df_masters.loc[index]}")

            if status == 'completed':
                
                batch_response = openai.files.content(output_file_id)

                #st.write(f"batch_response == {batch_response}")
        
                df_batch_response = pd.read_json(batch_response.text, lines=True)
        
                batch_id_response = {'batch_id': batch_id, 'df_batch_response': df_batch_response, 'gpt_model': gpt_model}

                if 'Your GPT API key' in all_df_masters.columns:
                    all_df_masters.loc[index, 'Your GPT API key'] = ''
                    
                if 'CourtListener API token' in all_df_masters.columns:
                    all_df_masters.loc[index, 'CourtListener API token'] = ''
                
                df_batch_id_response_list.append(batch_id_response)
    
                #Update counter 
                retrieve_counter += 1
        
                st.success(f"{batch_id}: status == {status}. Done {retrieve_counter}/{max_retrieve_counter}")
                print(f"{batch_id}: status == {status}. Done {retrieve_counter}/{max_retrieve_counter}")                

        except Exception as e:

            status = 'error'
            all_df_masters.loc[index, 'status'] = status
            
            print(traceback.format_exc())
            print(e)
            st.error(e)
            


# %% [markdown]
# # Append retrieved output to df_individuals

# %%
st.subheader("Append GPT output to judgment or file data")

# %%
if len(df_batch_id_response_list) == 0:
    
    st.warning('No GPT output needs to be appended.')


# %%
# Attach add gpt response to df_individual

append_counter = 0

for df_batch_response in df_batch_id_response_list:
    
    batch_id = df_batch_response['batch_id']
    
    #Get df_individual from aws
    df_individual = get_aws_df(f"{batch_id}.csv")
    
    #for key_body in aws_objects:
        #if key_body['key'] == f'{batch_id}.csv':
            #df_individual = pd.read_csv(BytesIO(key_body['body']), index_col=0)
            #print(f"Succesfully loaded {key_body['key']} as df_individual.")
            #break
    
    #Get df_individual from google sheets
    #conn_all_df_individuals = st.connection("gsheets_record_all_df_individuals", type=GSheetsConnection, ttl=0)
    #df_individual = conn_all_df_individuals.read(worksheet = batch_id)

    #Append gpt output to individual
    df_batch_response = df_batch_response['df_batch_response']

    for gpt_index in df_batch_response.index:

        #Get custom id of GPT case-specific response
        
        custom_id = df_batch_response.loc[gpt_index, 'custom_id']

        #Link GPT case-specific response to row in df_individual
        judgment_index_list = df_individual.index[df_individual['custom_id']==custom_id].tolist()

        if len(judgment_index_list) > 0:
            
            judgment_index = judgment_index_list[0]
            
            #Get gpt specific answers            
            try:
                
                answers_string = df_batch_response.loc[gpt_index, 'response']['body']['choices'][0]['message']['content']
                answers_dict = json.loads(answers_string)

            except Exception as e:
                
                answers_dict = {'ERROR': 'Unfortunately GPT did not produce a valid answer. Please change your questions and try again.'}
                
                print(f"{batch_id}: GPT did not produce a valid JSON.")
                print(e)
                
                st.error(f"{batch_id}: GPT did not produce a valid JSON.")

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

            #Add costs column
            df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = input_tokens*gpt_input_cost(gpt_model)/2 + output_tokens*gpt_output_cost(gpt_model)/2

            #for answers_dict in answers_list:        
            for answer_index in answers_dict.keys():
    
                #Check any errors
                answer_string = str(answers_dict[answer_index]).lower()
                
                if ((answer_string.startswith('your answer.')) or (answer_string.startswith('your response.'))):
                    
                    answers_dict[answer_index] = 'Error. Please try a different question or GPT model.'
    
                #Append answer to spreadsheet
    
                answer_header = answer_index
    
                try:
                
                    df_individual.loc[judgment_index, answer_header] = answers_dict[answer_index]
    
                except:
    
                    df_individual.loc[judgment_index, answer_header] = str(answers_dict[answer_index])
        
        #Remove judgment, opinions and PACER records columns
        if pop_judgment() > 0:
            if 'judgment' in df_individual.columns:
                df_individual.pop('judgment')
                
            if 'opinions' in df_individual.columns:
                df_individual.pop('opinions')
    
            if 'recap_documents' in df_individual.columns:
                df_individual.pop('recap_documents')
        
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
#Activate emails
ses = get_aws_ses()

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
    
    "Thank you for using LawtoData. You can now download your requested data from the following website:\r\n"
    f"{ACCESS_LINK}\r\n\r\n"
    
    f"Your access code is {BATCH_CODE}\r\n\r\n"
    
    f"{funder_msg} \r\n\r\n"

    "Please don't hesitate to reach out if I could be of assistance.\r\n\r\n"
    
    "Kind regards\r\n\r\n"
    
    "Ben\r\n\r\n\r\n\r\n"
    
    "Ben Chen | Associate Professor\r\n"
    "The University of Sydney Law School\r\n"
    " \r\n"
    "Email: ben.chen@sydney.edu.au | Phone: + 61 2 8627 6887 (by appointment)\r\n"
    "Webpage: https://www.sydney.edu.au/law/about/our-people/academic-staff/ben-chen.html\r\n"
    "Address: Room 431, New Law Building (F10), Eastern Ave, The University of Sydney, NSW 2006\r\n"
    )

    #"Please note that the data produced has been checked to avoid exposing personally identifiable information. \r\n\r\n"

    
    #<h1>LawtoData: an Empirical Legal Research Automator</h1>

    # The HTML body of the email.
    BODY_HTML = f"""<html>
    <head></head>
    <body>
    <p>
    Dear {ULTIMATE_RECIPIENT_NAME}
    </p>
    <p>
    Thank you for using LawtoData. You can now download your requested data from the following website:
    </p>
    <p>
    {ACCESS_LINK}
    </p>
    <p>
    Your access code is {BATCH_CODE}
    </p>    
    <p>
    {funder_msg}
    </p>    
    <p>Please don't hesitate to reach out if I could be of assistance.</p> 
    <p>
    Kind regards
    </p> 
    <p>
    Ben
    </p>   
    <p>
    </p>   
    <p>
    <b>Ben Chen</b> | Associate Professor
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

    #<p>
    #Please note that the data produced has been checked to avoid exposing personally identifiable information.
    #</p>

    
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
        #st.success(f"Email sent! Message ID: {response['MessageId']}.")        
        print(f"Email sent! Message ID: {response['MessageId']}.")        


# %%
#Define send error email function

def send_error_email(ULTIMATE_RECIPIENT_NAME, ULTIMATE_RECIPIENT_EMAIL, ACCESS_LINK, BATCH_CODE):
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

    f"Ref: {BATCH_CODE}\r\n\r\n"
        
    "Thank you for using LawtoData. Unfortunately, it was unable to produce your requested data due to an error. My Apologies.\r\n\r\n"
    
    "Please feel free to change your search terms or questions and try the app again. Please also feel free to ask me to look into the error.\r\n\r\n"
    
    "Kind regards\r\n\r\n"
    
    "Ben\r\n\r\n\r\n\r\n"
    
    "Ben Chen | Associate Professor\r\n"
    "The University of Sydney Law School\r\n"
    " \r\n"
    "Email: ben.chen@sydney.edu.au | Phone: + 61 2 8627 6887 (by appointment)\r\n"
    "Webpage: https://www.sydney.edu.au/law/about/our-people/academic-staff/ben-chen.html\r\n"
    "Address: Room 431, New Law Building (F10), Eastern Ave, The University of Sydney, NSW 2006\r\n"
    )

    #<h1>LawtoData: an Empirical Legal Research Automator</h1>

    # The HTML body of the email.
    BODY_HTML = f"""<html>
    <head></head>
    <body>
    <p>
    Dear {ULTIMATE_RECIPIENT_NAME}
    </p>
    <p>
    Ref: {BATCH_CODE}
    </p>
    <p>
    Thank you for using LawtoData. Unfortunately, it was unable to produce your requested data due to an error. My Apologies.
    </p>
    <p>
    Please feel free to change your search terms or questions and try the app again. Please also feel free to ask me to look into the error.
    </p>
    <p>
    Kind regards
    </p> 
    <p>
    Ben
    </p>   
    <p>
    </p>   
    <p>
    <b>Ben Chen</b> | Associate Professor
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

    if ((status in ['completed', 'error', 'failed']) and (sent_to_user not in [True, 1, 'yes', 'Yes', '1'])):
        emails_counter_total += 1

if emails_counter_total == 0:
    st.warning('No emails need to be sent.')

# %%
#Send emails

email_sent_counter = 0

for index in all_df_masters.index:

    email_sent = False

    status = all_df_masters.loc[index, 'status']
    
    sent_to_user = all_df_masters.loc[index, 'sent_to_user']

    if ((status in ['completed', 'error', 'failed']) and (sent_to_user not in [True, 1, 'yes', 'Yes', '1'])):

        batch_id = str(all_df_masters.loc[index, 'batch_id'])
        name = str(all_df_masters.loc[index, 'Your name']).replace('nan', 'anonymous user')
        email = str(all_df_masters.loc[index, 'Your email address'])

        link = 'https://lawtodata.streamlit.app/BATCH'

        try:
            if status == 'completed':
                send_email(ULTIMATE_RECIPIENT_NAME = name, 
                           ULTIMATE_RECIPIENT_EMAIL = email, 
                           ACCESS_LINK = link , 
                           BATCH_CODE = batch_id
                          )

                email_sent = True

            if status in ['error', 'failed']:
                send_error_email(ULTIMATE_RECIPIENT_NAME = name, 
                           ULTIMATE_RECIPIENT_EMAIL = email, 
                           ACCESS_LINK = link , 
                           BATCH_CODE = batch_id
                          )

                email_sent = True

            if email_sent == True:
    
                all_df_masters.loc[index, 'sent_to_user'] = 1
    
                email_sent_counter += 1
                
                st.success(f'{batch_id} for {name} at {email} successfully emailed. Done {email_sent_counter}/{emails_counter_total}.')
                print(f'{batch_id} for user {name} at {email} successfully emailed. Done {email_sent_counter}/{emails_counter_total}.')

        except Exception as e:
            st.error(f"{batch_id} not emailed to user {name} at {email}. status == {status}")
            print(f"{batch_id} not emailed to user {name} at {email}. status == {status}")

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

# %%
