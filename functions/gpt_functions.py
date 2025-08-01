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
#from dateutil.relativedelta import *
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
#import streamlit_ext as ste

#aws
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

#Excel
import openpyxl
from pyxlsb import open_workbook as open_xlsb

# %%
from functions.common_functions import check_questions_answers, pop_judgment, default_judgment_counter_bound, truncation_note, search_error_note, spinner_text, streamlit_timezone, get_aws_s3, aws_df_get, aws_df_put, get_aws_ses, send_notification_email, search_error_display

# %% [markdown]
# # GPT functions and variables

# %% [markdown]
# ## Preliminary functions and variables

# %%
#GPT models to use
basic_model = 'gpt-4.1-mini'
flagship_model = 'gpt-4.1'

# %%
#Upperbound on the length of questions for GPT
question_characters_bound = 5120


# %%
#Upperbound on the length of system instruction for GPT
system_characters_bound = 5120


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

    if isinstance(x_list, str):

        x_list = split_by_line(x_list)
    
    for i in x_list:
        
        if len(i) > 10:
            
            GPT_index = x_list.index(i) + 1
            
            i_label = f'GPT question {GPT_index}'
            
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
            model = basic_model, 
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

def tokens_cap(gpt_model):
    #This is the global cap for each model, which will be shown to users
    #Leaving 1000 tokens to spare
    
    if gpt_model == "gpt-3.5-turbo-0125":
        
        tokens_cap = int(16385 - (question_characters_bound + system_characters_bound)/4) #For GPT-3.5-turbo, token limit covering BOTH input and output is 16385,  while the output limit is 4096.
    
    elif "gpt-4o-mini" in gpt_model:
        tokens_cap = int(128000 - (question_characters_bound + system_characters_bound)/4) #For gpt-4o-mini, token limit covering both BOTH and output is 128000, while the output limit is 16384.

    elif "gpt-4o" in gpt_model:
        tokens_cap = int(128000 - (question_characters_bound + system_characters_bound)/4) #For gpt-4o, token limit covering both BOTH and output is 128000, while the output limit is 16384.

    elif "gpt-4.1-mini" in gpt_model:
        tokens_cap = int(1047576 - (question_characters_bound + system_characters_bound)/4) #For gpt-4o-mini, token limit covering both BOTH and output is 1,047,576, while the output limit is 32,768.

    elif "gpt-4.1-nano" in gpt_model:
        tokens_cap = int(1047576 - (question_characters_bound + system_characters_bound)/4) #For gpt-4o-nano, token limit covering both BOTH and output is 1,047,576, while the output limit is 32,768.

    else: #("gpt-4.1" in gpt_model) and ('nano' not in gpt_model) and ('mini' not in gpt_model):
        tokens_cap = int(1047576 - (question_characters_bound + system_characters_bound)/4) #For gpt-4o-nano, token limit covering both BOTH and output is 1,047,576, while the output limit is 32,768.
    
    return tokens_cap

def gpt_input_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_input_cost = 1/1000000*0.5

    elif "gpt-4o-mini" in gpt_model:
        gpt_input_cost = 1/1000000*0.15
    
    elif "gpt-4o" in gpt_model:
        gpt_input_cost = 1/1000000*2.5

    elif "gpt-4.1-mini" in gpt_model:
        gpt_input_cost = 1/1000000*0.4
        
    elif "gpt-4.1-nano" in gpt_model:
        gpt_input_cost = 1/1000000*0.1
    
    else: #("gpt-4.1" in gpt_model) and ('nano' not in gpt_model) and ('mini' not in gpt_model):

        gpt_input_cost = 1/1000000*2
    
    return gpt_input_cost

def gpt_output_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_output_cost = 1/1000000*1.5
        
    elif "gpt-4o-mini" in gpt_model:
        gpt_output_cost = 1/1000000*0.6

    elif "gpt-4o" in gpt_model:
        gpt_output_cost = 1/1000000*10

    elif "gpt-4.1-mini" in gpt_model:
        gpt_output_cost = 1/1000000*1.6
        
    elif "gpt-4.1-nano" in gpt_model:
        gpt_output_cost = 1/1000000*0.4
    
    else: #("gpt-4.1" in gpt_model) and ('nano' not in gpt_model) and ('mini' not in gpt_model):

        gpt_output_cost = 1/1000000*8
    
    return gpt_output_cost
    
def max_output(gpt_model, messages_for_GPT):

    if gpt_model == "gpt-3.5-turbo-0125":
        
        max_output_tokens = int(16385 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For GPT-3.5-turbo, token limit covering BOTH input and output is 16385,  while the output limit is 4096.

        output_limit = 4096
    
    elif gpt_model == "gpt-4o-mini":
        
        max_output_tokens = int(128000 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4o-mini, token limit covering both BOTH and output is 128000, while the output limit is 16384.

        output_limit = 16384
    
    elif "gpt-4o" in gpt_model:
        
        max_output_tokens = int(128000 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4o, token limit covering both BOTH and output is 128000, while the output limit is 16384.

        output_limit = 16384
    
    elif "gpt-4.1-mini" in gpt_model:

        max_output_tokens = int(1047576 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4.1-mini, token limit covering both BOTH and output is 1,047,576, while the output limit is 32,768.

        output_limit = 32768
        
    elif "gpt-4.1-nano" in gpt_model:

        max_output_tokens = int(1047576 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4.1-nano, token limit covering both BOTH and output is 1,047,576, while the output limit is 32,768.

        output_limit = 32768
    
    else: #("gpt-4.1" in gpt_model) and ('nano' not in gpt_model) and ('mini' not in gpt_model):

        max_output_tokens = int(1047576 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4.1, token limit covering both BOTH and output is 1,047,576, while the output limit is 32,768.

        output_limit = 32768
    
    return min(output_limit, abs(max_output_tokens))



# %%
default_msg = f'Please enter your search terms.'

default_caption = f'By default, this app will collect (ie scrape) up to {default_judgment_counter_bound} cases, and process up to approximately {round(tokens_cap(basic_model)*3/4)} words per case. Please reach out to Ben Chen at ben.chen@sydney.edu.au should you wish to cover more cases or process more words per case.'


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

    #Determine whether 'judgment', opinions, 'recap_documents', or extracted_text contains text

    text_key = ''

    #Loop through non-b64 keys
    for key in ['judgment', 'opinions', 'recap_documents', 'extracted_text']:
        if key in judgment_json.keys():
            text_key = key
            break
        
    #Just use original judgment_json if no long text
    if text_key not in judgment_json.keys():
        return judgment_json

    else:
        #Turn judgment, opinions, 'recap_documents', or extracted_text to string
        if isinstance(judgment_json[text_key], list):
            try:
                judgment_to_string = '\n'.join(judgment_json[text_key])
    
            except:
                judgment_to_string = str(judgment_json[text_key])
            
        elif isinstance(judgment_json[text_key], str):
            judgment_to_string = judgment_json[text_key]
            
        else:
            judgment_to_string = str(judgment_json[text_key])
    
        #Truncate judgment, opinions, 'recap_documents', or extracted_text if needed
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
#For modern judgments, define system role content for GPT
role_content = """You are a legal research assistant helping an academic researcher to answer questions about a public judgment and court record. You will be provided with the judgment, record and the associated metadata in JSON form. 
Please answer questions based only on information contained in the judgment, record and metadata. Where your answer comes from specific paragraphs, pages or sections of the judgment, record or metadata, include a reference to those paragraphs, pages or sections. 
If you cannot answer the questions based on the judgment, record or metadata, do not make up information, but instead write 'answer not found'."""
#Respond in JSON form. In your response, produce as many keys as you need. 


# %%
#Guidance on system role
gpt_system_msg = "The following system instruction provides context, rules and logic for GPT. [It takes priority over your questions.](https://model-spec.openai.com/) **Do not edit this** unless you know what you are doing."

# %% [markdown]
# ## Privacy

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


# %%
#Check questions for potential privacy infringement
#For instant mode

#Don't add @st.cache_data

def GPT_questions_label(_questions_json, gpt_model, questions_check_system_instruction):
    #'question_json' variable is a json of questions to GPT
    #'jugdment' variable is a judgment_json   
    #Returns a json of checked questions

    json_direction = [{"role": "user", "content": 'Label the following questions or instructions in JSON form.'}]

    #Create answer format
    
    q_keys = [*_questions_json]
    
    labels_json = {}
    
    for q_index in q_keys:
        labels_json.update({q_index: 'Your label for the question or instruction with index ' + q_index})
    
    #Create questions, which include the answer format
    
    question_to_check = [{"role": "user", "content": json.dumps(_questions_json, default = str) + ' Return labels in the following JSON form: ' + json.dumps(labels_json, default = str)}]
    
    #Create messages in one prompt for GPT
    
    intro_for_GPT = [{"role": "developer", "content": questions_check_system_instruction}]
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
    #st.session_state['unanswered_questions'] = ''

    #Produce unanswered questions
    unanswered_questions_list = []
    
    for question in unchecked_questions_json.values():
        if question not in checked_questions_json.values():
            unanswered_questions_list.append(question)

    if len(unanswered_questions_list) > 0:
                
        if len(unanswered_questions_list) == 1:

            withheld_text = 'To avoid exposing personally identifiable information, the following question/instruction was withheld:\n\n'
        
        if len(unanswered_questions_list) > 1: 
            
            withheld_text = 'To avoid exposing personally identifiable information, the following questions/instructions were withheld:\n\n'

        withheld_text += '\n\n'.join(unanswered_questions_list)
    
        #Display unanswered questions
        st.warning(withheld_text)



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
#Don't add @st.cache_data

def GPT_questions_check(_questions_json_or_string, gpt_model, questions_check_system_instruction):
    #'questions_str' variable is a string of questions to GPT
    #Returns both a string and a json of checked questions, together with costs, and displays any withheld questions
    
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

        #Reorganise checked questions
        #st.write(questions_json)
        
        questions_json = GPT_label_dict(list(questions_json.values()))
    
        #st.write(questions_json)
        
        #Stop if all questions are problematic
    
        #if len(questions_json) == 0:

            #st.error('All your questions may lead to expsure of personally identifiable information. As a precautionary measure, GPT has been instructed to stop responding.')

            #st.stop()

            #quit()

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
#Check system instruction for potential privacy infringement

system_instruction_check_system_instruction = """
You are a compliance officer helping a human ethics committee to ensure that no personally identifiable information will be exposed. 
You will be given instructions to check in JSON form. Please provide labels for these instructions based only on information contained in the JSON.
Where an instruction seeks information about a person's birth or address, you label "1". If an instruction does not seek such information, you label "0". If you are not sure, label "unclear".
For example, the instruction "Get each party's date of birth" should be labelled "1".
For example, the instruction "Get each party's address" should be labelled "1".
For example, the instruction "Get each party's date of death" should be labelled "0".
For example, the instruction "Get the judge's name" should be labelled "0".
For example, the instruction "Get each party's age" should be labelled "0".
"""


# %%
#Create function to split a list into a dictionary for list items longer than 10 characters
#Apply split_by_line() before the following function
def GPT_instruction_dict(x_list):
    GPT_dict = {}
    for i in x_list:
        if len(i) > 10:
            GPT_index = x_list.index(i) + 1
            i_label = f'Instruction {GPT_index}'
            GPT_dict.update({i_label: i})
    return GPT_dict


# %%
#Check questions for potential privacy infringement
#Don't add @st.cache_data

def GPT_system_check(_system_instruction, gpt_model, system_instruction_check_system_instruction):
    #'system_instruction' variable is the system_instruction given to GPT
    #Returns both a string and a json of checked system_instruction, together with costs, and displays any withheld instructions
    
    #Create dict of system_instruction for GPT

    #system_instruction_json = {'Instructions to check': _system_instruction}
        
    system_instruction_list = split_by_line(_system_instruction[0: system_characters_bound])
    system_instruction_json = GPT_instruction_dict(system_instruction_list)
    
    #Check questions for privacy violation
    
    try:

        unchecked_system_instruction_json = system_instruction_json.copy()
        
        labels_output = GPT_questions_label(system_instruction_json, gpt_model, system_instruction_check_system_instruction)

        system_instruction_check_output_tokens = labels_output[1]

        system_instruction_check_input_tokens = labels_output[2]

        print('system_instruction checked.')
        
        #Stop if system instruction is problematic
    
        system_instruction_json = checked_questions_json(system_instruction_json, labels_output)

        unanswered_questions(unchecked_system_instruction_json, system_instruction_json)

        #if len(system_instruction_json) == 0:

            #st.error('Your system instruction may lead to expsure of personally identifiable information. As a precautionary measure, GPT has been instructed to stop responding.')

            #st.stop()

            #quit()

    except Exception as e:

        print('system_instruction failed.')
        print(e)

        #create placeholder input and output tokens
        system_instruction_check_output_tokens = 0
        system_instruction_check_input_tokens = 0
        
    #Returns a stirng of questions
    system_instruction_string = dict_to_string(system_instruction_json)

    return {'system_instruction_json': system_instruction_json, 
            'system_instruction': system_instruction_string, 
            'system_instruction': _system_instruction, 
            'system_instruction_check_output_tokens': system_instruction_check_output_tokens, 
            'system_instruction_check_input_tokens': system_instruction_check_input_tokens
           }
    


# %%
#Check questions for potential privacy infringement

answers_check_system_instruction = """
You are a compliance officer helping an academic researcher to redact information about birth and address. 
You will be given text to check in JSON form. Please check the text based only on information contained in the JSON. 
Where any part of the text identifies birth or an address, you replace that part with "[redacted]". 
You then return the remainder of the text unredacted. Do not explain your reasoning. 
You redact birth and address only. Do not redact anything else, such as names, date of death, age.
For example, if the text given to you is "John Smith, born 1 January 1950, died on 20 December 2008 at 1 Main St Blackacre aged 58.", you return "John Smith, born [redacted], died on 20 December 2008 at [redacted] aged 58.".
For example, if the text given to you is "", you return "".
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
    
    question_to_check = [{"role": "user", "content": json.dumps(_answers_to_check_json, default = str) + '\n Respond in the following JSON form: ' + json.dumps(redacted_answers_json, default = str)}]
    
    #Create messages in one prompt for GPT
    
    intro_for_GPT = [{"role": "developer", "content": answers_check_system_instruction}]
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
    
    q_keys = [*questions_json]

    if len(df_example.replace('"', '')) > 0:

        try:
            
            if isinstance(df_example, str):
                
                answers_json = json.loads(df_example)

            if isinstance(df_example, dict):
                
                answers_json = df_example

            answers_json_instruction = '\n Return your answer as a JSON object, following this example: ' + json.dumps(answers_json, default = str)
            
        except Exception as e:
            print(f"Example provided but can't produce json to send to GPT.")
            print(e)
    
    if len(answers_json) == 0:

        q_counter = 1
        for q_index in q_keys:
            answers_json.update({f'GPT question {q_counter}: {questions_json[q_index]}': f'Your answer. (The paragraphs, pages or sections from which you obtained your answer)'})
            q_counter += 1
        
        answers_json_instruction = '\n Respond in the following JSON form: ' + json.dumps(answers_json, default = str) + '\n Every key in your JSON response must contain the relevant question.'

    #Create questions, which include the answer format
    question_for_GPT = [{"role": "user", "content": json.dumps(questions_json, default = str) + answers_json_instruction}]
    
    #Create messages in one prompt for GPT
    intro_for_GPT = [{"role": "developer", "content": system_instruction}]
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

        #Check system instruction
        system_instruction_checked_dict = GPT_system_check(system_instruction, gpt_model, system_instruction_check_system_instruction)

        system_instruction = system_instruction_checked_dict['system_instruction']

        system_instruction_check_output_tokens = system_instruction_checked_dict['system_instruction_check_output_tokens']
    
        system_instruction_check_input_tokens = system_instruction_checked_dict['system_instruction_check_input_tokens']
        
        #Check questions
        questions_checked_dict = GPT_questions_check(questions_json, gpt_model, questions_check_system_instruction)

        questions_json = questions_checked_dict['questions_json']
    
        questions_check_output_tokens = questions_checked_dict['questions_check_output_tokens']
    
        questions_check_input_tokens = questions_checked_dict['questions_check_input_tokens']

        #Add tokens

        questions_check_output_tokens += system_instruction_check_output_tokens
        
        questions_check_input_tokens +=system_instruction_check_input_tokens
    
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
        for text_key in ['judgment', 'opinions', 'recap_documents', 'extracted_text']:
            if text_key in judgment_json.keys():

                #Checking if judgment_json[text_key] is np.nan
                if isinstance(judgment_json[text_key], float):
                
                    judgment_json[text_key] = ''
                    
                if len(judgment_json[text_key]) == 0:
                    text_error = True
                    df_individual.loc[judgment_index, 'Note'] = search_error_note
                    print(f"Case/file indexed {judgment_index} not sent to GPT given full text was not scrapped.")
                        
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

            q_counter = 1
            for q_index in question_keys:
                #Increases judgment index by 2 to ensure consistency with Excel spreadsheet
                answer = ''
                answers_dict.update({f'GPT question {q_counter}: {questions_json[q_index]}': answer})
                q_counter += 1

            answers_json_instruction = '\n Respond in the following JSON form: ' + json.dumps(answers_dict, default = str)
            
            #st.write(answers_dict)
            
            #Calculate capped judgment tokens

            judgment_capped_tokens = num_tokens_from_string(judgment_prompt_json(judgment_json, gpt_model), "cl100k_base")

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(json.dumps(questions_json, default = str), "cl100k_base")

            #Calculate other instructions' tokens

            system_answers_instructions = system_instruction + 'you will be given questions to answer in JSON form.' + answers_json_instruction

            system_answers_tokens = num_tokens_from_string(system_answers_instructions, "cl100k_base")

            #Calculate number of tokens of answers
            answers_output_tokens = num_tokens_from_string(json.dumps(answers_dict, default = str), "cl100k_base")

            answers_input_tokens = judgment_capped_tokens + questions_tokens + system_answers_tokens
            
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
# ## Vision instant mode

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


# %%
#Define GPT answer function for answers in json form, YES TOKENS
#For vision

@st.cache_data(show_spinner = False)
def GPT_b64_json(questions_json, df_example, judgment_json, gpt_model, system_instruction):
    #'question_json' variable is a json of questions to GPT

    #file_for_GPT = [{"role": "user", "content": file_prompt(file_triple, gpt_model) + 'you will be given questions to answer in JSON form.'}]

    #Add images to messages to GPT
    image_content_value = [{"type": "text", "text": 'Based on the following images:'}]

    for key in ['judgment_b64', 'b64_list']:
        if key in judgment_json.keys():
            for image_b64 in judgment_json[key]:
                image_message_to_attach = {"type": "image_url", "image_url": {"url": image_b64,}}
                image_content_value.append(image_message_to_attach)
            break

    image_content = [{"role": "user", 
                      "content": image_content_value
                     }
                  ]

    metadata_content = [{"role": "user", "content": ''}]

    metadata_json_raw = judgment_json

    for key in ['tokens_raw', 'judgment_b64', 'b64_list']: #'Hyperlink to CommonLII'
        if key in metadata_json_raw.keys():
            metadata_json_raw.pop(key)
        #except:
            #print(f'Unable to remove {key} from metadata_json_raw')

    metadata_json = metadata_json_raw

    #print(f"metadata_json == {metadata_json}")
    
    #if 'judgment' not in metadata_json.keys():
    metadata_content = [{"role": "user", "content": 'Based on the following metadata:' + str(metadata_json)}]

    #print(f"metadata_content == {metadata_content}")

    #Create json direction content

    json_direction = [{"role": "user", "content": 'You will be given questions to answer in JSON form.'}]

    file_for_GPT = image_content + metadata_content + json_direction
    
    #Create answer format
    answers_json = {}

    q_keys = [*questions_json]
    
    if len(df_example.replace('"', '')) > 0:

        try:
            
            if isinstance(df_example, str):
                
                answers_json = json.loads(df_example)

            if isinstance(df_example, dict):
                
                answers_json = df_example

            answers_json_instruction = '\n Return your answer as a JSON object, following this example: ' + json.dumps(answers_json, default = str)
        
        except Exception as e:
            print(f"Example provided but can't produce json to send to GPT.")
            print(e)
    
    if len(answers_json) == 0:
        q_counter = 1
        for q_index in q_keys:
            answers_json.update({f'GPT question {q_counter}: {questions_json[q_index]}': f'Your answer. (The paragraphs, pages or sections from which you obtained your answer)'})
            q_counter += 1

        answers_json_instruction = '\n Respond in the following JSON form: ' + json.dumps(answers_json, default = str) + '\n Every key in your JSON response must contain the relevant question.'
    
    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": json.dumps(questions_json, default = str) + answers_json_instruction}]
    
    #Create messages in one prompt for GPT
    if 'Language choice' in metadata_json.keys():
        language_content = f"The file is written in {metadata_json['Language choice']}."
    else:
        language_content = ''

    intro_for_GPT = [{"role": "developer", "content": system_instruction + language_content}] 
    messages_for_GPT = intro_for_GPT + file_for_GPT + question_for_GPT
    
#   return messages_for_GPT

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model=gpt_model,
            messages=messages_for_GPT, 
            response_format={"type": "json_object"}, 
            temperature = 0.2, 
            top_p = 0.2
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
                                
        answers_dict = json.loads(completion.choices[0].message.content)
        
        #Obtain tokens
        output_tokens = completion.usage.completion_tokens
        
        prompt_tokens = completion.usage.prompt_tokens
        
        #return [answers_dict, output_tokens, prompt_tokens]

        #Check answers

        if check_questions_answers() > 0:
            
            try:
                redacted_output = GPT_answers_check(answers_dict, gpt_model, answers_check_system_instruction)
        
                redacted_answers_dict = redacted_output[0]
        
                redacted_answers_output_tokens = redacted_output[1]
        
                redacted_answers_prompt_tokens = redacted_output[2]
        
                return [redacted_answers_dict, output_tokens + redacted_answers_output_tokens, prompt_tokens + redacted_answers_prompt_tokens]

                print('Answers checked.')
                
            except Exception as e:
    
                print('Answers check failed.')
    
                print(e)
    
                return [answers_dict, output_tokens, prompt_tokens]

        else:

            print('Answers not checked.')
            
            return [answers_dict, output_tokens, prompt_tokens]

    except Exception as error:
        
        print('GPT failed to produce answers.')
        
        for q_index in q_keys:
            
            answers_json.update({q_index: error})
        
        return [answers_json, 0, 0]



# %%
#Define GPT function for each respondent's dataframe, index by judgment then question, with input and output tokens given by GPT itself
#For vision

#The following function DOES NOT check for existence of questions for GPT
    # To so check, active line marked as #*

@st.cache_data(show_spinner = False)
def engage_GPT_b64_json(questions_json, df_example, df_individual, GPT_activation, gpt_model, system_instruction):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # f"Length of first 10 pages in tokens (up to {tokens_cap(gpt_model)} given to GPT)"
        # 'GPT cost estimate (USD excl GST)'
        # 'GPT time estimate (seconds)'
        # GPT questions/answers

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()

    #Check questions for privacy violation
    if check_questions_answers() > 0:

        #Check system instruction
        system_instruction_checked_dict = GPT_system_check(system_instruction, gpt_model, system_instruction_check_system_instruction)

        system_instruction = system_instruction_checked_dict['system_instruction']

        system_instruction_check_output_tokens = system_instruction_checked_dict['system_instruction_check_output_tokens']
    
        system_instruction_check_input_tokens = system_instruction_checked_dict['system_instruction_check_input_tokens']
        
        #Check questions
        questions_checked_dict = GPT_questions_check(questions_json, gpt_model, questions_check_system_instruction)

        questions_json = questions_checked_dict['questions_json']
    
        questions_check_output_tokens = questions_checked_dict['questions_check_output_tokens']
    
        questions_check_input_tokens = questions_checked_dict['questions_check_input_tokens']

        #Add tokens

        questions_check_output_tokens += system_instruction_check_output_tokens
        
        questions_check_input_tokens +=system_instruction_check_input_tokens
        
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
        for key in ['judgment_b64', 'b64_list']:#, 'extracted_text']:
            if key in judgment_json.keys():
                if len(judgment_json[key]) == 0:
                    text_error = True
                    df_individual.loc[judgment_index, 'Note'] = search_error_note
                    print(f"Case/file indexed {judgment_index} not sent to GPT given full text was not scrapped.")
                break

        #Calculate and append number of tokens of judgment, regardless of whether given to GPT
        df_individual.loc[judgment_index, f"Tokens (up to {tokens_cap(gpt_model)} given to GPT)"] = judgment_json['tokens_raw']       

        #Create columns for respondent's GPT cost, time
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = ''
        df_individual.loc[judgment_index, 'GPT time estimate (seconds)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each judgment, gives answers as a string containing a dictionary

        if ((int(GPT_activation) > 0) and (text_error == False)):
            GPT_output_list = GPT_b64_json(questions_json, df_example, judgment_json, gpt_model, system_instruction) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_output_list[0]

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

            q_counter = 1
            for q_index in question_keys:
                #Increases judgment index by 2 to ensure consistency with Excel spreadsheet
                answer = ''
                answers_dict.update({f'GPT question {q_counter}: {questions_json[q_index]}': answer})
                q_counter += 1

            answers_json_instruction = '\n Respond in the following JSON form: ' + json.dumps(answers_dict, default = str)
            
            #Calculate capped judgment tokens

            judgment_capped_tokens = min(judgment_json['tokens_raw'], tokens_cap(gpt_model))

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(json.dumps(questions_json), "cl100k_base")

            #Calculate metadata tokens

            metadata_tokens = 0
            
            metadata_json_for_counting = judgment_json

            for key in ['tokens_raw', 'judgment_b64', 'b64_list']: #['Hyperlink to CommonLII', 'judgment', 'tokens_raw']:
                if key in metadata_json_for_counting.keys():
                    metadata_json_for_counting.pop(key)
                #except:
                    #print(f'Unable to remove {key} from metadata_json_for_counting')        

            #if 'judgment' not in metadata_json_for_counting.keys():
            metadata_tokens = metadata_tokens + num_tokens_from_string(str(metadata_json_for_counting), "cl100k_base")

            #Calculate other instructions' tokens

            system_answers_instructions = system_instruction + 'you will be given questions to answer in JSON form.' + answers_json_instruction

            system_answers_tokens = num_tokens_from_string(system_answers_instructions, "cl100k_base")

            #Calculate number of tokens of answers
            answers_output_tokens = num_tokens_from_string(json.dumps(answers_dict, default = str), "cl100k_base")

            answers_input_tokens = judgment_capped_tokens + questions_tokens + metadata_tokens + system_answers_tokens
            
        #Create GPT question headings and append answers to individual spreadsheets
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

        #If check for questions
        GPT_cost = (answers_output_tokens + questions_check_output_tokens/len(df_individual))*gpt_output_cost(gpt_model) + (answers_input_tokens + questions_check_input_tokens/len(df_individual))*gpt_input_cost(gpt_model)

        #If no check for questions
        #GPT_cost = answers_output_tokens*gpt_output_cost(gpt_model) + answers_input_tokens*gpt_input_cost(gpt_model)

        #Calculate and append GPT cost to individual df
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual
    


# %% [markdown]
# ## Batch mode

# %%
#Create custom id for one judgment_json file

#custom_id should be mnc plus time now

def gpt_get_custom_id(judgment_json):
    
    #Returns time now by default
    time_now = str(datetime.now()).replace(' ', '_').replace(':', '_').replace('.', '_')[8:]

    mnc = ''

    if 'Medium neutral citation' in judgment_json.keys():
        mnc = judgment_json['Medium neutral citation'].replace(' ', '_')
    
    elif 'mnc' in judgment_json.keys():

        mnc = judgment_json['mnc'].replace(' ', '_')

    else:
        mnc = ''

    case_name = ''

    if 'Case name' in judgment_json.keys():
        case_name = judgment_json['Case name'].replace(' ', '_')
    
    elif 'title' in judgment_json.keys():

        case_name = judgment_json['title'].replace(' ', '_')
    
    elif 'File name' in judgment_json.keys():
    
        case_name = judgment_json['File name'].replace(' ', '_')
    
    else:
        case_name = ''
    
    custom_id = f"{time_now}_{case_name}_{mnc}"[0:50]

    return custom_id



# %%
#Define function for creating custom id and one line of jsonl file for batching
#Returns a dictionary of custom id and one line

def gpt_batch_input_id_line(questions_json, df_example, judgment_json, gpt_model, system_instruction):
    #'question_json' variable is a json of questions to GPT
    #'jugdment' variable is a judgment_json   

    #Loop through non-b64 keys
    for key in ['judgment', 'opinions', 'recap_documents', 'extracted_text']:
        if key in judgment_json.keys():      
            judgment_for_GPT = [{"role": "user", "content": judgment_prompt_json(judgment_json, gpt_model)}]
            
            break
            
    else: #If one of b64 key ['judgment_b64', 'b64_list'] in judgment_json.keys():
        
        #Add images to messages to GPT
        image_content_value = [{"type": "text", "text": 'Based on the following images:'}]
        
        for key in ['judgment', 'b64_list']:
            if key in judgment_json.keys():
                for image_b64 in judgment_json[key]:
                    image_message_to_attach = {"type": "image_url", "image_url": {"url": image_b64,}}
                    image_content_value.append(image_message_to_attach)
                    
                break
        
        image_content = [{"role": "user", 
                          "content": image_content_value
                         }
                      ]

        judgment_for_GPT = image_content

    json_direction = [{"role": "user", "content": 'You will be given questions to answer in JSON form.'}]

    #Create answer format
    answers_json = {}

    q_keys = [*questions_json]
    
    if len(df_example.replace('"', '')) > 0:

        try:
            
            if isinstance(df_example, str):
                
                answers_json = json.loads(df_example)

            if isinstance(df_example, dict):
                
                answers_json = df_example
        
            answers_json_instruction = '\n Return your answer as a JSON object, following this example: ' + json.dumps(answers_json, default = str)
        
        except Exception as e:
            print(f"Example provided but can't produce json to send to GPT.")
            print(e)
        
    if len(answers_json) == 0:
        q_counter = 1
        for q_index in q_keys:
            answers_json.update({f'GPT question {q_counter}: {questions_json[q_index]}': f'Your answer. (The paragraphs, pages or sections from which you obtained your answer)'})
            q_counter += 1

        answers_json_instruction = '\n Respond in the following JSON form: ' + json.dumps(answers_json, default = str) + '\n Every key in your JSON response must contain the relevant question.'

    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": json.dumps(questions_json, default = str) + answers_json_instruction}]
    
    #Create messages in one prompt for GPT
    intro_for_GPT = [{"role": "developer", "content": system_instruction}]
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
        for text_key in ['judgment', 'opinions', 'recap_documents', 'extracted_text', 'judgment_b64', 'b64_list']:
            if text_key in judgment_json.keys():

                #Checking if judgment_json[text_key] is np.nan
                if isinstance(judgment_json[text_key], float):
                
                    judgment_json[text_key] = ''
                
                if len(judgment_json[text_key]) == 0:
                    text_error = True
                    df_individual.loc[judgment_index, 'Note'] = search_error_note
                    print(f"Case/file indexed {judgment_index} not sent to GPT given full text was not scrapped.")
                    
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

            #Remove full text/b64
            for text_key in ['judgment', 'opinions', 'recap_documents', 'extracted_text', 'judgment_b64', 'b64_list']:
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

    #print(f"jsonl_for_batching == {jsonl_for_batching}")
    
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

        #st.write(f"st.session_state['df_master'].loc[0, 'Use own account'] == {st.session_state['df_master'].loc[0, 'Use own account']}, st.session_state['df_master'].loc[0, 'Use GPT'] == {st.session_state['df_master'].loc[0, 'Use GPT']}")
        
        if ((st.session_state['df_master'].loc[0, 'Use own account'] == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
        #if ((st.session_state.own_account == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                
            if is_api_key_valid(st.session_state.df_master.loc[0, 'Your GPT API key']) == False:
                
                st.error('Your API key is not valid.')
                
                st.session_state["batch_ready_for_submission"] = False

                st.stop()

            else:
                
                st.session_state["batch_ready_for_submission"] = True

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

            st.write('Please enter a valid email address to receive your requested data.')
            
            batch_email_entry = st.text_input(label = "Your email address (mandatory)", value =  st.session_state['df_master'].loc[0, 'Your email address'])

            if st.button(label = 'CONFIRM your email address', disabled = bool(st.session_state.batch_submitted)):
                
                st.session_state['df_master'].loc[0, 'Your email address'] = batch_email_entry
    
                if '@' not in st.session_state['df_master'].loc[0, 'Your email address']:
                
                    st.error('You must enter a valid email address to receive your requested data.')
                    st.stop()
                else:
                    st.session_state["batch_ready_for_submission"] = True

        #st.write(f'st.session_state["batch_ready_for_submission"] == {st.session_state["batch_ready_for_submission"]}')
        
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
                    if st.session_state['df_master'].loc[0, 'Use own account'] == True:
                    #if st.session_state.own_account == True:
                        
                        API_key = st.session_state.df_master.loc[0, 'Your GPT API key']
        
                    else:
                        
                        API_key = st.secrets["openai"]["gpt_api_key"]
                        
                        st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = st.session_state["judgment_counter_max"]

                    #Check questions for potential privacy violation
                    openai.api_key = API_key

                    if df_master.loc[0, 'Use flagship version of GPT'] == True:
                        gpt_model = flagship_model
                    else:        
                        gpt_model = basic_model

                    #Check system instruction and questions for privacy violation
                    if check_questions_answers() > 0:

                        #Check system instruction
                        system_instruction_checked_dict = GPT_system_check(df_master.loc[0, 'System instruction'], gpt_model, system_instruction_check_system_instruction)
                
                        df_master.loc[0, 'System instruction'] = system_instruction_checked_dict['system_instruction']

                        #Check questions
                        questions_checked_dict = GPT_questions_check(df_master.loc[0, 'Enter your questions for GPT'], gpt_model, questions_check_system_instruction)
    
                        df_master.loc[0, 'Enter your questions for GPT'] = questions_checked_dict['questions_string']
                    
                    #Initiate aws s3
                    #s3_resource = boto3.resource('s3',region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"], aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"])

                    s3_resource = get_aws_s3()
                    
                    #Get a list of all files on s3
                    #bucket = s3_resource.Bucket('lawtodata')
    
                    #Get all_df_masters
                    all_df_masters = aws_df_get(s3_resource, 'all_df_masters.csv')
                    #for obj in bucket.objects.all():
                        #key = obj.key
                        #if key == 'all_df_masters.csv':
                            #body = obj.get()['Body'].read()
                            #all_df_masters = pd.read_csv(BytesIO(body), index_col=0)
                            #break
                            
                    #Add df_master to all_df_masters 
                    all_df_masters = pd.concat([all_df_masters, df_master], ignore_index=True)
    
                    #Upload all_df_masters to aws
                    aws_df_put(s3_resource, all_df_masters, 'all_df_masters.csv')

                    #csv_buffer = StringIO()
                    #all_df_masters.to_csv(csv_buffer)
                    #s3_resource.Object('lawtodata', 'all_df_masters.csv').put(Body=csv_buffer.getvalue())
                                           
                    #Send me an email to let me know
                    send_notification_email(ULTIMATE_RECIPIENT_NAME = st.session_state['df_master'].loc[0, 'Your name'], 
                                            ULTIMATE_RECIPIENT_EMAIL = st.session_state['df_master'].loc[0, 'Your email address'], 
                                            jurisdiction_page = st.session_state['df_master'].loc[0, 'jurisdiction_page']
                                           )

                    #Change session states
                    st.session_state["batch_submitted"] = True
                    st.session_state['need_resetting'] = 1
                    st.session_state["batch_error"] == False
                    st.session_state['error_msg'] = ''
                    
                    st.rerun()
                
                except Exception as e:

                    #Change session states
                    st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound                    
                    st.session_state["batch_submitted"] = False
                    st.session_state["batch_error"] = True
    
                    st.error(search_error_display)
                                    
                    print(traceback.format_exc())
    
                    st.session_state['error_msg'] = traceback.format_exc()

                    st.rerun()



# %% [markdown]
# # GPT run

# %%
#Jurisdiction specific instruction and functions

def gpt_run(jurisdiction_page, df_master):

    if jurisdiction_page == 'pages/HCA.py':
        
        from functions.hca_functions import hca_run
        
        run = copy.copy(hca_run)

    if jurisdiction_page == 'pages/NSW.py':
        
        from nswcaselaw.search import Search
        
        from functions.nsw_functions import nsw_run
        
        run = copy.copy(nsw_run)
    
    if jurisdiction_page == 'pages/FCA.py':
                
        from functions.fca_functions import fca_run
        
        run = copy.copy(fca_run)

    if jurisdiction_page == 'pages/HK.py':
                
        from functions.hk_functions import hk_run, role_content_hk
        
        run = copy.copy(hk_run)

    if jurisdiction_page == 'pages/HKLII.py':
                
        from functions.hklii_functions import hklii_run, role_content_hklii
        
        run = copy.copy(hklii_run)
    
    if jurisdiction_page == 'pages/US.py':
                
        from functions.us_functions import us_run
        
        run = copy.copy(us_run)

    if jurisdiction_page == 'pages/CA.py':
                
        from functions.ca_functions import ca_run
        
        run = copy.copy(ca_run)

    if jurisdiction_page == 'pages/UK.py':
                
        from functions.uk_functions import uk_run
        
        run = copy.copy(uk_run)

    if jurisdiction_page == 'pages/BAILII.py':
                
        from functions.bailii_functions import bailii_run
        
        run = copy.copy(bailii_run)

    if jurisdiction_page == 'pages/AFCA.py':
                
        from functions.afca_functions import afca_run
        
        if streamlit_timezone() == True:

            st.warning('One or more Chrome window may be launched. It must be kept open.')

        run = copy.copy(afca_run)

    if jurisdiction_page == 'pages/ER.py':

        from functions.er_functions import er_run, role_content_er
        
        run = copy.copy(er_run)

    if jurisdiction_page == 'pages/KR.py':

        system_instruction = role_content
                
        from functions.kr_functions import kr_run
        
        run = copy.copy(kr_run)

    if jurisdiction_page == 'pages/SCTA.py':
        
        from functions.scta_functions import scta_run
        
        run = copy.copy(scta_run)

    if jurisdiction_page == 'pages/UKPO.py':
        
        from functions.ukpo_functions import ukpo_run
                
        run = copy.copy(ukpo_run)
    
    df_individual = run(df_master)

    return df_individual



# %% [markdown]
# # GPT batch run

# %%
pages_w_batch = ['pages/HCA.py', 'pages/FCA.py', 'pages/NSW.py', 'pages/HK.py', 'pages/HKLII.py', 'pages/US.py', 'pages/CA.py']


# %%
#Jurisdiction specific instruction and functions

def gpt_batch_input_submit(jurisdiction_page, df_master):

    if jurisdiction_page == 'pages/HCA.py':
        
        from functions.hca_functions import hca_batch
        
        batch =  copy.copy(hca_batch)

    if jurisdiction_page == 'pages/NSW.py':
        
        from nswcaselaw.search import Search

        from functions.nsw_functions import nsw_batch
        
        batch =  copy.copy(nsw_batch)
    
    if jurisdiction_page == 'pages/FCA.py':
                
        from functions.fca_functions import fca_batch
        
        batch = copy.copy(fca_batch)

    if jurisdiction_page == 'pages/HK.py':
                
        from functions.hk_functions import hk_batch, role_content_hk
        
        batch = copy.copy(hk_batch)

    if jurisdiction_page == 'pages/HKLII.py':
                
        from functions.hklii_functions import hklii_batch, role_content_hklii
        
        batch = copy.copy(hklii_batch)
    
    if jurisdiction_page == 'pages/US.py':
                
        from functions.us_functions import us_batch
        
        batch = copy.copy(us_batch)

    if jurisdiction_page == 'pages/CA.py':
                
        from functions.ca_functions import ca_batch

        batch = copy.copy(ca_batch)
    
    batch_record_df_individual = batch(df_master)
    
    return batch_record_df_individual


# %%

