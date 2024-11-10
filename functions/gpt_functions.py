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
from datetime import datetime
import sys
import pause
import os
import io
from io import BytesIO
from dateutil import parser
from dateutil.relativedelta import *
from datetime import timedelta
from PIL import Image
import math
from math import ceil
import matplotlib.pyplot as plt
import ast
from io import StringIO
import copy
#import time
import traceback


#OpenAI
import openai
import tiktoken

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
#from streamlit.components.v1 import html
import streamlit_ext as ste

#aws
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

#PandasAI
#from dotenv import load_dotenv
from pandasai import SmartDataframe
from pandasai import Agent
#from pandasai.llm import BambooLLM
from pandasai.llm.openai import OpenAI
import pandasai as pai
from pandasai.responses.streamlit_response import StreamlitResponse
from pandasai.helpers.openai_info import get_openai_callback as pandasai_get_openai_callback

#Excel
import openpyxl
from pyxlsb import open_workbook as open_xlsb

# %%
from functions.common_functions import check_questions_answers, default_judgment_counter_bound, truncation_note, search_error_note, spinner_text, send_notification_email

# %% [markdown]
# # gpt-3.5, 4o-mini and 4o

# %% [markdown]
# ## Common functions and variables

# %%
#Upperbound on the length of questions for GPT

question_characters_bound = 2000

#Upperbound on number of judgments to scrape


# %%
#Create function to split a string into a list by line
def split_by_line(x):
    y = x.split('\n')
    for i in y:
        if len(i) == 0:
            y.remove(i)
    return y
    


# %%
#Create function to converting a dict into a line-separated string
def dict_to_string(questions_dict):
    questions_list = [*questions_dict.values()]
    questions_str = '\n'.join(questions_list)

    return questions_str
    


# %%
#Create function to split a list into a dictionary for list items longer than 10 characters
#Apply split_by_line() before the following function
def GPT_label_dict(x_list):
    GPT_dict = {}
    for i in x_list:
        if len(i) > 10:
            GPT_index = x_list.index(i) + 1
            i_label = 'GPT question ' + f'{GPT_index}'
            GPT_dict.update({i_label: i})
    return GPT_dict


# %%
#Check validity of API key

@st.cache_data(show_spinner = False)
def is_api_key_valid(key_to_check):
    openai.api_key = key_to_check
    
    try:
        completion = openai.chat.completions.create(
            #model="gpt-3.5-turbo-0125",
            model = 'gpt-4o-mini', 
            messages=[{"role": "user", "content": 'Hi'}], 
            max_tokens = 1
        )
    except:
        return False
    else:
        return True


# %%
#Define input and output costs, token caps and maximum characters
#each token is about 4 characters

def gpt_input_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_input_cost = 1/1000000*0.5
        
    if gpt_model == "gpt-4o-2024-05-13": #As of 20240910, gpt-4o points towards gpt-4o-2024-05-13
        gpt_input_cost = 1/1000000*5

    if gpt_model == "gpt-4o-2024-08-06": #From 20241002, gpt-4o points towards gpt-4o-2024-08-06
        gpt_input_cost = 1/1000000*2.5

    if gpt_model == "gpt-4o":
        gpt_input_cost = 1/1000000*2.5
        
    if gpt_model == "gpt-4o-mini":
        gpt_input_cost = 1/1000000*0.15
        
    return gpt_input_cost

def gpt_output_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_output_cost = 1/1000000*1.5
        
    if gpt_model == "gpt-4o-2024-05-13": #As of 20240910, gpt-4o points towards gpt-4o-2024-05-13
        gpt_output_cost = 1/1000000*15

    if gpt_model == "gpt-4o-2024-08-06": #From 20241002, gpt-4o points towards gpt-4o-2024-08-06
        gpt_output_cost = 1/1000000*10

    if gpt_model == "gpt-4o":
        gpt_output_cost = 1/1000000*10
    
    if gpt_model == "gpt-4o-mini":
        gpt_output_cost = 1/1000000*0.6
    
    return gpt_output_cost
    
#As of 2024-06-07, questions are capped at about 1000 characters ~ 250 tokens, role_content/system_instruction is about 115 tokens, json_direction is about 11 tokens, answers_json is about 8 tokens plus 30 tokens per question 

def tokens_cap(gpt_model):
    #This is the global cap for each model, which will be shown to users
    #Leaving 1000 tokens to spare
    
    if gpt_model == "gpt-3.5-turbo-0125":
        
        tokens_cap = int(16385 - 3000) #For GPT-3.5-turbo, token limit covering BOTH input and output is 16385,  while the output limit is 4096.
    
    if gpt_model == "gpt-4o-2024-05-13": #As of 20240910, gpt-4o points towards gpt-4o-2024-05-13
        tokens_cap = int(128000 - 3000) #For gpt-4o, token limit covering both BOTH and output is 128000, while the output limit is 4096.

    if gpt_model == "gpt-4o-2024-08-06": #From 20241002, gpt-4o points towards gpt-4o-2024-08-06
        
        tokens_cap = int(128000 - 3000) #For gpt-4o, token limit covering both BOTH and output is 128000, while the output limit is 16384.

    if gpt_model == "gpt-4o":
        
        tokens_cap = int(128000 - 3000) #For gpt-4o, token limit covering both BOTH and output is 128000, while the output limit is 16384.
    
    if gpt_model == "gpt-4o-mini":
        tokens_cap = int(128000 - 3000) #For gpt-4o-mini, token limit covering both BOTH and output is 128000, while the output limit is 16384.

    return tokens_cap

def max_output(gpt_model, messages_for_GPT):

    if gpt_model == "gpt-3.5-turbo-0125":
        
        max_output_tokens = int(16385 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For GPT-3.5-turbo, token limit covering BOTH input and output is 16385,  while the output limit is 4096.
    
    if gpt_model == "gpt-4o-2024-05-13": #As of 20240910, gpt-4o points towards gpt-4o-2024-05-13
        
        max_output_tokens = int(128000 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4o, token limit covering both BOTH and output is 128000, while the output limit is 4096.

    if gpt_model == "gpt-4o-2024-08-06": #From 20241002, gpt-4o points towards gpt-4o-2024-08-06
        
        max_output_tokens = int(128000 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4o, token limit covering both BOTH and output is 128000, while the output limit is 16384.

    if gpt_model == "gpt-4o":
        
        max_output_tokens = int(128000 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4o, token limit covering both BOTH and output is 128000, while the output limit is 16384.s
    
    if gpt_model == "gpt-4o-mini":
        
        max_output_tokens = int(128000 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4o-mini, token limit covering both BOTH and output is 128000, while the output limit is 16384.

    return min(4096, abs(max_output_tokens))
    


# %%
default_msg = f'**Please enter your search terms.** By default, this app will collect (ie scrape) up to {default_judgment_counter_bound} cases, and process up to approximately {round(tokens_cap("gpt-4o-mini")*3/4)} words from each case.'

default_caption = f'Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more cases.'


# %%
#Tokens estimate preliminaries

#encoding = tiktoken.get_encoding("cl100k_base")
#encoding = tiktoken.encoding_for_model(gpt_model)

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    #Tokens estimate function
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    
    return num_tokens


# %%
def judgment_prompt_json(judgment_json, gpt_model):

    #Remove hyperlink
    for key in judgment_json.keys():
        if 'hyperlink' in key.lower():
            judgment_json[key] = ''
            break

    #Determine whether 'judgment', opinions, or 'recap_documents' contains text

    text_key = ''
    
    if 'judgment' in judgment_json.keys():
        text_key = 'judgment'

    if 'opinions' in judgment_json.keys():
        text_key = 'opinions'

    if 'recap_documents' in judgment_json.keys():
        text_key = 'recap_documents'

    #st.write(f"text_key is {text_key}")
    
    #Just use original judgment_json if no long text
    if text_key not in judgment_json.keys():
        return judgment_json

    else:        
        #Turn judgment, opinions or recap_documents to string
        if isinstance(judgment_json[text_key], list):
            try:
                judgment_to_string = '\n'.join(judgment_json[text_key])
    
            except:
                judgment_to_string = str(judgment_json[text_key])
            
        elif isinstance(judgment_json[text_key], str):
            judgment_to_string = judgment_json[text_key]
            
        else:
            judgment_to_string = str(judgment_json[text_key])
    
        #Truncate judgment, opinions or recap_documents if needed
        judgment_content = f'Based on the metadata and {text_key} in the following JSON: """ {json.dumps(judgment_json, default=str)} """'
    
        judgment_content_tokens = num_tokens_from_string(judgment_content, "cl100k_base")
        
        if judgment_content_tokens <= tokens_cap(gpt_model):
            
            return judgment_content
    
        else:
            
            meta_data_len = judgment_content_tokens - num_tokens_from_string(judgment_to_string, "cl100k_base")
    
            intro_len = num_tokens_from_string(f'Based on the metadata and {text_key} in the following JSON: """  """', "cl100k_base")
            
            judgment_chars_capped = int(round((tokens_cap(gpt_model) - meta_data_len - intro_len)*4))
            
            judgment_string_trimmed = judgment_to_string[ :int(judgment_chars_capped/2)] + judgment_to_string[-int(judgment_chars_capped/2): ]
    
            judgment_json[text_key] = judgment_string_trimmed     
            
            judgment_content_capped = f'Based on the metadata and {text_key} in the following JSON:  """ {json.dumps(judgment_json, default=str)} """'
            
            return judgment_content_capped
    


# %%
#Check questions for potential privacy infringement

questions_check_system_instruction = """
You are a compliance officer helping a human ethics committee to ensure that no personally identifiable information will be exposed. 
You will be given questions to check in JSON form. Please provide labels for these questions based only on information contained in the JSON.
Where a question seeks information about a person's birth or address, you label "1". If a question does not seek such information, you label "0". If you are not sure, label "unclear".
For example, the question "What's the plaintiff's date of birth?" should be labelled "1".
For example, the question "What's the defendant's address?" should be labelled "1".
For example, the question "What's the victim's date of death?" should be labelled "0".
For example, the question "What's the judge's name?" should be labelled "0".
For example, the question "What's the defendant's age?" should be labelled "0".
"""

#More general below
#questions_check_system_instruction = """
#You are a compliance officer helping a human ethics committee to ensure that no personally identifiable information will be exposed. 
#You will be given questions to check in JSON form. 
#Based only on information contained in the JSON, please check each question for whether it seeks a person's birth, address, or other personally identifiable information. 
#Where a question indeed seeks personally identifiable information, you label "1". 
#Where a question does not seek personally identifiable information, you label "0". 
#If you are not sure, label "unclear".
#"""

# %%
#Check questions for potential privacy infringement
#For instant mode

@st.cache_data(show_spinner = False)
def GPT_questions_label(_questions_json, gpt_model, questions_check_system_instruction):
    #'question_json' variable is a json of questions to GPT
    #'jugdment' variable is a judgment_json   
    #Returns a json of checked questions

    json_direction = [{"role": "user", "content": 'Label the following questions in JSON form.'}]

    #Create answer format
    
    q_keys = [*_questions_json]
    
    labels_json = {}
    
    for q_index in q_keys:
        labels_json.update({q_index: 'Your label for the question with index ' + q_index})
    
    #Create questions, which include the answer format
    
    question_to_check = [{"role": "user", "content": json.dumps(_questions_json, default = str) + ' Return labels in the following JSON form: ' + json.dumps(labels_json, default = str)}]
    
    #Create messages in one prompt for GPT
    
    intro_for_GPT = [{"role": "system", "content": questions_check_system_instruction}]
    #messages_for_GPT = intro_for_GPT + judgment_for_GPT + json_direction + question_to_check
    messages_for_GPT = intro_for_GPT + json_direction + question_to_check
    
#   return messages_for_GPT

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model = gpt_model,
            messages = messages_for_GPT, 
            response_format = {"type": "json_object"}, 
            max_tokens = max_output(gpt_model, messages_for_GPT), 
            temperature = 0.1, 
            #top_p = 0.1
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        #To obtain a json directly, use below
        labels_dict = json.loads(completion.choices[0].message.content)
        
        #Obtain tokens
        output_tokens = completion.usage.completion_tokens
        
        prompt_tokens = completion.usage.prompt_tokens
        
        return [labels_dict, output_tokens, prompt_tokens]

    except Exception as error:
        
        for q_index in q_keys:
            
            labels_json.update({q_index: error})
        
        return [labels_json, 0, 0]



# %%
#Display unanswered questions
def unanswered_questions(unchecked_questions_json, checked_questions_json):

    #Reset unanswered questions text for batch get email
    st.session_state['unanswered_questions'] = ''

    #Produce unanswered questions
    unanswered_questions_list = []
    
    for question in unchecked_questions_json.values():
        if question not in checked_questions_json.values():
            unanswered_questions_list.append(question)

    if len(unanswered_questions_list) > 0:
                
        if len(unanswered_questions_list) == 1:

            witheld_text = 'To avoid exposing personally identifiable information, the following question was witheld:\n\n'
        
        if len(unanswered_questions_list) > 1: 
            
            witheld_text = 'To avoid exposing personally identifiable information, the following questions were witheld:\n\n'

        witheld_text += '\n\n'.join(unanswered_questions_list)
    
        #Display unanswered questions
        st.warning(witheld_text)



# %%
#Function to replace unchecked questions with checked questions
def checked_questions_json(questions_json, gpt_labels_output):
    
    checked_questions_json = questions_json

    for q_key in gpt_labels_output[0]:
        
        if str(gpt_labels_output[0][q_key]) == '1':
            
            checked_questions_json.pop(q_key)
    
    return checked_questions_json



# %%
#Check questions for potential privacy infringement

@st.cache_data(show_spinner = False)
def GPT_questions_check(_questions_json_or_string, gpt_model, questions_check_system_instruction):
    #'questions_str' variable is a string of questions to GPT
    #Returns both a string and a json of checked questions, together with costs, and displays any witheld questions
    
    #Create dict of questions for GPT

    if isinstance(_questions_json_or_string, str):
    
        questions_list = split_by_line(_questions_json_or_string[0: question_characters_bound])
        questions_json = GPT_label_dict(questions_list)

    else:
        questions_json = _questions_json_or_string

    #Check questions for privacy violation
    
    try:

        unchecked_questions_json = questions_json.copy()
        
        labels_output = GPT_questions_label(questions_json, gpt_model, questions_check_system_instruction)

        questions_check_output_tokens = labels_output[1]

        questions_check_input_tokens = labels_output[2]
    
        questions_json = checked_questions_json(questions_json, labels_output)

        unanswered_questions(unchecked_questions_json, questions_json)

        print('Questions checked.')

    except Exception as e:

        print('Questions check failed.')
        print(e)


        #create placeholder input and output tokens
        questions_check_output_tokens = 0
        questions_check_input_tokens = 0
        
    
    #Returns a stirng of questions
    questions_string = dict_to_string(questions_json)

    return {'questions_json': questions_json, 
            'questions_string': questions_string, 
            'questions_check_output_tokens': questions_check_output_tokens, 
            'questions_check_input_tokens': questions_check_input_tokens
           }


# %%
#Check questions for potential privacy infringement

answers_check_system_instruction = """
You are a compliance officer helping an academic researcher to redact information about birth and address. 
You will be given text to check in JSON form. Please check the text based only on information contained in the JSON. 
Where any part of the text identifies birth or an address, you replace that part with "[redacted]". 
You then return the remainder of the text unredacted.
You redact birth and address only. Do not redact anything else, such as names, date of death, age.
For example, if the text given to you is "John Smith, born 1 January 1950, died on 20 December 2008 at 1 Main St Blackacre aged 58.", you return "John Smith, born [redacted], died on 20 December 2008 at [redacted] aged 58.".
"""


# %%
#Check _answers_to_check_json for potential privacy infringement
#Don't add @st.cache_data

def GPT_answers_check(_answers_to_check_json, gpt_model, answers_check_system_instruction):

    #Check answers
    
    json_direction = [{"role": "user", "content": 'Check the following text in JSON form.'}]

    #Create answer format

    answers_to_check_list = [_answers_to_check_json]

    redacted_answers_json = {}
    
    if isinstance(_answers_to_check_json, list):
        
        answers_to_check_list = _answers_to_check_json

    for _answers_to_check_json in answers_to_check_list:
        
        q_keys = [*_answers_to_check_json]
        
        for q_index in q_keys:
            
            redacted_answers_json.update({q_index: 'Your response.'})

    #Create _answers_to_check_json, which include the answer format
    
    question_to_check = [{"role": "user", "content": json.dumps(_answers_to_check_json, default = str) + ' Respond in the following JSON form: ' + json.dumps(redacted_answers_json, default = str)}]
    
    #Create messages in one prompt for GPT
    
    intro_for_GPT = [{"role": "system", "content": answers_check_system_instruction}]
    messages_for_GPT = intro_for_GPT + json_direction + question_to_check

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model = gpt_model,
            messages = messages_for_GPT, 
            response_format = {"type": "json_object"}, 
            max_tokens = max_output(gpt_model, messages_for_GPT), 
            temperature = 0.1, 
            #top_p = 0.1
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        #To obtain a json directly, use below
        redacted_answers_dict = json.loads(completion.choices[0].message.content)
        
        #Obtain tokens
        redacted_answers_output_tokens = completion.usage.completion_tokens
        
        redacted_answers_prompt_tokens = completion.usage.prompt_tokens

        print('Answers checked.')

    except Exception as error:
        
        print('Answers check failed.')

        #Create placeholder GPT answers check output
        redacted_answers_dict = {}
        for q_index in q_keys:
            redacted_answers_dict.update({q_index: error})

        redacted_answers_output_tokens = 0

        redacted_answers_prompt_tokens = 0
        
    return [redacted_answers_dict, redacted_answers_output_tokens, redacted_answers_prompt_tokens]



# %%
#For modern judgments, define system role content for GPT
role_content = """You are a legal research assistant helping an academic researcher to answer questions about a public judgment and court record. You will be provided with the judgment, record and the associated metadata in JSON form. 
Please answer questions based only on information contained in the judgment, record and metadata. Where your answer comes from specific paragraphs, pages or sections of the judgment, record or metadata, include a reference to those paragraphs, pages or sections. 
If you cannot answer the questions based on the judgment, record or metadata, do not make up information, but instead write 'answer not found'. 
"""


# %% [markdown]
# ## GPT instant response

# %%
#Define GPT answer function for answers in json form, YES TOKENS
#IN USE

@st.cache_data(show_spinner = False)
def GPT_json(questions_json, df_example, judgment_json, gpt_model, system_instruction):
    #'question_json' variable is a json of questions to GPT
    #'jugdment' variable is a judgment_json   

    judgment_for_GPT = [{"role": "user", "content": judgment_prompt_json(judgment_json, gpt_model)}]

    json_direction = [{"role": "user", "content": 'You will be given questions to answer in JSON form.'}]

    #Create answer format
    answers_json = {}
    
    if len(df_example.replace('"', '')) > 0:

        try:
            
            if isinstance(df_example, str):
                
                answers_json = json.loads(df_example)

            if isinstance(df_example, dict):
                
                answers_json = df_example
                
        except Exception as e:
            print(f"Example provided but can't produce json to send to GPT.")
            print(e)
    
    q_keys = [*questions_json]
    
    if len(answers_json) == 0:

        q_counter = 1
        for q_index in q_keys:
            answers_json.update({f'GPT question {q_counter}: {questions_json[q_index]}': f'Your answer. (The paragraphs, pages or sections from which you obtained your answer)'})
            q_counter += 1
    
    #Create questions, which include the answer format
    question_for_GPT = [{"role": "user", "content": json.dumps(questions_json, default = str) + ' Respond in the following JSON form: ' + json.dumps(answers_json, default = str)}]
    
    #Create messages in one prompt for GPT
    intro_for_GPT = [{"role": "system", "content": system_instruction}]
    messages_for_GPT = intro_for_GPT + judgment_for_GPT + json_direction + question_for_GPT
    
#   return messages_for_GPT

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model = gpt_model,
            messages = messages_for_GPT, 
            response_format = {"type": "json_object"}, 
            max_tokens = max_output(gpt_model, messages_for_GPT), 
            temperature = 0.1, 
            #top_p = 0.1
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        #To obtain a json directly
        answers_dict = json.loads(completion.choices[0].message.content)

        #Obtain tokens
        output_tokens = completion.usage.completion_tokens
        
        prompt_tokens = completion.usage.prompt_tokens
        
        return [answers_dict, output_tokens, prompt_tokens]

    except Exception as error:
        
        print('GPT failed to produce answers.')
        
        for q_index in q_keys:
            
            answers_json.update({q_index: error})
        
        return [answers_json, 0, 0]



# %%
#Define GPT function for each respondent's dataframe, index by judgment then question, with input and output tokens given by GPT itself
#IN USE

#The following function DOES NOT check for existence of questions for GPT
    # To so check, active line marked as #*

@st.cache_data(show_spinner = False)
def engage_GPT_json(questions_json, df_example, df_individual, GPT_activation, gpt_model, system_instruction):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # f"File length in tokens (up to {tokens_cap(gpt_model)} given to GPT)"
        # 'GPT cost estimate (USD excl GST)'
        # 'GPT time estimate (seconds)'
        # GPT questions/answers

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()

    #Check questions for privacy violation

    if check_questions_answers() > 0:
    
        questions_checked_dict = GPT_questions_check(questions_json, gpt_model, questions_check_system_instruction)

        questions_json = questions_checked_dict['questions_json']
    
        questions_check_output_tokens = questions_checked_dict['questions_check_output_tokens']
    
        questions_check_input_tokens = questions_checked_dict['questions_check_input_tokens']

    else:

        print('Questions not checked.')
        
        questions_check_output_tokens = 0
        
        questions_check_input_tokens = 0
    
    #Process questions

    #GPT use counter
    gpt_use_counter = 0
    
    for judgment_index in df_individual.index:
        
        judgment_json = df_individual.to_dict('index')[judgment_index]

        #Check wither error in getting the full text
        text_error = False
        for text_key in ['judgment', 'opinions', 'recap_documents']:
            if text_key in judgment_json.keys():
                if len(judgment_json[text_key]) == 0:
                    text_error = True
                    df_individual.loc[judgment_index, 'Note'] = search_error_note
                    print(f"Case indexed {judgment_index} not sent to GPT given full text was not scrapped.")
                break
        
        #Calculate and append number of tokens of judgment, regardless of whether given to GPT
        judgment_tokens = num_tokens_from_string(str(judgment_json), "cl100k_base")
        df_individual.loc[judgment_index, f"File length in tokens (up to {tokens_cap(gpt_model)} given to GPT)"] = judgment_tokens       

        #Indicate whether judgment truncated        
        if judgment_tokens > tokens_cap(gpt_model):
            df_individual.loc[judgment_index, 'Note'] = truncation_note

        #Create columns for respondent's GPT cost, time
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = ''
        df_individual.loc[judgment_index, 'GPT time estimate (seconds)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each judgment, gives answers as a string containing a dictionary

        if ((int(GPT_activation) > 0) and (text_error == False)):
            GPT_output_list = GPT_json(questions_json, df_example, judgment_json, gpt_model, system_instruction) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_output_list[0]

            #Check answers for potential policy violation
            if check_questions_answers() > 0:
            
                GPT_answers_check_output_list = GPT_answers_check(answers_dict, gpt_model, answers_check_system_instruction)

                #Get potentially redacted answers and costs
                answers_dict = GPT_answers_check_output_list[0]
                redacted_answers_output_tokens = GPT_answers_check_output_list[1]
                redacted_answers_prompt_tokens = GPT_answers_check_output_list[2]

            else:
                print('Answers not checked.')
                redacted_answers_output_tokens = 0
                redacted_answers_prompt_tokens = 0

            #Calculate GPT cost of answering questions
            answers_output_tokens = GPT_output_list[1] + redacted_answers_output_tokens
            answers_input_tokens  = GPT_output_list[2] + redacted_answers_output_tokens
                    
            #Calculate and append GPT finish time and time difference to individual df
            GPT_finish_time = datetime.now()
            
            GPT_time_difference = GPT_finish_time - GPT_start_time
    
            df_individual.loc[judgment_index, 'GPT time estimate (seconds)'] = GPT_time_difference.total_seconds()    

            #Display GPT use counter
            gpt_use_counter += 1
            print(f"GPT proccessed {gpt_use_counter}/{len(df_individual)} cases.")

        else:
            answers_dict = {}
            
            question_keys = [*questions_json]
            
            for q_index in question_keys:
                #Increases judgment index by 2 to ensure consistency with Excel spreadsheet
                answer = ''
                answers_dict.update({questions_json[q_index]: answer})

            #st.write(answers_dict)
            
            #Calculate capped judgment tokens

            judgment_capped_tokens = num_tokens_from_string(judgment_prompt_json(judgment_json, gpt_model), "cl100k_base")

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(json.dumps(questions_json, default = str), "cl100k_base")

            #Calculate other instructions' tokens

            other_instructions = system_instruction + 'you will be given questions to answer in JSON form.' + ' Respond in the following JSON form: '

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer. (The paragraphs, pages or sections from which you obtained your answer)", "cl100k_base")

            #Calculate number of tokens of answers
            answers_output_tokens = num_tokens_from_string(str(answers_dict), "cl100k_base")

            answers_input_tokens = judgment_capped_tokens + questions_tokens + other_tokens
            
    	#Create GPT question headings, append answers to individual spreadsheets, and remove template answers

        #answers_list = [answers_dict]

        #if isinstance(answers_dict, list):
            #answers_list = answers_dict
        
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
        
        #Calculate GPT costs

        #If no check for questions
        #GPT_cost = answers_output_tokens*gpt_output_cost(gpt_model) + answers_input_tokens*gpt_input_cost(gpt_model)

        #If check for questions
        GPT_cost = (answers_output_tokens + questions_check_output_tokens/len(df_individual))*gpt_output_cost(gpt_model) + (answers_input_tokens + questions_check_input_tokens/len(df_individual))*gpt_input_cost(gpt_model)

        #Calculate and append GPT cost to individual df
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual


# %% [markdown]
# ## Batch mode

# %%
#If own account

#Cutoff for requiring activate batch mode

judgment_batch_cutoff = 25

#max number of judgments under any mode
judgment_batch_max = 100


# %%
#Create custom id for one judgment_json file

#custom_id should be mnc plus time now

def gpt_get_custom_id(judgment_json):
    
    #Returns time now by default
    time_now = str(datetime.now()).replace(' ', '_').replace(':', '_').replace('.', '_')

    mnc = ''

    if 'Medium neutral citation' in judgment_json.keys():
        mnc = judgment_json['Medium neutral citation'].replace(' ', '_')
    
    elif 'mnc' in judgment_json.keys():

        mnc = judgment_json['mnc'].replace(' ', '_')

    else:
        mnc = 'unknown_mnc'

    case_name = ''

    if 'Case name' in judgment_json.keys():
        case_name = judgment_json['Case name'].replace(' ', '_')
    
    elif 'title' in judgment_json.keys():

        case_name = judgment_json['title'].replace(' ', '_')

    else:
        case_name = 'unknown_case_name'
    
    custom_id = f"{time_now}_{case_name}_{mnc}"

    return custom_id



# %%
#Define function for creating custom id and one line of jsonl file for batching
#Returns a dictionary of custom id and one line

def gpt_batch_input_id_line(questions_json, df_example, judgment_json, gpt_model, system_instruction):
    #'question_json' variable is a json of questions to GPT
    #'jugdment' variable is a judgment_json   

    judgment_for_GPT = [{"role": "user", "content": judgment_prompt_json(judgment_json, gpt_model)}]

    json_direction = [{"role": "user", "content": 'You will be given questions to answer in JSON form.'}]

    #Create answer format
    answers_json = {}

    if len(df_example.replace('"', '')) > 0:

        try:
            
            if isinstance(df_example, str):
                
                answers_json = json.loads(df_example)

            if isinstance(df_example, dict):
                
                answers_json = df_example

        except Exception as e:
            print(f"Example provided but can't produce json to send to GPT.")
            print(e)
    
    #Check if answers format succesfully created by following any example uploaded
    q_keys = [*questions_json]
    
    if len(answers_json) == 0:
        q_counter = 1
        for q_index in q_keys:
            answers_json.update({f'GPT question {q_counter}: {questions_json[q_index]}': f'Your answer. (The paragraphs, pages or sections from which you obtained your answer)'})
            q_counter += 1
            
    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": json.dumps(questions_json, default = str) + ' Respond in the following JSON form: ' + json.dumps(answers_json, default = str)}]
    
    #Create messages in one prompt for GPT
    intro_for_GPT = [{"role": "system", "content": system_instruction}]
    messages_for_GPT = intro_for_GPT + judgment_for_GPT + json_direction + question_for_GPT

    #Create one line in batch input
    #Format for one line in batch input file is
    #{"custom_id": "request-1", "method": "POST", "url": "/v1/chat/completions", "body": {"model": "gpt-3.5-turbo-0125", "messages": [{"role": "system", "content": "You are a helpful assistant."},{"role": "user", "content": "Hello world!"}],"max_tokens": 1000}}

    body = {"model": gpt_model, 
            "messages": messages_for_GPT, 
            "response_format": {"type": "json_object"}, 
            "max_tokens": max_output(gpt_model, messages_for_GPT), 
            "temperature": 0.1, 
            #"top_p" = 0.1
           }

    custom_id = gpt_get_custom_id(judgment_json)
    
    oneline = {"custom_id": custom_id, 
              "method": "POST", 
              "url": "/v1/chat/completions", 
              "body": body
             }

    return {"custom_id": custom_id, "oneline": oneline}



# %%
#Define function for creating jsonl file for batching together with df_individual with custom id inserted

#@st.cache_data(show_spinner = False)
def gpt_batch_input(questions_json, df_example, df_individual, GPT_activation, gpt_model, system_instruction):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()

    #Create list for conversion to jsonl

    batch_input_list = []
    
    #Process questions
    
    for judgment_index in df_individual.index:
        
        judgment_json = df_individual.to_dict('index')[judgment_index]

        #Check wither error in getting the full text
        text_error = False
        for text_key in ['judgment', 'opinions', 'recap_documents']:
            if text_key in judgment_json.keys():
                if len(judgment_json[text_key]) == 0:
                    text_error = True
                    df_individual.loc[judgment_index, 'Note'] = search_error_note
                    print(f"Case indexed {judgment_index} not sent to GPT given full text was not scrapped.")
                break
        
        #Calculate and append number of tokens of judgment, regardless of whether given to GPT
        judgment_tokens = num_tokens_from_string(str(judgment_json), "cl100k_base")
        df_individual.loc[judgment_index, f"File length in tokens (up to {tokens_cap(gpt_model)} given to GPT)"] = judgment_tokens       

        #Indicate whether judgment truncated
                
        if judgment_tokens > tokens_cap(gpt_model):
            df_individual.loc[judgment_index, 'Note'] = truncation_note

        #Create columns for respondent's GPT cost
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each judgment, gives answers as a string containing a dictionary
        if ((int(GPT_activation) > 0) and (text_error == False)):

            get_id_oneline = gpt_batch_input_id_line(questions_json, df_example, judgment_json, gpt_model, system_instruction)
            
            df_individual.loc[judgment_index, 'custom_id'] = get_id_oneline['custom_id']

            batch_input_list.append(get_id_oneline['oneline'])

            #Remove full text
            for text_key in ['judgment', 'opinions', 'recap_documents']:
                if text_key in df_individual.columns:
                    df_individual.loc[judgment_index, text_key] = ''
                    break
            
            df_individual.loc[judgment_index, 'GPT submission time'] = str(GPT_start_time)

        else:
            
            print(f'Case {judgment_index}: GPT not activated.')

    #Convert batch_input_list to jsonl
    #The following steps are based on
    #https://stackoverflow.com/questions/51775175/pandas-dataframe-to-jsonl-json-lines-conversion
    #https://github.com/openai/openai-python/tree/main#file-uploads
        #Replace 'client.' with 'openai.'
        #Need to convert jsonl_for_batching to bytes mode, see https://www.datacamp.com/tutorial/string-to-bytes-conversion

    df_jsonl = pd.DataFrame(batch_input_list)

    jsonl_for_batching = df_jsonl.to_json(orient='records', lines=True)
    
    batch_input_file = openai.files.create(
        file = jsonl_for_batching.encode(encoding="utf-8"),
        purpose="batch"
    )

    batch_input_file_id = batch_input_file.id
    
    batch_record = openai.batches.create(
        input_file_id=batch_input_file_id,
        endpoint="/v1/chat/completions",
        completion_window="24h", 
            #metadata={
      #"name":
        #"email":
    #}
    )
    
    return {'batch_record': batch_record, 'df_individual': df_individual}
    


# %%
#Batch function

@st.dialog("Requesting data")
def batch_request_function():

    if int(st.session_state.df_master.loc[0, 'Consent']) == 0:
        st.warning("You must tick 'Yes, I agree.' to use the app.")

    elif len(st.session_state.df_individual)>0:
        st.warning('You must :red[REMOVE] the data already produced before producing new data.')

    elif st.session_state['df_master'].loc[0, 'Use GPT'] == False:
        st.error("You must tick 'Use GPT'.")
        
    else:
 
        if ((st.session_state.own_account == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                
            if is_api_key_valid(st.session_state.df_master.loc[0, 'Your GPT API key']) == False:
                st.error('Your API key is not valid.')
                
                st.session_state["batch_ready_for_submission"] = False

                st.stop()

            else:
                
                st.session_state["batch_ready_for_submission"] = True

        if st.session_state.jurisdiction_page == 'pages/US.py':
            
            if len(str(st.session_state.df_master.loc[0, 'CourtListener API token'])) < 20:

                st.session_state["batch_ready_for_submission"] = False

                st.write('Please enter a valid CourtListener API token. You can sign up for one [here](https://www.courtlistener.com/sign-in/).')

                batch_token_entry = st.text_input(label = 'your CourtListener API token (mandatory)', value = st.session_state['df_master'].loc[0, 'CourtListener API token'])

                if st.button(label = 'CONFIRM your CourtListener API token', disabled = bool(st.session_state.batch_submitted)):
                    
                    st.session_state['df_master'].loc[0, 'CourtListener API token'] = batch_token_entry

                    if len(str(st.session_state.df_master.loc[0, 'CourtListener API token'])) < 20:
                
                        st.error('You must enter a valid CourtListener API token.')
                        st.stop()
                    else:
                        st.session_state["batch_ready_for_submission"] = True
        
        #Check if valid email address entered
        if '@' not in st.session_state['df_master'].loc[0, 'Your email address']:
            
            st.session_state["batch_ready_for_submission"] = False

            st.write('Please enter a valid email address to receive your request data.')
            
            batch_email_entry = st.text_input(label = "Your email address (mandatory)", value =  st.session_state['df_master'].loc[0, 'Your email address'])

            if st.button(label = 'CONFIRM your email address', disabled = bool(st.session_state.batch_submitted)):
                
                st.session_state['df_master'].loc[0, 'Your email address'] = batch_email_entry
    
                if '@' not in st.session_state['df_master'].loc[0, 'Your email address']:
                
                    st.error('You must enter a valid email address to receive your request data.')
                    st.stop()
                else:
                    st.session_state["batch_ready_for_submission"] = True

        if st.session_state["batch_ready_for_submission"] == True:
        
            with st.spinner(spinner_text):
                
                try:
    
                    #Create spreadsheet of responses
                    df_master = st.session_state.df_master

                    jurisdiction_page = st.session_state.jurisdiction_page
    
                    df_master['jurisdiction_page'] = jurisdiction_page
                    
                    df_master['status'] = 'to_process'
    
                    df_master['submission_time'] = str(datetime.now())

                    #Activate user's own key or mine
                    if st.session_state.own_account == True:
                        
                        API_key = st.session_state.df_master.loc[0, 'Your GPT API key']
        
                    else:
                        
                        API_key = st.secrets["openai"]["gpt_api_key"]
                        
                        st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = st.session_state["judgment_counter_max"]

                    #Check questions for potential privacy violation
                    openai.api_key = API_key

                    if df_master.loc[0, 'Use flagship version of GPT'] == True:
                        gpt_model = "gpt-4o-2024-08-06"
                    else:        
                        gpt_model = "gpt-4o-mini"

                    questions_checked_dict = GPT_questions_check(df_master.loc[0, 'Enter your questions for GPT'], gpt_model, questions_check_system_instruction)

                    #Use checked questions
                    df_master.loc[0, 'Enter your questions for GPT'] = questions_checked_dict['questions_string']
                    
                    #Initiate aws s3
                    s3_resource = boto3.resource('s3',region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"], aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"])
                    
                    #Get a list of all files on s3
                    bucket = s3_resource.Bucket('lawtodata')
    
                    #Get all_df_masters
                    for obj in bucket.objects.all():
                        key = obj.key
                        if key == 'all_df_masters.csv':
                            body = obj.get()['Body'].read()
                            all_df_masters = pd.read_csv(BytesIO(body), index_col=0)
                            break
                            
                    #Add df_master to all_df_masters 
                    all_df_masters = pd.concat([all_df_masters, df_master], ignore_index=True)
    
                    #Upload all_df_masters to aws
                    csv_buffer = StringIO()
                    all_df_masters.to_csv(csv_buffer)
                    s3_resource = boto3.resource('s3',region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"], aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"])
                    s3_resource.Object('lawtodata', 'all_df_masters.csv').put(Body=csv_buffer.getvalue())
                                           
                    #Send me an email to let me know
                    send_notification_email(ULTIMATE_RECIPIENT_NAME = st.session_state['df_master'].loc[0, 'Your name'], 
                                            ULTIMATE_RECIPIENT_EMAIL = st.session_state['df_master'].loc[0, 'Your email address']
                                           )

                    st.session_state["batch_submitted"] = True
                                        
                    st.rerun()
                
                except Exception as e:

                    st.error('Sorry, an error has occurred. Please change your questions or wait a few hours, and try again.')
                    
                    st.error(e)
                    
                    st.error(traceback.format_exc())
    
                    print(e)
    
                    print(traceback.format_exc())


# %% [markdown]
# ## Vision

# %%
#Tokens counter

def get_image_dims(image):
    if re.match(r"data:image\/\w+;base64", image):
        image = re.sub(r"data:image\/\w+;base64,", "", image)
        image = Image.open(BytesIO(base64.b64decode(image)))
        return image.size
    else:
        raise ValueError("Image must be a base64 string.")

def calculate_image_token_cost(image, detail="auto"):
    # Constants
    LOW_DETAIL_COST = 85
    HIGH_DETAIL_COST_PER_TILE = 170
    ADDITIONAL_COST = 85

    if detail == "auto":
        # assume high detail for now
        detail = "high"

    if detail == "low":
        # Low detail images have a fixed cost
        return LOW_DETAIL_COST
    elif detail == "high":
        # Calculate token cost for high detail images
        width, height = get_image_dims(image)
        # Check if resizing is needed to fit within a 2048 x 2048 square
        if max(width, height) > 2048:
            # Resize the image to fit within a 2048 x 2048 square
            ratio = 2048 / max(width, height)
            width = int(width * ratio)
            height = int(height * ratio)
        # Further scale down to 768px on the shortest side
        if min(width, height) > 768:
            ratio = 768 / min(width, height)
            width = int(width * ratio)
            height = int(height * ratio)
        # Calculate the number of 512px squares
        num_squares = math.ceil(width / 512) * math.ceil(height / 512)
        # Calculate the total token cost
        total_cost = num_squares * HIGH_DETAIL_COST_PER_TILE + ADDITIONAL_COST
        return total_cost
    else:
        # Invalid detail_option
        raise ValueError("Invalid value for detail parameter. Use 'low' or 'high'.")


# %% [markdown]
# # Run

# %%
#Jurisdiction specific instruction and functions

def gpt_run(jurisdiction_page, df_master):

    if jurisdiction_page == 'pages/HCA.py':
        
        system_instruction = role_content
        
        from functions.hca_functions import hca_run#, hca_collections, hca_search, hca_pdf_judgment, hca_meta_labels_droppable, hca_meta_judgment_dict, hca_meta_judgment_dict_alt, hca_mnc_to_link_browse, hca_citation_to_link, hca_mnc_to_link, hca_load_data, hca_data_url, hca_df, hca_judgment_to_exclude, hca_search_results_to_judgment_links_filtered_df, hca_year_range, hca_judge_list, hca_party_list, hca_terms_to_add, hca_enhanced_search  
        #hca_search_results_to_judgment_links
        
        run = copy.copy(hca_run)

    if jurisdiction_page == 'pages/NSW.py':
        
        system_instruction = role_content

        from nswcaselaw.search import Search
        
        from functions.nsw_functions import nsw_run#, nsw_search, nsw_meta_labels_droppable, nsw_courts, nsw_courts_positioning, nsw_default_courts, nsw_tribunals, nsw_tribunals_positioning, nsw_court_choice, nsw_tribunal_choice, nsw_date, nsw_link, nsw_short_judgment, nsw_tidying_up, nsw_tidying_up_pre_gpt
    
        run = copy.copy(nsw_run)
    
    if jurisdiction_page == 'pages/FCA.py':
        
        system_instruction = role_content
        
        from functions.fca_functions import fca_run#, fca_courts, fca_courts_list, fca_search, fca_search_url, fca_search_results_to_judgment_links, fca_metalabels, fca_metalabels_droppable, fca_meta_judgment_dict, fca_pdf_name_mnc_list, fca_pdf_name
        #fca_link_to_doc
        
        run = copy.copy(fca_run)

    if jurisdiction_page == 'pages/US.py':
        
        system_instruction = role_content
        
        from functions.us_functions import us_run#, us_search_function, us_court_choice_to_list, us_court_choice_clean, us_order_by, us_pacer_order_by, us_precedential_status, us_fed_app_courts, us_fed_dist_courts, us_fed_hist_courts, us_bankr_courts, us_state_courts, us_more_courts, all_us_jurisdictions, us_date, us_collections, us_pacer_fed_app_courts, us_pacer_fed_dist_courts, us_pacer_bankr_courts, us_pacer_more_courts, all_us_pacer_jurisdictions, us_court_choice_clean_pacer
        
        run = copy.copy(us_run)

    if jurisdiction_page == 'pages/CA.py':
        
        system_instruction = role_content
        
        from functions.ca_functions import ca_run#, all_ca_jurisdictions, ca_courts, bc_courts, ab_courts, sk_courts, mb_courts, on_courts, qc_courts, nb_courts, ns_courts, pe_courts, nl_courts, yk_courts, nt_courts, nu_courts, all_ca_jurisdiction_court_pairs, ca_court_tribunal_types, all_subjects, ca_search, ca_search_url, ca_search_results_to_judgment_links, ca_meta_labels_droppable, ca_meta_dict, ca_date, ca_meta_judgment_dict
        
        run = copy.copy(ca_run)

    if jurisdiction_page == 'pages/UK.py':
        
        system_instruction = role_content
        
        from functions.uk_functions import uk_run#, uk_courts_default_list, uk_courts, uk_courts_list, uk_court_choice, uk_link, uk_search, uk_search_results_to_judgment_links, uk_meta_labels_droppable, uk_meta_judgment_dict
        
        run = copy.copy(uk_run)

    if jurisdiction_page == 'pages/AFCA.py':

        system_instruction = role_content
                
        from functions.afca_functions import afca_run#, afca_old_run, afca_new_run, product_line_options, product_category_options, product_name_options, issue_type_options, issue_options, afca_search, afca_meta_judgment_dict,  afca_meta_labels_droppable, afca_old_pdf_judgment, afca_old_element_meta, afca_old_search, afca_old_meta_labels_droppable, afca_meta_labels_droppable, streamlit_timezone
                
        if streamlit_timezone() == True:

            st.warning('One or more Chrome window may be launched. It must be kept open.')

        run = copy.copy(afca_run)

    if jurisdiction_page == 'pages/ER.py':

        from functions.er_functions import er_run#, er_run_b64, er_methods_list, er_method_types, er_search, er_search_results_to_case_link_pairs, er_judgment_text, er_meta_judgment_dict, role_content_er, er_judgment_tokens_b64, er_meta_judgment_dict_b64, er_GPT_b64_json, er_engage_GPT_b64_json

        system_instruction = role_content_er

        run = copy.copy(er_run)

    if jurisdiction_page == 'pages/KR.py':

        system_instruction = role_content
                
        from functions.kr_functions import kr_run#, kr_methods_list, kr_method_types, kr_search, kr_search_results_to_case_link_pairs, kr_judgment_text, kr_meta_judgment_dict
        
        run = copy.copy(kr_run)

    if jurisdiction_page == 'pages/SCTA.py':

        system_instruction = role_content
                
        from functions.scta_functions import scta_run#, scta_methods_list, scta_method_types, scta_search, scta_search_results_to_case_link_pairs, scta_judgment_text, scta_meta_judgment_dict
        
        run = copy.copy(scta_run)
    
    intro_for_GPT = [{"role": "system", "content": system_instruction}]

    df_individual = run(df_master)

    return df_individual



# %% [markdown]
# # Batch run

# %%
#Jurisdiction specific instruction and functions

def gpt_batch_input_submit(jurisdiction_page, df_master):

    if jurisdiction_page == 'pages/HCA.py':
        
        system_instruction = role_content
        
        from functions.hca_functions import hca_batch#, hca_collections, hca_search, hca_pdf_judgment, hca_meta_labels_droppable, hca_meta_judgment_dict, hca_meta_judgment_dict_alt, hca_mnc_to_link_browse, hca_citation_to_link, hca_mnc_to_link, hca_load_data, hca_data_url, hca_df, hca_judgment_to_exclude, hca_search_results_to_judgment_links_filtered_df, hca_year_range, hca_judge_list, hca_party_list, hca_terms_to_add, hca_enhanced_search  
        #hca_search_results_to_judgment_links
        
        batch =  copy.copy(hca_batch)

    if jurisdiction_page == 'pages/NSW.py':
        
        system_instruction = role_content

        from nswcaselaw.search import Search

        from functions.nsw_functions import nsw_batch#, nsw_search, nsw_tidying_up_pre_gpt, nsw_meta_labels_droppable, nsw_courts, nsw_courts_positioning, nsw_default_courts, nsw_tribunals, nsw_tribunals_positioning, nsw_court_choice, nsw_tribunal_choice, nsw_date, nsw_link, nsw_short_judgment
    
        batch =  copy.copy(nsw_batch)
    
    if jurisdiction_page == 'pages/FCA.py':
        
        system_instruction = role_content
        
        from functions.fca_functions import fca_batch#, fca_courts, fca_courts_list, fca_search, fca_search_url, fca_search_results_to_judgment_links, fca_metalabels, fca_metalabels_droppable, fca_meta_judgment_dict, fca_pdf_name_mnc_list, fca_pdf_name
        #fca_link_to_doc
        batch = copy.copy(fca_batch)

    if jurisdiction_page == 'pages/US.py':
        
        system_instruction = role_content
        
        from functions.us_functions import us_batch#, us_search_function, us_court_choice_clean, us_order_by, us_pacer_order_by, us_precedential_status, us_fed_app_courts, us_fed_dist_courts, us_fed_hist_courts, us_bankr_courts, us_state_courts, us_more_courts, all_us_jurisdictions, us_date, us_collections, us_pacer_fed_app_courts, us_pacer_fed_dist_courts, us_pacer_bankr_courts, us_pacer_more_courts, all_us_pacer_jurisdictions, us_court_choice_clean_pacer
            
        batch = copy.copy(us_batch)

    intro_for_GPT = [{"role": "system", "content": system_instruction}]

    batch_record_df_individual = batch(df_master)
    
    return batch_record_df_individual



# %%

