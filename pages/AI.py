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
import matplotlib.pyplot as plt
import re
import datetime
from datetime import date
from datetime import datetime
from dateutil import parser
from dateutil.relativedelta import *
from datetime import datetime, timedelta
import sys
import pause
import os
import io
import openpyxl

#Streamlit
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste

#OpenAI
import openai
#from openai import OpenAI
import tiktoken

#PandasAI
#from dotenv import load _dotenv
from pandasai import SmartDataframe
from pandasai import Agent
from pandasai.llm import BambooLLM
from pandasai.llm.openai import OpenAI
import pandasai as pai
from pandasai.responses.streamlit_response import StreamlitResponse
from pandasai.helpers.openai_info import get_openai_callback as pandasai_get_openai_callback

#langchain
from langchain_community.chat_models import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType
#from langchain_openai import OpenAI
from langchain_community.callbacks import get_openai_callback as langchain_get_openai_callback

#Excel
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb


# %%
#Whether users are allowed to use their account
from extra_functions import own_account_allowed

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

# %%
#Title of webpage
st.set_page_config(
   page_title="Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#today and time
today_in_nums = str(datetime.now())[0:10]


# %%
#Create function for saving responses and results
def convert_df_to_json(df):
    return df.to_json(orient = 'split', compression = 'infer')

def convert_df_to_csv(df):
   return df.to_csv(index=False).encode('utf-8')

#Excel metadata
excel_author = 'The Empirical Legal Research Kickstarter'
excel_description = 'A 2022 University of Sydney Research Accelerator (SOAR) Prize partially funded the development of the Empirical Legal Research Kickstarter, which generated this spreadsheet.'

def convert_df_to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'strings_to_urls': False}})
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    workbook = writer.book
    workbook.set_properties({"author": excel_author, "comments": excel_description})
    worksheet = writer.sheets['Sheet1']
#    format1 = workbook.add_format({'num_format': '0.00'}) 
    worksheet.set_column('A:A', None)#, format1)  
    writer.save()
    processed_data = output.getvalue()
    return processed_data


# %% [markdown]
# # AI model and context

# %% [markdown]
# ## Applicable to all AIs

# %%
#Check validity of API key

def is_api_key_valid(key_to_check):
    openai.api_key = key_to_check
    
    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": "user", "content": 'Who is Taylor Swift?'}], 
            max_tokens = 5
        )
    except:
        return False
    else:
        return True


# %%
#Initialize default GPT settings

if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

#Initialize key validity check

if 'gpt_api_key_validity' not in st.session_state:
    st.session_state['gpt_api_key_validity'] = False


# %%
#Default choice of AI

default_ai = 'GPT'
#default_ai = 'BambooLLM'
#default_ai = 'LangChain'

if 'ai_choice' not in st.session_state:
    st.session_state['ai_choice'] = default_ai

ai_list_raw = ['GPT'] #, 'BambooLLM'] 

#Add LangChain
#ai_list_raw.append('LangChain')

#Add BambooLLM
#ai_list_raw.append('BambooLLM')

default_ai_index = ai_list_raw.index(default_ai)


# %%
#The choice of model function

def llm_setting(ai_choice, key, gpt_model_choice):

    if ai_choice == 'GPT': #llm.type == 'GPT':
        if gpt_model_choice == 'gpt-4-turbo':
            gpt_model_choice = 'gpt-4-0125-preview'
        
        llm = OpenAI(api_token=key, model = gpt_model_choice)

    if ai_choice == 'BambooLLM': #llm.type == 'Bamboollm':

        llm = BambooLLM(api_key = st.secrets["pandasai"]["bamboollm_api_key"])
    
    if ai_choice == 'LangChain': #llm.type == 'Bamboollm':

        llm = ChatOpenAI(model_name = gpt_model_choice, temperature=0.2, openai_api_key=key, streaming = False)

    return llm

def ai_model_printing(ai_choice, gpt_model_choice):
#NOT in use
    
    output = ai_choice

    if ai_choice == 'GPT':
        
        output = f'GPT model {gpt_model_choice}'

    return output



# %%
#Agent description

#default_agent_description = """You are a data analyst. Your main goal is to help clean, analyse and visualise data. You will be given a spreadsheet of data. 
#You will be given questions or instructions about the spreadsheet.  
#"""

default_agent_description = 'You are a data analyst. Your main goal is to help clean, analyse and visualise data. You will be given a spreadsheet of data. You will be given questions or instructions about the spreadsheet. You think step by step to answer these questions or instructions.'
#

# %%
def agent(ai_choice, key, gpt_model_choice, instructions_bound, df):

    response = ''
    
    llm = llm_setting(ai_choice, key, gpt_model_choice)
    
    if ai_choice in {'GPT', 'BambooLLM'}:            
        
        agent = Agent(df, 
                      config={"llm": llm, 
                              "verbose": True, 
                              "response_parser": StreamlitResponse, 
                              'enable_cache': True, 
                              'use_error_correction_framework': True, 
                              'max_retries': 10
                             }, 
                      memory_size = instructions_bound, 
                      description = pandasai_agent_description
                     )
        #agent = SmartDataframe(st.session_state.edited_df, config={"llm": llm, "verbose": True, "response_parser": StreamlitResponse, 'enable_cache': True}, description = pandasai_agent_description)
        
    if ai_choice == 'LangChain':

        agent_kwargs={"system_message": default_agent_description, #+ langchain_pandasai_further_instructions, 
                    "handle_parsing_errors": True,
                      'streaming' : False, 
                     }
        
        agent =  create_pandas_dataframe_agent(llm, df, verbose=True, agent_type=AgentType.OPENAI_FUNCTIONS, agent_executor_kwargs= agent_kwargs)

    return agent
    


# %%
def agent_alt(llm, ai_choice, instructions_bound, df):

    response = ''
    
    #llm = llm_setting(ai_choice, key, gpt_model_choice)
    
    if ai_choice in {'GPT', 'BambooLLM'}:            
        
        agent = Agent(df, 
                      config={"llm": llm, 
                              "verbose": True, 
                              "response_parser": StreamlitResponse, 
                              'enable_cache': True, 
                              'use_error_correction_framework': True, 
                              'max_retries': 10
                             }, 
                      memory_size = instructions_bound, 
                      description = pandasai_agent_description
                     )
        #agent = SmartDataframe(st.session_state.edited_df, config={"llm": llm, "verbose": True, "response_parser": StreamlitResponse, 'enable_cache': True}, description = pandasai_agent_description)
        
    if ai_choice == 'LangChain':

        agent_kwargs={"system_message": default_agent_description, #+ langchain_pandasai_further_instructions, 
                    "handle_parsing_errors": True,
                      'streaming' : False, 
                     }
        
        agent =  create_pandas_dataframe_agent(llm, df, verbose=True, agent_type=AgentType.OPENAI_FUNCTIONS, agent_executor_kwargs= agent_kwargs)

    return agent
    


# %%
#AI model descript
#NOT in use

def ai_model_description(ai_choice):
    
    model_description = ''
    
    if ai_choice == 'GPT': #llm.type == 'GPT':
    
        model_description = "GPT model gpt-3.5-turbo-0125 is selected by default. This model can explain its reasoning."
    
    if ai_choice == 'BambooLLM': #llm.type == 'Bamboollm':
    
        model_description = 'BambooLLM is selected by default. This model is developed by PandasAI with data analysis in mind (see https://docs.pandas-ai.com/en/stable/).'

    return model_description



# %% [markdown]
# ## Pandas AI

# %%
#Agent description

#default_agent_description = """You are a data analyst. Your main goal is to help clean, analyse and visualise data. You will be given a spreadsheet of data. 
#You will be given questions or instructions about the spreadsheet.  
#"""

pandasai_further_instructions = """

The columns starting with "GPT question" were previously entered by you. These columns likely have the information you need.

If you need to use any modules to execute a code, import such modules first. 

If you are asked to visualise your answer, provide the code for visualisation using Matplotlib. 

You must not remove the columns entitiled "Case name" and "Medium neutral citation" from the spreadsheet. 
"""

#If there are values which are "nonetype" objects, you ignore such values first. 
#If there are values which are "list" objects, you convert such values to "string" objects first. 

#visualisation = ' Everytime you are given a question or an instruction, try to provide the code to visualise your answer using Matplotlib.'

pandasai_agent_description = default_agent_description + pandasai_further_instructions
#If want to minimize technicality
#pandasai_agent_description = 'You are a data analyst. Your main goal is to help non-technical users to clean, analyse and visualise data. You will be given a spreadsheet of data. Each column starting with "GPT question" was previously entered by you. You will be given questions or instructions about the spreadsheet.'

#Common errors:
#Value type <class 'list'> must match with type dataframe

# %%

def pandasai_ask():
    with pandasai_get_openai_callback() as cb, st.spinner("Running..."):

        #Get response and keep in session state

        response = agent.chat(prompt)
        st.session_state.response = response
    
        #Show response
        st.subheader(f'{st.session_state.ai_choice} Response')
        st.caption('To download, search within or maximise any spreadsheet produced, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')
    
        #st.write('*If you see an error, please modify your instructions or press :red[RESET] below and try again.*') # or :red[RESET] the AI.')
    
        if agent.last_error is not None:
            st.error(response)
        else:
            st.write(response)
        
        #Show any figure generated
        if plt.get_fignums():
            try:
                st.write('**Visualisation**')
                fig_to_plot = plt.gcf()
                st.pyplot(fig = fig_to_plot)
    
                #Enable downloading
                pdf_to_download = io.BytesIO()
                png_to_download = io.BytesIO()
                
                plt.savefig(pdf_to_download, bbox_inches='tight', format = 'pdf')
                
                pdf_button = ste.download_button(
                   label="DOWNLOAD the chart as a PDF",
                   data=pdf_to_download,
                   file_name='chart.pdf',
                   mime="image/pdf"
                )
    
                plt.savefig(png_to_download, bbox_inches='tight', format = 'png')
                
                png_button = ste.download_button(
                   label="DOWNLOAD the chart as a PNG",
                   data=png_to_download,
                   file_name='chart.png',
                   mime="image/png"
                )
    
            except Exception as e:
                print('An error with visualisation has occured.')
                print(e)
    
        #For displaying logs
        #st.subheader('Logs')
        #df_logs = agent.logs
        #st.dataframe(df_logs)
                
        #Display cost and tokens
        response_cost = cb.total_cost
        response_tokens = cb.total_tokens
        
        #Keep record of response, cost and tokens
        st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": response_cost, "tokens": response_tokens,   "role": "assistant", "content": response})
    
        #Explanations
        if st.session_state.explain_status is True:
    
            explanation = agent.explain()
            st.write('**Explanation**')
            st.write(explanation)
    
            #Display cost and tokens
            explanation_cost = cb.total_cost - response_cost
            explanation_tokens = cb.total_tokens - response_tokens
                
            #Keep record of explanation
            st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": explanation_cost, "tokens": explanation_tokens,   "role": "assistant", "content": explanation})
    
            try:
                code = agent.generate_code(prompt)
                
                st.write('**Code**')
                st.code(code)
    
                #Display cost and tokens
                code_cost = cb.total_cost - response_cost - explanation_cost
                code_tokens = cb.total_tokens - response_tokens  - explanation_tokens
    
                #Keep record of code
                st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": code_cost, "tokens": code_tokens,   "role": "assistant", "content": code})
            
            except Exception as e:
                st.warning('No code generated.')
                print(e)
    
        #Display tokens and costs
        total_cost_tokens = f'(This response costed USD $ {round(cb.total_cost, 5)} and totalled {cb.total_tokens} tokens.)'
        st.write(total_cost_tokens)
        st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": float(0), "tokens": float(0),   "role": "assistant", "content": total_cost_tokens})
          


# %% [markdown]
# ## LangChain

# %%
#Got some ideas from https://dev.to/ngonidzashe/chat-with-your-csv-visualize-your-data-with-langchain-and-streamlit-ej7

langchain_further_instructions = """

If you need to use any modules to execute a code, import such modules first. 

Your output should be in JSON form with three fields: "text", "dataframe" and "code". These are the only possible fields.

If your output includes a table, format the table as a Pandas dataframe, and then place the dataframe in the "dataframe" field. Specifcially: {"dataframe": the Pandas dataframe from your ouput}.

If your output includes a code,  provide the code in the "code" field. Specifcially: {"code": the code from your output}.

Any other part of your output should be placed in the "text" field. Specifically: {"text": anything that is not a dataframe or a code}.

If you do not know how to answer the questions or instructions given, write {"text": "Answer not found."}.

You must not remove the columns entitiled "Case name" and "Medium neutral citation" from the spreadsheet. 

The questions or instructions are as follows: 
"""

#Return all output as a string.


# %%
def langchain_write(response_json):
    #if "text" in response_json:

    if "text" in response_json:
    
        if response_json["text"]:
            
            st.write(response_json["text"])
    
    if "dataframe" in response_json:
        
        if response_json["dataframe"]:
        
            st.dataframe(response_json["dataframe"])

    if "code" in response_json:
        
        if response_json["code"]:

            if st.session_state.explain_status == True:
            
                    st.write("**Code**")
                
                    st.code(response_json["code"])



# %%
#Langchain ask function

def langchain_ask():
    with langchain_get_openai_callback() as cb, st.spinner("Running..."):

        prompt_to_process = langchain_further_instructions + prompt

        if st.session_state.explain_status == True:
            
            prompt_to_process = prompt_to_process + ' Explain your answer. '

        response = agent.invoke(prompt_to_process)

        #Keep record of tokens and costs
        cost_tokens = f'(Cost: USD $ {round(cb.total_cost, 5)} Tokens: {cb.total_tokens})'

        st.subheader(f'{st.session_state.ai_choice} Response')

        #st.session_state.response = response.__str__()

        try:

            response_json = json.loads(response["output"].__str__())

            st.session_state.response_json = response_json

            langchain_write(response_json)

            st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": cb.total_cost, "tokens": cb.total_tokens,   "role": "assistant", "content": response_json})

            #st.success('Converted to JSON successfully.')
            
        except:
            #response_json_manual = '{"text": "placeholder"}'
            #response_json = json.loads(response_json_manual)
            #response_json['text'] = response["output"]
            #st.success('Manually converted to JSON')
            #st.write(response["output"])

            st.warning('An error has occured. Please try again.')

            #st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": cb.total_cost, "tokens": cb.total_tokens,   "role": "assistant", "content": response["output"]})

        
        #st.write('*If you see an error, please modify your instructions or press :red[RESET] below and try again.*') # or :red[RESET] the AI.')
    
        #Display tokens and costs
        st.write(cost_tokens)


# %% [markdown]
# # Streamlit form, functions and parameters

# %% [markdown]
# ## Function definitions

# %%
#Reverse hyperlink display

def link_heading_picker(df):
    y = ''
    for x in df.columns:
        if 'Hyperlink' in str(x):
            y = x
    return y

def reverse_link(x):
    value = str(x).replace('=HYPERLINK("', '').replace('")', '')
    return value

def convert_links_column(df):
    new_df = df.copy()
    
    link_header = link_heading_picker(df)
    new_df[link_header] = df[link_header].apply(reverse_link)

    return new_df
    


# %%
# For NSW, function for columns which are lists to strings:

list_columns = ['Catchwords', 'Legislation cited', 'Cases cited', 'Texts cited', 'Parties', 'Representation', 'Decision under appeal'] 

#'Decision under appeal' is a dictionary but the values of some keys are lists

def nsw_df_list_columns(df):
    df_new = df.copy()

    for heading in list_columns:
        if heading in df.columns:
            df_new[heading] = df[heading].astype(str)

    return df_new


# %%
def clear_cache_except_validation():
    keys = list(st.session_state.keys())
    for key in keys:
        if key != 'gpt_api_key_validity': #Remove this line if wants to clear key validation as well
            st.session_state.pop(key)


# %%
def clear_most_cache():
    keys = list(st.session_state.keys())
    #These are the keys to KEEP upon clearing
    for key_to_keep in ['gpt_api_key_validity', 'messages', 'df_uploaded_key', 'page_from']: 
        try:
            keys.remove('key_to_keep')
        except:
            print(f"No {'key_to_keep'} in session state.")

    for key in keys:
        st.session_state.pop(key)


# %% [markdown]
# ## Initialize session states

# %%
#Initialize default values

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

#Initalize page_from:
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

#Initalize df_individual_output:
if 'df_master' not in st.session_state:

    st.session_state['df_master'] = []

#Initalize df_individual_output:
if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = []

#Initalize df_uploaded:
if 'df_uploaded' not in st.session_state:

    st.session_state['df_uploaded'] = []

#Initalize df_uploaded_key
if "df_uploaded_key" not in st.session_state:
    st.session_state["df_uploaded_key"] = 0

#Initalize df_produced:
if 'df_produced' not in st.session_state:

    st.session_state['df_produced'] = []

#Initalize df_to_analyse:
if 'df_to_analyse' not in st.session_state:

    st.session_state['df_to_analyse'] = []

#Initalize edited_df:
if 'edited_df' not in st.session_state:

    st.session_state['edited_df'] = []

#Initialize default instructions bound

default_instructions_bound = 10

print(f"The default maximum number of instructions per thread is {default_instructions_bound}.\n")

#Initialize instructions cap

if 'instructions_bound' not in st.session_state:
    st.session_state['instructions_bound'] = default_instructions_bound

#Initialize instructions counter

if 'instruction_left' not in st.session_state:

    st.session_state["instruction_left"] = default_instructions_bound

#Initialize default show code status

if 'explain_status' not in st.session_state:
    st.session_state["explain_status"] = False

#Initialize default own account status

if 'own_account' not in st.session_state:
    st.session_state['own_account'] = False

#Initilize default gpt model

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-3.5-turbo-0125"

#Initialize default gpt enhacement status

if 'gpt_enhancement_entry' not in st.session_state:
    st.session_state["gpt_enhancement_entry"] = False

#Initialize responses

#For pandas ai
if 'response' not in st.session_state:
    st.session_state["response"] = {}

#For langchain
if 'response_json' not in st.session_state:
    st.session_state["response_json"] = {}

#initialize prompt
if 'prompt' not in st.session_state:
    st.session_state["prompt"] = ''

#Initialize clarifyng questions and answers

if 'clarifying_questions' not in st.session_state:
    st.session_state["clarifying_questions"] = ['', '', '']

if 'clarifying_answers' not in st.session_state:
    st.session_state["clarifying_answers"] = ['', '', '']

#Initialize enhanced prompt
if 'prompt_prefill' not in st.session_state:
    st.session_state["prompt_prefill"] = ''

#Initialize clarifying questions and answers status
if 'q_and_a_provided' not in st.session_state:
    st.session_state["q_and_a_provided"] = 0

#Initialize clarifying questions and answers toggle
if 'q_and_a_toggle' not in st.session_state:
    st.session_state["q_and_a_toggle"] = False

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

# %% [markdown]
# ## Form before choosing AI

# %%
if st.button('RETURN to previous page'):

    st.switch_page(st.session_state.page_from)

st.header("You have chosen to :blue[analyse your spreadsheet].")

#Open spreadsheet and personal details
if len(st.session_state.df_individual_output) > 0:

    st.success('Your spreadsheet has been imported. Please scroll down.')

else: #if len(st.session_state.df_individual_output) == 0:

    st.markdown("""**:green[Please upload a spreadsheet.]** Supported formats: CSV, XLSX, JSON.""")
    
    uploaded_file = st.file_uploader(label = "You may upload a spreadsheet generated by the Empirical Legal Research Kickstarter. The CSV format is preferred.", 
                                     type=['csv', 'xlsx', 'json'], 
                                     accept_multiple_files=False, 
                                     key = st.session_state["df_uploaded_key"]
                                    )

    if uploaded_file:
        
        #Get uploaded file extension
        extension = uploaded_file.name.split('.')[-1].lower()
        
        if extension == 'csv':
            df_uploaded = pd.read_csv(uploaded_file)
    
        if extension == 'xlsx':
            df_uploaded = pd.read_excel(uploaded_file)
    
        if extension == 'json':
            df_uploaded = pd.read_json(uploaded_file, orient= 'split')

        st.session_state.df_uploaded = df_uploaded
        
        st.success('Your spreadsheet has been imported. Please scroll down.')


# %% [markdown]
# ## Choice of AI and GPT account

# %%

if len(ai_list_raw) > 1:

    st.subheader('Choose an AI')

    st.markdown("""Please choose an AI to help with data cleaning, analysis and visualisation.
    """)
    
    ai_choice = st.selectbox(label = f'{default_ai} is selected by default.', options = ai_list_raw, index=default_ai_index)
    
    if ai_choice != st.session_state.ai_choice:
        #pai.clear_cache()
        st.session_state['ai_choice'] = ai_choice
        st.rerun()
        
    st.markdown("""
    GPT can be interactive. LangChain is more agile but can't produce charts.
""")
# BambooLLM is developed for data analysis (see https://docs.pandas-ai.com/en/stable/).
    

    if st.toggle(f'See the instruction given to {st.session_state.ai_choice}'):
        
        st.write(f"*{default_agent_description}*")

else:
    st.session_state.ai_choice = 'GPT'

#if st.session_state.ai_choice in {'GPT', 'BambooLLM'}:

if own_account_allowed() > 0:

    if st.session_state.ai_choice != 'BambooLLM':
    
        st.subheader(':orange[Enhance program capabilities]')
        
        st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or increase the maximum nunber of instructions to process? You can do so with your own GPT account.
        """)
        
        own_account_entry = st.toggle('Use my own GPT account')
        
        if own_account_entry:
            
            st.session_state["own_account"] = True
        
            st.markdown("""**:green[Please enter your name, email address and API key.]** You can sign up for a GPT account and pay for your own usage at https://platform.openai.com/signup. You can then find your API key at https://platform.openai.com/api-keys.
""")
                
            name_entry = st.text_input(label = "Your name", value = st.session_state.name_entry)
    
            st.session_state['name_entry'] = name_entry
            
            email_entry = st.text_input(label = "Your email address", value = st.session_state.email_entry)
            
            gpt_api_key_entry = st.text_input(label = "Your GPT API key (mandatory)", value = st.session_state.gpt_api_key_entry)
            
            valdity_check = st.button('VALIDATE your API key')
        
            if valdity_check:
                
                api_key_valid = is_api_key_valid(gpt_api_key_entry)
                        
                if api_key_valid == False:
                    st.session_state['gpt_api_key_validity'] = False
                    st.error('Your API key is not valid.')
                    
                else:
                    st.session_state['gpt_api_key_validity'] = True
                    st.success('Your API key is valid.')
        
            st.markdown("""**:green[You can use the latest version of GPT model (gpt-4-turbo),]** which is :red[20 times more expensive, per character] than the default model (gpt-3.5-turbo) which you can use for free.""")  
            
            gpt_enhancement_entry = st.checkbox('Use the latest GPT model', value = False)
        
            st.caption('For more on pricing for different GPT models, please see https://openai.com/api/pricing.')
            
            if gpt_enhancement_entry == True:
                #Reset AI first
                pai.clear_cache()
            
                st.session_state.gpt_model = "gpt-4-turbo"
                st.session_state.gpt_enhancement_entry = True
    
            else:
                #Reset AI first
                pai.clear_cache()
                
                st.session_state.gpt_model = "gpt-3.5-turbo-0125"
                st.session_state.gpt_enhancement_entry = False
            
            st.write(f'**:green[You can remove the cap on the number of instructions to process.]** The default cap is {default_instructions_bound}.')
                
            drop_instructions_bound = st.button('REMOVE the cap on the number of instructions')
        
            if drop_instructions_bound:
        
                st.session_state.instructions_bound = 999
                st.session_state.instruction_left = 999
        
            #st.session_state.instruction_left = st.session_state.instructions_bound
        
        else:
            st.session_state["own_account"] = False
        
            st.session_state.gpt_model = "gpt-3.5-turbo-0125"
        
            st.session_state.instructions_bound = default_instructions_bound
        
            st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]
            
            print('User GPT API key not entered. Using own API key instead.')
    
    else:
        st.session_state["own_account"] = False
        st.session_state.gpt_enhancement_entry = False
    
else:
    print('Users are NOT allowed to use their own accounts.')


# %% [markdown]
# ## Consent

# %%
st.subheader("Consent")

st.markdown("""By running this program, you agree that the data and/or information this form provides will be temporarily stored on one or more remote servers for the purpose of producing an output containing data. Any such data and/or information may also be given to an artificial intelligence provider for the same purpose.""")

consent =  st.checkbox('Yes, I agree.', value = False)

st.markdown("""If you do not agree, then please feel free to close this form.""")


# %% [markdown]
# ## Spreadsheet

# %%
#Determine which spreadsheet to analyse

if len(st.session_state.df_produced) > 0:
    st.session_state.df_to_analyse = st.session_state.df_produced
    
elif len(st.session_state.df_uploaded) > 0:
    st.session_state.df_to_analyse = st.session_state.df_uploaded
    
else: #elif len(st.session_state.df_individual_output) > 0:
    st.session_state.df_to_analyse = st.session_state.df_individual_output

#Start analysing spreadsheet
if len(st.session_state.df_to_analyse) > 0:

    df_to_analyse = st.session_state.df_to_analyse
    
else:
    st.warning('Please upload a spreadsheet.')
    quit()

#Obtain clolumns with hyperlinks
link_heading_config = {} 

try:
    link_heading = link_heading_picker(df_to_analyse)       
    df_to_analyse = convert_links_column(df_to_analyse)
    link_heading_config={link_heading: st.column_config.LinkColumn()}       

except Exception as e:
    print(e)
    print('No column has hyperlinks.')


#Display spreadsheet
st.subheader('Your spreadsheet')

st.caption('To download, search within or maximise this spreadsheet, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')

st.write('You can directly edit this spreadsheet.')

#Make any column of hyperlinks clickable
try:
    st.session_state["edited_df"] = st.data_editor(df_to_analyse,  column_config=link_heading_config)

except Exception as e:

    error_to_show = ''

    if st.session_state.page_from == 'pages/NSW.py':
        
        df_to_analyse = nsw_df_list_columns(df_to_analyse)

        error_to_show = 'The lists in your spreadsheet have been converted to text.'

    else:
        df_to_analyse = df_to_analyse.astype(str)

        error_to_show = 'The non-textual data in your spreadsheet have been converted to text.'
                
    st.session_state["edited_df"] = st.data_editor(df_to_analyse,  column_config=link_heading_config)

    st.warning(error_to_show)
    
    print(f'Error: {e}.')

#Note importation of AI produced spreadsheet
if len(st.session_state.df_produced) > 0:
    st.success('The spreadsheet produced has been imported.')

#New spreadsheet button

if st.button('UPLOAD a new spreadsheet'):
    st.session_state.df_uploaded_key += 1
    clear_most_cache()
    st.rerun()



# %% [markdown]
# ## AI activation and prompt

# %%
#Activate AI

#try:
    #llm = llm_setting(st.session_state.ai_choice, st.session_state.gpt_api_key, st.session_state.gpt_model)
    #agent = agent_alt(llm, st.session_state.ai_choice, st.session_state.instructions_bound, st.session_state.edited_df)

#except Exception as e:
    #st.error('Please double-check your API key.')
    #st.exception(e)
    #quit()

try:
    agent = agent(st.session_state.ai_choice, 
                  st.session_state.gpt_api_key, 
                  st.session_state.gpt_model, 
                  st.session_state.instructions_bound, 
                  st.session_state.edited_df
                 )

except Exception as e:
    st.error('Please double-check your API key.')
    st.exception(e)
    quit()

#Area for entering instructions
st.subheader(f'Enter your instructions for {st.session_state.ai_choice}')

st.write(f':green[Please give your instructions in sequence.] {ai_model_printing(st.session_state.ai_choice, st.session_state.gpt_model)} will respond to at most {st.session_state.instructions_bound} instructions.')

prompt = st.text_area(f'Each instruction must not exceed 1000 characters.', value = st.session_state.prompt_prefill, height= 200, max_chars=1000) 

st.session_state.prompt = prompt

st.caption('During the pilot stage, the number of instructions and the number of characters per instruction are capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to give more instructions or longer instructions.')

#Disable toggle for clarifying questions and answers BEFORE asking AI again
if st.session_state.q_and_a_provided == 1:
    st.success('Your clarifying answers have been added to your instructions. Please press ASK again.')
    st.session_state.q_and_a_toggle = False

#AI warning
if st.session_state.ai_choice == 'GPT':

    if st.session_state.gpt_model == 'gpt-3.5-turbo-0125':
        st.warning('A low-cost GPT model will process your instructions. This model is *not* designed for data analysis.')

    if st.session_state.gpt_model == "gpt-4-turbo":
        st.warning(f'An expensive GPT model will process your instructions.')
        
else: #if st.session_state.ai_choice == 'BambooLLM':
    st.warning('An experimental AI model will respond to your instructions. Please be cautious.')

#Generate explain button
if st.session_state.ai_choice != 'BambooLLM':

    #Explain 
    explain_toggle = st.toggle('Explain')

    if explain_toggle:
        st.session_state.explain_status = True
    else:
        st.session_state.explain_status = False

else:
    st.session_state.explain_status = False


# %% [markdown]
# ## Buttons

# %%
# Generate output

if st.button("ASK"):

    if int(consent) == 0:
        st.warning("You must click on 'Yes, I agree.' to run the program.")
        quit()
        
    elif ((st.session_state.own_account == True) and (st.session_state.gpt_api_key_validity == False)):
            
        st.warning('You have not validated your API key.')
        quit()

    elif ((st.session_state.own_account == True) and (len(gpt_api_key_entry) < 20)):

        st.warning('You have not entered a valid API key.')
        quit()

    elif st.session_state.instruction_left == 0:
        no_more_instructions = 'You have reached the maximum number of instructions allowed during the pilot stage.'
        st.error(no_more_instructions)
        
        #Keep record of response
        st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": float(0), "tokens": float(0),   "role": "assistant", "content": no_more_instructions, 'tokens': 0, 'cost (USD)': 0})

    elif len(st.session_state.prompt) == 0:
        st.warning("Please enter some instruction.")

    else:
        
        #Keep record of prompt
        prompt = st.session_state.prompt
        st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": float(0), "tokens": float(0),   "role": "user", "content": prompt})

        #Change q_and_a_provided status
        st.session_state["q_and_a_provided"] = 0

        if st.session_state.ai_choice in {'GPT', 'BambooLLM'}:
            
            pandasai_ask()

        else: #if st.session_state.ai_choice == 'LangChain':

            langchain_ask()
                        
        #Display number of instructionsl left
        st.session_state.instruction_left -= 1
        instructions_left_text = f"*You have :orange[{st.session_state.instruction_left}] instructions left.*"
        st.write(instructions_left_text)

        #Keep record of instructions left
        st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": float(0), "tokens": float(0),   "role": "assistant", "content": instructions_left_text})


# %%
#Buttons for importing any df produced    

#For Pandasai
if isinstance(st.session_state.response, pd.DataFrame):
    
    if st.button('ANALYSE the spreadsheet produced'):
        st.session_state.df_produced = st.session_state.response
        st.session_state.df_uploaded_key += 1
        st.rerun()

#For Langchain,
if "dataframe" in st.session_state.response_json:
    if st.session_state.response_json["dataframe"]:

        if st.button('ANALYSE this spreadsheet only'):
            #data = st.session_state.response_json["table"]
            #df_to_add = pd.DataFrame(data["data"], columns=data["columns"])
            st.session_state.df_produced = pd.DataFrame(data = st.session_state.response_json["dataframe"])
            st.session_state.df_uploaded_key += 1
            st.rerun()
        
        if st.button('MERGE with your spreadsheet'):
            #data = st.session_state.response_json["table"]
            #df_to_add = pd.DataFrame(data["data"], columns=data["columns"])
            current_pd = st.session_state.edited_df
            df_to_add = pd.DataFrame(data = st.session_state.response_json["dataframe"])
            st.session_state.df_produced = current_pd.merge(df_to_add, on = 'Case name', how = 'left')
            st.session_state.df_produced = st.session_state.df_produced.loc[:,~st.session_state.df_produced.columns.duplicated()].copy()
            st.session_state.df_uploaded_key += 1
            st.rerun()
            


# %%
#Reset button

if st.button('RESET to get fresh responses', type = 'primary'):#, help = "Press to engage with the AI afresh."):
    pai.clear_cache()
    st.session_state['response'] = '' #Adding this to hide clarifying questions and answers toggle upon resetting
    #clear_most_cache()
    st.rerun()
    


# %%
#Clarifying questions form

if ((st.session_state.ai_choice != 'LangChain') 
    and 
    (len(st.session_state.response) > 0)
    ):
    
    if st.toggle(label = 'Get clarifying questions', key = 'q_and_a_toggle'):
    
        with pandasai_get_openai_callback() as cb, st.spinner("Running..."):
            prompt = st.session_state.prompt
    
            clarifying_questions = agent.clarification_questions(prompt)

            st.session_state.clarifying_questions = clarifying_questions

            #Keep record of clarifying questions
            st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": cb.total_cost, "tokens": {cb.total_tokens},   "role": "assistant", "content": clarifying_questions})
                            
        with st.form("clarifying_questions_form"):
    
            st.write('Please answer the following clarifying questions from the AI.')

            #Display up to 3 clarifying questions
            if len(st.session_state.clarifying_questions) > 0:
    
                st.warning(f'Question 1: {st.session_state.clarifying_questions[0]}')
                st.session_state.clarifying_answers[0] = st.text_input(label = f'Enter your answer to question 1', max_chars = 250)
    
            if len(st.session_state.clarifying_questions) > 1: 
    
                st.warning(f'Question 2: {st.session_state.clarifying_questions[1]}')
                st.session_state.clarifying_answers[1] = st.text_input(label = f'Enter your answer to question 2', max_chars = 250)
    
            if len(st.session_state.clarifying_questions) > 2: 
    
                st.warning(f'Question 3: {st.session_state.clarifying_questions[2]}')
                st.session_state.clarifying_answers[2] = st.text_input(label = f'Enter your answer to question 3', max_chars = 250)
    
            #Display and keep record of tokens and costs
            clarifying_questions_cost_tokens = f'(These clarifying questions costed USD $ {round(cb.total_cost, 5)} to produce and totalled {cb.total_tokens} tokens.)'
            st.write(clarifying_questions_cost_tokens)
            
            add_q_a_button = st.form_submit_button('ADD these answers to your instructions')
    
            if add_q_a_button:
                for question_index in range(0, len(st.session_state.clarifying_answers)):
                    st.write(f'Answer to question {question_index + 1}: + st.session_state.clarifying_answers[question_index]')
                    
                intro_q_and_a = ' Take into account the following clarifying questions and their answers. '             
    
                q_and_a_pairs = ''
                
                for question_index in range(0, len(st.session_state.clarifying_answers)):
                    if len(st.session_state.clarifying_answers[question_index]) > 0:
                        question_answer_pair = f' Question: ' + st.session_state.clarifying_questions[question_index] + f' Answer: ' + st.session_state.clarifying_answers[question_index]
                        
                        if question_answer_pair[-1] != '.':
                            question_answer_pair = question_answer_pair + '. '
                        
                        q_and_a_pairs = q_and_a_pairs + question_answer_pair            
    
                if intro_q_and_a in st.session_state.prompt_prefill:
                    
                    st.session_state.prompt_prefill = st.session_state.prompt + q_and_a_pairs
               
                else:
                    
                    st.session_state.prompt_prefill = st.session_state.prompt + intro_q_and_a + q_and_a_pairs

                #Add clarifying answers to history
                st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": cb.total_cost, "tokens": {cb.total_tokens},   "role": "assistant", "content": st.session_state.clarifying_answers})
                
                #Change clarifying questions and answers status
                st.session_state['q_and_a_provided'] = 1

                st.rerun()


# %%
#Button for displaying chat history
history_on = st.toggle(label = 'See all instructions and responses')

if history_on:

    #Check if history exists
    if len(st.session_state.messages) > 0:

        st.subheader('Conversation')

        st.write('Instructions and responses are displayed from earliest to latest.')

        st.caption('To download, search within or maximise any spreadsheet produced, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')

        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            st.caption(' ')
            st.caption(message["time"][0:19])
            with st.chat_message(message["role"]):
                if st.session_state.ai_choice == 'LangChain':
                    if isinstance(message["content"], dict):
                    #if "role" == 'assistant':
                        langchain_write(message["content"])
                    else: #isinstance(message["content"], str)
                        st.write(message["content"])
                else: #if st.session_state.ai_choice in {'GPT', 'BambooLLM'}:
                    #For pandas ai responses
                    st.write(message["content"])

        #Create and export json file with instructions and responses for downloading
        
        df_history = pd.DataFrame(st.session_state.messages)
    
        if len(st.session_state.df_master)>0:
            history_output_name = st.session_state.df_master.loc[0, 'Your name'] + '_' + str(today_in_nums) + '_chat_history'
        else:
            history_output_name = str(today_in_nums) + '_chat_history'
        
        csv = convert_df_to_csv(df_history)
    
        ste.download_button(
            label="Download the conversation as a CSV (for use in Excel etc)", 
            data = csv,
            file_name=history_output_name + '.csv', 
            mime= "text/csv", 
    #            key='download-csv'
        )
    
        xlsx = convert_df_to_excel(df_history)
        
        ste.download_button(label='Download the conversation as an Excel spreadsheet (XLSX)',
                            data=xlsx,
                            file_name=history_output_name + '.xlsx', 
                            mime='application/vnd.ms-excel',
                           )
    
        json = convert_df_to_json(df_history)
        
        ste.download_button(
            label="Download the conversation as a JSON", 
            data = json,
            file_name= history_output_name + '.json', 
            mime= "application/json", 
        )
