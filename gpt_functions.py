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
import copy

#OpenAI
import openai
import tiktoken

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
#from streamlit.components.v1 import html
import streamlit_ext as ste

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
from common_functions import check_questions_answers

# %% [markdown]
# # gpt-3.5, 4o-mini and 4o

# %%
#Upperbound on the length of questions for GPT

question_characters_bound = 2000

print(f"Questions for GPT are capped at {question_characters_bound} characters.\n")

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

@st.cache_data
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
        
    if gpt_model == "gpt-4o":
        gpt_input_cost = 1/1000000*5

    if gpt_model == "gpt-4o-mini":
        gpt_input_cost = 1/1000000*0.15
    return gpt_input_cost

def gpt_output_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_output_cost = 1/1000000*1.5
        
    if gpt_model == "gpt-4o":
        gpt_output_cost = 1/1000000*15

    if gpt_model == "gpt-4o-mini":
        gpt_output_cost = 1/1000000*0.6
    
    return gpt_output_cost

#As of 2024-06-07, questions are capped at about 1000 characters ~ 250 tokens, role_content/system_instruction is about 115 tokens, json_direction is about 11 tokens, answers_json is about 8 tokens plus 30 tokens per question 

def tokens_cap(gpt_model):
    #This is the global cap for each model, which will be shown to users
    #Leaving 1000 tokens to spare
    
    if gpt_model == "gpt-3.5-turbo-0125":
        
        tokens_cap = int(16385 - 3000) #For GPT-3.5-turbo, token limit covering BOTH input and output is 16385,  while the output limit is 4096.
    
    if gpt_model == "gpt-4o":
        tokens_cap = int(128000 - 3000) #For gpt-4o, token limit covering both BOTH and output is 128000, while the output limit is 4096.

    if gpt_model == "gpt-4o-mini":
        tokens_cap = int(128000 - 3000) #For gpt-4o-mini, token limit covering both BOTH and output is 128000, while the output limit is 4096.

    return tokens_cap

def max_output(gpt_model, messages_for_GPT):

    if gpt_model == "gpt-3.5-turbo-0125":
        
        max_output_tokens = int(16385 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For GPT-3.5-turbo, token limit covering BOTH input and output is 16385,  while the output limit is 4096.
    
    if gpt_model == "gpt-4o":
        
        max_output_tokens = int(128000 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4o, token limit covering both BOTH and output is 128000, while the output limit is 4096.
    
    if gpt_model == "gpt-4o-mini":
        
        max_output_tokens = int(128000 - num_tokens_from_string(str(messages_for_GPT), "cl100k_base")) #For gpt-4o-mini, token limit covering both BOTH and output is 128000, while the output limit is 4096.

    return min(4096, abs(max_output_tokens))
    


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
    
    #Turn judgment to string
    if isinstance(judgment_json["judgment"], list):
        judgment_to_string = '\n'.join(judgment_json["judgment"])
        
    elif isinstance(judgment_json["judgment"], str):
        judgment_to_string = judgment_json["judgment"]
        
    else:
        judgment_to_string = str(judgment_json["judgment"])

    #Truncate judgment if needed
    judgment_content = f'Based on the metadata and judgment in the following JSON: """ {json.dumps(judgment_json, default=str)} """'

    judgment_content_tokens = num_tokens_from_string(judgment_content, "cl100k_base")
    
    if judgment_content_tokens <= tokens_cap(gpt_model):
        
        return judgment_content

    else:
        
        meta_data_len = judgment_content_tokens - num_tokens_from_string(judgment_to_string, "cl100k_base")

        intro_len = num_tokens_from_string('Based on the metadata and judgment in the following JSON: """  """', "cl100k_base")
        
        judgment_chars_capped = int(round((tokens_cap(gpt_model) - meta_data_len - intro_len)*4))
        
        judgment_string_trimmed = judgment_to_string[ :int(judgment_chars_capped/2)] + judgment_to_string[-int(judgment_chars_capped/2): ]

        judgment_json["judgment"] = judgment_string_trimmed     
        
        judgment_content_capped = f'Based on the metadata and judgment in the following JSON:  """ {json.dumps(judgment_json, default=str)} """'
        
        return judgment_content_capped
        


# %%
#Check questions for potential privacy infringement

questions_check_system_instruction = """
You are a compliance officer helping a human ethics committee to ensure that no personally identifiable information will be exposed. 
You will be given questions to check in JSON form. Please provide labels for these questions based only on information contained in the JSON.
Where a question seeks information about a person's birthday or address, you label "1". If a question does not seek such information, you label "0". If you are not sure, label "unclear".
"""

#More general below
#questions_check_system_instruction = """
#You are a compliance officer helping a human ethics committee to ensure that no personally identifiable information will be exposed. 
#You will be given questions to check in JSON form. 
#Based only on information contained in the JSON, please check each question for whether it seeks a person's birthday, address, or other personally identifiable information. 
#Where a question indeed seeks personally identifiable information, you label "1". 
#Where a question does not seek personally identifiable information, you label "0". 
#If you are not sure, label "unclear".
#"""

# %%
#Check questions for potential privacy infringement

@st.cache_data
def GPT_questions_check(questions_json, gpt_model, questions_check_system_instruction):
    #'question_json' variable is a json of questions to GPT
    #'jugdment' variable is a judgment_json   

    #judgment_for_GPT = [{"role": "user", "content": judgment_prompt_json(judgment_json, gpt_model)}]

    json_direction = [{"role": "user", "content": 'Label the following questions in JSON form.'}]

    #Create answer format
    
    q_keys = [*questions_json]
    
    labels_json = {}
    
    for q_index in q_keys:
        labels_json.update({q_index: 'Your label for the question with index ' + q_index})
    
    #Create questions, which include the answer format
    
    question_to_check = [{"role": "user", "content": json.dumps(questions_json, default = str) + ' Return labels in the following JSON form: ' + json.dumps(labels_json, default = str)}]
    
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
            temperature = 0.2, 
            top_p = 0.2
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
            labels_json[q_index] = error
        
        return [labels_json, 0, 0]



# %%
#Function to replace unchecked questions with checked questions
def checked_questions_json(questions_json, gpt_labels_output):
    
    checked_questions_json = questions_json

    for q_key in gpt_labels_output[0]:
        
        if str(gpt_labels_output[0][q_key]) == '1':
            
            checked_questions_json[q_key] = 'Say "Potential privacy violation" only.'
    
    return checked_questions_json
    


# %%
#Check questions for potential privacy infringement

answers_check_system_instruction = """
You are a compliance officer helping an academic researcher to redact personally identifiable information. 
You will be given text to check in JSON form. Please check the text based only on information contained in the JSON. 
Where any part of the text contains a birthday or an address, you replace that part with "[redacted]". 
You then return the remainder of the text unredacted.
"""

#If more general below
#answers_check_system_instruction = """
#You are a compliance officer helping an academic researcher to redact personally identifiable information. 
#You will be given text to check in JSON form. 
#Based only on information contained in the JSON, please check each text for whether it contains a person's birthday, address, or other personally identifiable information. 
#Where any part of the text contains personally identifiable information, you replace that part with "[redacted]". 
#You then return the remainder of the text unredacted.
#"""


# %%
#Check answers_to_check_json for potential privacy infringement

@st.cache_data
def GPT_answers_check(answers_to_check_json, gpt_model, answers_check_system_instruction):
    #'question_json' variable is a json of answers_to_check_json to GPT
    #'jugdment' variable is a judgment_json   

    #judgment_for_GPT = [{"role": "user", "content": judgment_prompt_json(judgment_json, gpt_model)}]

    json_direction = [{"role": "user", "content": 'Check the following text in JSON form.'}]

    #Create answer format
    
    q_keys = [*answers_to_check_json]
    
    redacted_answers_json = {}
    
    for q_index in q_keys:
        
        redacted_answers_json.update({q_index: 'Your answer for the question with index ' + q_index})
    
    #Create answers_to_check_json, which include the answer format
    
    question_to_check = [{"role": "user", "content": json.dumps(answers_to_check_json, default = str) + ' Answer in the following JSON form: ' + json.dumps(redacted_answers_json, default = str)}]
    
    #Create messages in one prompt for GPT
    
    intro_for_GPT = [{"role": "system", "content": answers_check_system_instruction}]
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
            temperature = 0.2, 
            top_p = 0.2
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        #To obtain a json directly, use below
        answers_dict = json.loads(completion.choices[0].message.content)
        
        #Obtain tokens
        output_tokens = completion.usage.completion_tokens
        
        prompt_tokens = completion.usage.prompt_tokens
        
        return [answers_dict, output_tokens, prompt_tokens]

    except Exception as error:
        
        for q_index in q_keys:
            redacted_answers_json[q_index] = error
        
        return [redacted_answers_json, 0, 0]



# %%
#For modern judgments, define system role content for GPT
role_content = "You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from specific paragraphs, pages or sections of the judgment or metadata, include a reference to those paragraphs, pages or sections. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write 'answer not found'. "

#safeguards = "Where you are asked to identify a party's birthday, address, or other personally identifiable information, answer 'potential privacy violation'. " 

#role_content = role_content_raw# + safeguards

#role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a public judgment. You will be provided with the judgment and metadata in JSON form. Please answer questions based only on information contained in the judgment and metadata. Where your answer comes from a part of the judgment or metadata, include a reference to that part of the judgment or metadata. If you cannot answer the questions based on the judgment or metadata, do not make up information, but instead write "answer not found". '

# %%
#Define GPT answer function for answers in json form, YES TOKENS
#IN USE

@st.cache_data
def GPT_json(questions_json, judgment_json, gpt_model, system_instruction):
    #'question_json' variable is a json of questions to GPT
    #'jugdment' variable is a judgment_json   

    judgment_for_GPT = [{"role": "user", "content": judgment_prompt_json(judgment_json, gpt_model)}]

    json_direction = [{"role": "user", "content": 'You will be given questions to answer in JSON form.'}]

    #Create answer format
    
    q_keys = [*questions_json]
    
    answers_json = {}
    
    for q_index in q_keys:
        answers_json.update({q_index: f'Your answer to the question with index {q_index}. The paragraphs, pages or sections from which you obtained your answer.'})
    
    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": json.dumps(questions_json, default = str) + ' Give responses in the following JSON form: ' + json.dumps(answers_json, default = str)}]
    
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
            temperature = 0.2, 
            top_p = 0.2
        )
        
#        return completion.choices[0].message.content #This gives answers as a string containing a dictionary
        
        #To obtain a json directly, use below
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
            
            answers_json[q_index] = error
        
        return [answers_json, 0, 0]



# %%
#Define GPT function for each respondent's dataframe, index by judgment then question, with input and output tokens given by GPT itself
#IN USE

#The following function DOES NOT check for existence of questions for GPT
    # To so check, active line marked as #*

@st.cache_data
def engage_GPT_json(questions_json, df_individual, GPT_activation, gpt_model, system_instruction):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # f"Judgment length in tokens (up to {tokens_cap(gpt_model)} given to GPT)"
        # 'GPT cost estimate (USD excl GST)'
        # 'GPT time estimate (seconds)'
        # GPT questions/answers

    #os.environ["OPENAI_API_KEY"] = API_key

    #openai.api_key = API_key
    
    #client = OpenAI()

    #Make a copy of questions for making headings later
    unchecked_questions_json = questions_json.copy()

    #Check questions for privacy violation

    if check_questions_answers() > 0:
    
        try:
    
            labels_output = GPT_questions_check(questions_json, gpt_model, questions_check_system_instruction)
    
            labels_output_tokens = labels_output[1]
    
            labels_prompt_tokens = labels_output[2]
        
            questions_json = checked_questions_json(questions_json, labels_output)

            print('Questions checked.')
    
        except Exception as e:
            
            print('Questions check failed.')
            
            print(e)
    
            labels_output_tokens = 0
            
            labels_prompt_tokens = 0

    else:

        print('Questions not checked.')
        
        labels_output_tokens = 0
        
        labels_prompt_tokens = 0

    #Process questions
    
    question_keys = [*questions_json]
    
    for judgment_index in df_individual.index:
        
        judgment_json = df_individual.to_dict('index')[judgment_index]
        
        #Calculate and append number of tokens of judgment, regardless of whether given to GPT
        judgment_tokens = num_tokens_from_string(str(judgment_json), "cl100k_base")
        df_individual.loc[judgment_index, f"Judgment length in tokens (up to {tokens_cap(gpt_model)} given to GPT)"] = judgment_tokens       

        #Indicate whether judgment truncated
        
        df_individual.loc[judgment_index, "Judgment truncated (if given to GPT)?"] = ''       
        
        if judgment_tokens <= tokens_cap(gpt_model):
            
            df_individual.loc[judgment_index, "Judgment truncated (if given to GPT)?"] = 'No'
            
        else:
            
            df_individual.loc[judgment_index, "Judgment truncated (if given to GPT)?"] = 'Yes'

        #Create columns for respondent's GPT cost, time
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = ''
        df_individual.loc[judgment_index, 'GPT time estimate (seconds)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each judgment, gives answers as a string containing a dictionary

        if int(GPT_activation) > 0:
            GPT_output_list = GPT_json(questions_json, judgment_json, gpt_model, system_instruction) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_output_list[0]

            #Calculate and append GPT finish time and time difference to individual df
            GPT_finish_time = datetime.now()
            
            GPT_time_difference = GPT_finish_time - GPT_start_time
    
            df_individual.loc[judgment_index, 'GPT time estimate (seconds)'] = GPT_time_difference.total_seconds()        

        else:
            answers_dict = {}    
            for q_index in question_keys:
                #Increases judgment index by 2 to ensure consistency with Excel spreadsheet
                answer = 'Placeholder answer for ' + ' judgment ' + str(int(judgment_index) + 2) + ' ' + str(q_index)
                answers_dict.update({q_index: answer})
            
            #Own calculation of GPT costs for Placeholder answer fors

            #Calculate capped judgment tokens

            judgment_capped_tokens = num_tokens_from_string(judgment_prompt_json(judgment_json, gpt_model), "cl100k_base")

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(json.dumps(questions_json, default = str), "cl100k_base")

            #Calculate other instructions' tokens

            other_instructions = system_instruction + 'you will be given questions to answer in JSON form.' + ' Give responses in the following JSON form: '

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. The paragraph or page numbers in the judgment, or sections of the metadata from which you obtained your answer. ", "cl100k_base")

            #Calculate number of tokens of answers
            answers_tokens = num_tokens_from_string(str(answers_dict), "cl100k_base")

            input_tokens = judgment_capped_tokens + questions_tokens + other_tokens
            
            GPT_output_list = [answers_dict, answers_tokens, input_tokens]

    	#Create GPT question headings, append answers to individual spreadsheets, and remove template/erroneous answers

        for question_index in question_keys:

            #If not checking questions
            #question_heading = question_index + ': ' + questions_json[question_index]

            #If checking questions
            question_heading = question_index + ': ' + unchecked_questions_json[question_index]
            
            df_individual.loc[judgment_index, question_heading] = answers_dict[question_index]
            
            if 'Your answer to the question with index' in str(answers_dict[question_index]):
                
                df_individual.loc[judgment_index, question_heading] = 'Error for ' + ' judgment ' + str(int(judgment_index) + 2) + ' ' + str(question_index) + ' Please try again.'

        #Calculate GPT costs

        #If no check for questions
        #GPT_cost = GPT_output_list[1]*gpt_output_cost(gpt_model) + GPT_output_list[2]*gpt_input_cost(gpt_model)

        #If check for questions
        GPT_cost = (GPT_output_list[1] + labels_output_tokens/len(df_individual))*gpt_output_cost(gpt_model) + (GPT_output_list[2] + labels_prompt_tokens/len(df_individual))*gpt_input_cost(gpt_model)

        #Calculate and append GPT cost to individual df
        df_individual.loc[judgment_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual



# %% [markdown]
# # Vision

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
