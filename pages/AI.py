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


# %%
#Title of webpage
st.set_page_config(
   page_title="Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Questions cap
questions_bound = 10

print(f"\nThe maximum number of questions per thread is {questions_bound}.")

# %% [markdown]
# # AI model and context

# %%
#Default choice of AI

default_ai = 'BambooLLM' #'GPT'

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
    
        model_description = "GPT model gpt-3.5-turbo-0125 will respond to your questions."
    
    if ai_choice == 'BambooLLM': #llm.type == 'Bamboollm':
    
        model_description = 'BambooLLM will respond to your question(s). This model is developed by PandasAI with data analysis in mind (see https://docs.pandas-ai.com/en/latest/LLMs/llms/).'

    return model_description
    


# %%
agent_description = 'You are a data analyst. Your main goal is to help non-technical users to analyze data. You will be given a spreadsheet of mainly textual data. The values under each column starting with "GPT question" were previously entered by you.'


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
if st.button('RETURN to previous page'):

    if 'page_from' in st.session_state:
        st.switch_page(st.session_state.page_from)

    else:
        st.switch_page('Home.py')

st.title("You have chosen to :blue[analyse your spreadsheet].")

#Activate questions bound
if 'question_left' not in st.session_state:

    st.session_state["question_left"] = questions_bound

#Open spreadsheet
if 'df_individual_output' not in st.session_state:

    st.markdown("""**Please upload a spreadsheet for analysis.** Supported formats: CSV, XLSX, JSON.""")
    
    uploaded_file = st.file_uploader("You may upload a spreadsheet generated by the Empirical Legal Research Kickstarter.", type=['csv', 'xlsx', 'json'], accept_multiple_files=False)

    if uploaded_file is not None:
        #Extension
        extension = uploaded_file.name.split('.')[-1].lower()
        
        if extension == 'csv':
            df_uploaded = pd.read_csv(uploaded_file)
    
        if extension == 'xlsx':
            df_uploaded = pd.read_excel(uploaded_file)
    
        if extension == 'json':
            df_uploaded = pd.read_json(uploaded_file, orient= 'split')

        st.session_state["df_individual_output"]=df_uploaded

if 'df_individual_output' in st.session_state:

    df_individual_output = st.session_state.df_individual_output

    #Make any column of hyperlinks clickable

    try:
        link_heading = link_heading_picker(df_individual_output)
        
        df_individual_output = convert_links_column(df_individual_output)
    except Exception as e:
        print(e)
        print('No column has hyperlinks.')
    
#    st.write(df_individual_output.head(10))

#    edited_df = st.data_editor(df_individual_output)

    st.caption('To download, search or maximise this spreadsheet, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')
    
    st.session_state["edited_df"] = st.data_editor(df_individual_output,  column_config={link_heading: st.column_config.LinkColumn()})

    st.markdown("""**You can edit this spreadsheet.** Your edits will be read by the AI.""")
    
    #Permit uploading of new spreadsheet
    
    if st.button(label = 'CLEAR the spreadsheet', type = 'primary'):
        pai.clear_cache()
        clear_cache()
        st.rerun()
    
    #Choice of AI
#    st.subheader("Which AI would you like to use?")
    
#    st.markdown("""BambooLLM is better at answering questions about statistics while GPT questions about words.
    
#BambooLLM is chosen by default.
#""")
    
#    st.session_state["ai_choice"] = st.selectbox(label = 'Please choose an AI.', options = ai_list, index = 0)
    
#    st.caption('BambooLLM is developed by PandasAI with data analysis in mind (see https://docs.pandas-ai.com/en/latest/LLMs/llms/). GPT is released by OpenAI. The GPT model to be used is model gpt-3.5-turbo-0125.')

#    if 'ai_choice' in st.session_state:
    llm = ai_model_setting(st.session_state.ai_choice)
#    sdf = SmartDataframe(st.session_state.edited_df, config = {'llm': llm})
    agent = Agent(st.session_state.edited_df, config={"llm": llm}, memory_size=questions_bound, description = agent_description)
    
    st.subheader('Please enter your question.')

    st.write('You may ask at most 10 questions. Each question may amount to at most 1000 characters.')
    
    prompt = st.text_area(ai_model_description(st.session_state.ai_choice), height= 200, max_chars=1000) 

#    prompt = st.text_area(st.session_state.ai_choice + ' will respond to your questions.', height= 200, max_chars=1000) 
    st.caption('During the pilot stage, the number of questions and the number of characters per question are capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to ask more or longer questions.')

    # Generate output
    
    if st.button("ASK the AI"):
        if prompt:
            if st.session_state.question_left > 0:
                # call pandas_ai.run(), passing dataframe and prompt
                with st.spinner("Generating response..."):
                    #response = sdf.chat(prompt)

                    response = agent.chat(prompt)

                    st.write('If you see an error, please ask your question again or :red[RESET] the AI.')

                    st.subheader('Response')

                    
                    st.caption('To download, search or maximise any spreadsheet produced, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')
                    
                    st.write(response)

                    #st.write('*:red[An experimental AI produced this response. Please be cautious.]*')

                    #Display number of questionsl left
                    st.session_state.question_left -= 1
                    st.write(f"*Number of questions left: :orange[{st.session_state.question_left}].*")

                    #Button for clarifications; NOT WORKING YET
                    #if st.button('Clarify'):
                        #questions = agent.clarification_questions(prompt)
                        #for question in questions:
                            #st.write(question)
    
                    #if st.button('Explain'):
                        #explanation = agent.explain()
                        #st.write(explanation)
            
            else:
                st.write('You have reached the maximum number of questions allowed during the pilot stage.')
        else:
            st.warning("Please enter a question.")

    if st.button('RESET the AI', type = 'primary', help = "Press to obtain fresh responses from the AI."):
        pai.clear_cache()

