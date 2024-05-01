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

# %%
#streamlit run Dropbox/Python/GitHub/au-uk-empirical-legal-research/pages/AI.py

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

#Excel
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb


# %%
#Title of webpage
st.set_page_config(
   page_title="Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Instructions cap
instructions_bound = 10

print(f"\nThe maximum number of instructions per thread is {instructions_bound}.")

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
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
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

# %%
#Default choice of AI

default_ai = 'GPT' #'BambooLLM'

if 'ai_choice' not in st.session_state:
    st.session_state['ai_choice'] = default_ai

ai_list_raw = ['BambooLLM', 'GPT']
ai_list = ['0', '1']
for ai in ai_list_raw:
    if ai == default_ai:
        ai_list[0] = ai
    else:
        ai_list[1] = ai


# %%
#The choice of model function

def ai_model_setting(ai_choice):
    
    if ai_choice == 'GPT': #llm.type == 'GPT':

        llm = OpenAI(api_token=st.secrets["openai"]["gpt_api_key"], model = 'gpt-3.5-turbo-0125')

    if ai_choice == 'BambooLLM': #llm.type == 'Bamboollm':

        llm = BambooLLM(api_key=st.secrets["pandasai"]["bamboollm_api_key"])

    return llm
        
#llm = OpenAI(api_token=st.secrets["openai"]["gpt_api_key"], model = 'gpt-3.5-turbo-0125')

#llm = BambooLLM(api_key=st.secrets["pandasai"]["bamboollm_api_key"])

#if 'openai_key' not in st.session_state:
#    st.session_state.openai_key = st.secrets["openai"]["gpt_api_key"]



# %%
#AI model descript

def ai_model_description(ai_choice):
    
    model_description = ''
    
    if ai_choice == 'GPT': #llm.type == 'GPT':
    
        model_description = "GPT model gpt-3.5-turbo-0125 will respond to your instructions."
    
    if ai_choice == 'BambooLLM': #llm.type == 'Bamboollm':
    
        model_description = 'BambooLLM will respond to your instruction(s). This model is developed by PandasAI with data analysis in mind (see https://docs.pandas-ai.com/en/latest/LLMs/llms/).'

    return model_description
    


# %%
agent_description = 'You are a data analyst. Your main goal is to help non-technical users to clean and analyze data. You will be given a spreadsheet of data. Each column starting with "GPT question" was previously entered by you. You will be given questions or instructions about the spreadsheet.'


# %% [markdown]
# # Streamlit form, functions and parameters

# %%
#Reverse hyperlink display

def link_heading_picker(df):
    y = ''
    for x in df.columns:
        if 'Hyperlink to' in str(x):
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
def clear_cache():
    keys = list(st.session_state.keys())
    for key in keys:
        st.session_state.pop(key)


# %%
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun

# %%
#Initialize instructions counter
if 'instruction_left' not in st.session_state:

    st.session_state["instruction_left"] = instructions_bound

# %%
#Initialize AI choice counter
#NO USE YET

#if 'ai_choice' not in st.session_state:
    #st.session_state["ai_choice"] = ''


# %%
if st.button('RETURN to previous page'):

    if 'page_from' in st.session_state:
        st.switch_page(st.session_state.page_from)

    else:
        st.switch_page('Home.py')

st.header("You have chosen to :blue[analyse your spreadsheet].")

#Open spreadsheet
if 'df_individual_output' in st.session_state:

    st.session_state['df_to_analyse'] = st.session_state.df_individual_output.astype(str)

if 'df_individual_output' not in st.session_state:

    st.markdown("""**:green[Please upload a spreadsheet.]** Supported formats: CSV, XLSX, JSON.""")
    
    uploaded_file = st.file_uploader("You may upload a spreadsheet generated by the Empirical Legal Research Kickstarter. The CSV format is preferred.", type=['csv', 'xlsx', 'json'], accept_multiple_files=False)

    if uploaded_file is not None:
        #Extension
        extension = uploaded_file.name.split('.')[-1].lower()
        
        if extension == 'csv':
            df_uploaded = pd.read_csv(uploaded_file)
    
        if extension == 'xlsx':
            df_uploaded = pd.read_excel(uploaded_file)
    
        if extension == 'json':
            df_uploaded = pd.read_json(uploaded_file, orient= 'split')

        st.session_state["df_to_analyse"]=df_uploaded.astype(str)

if 'df_to_analyse' in st.session_state:

    df_to_analyse = st.session_state.df_to_analyse

    #Make any column of hyperlinks clickable

    link_heading_config = {} 
    
    try:
        link_heading = link_heading_picker(df_to_analyse)       
        df_to_analyse = convert_links_column(df_to_analyse)
        link_heading_config={link_heading: st.column_config.LinkColumn()}       
    except Exception as e:
        print(e)
        print('No column has hyperlinks.')

    st.subheader('Your spreadsheet')
    
    st.caption('To download, search or maximise this spreadsheet, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')
    
    st.session_state["edited_df"] = st.data_editor(df_to_analyse,  column_config=link_heading_config)

    st.markdown("""You can directly edit this spreadsheet.""")
    
    #Choice of AI
#    st.subheader("Which AI would you like to use?")
#    if 'ai_choice' in st.session_state:

    llm = ai_model_setting(st.session_state.ai_choice)
#    sdf = SmartDataframe(st.session_state.edited_df, config = {'llm': llm})
    agent = Agent(st.session_state.edited_df, config={"llm": llm}, memory_size=instructions_bound, description = agent_description)
    
    st.subheader(f'Enter your instruction for {st.session_state.ai_choice}')

    st.write(':green[You may give at most 10 instructions in sequence.] Each instruction must not exceed 1000 characters.')
    
    prompt = st.text_area(ai_model_description(st.session_state.ai_choice), height= 200, max_chars=1000) 

    st.caption('During the pilot stage, the number of instructions and the number of characters per instruction are capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to give more instructions or longer instructions.')

    # Generate output

    st.warning('A low-cost AI will respond to your instruction(s). Please be cautious.')

    if st.button("ASK the AI"):
        if prompt:
            #Keep record of prompt
            st.session_state.messages.append({"time": str(datetime.now()), "role": "user", "content": prompt})
            
            if st.session_state.instruction_left > 0:
                # call pandas_ai.run(), passing dataframe and prompt
                with st.spinner("Running..."):
                    #response = sdf.chat(prompt)

                    response = agent.chat(prompt)

                    st.write('If you see an error, please modify your instruction or :red[RESET] the AI and try again.') # or :red[RESET] the AI.')

                    st.subheader(f'{st.session_state.ai_choice} Response')

                    st.caption('To download, search or maximise any spreadsheet produced, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')
                    
                    st.write(response)

                    #st.write('*:red[An experimental AI produced this response. Please be cautious.]*')

                    #Display number of instructionsl left
                    st.session_state.instruction_left -= 1
                    instructions_left_text = f"You have :orange[{st.session_state.instruction_left}] instructions left."
                    st.write(instructions_left_text)

                    #Keep record of response
                    st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": response})
                    st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": instructions_left_text})

            else:
                no_more_instructions = 'You have reached the maximum number of instructions allowed during the pilot stage.'
                st.write(no_more_instructions)
                
                #Keep record of response
                st.session_state.messages.append({"role": "assistant", "content": no_more_instructions})
        else:
            st.warning("Please enter some instruction.")

    #Show code and clarification are not working yet
    #if len(st.session_state.messages) > 0:
        #if st.button('SHOW code'):
            #explanation = agent.explain()
            #st.write(explanation)

        #if st.button('Clarify'):
            #instructions = agent.clarification_instructions(prompt)
            #for instruction in instructions:
                #st.write(instruction)

    #Reset button, not particularly useful
    if st.button('RESET the AI', type = 'primary', help = "Press to engage with the AI afresh."):
        pai.clear_cache()
        #clear_cache()
        #st.rerun()

    #Button for displaying chat history
    history_on = st.toggle(label = 'SEE all instructions and responses')

    if history_on:

        #Check if history exists
        if len(st.session_state.messages) > 0:
    
            st.subheader('Conversation')

            st.write('Instructions and responses are displayed from earliest to latest.')

            st.caption('To download, search or maximise any spreadsheet produced, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')

            # Display chat messages from history on app rerun
            for message in st.session_state.messages:
                st.caption(' ')
                st.caption(message["time"][0:19])
                with st.chat_message(message["role"]):
                    st.write(message["content"])
    
            #Create and export json file with instructions and responses for downloading
            
            df_history = pd.DataFrame(st.session_state.messages)
        
            if "df_master" in st.session_state:
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

