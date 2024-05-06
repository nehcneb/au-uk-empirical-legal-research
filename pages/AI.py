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
from pandasai.responses.streamlit_response import StreamlitResponse

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

#default_ai = 'GPT'
default_ai = 'BambooLLM'

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
#NOT in use

def ai_model_description(ai_choice):
    
    model_description = ''
    
    if ai_choice == 'GPT': #llm.type == 'GPT':
    
        model_description = "GPT model gpt-3.5-turbo-0125 is selected by default. This model can explain its reasoning."
    
    if ai_choice == 'BambooLLM': #llm.type == 'Bamboollm':
    
        model_description = 'BambooLLM is selected by default. This model is developed by PandasAI with data analysis in mind (see https://docs.pandas-ai.com/en/stable/).'

    return model_description
    


# %%
def ai_model_printing(ai_choice, gpt_model_choice):

    output = 'BambooLLM'

    if ai_choice == 'GPT':
        
        output = 'GPT model ' + gpt_model_choice

    return output


# %%
#Agent description

default_agent_description = 'You are a data analyst. Your main goal is to help clean, analyse and visualise data. You will be given a spreadsheet of data. Each column starting with "GPT question" was previously entered by you. You will be given questions or instructions about the spreadsheet.'

#visualisation = ' Everytime you are given a question or an instruction, try to provide the code to visualise your answer using Matplotlib.'

visualisation = ' If you are asked to visualise your answer, try to provide the code for visualisation using Matplotlib.'

agent_description = default_agent_description + visualisation
#If want to minimize technicality
#agent_description = 'You are a data analyst. Your main goal is to help non-technical users to clean, analyse and visualise data. You will be given a spreadsheet of data. Each column starting with "GPT question" was previously entered by you. You will be given questions or instructions about the spreadsheet.'

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
def clear_cache():
    keys = list(st.session_state.keys())
    for key in keys:
        st.session_state.pop(key)


# %%
#Initialize default values

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

#Initalize page_from:
if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

#Initialize default instructions bound

default_instructions_bound = 10

print(f"The default maximum number of instructions per thread is {default_instructions_bound}.\n")

#Initialize instructions cap

if 'instructions_bound' not in st.session_state:
    st.session_state['instructions_bound'] = default_instructions_bound

#Initialize instructions counter

if 'instruction_left' not in st.session_state:

    st.session_state["instruction_left"] = st.session_state.instructions_bound

#Initialize default show code status

if 'explain_status' not in st.session_state:
    st.session_state["explain_status"] = False

#Initilize default gpt model

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-3.5-turbo-0125"


# %%
if st.button('RETURN to previous page'):

    st.switch_page(st.session_state.page_from)

st.header("You have chosen to :blue[analyse your spreadsheet].")

#Open spreadsheet
if 'df_individual_output' in st.session_state:

    st.session_state['df_to_analyse'] = st.session_state.df_individual_output

    st.success('Your spreadsheet has been imported. Please scroll down.')


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

        st.session_state["df_to_analyse"]=df_uploaded

        st.success('Your spreadsheet has been imported. Please scroll down.')

st.subheader('Choose an AI')

st.markdown("""Please choose an AI to respond to your instructions.
""")

st.markdown("""GPT can explain its reasoning. BambooLLM is developed with data analysis in mind (see https://docs.pandas-ai.com/en/stable/).""")

ai_choice = st.selectbox(label = f'{default_ai} is selected by default.', options = ai_list, index=0)

if ai_choice:
    pai.clear_cache()
    
st.session_state['ai_choice'] = ai_choice

st.subheader("Consent")

st.markdown("""By running the Empirical Legal Research Kickstarter, you agree that the data and/or information this form provides will be temporarily stored on one or more of Ben Chen's electronic devices and/or one or more remote servers for the purpose of producing an output containing data in relation to judgments. Any such data and/or information may also be given to GPT for the same purpose should you choose to use GPT.
""")

consent =  st.checkbox('Yes, I agree.', value = False)

st.markdown("""If you do not agree, then please feel free to close this form. Any data or information this form provides will neither be received by Ben Chen nor be sent to GPT.
""")

if 'df_to_analyse' in st.session_state:

    st.subheader('Your spreadsheet')

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

    st.write('You can directly edit this spreadsheet.')
    st.caption('To download, search or maximise this spreadsheet, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')

    #Try to avoid conflict between PyArrow and numpy by converting columns with both lists and null values to string

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

    if 'df_individual_output' in st.session_state:
        if st.button('UPLOAD a spreadsheet instead'):
            clear_cache()
            st.rerun()

    llm = ai_model_setting(st.session_state.ai_choice)
    
    agent = Agent(st.session_state.edited_df, config={"llm": llm, "verbose": True, "response_parser": StreamlitResponse}, memory_size=st.session_state.instructions_bound, description = agent_description)
    #agent = SmartDataframe(st.session_state.edited_df, config={"llm": llm, "verbose": True, "response_parser": StreamlitResponse}, description = agent_description)
    
    st.subheader(f'Enter your instruction(s) for {st.session_state.ai_choice}')

    st.write(f':green[Please give your instructions in sequence.] {ai_model_printing(st.session_state.ai_choice, st.session_state.gpt_model)} will respond to at most {st.session_state.instructions_bound} instruction(s).')
    
    prompt = st.text_area('Each instruction must not exceed 1000 characters.', height= 200, max_chars=1000) 

    st.caption('During the pilot stage, the number of instructions and the number of characters per instruction are capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to give more instructions or longer instructions.')

    #Generate explain button
    if st.session_state.ai_choice == 'GPT':
        code_show = st.toggle('Explain reasoning')
    
        if code_show:
            st.session_state.explain_status = True
        else:
            st.session_state.explain_status = False

    # Generate output

    if st.button("ASK the AI"):
        if prompt:
            if int(consent) == 0:
                st.warning("You must click on 'Yes, I agree.' to run the program.")
                quit()
                
            #Keep record of prompt
            st.session_state.messages.append({"time": str(datetime.now()), "role": "user", "content": prompt})
            
            if st.session_state.instruction_left > 0:
                # call pandas_ai.run(), passing dataframe and prompt
                with st.spinner("Running..."):
                    
                    response = agent.chat(prompt)
                    
                    st.write('If you see an error, please modify your instruction or :red[RESET] the AI and try again.') # or :red[RESET] the AI.')

                    st.subheader(f'{st.session_state.ai_choice} Response')
                    st.caption('To download, search or maximise any spreadsheet produced, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')
                    st.write(response)

                    #Keep record of response
                    st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": response})
                        
                    #Check if any figure generated
                    try:
                        if plt.get_fignums():
                            st.write('**Visualisation**')
                            fig_to_plot = plt.gcf()
                            st.pyplot(fig = fig_to_plot)

                            #Enable downloading
                            pdf_to_download = io.BytesIO()
                            png_to_download = io.BytesIO()
                            
                            plt.savefig(pdf_to_download, format = 'pdf')
                            
                            pdf_button = ste.download_button(
                               label="DOWNLOAD the figure as a PDF",
                               data=pdf_to_download,
                               file_name='Figure generated.pdf',
                               mime="image/pdf"
                            )

                            plt.savefig(png_to_download, format = 'png')
                            
                            png_button = ste.download_button(
                               label="DOWNLOAD the figure as a PNG",
                               data=png_to_download,
                               file_name='Figure generated.png',
                               mime="image/png"
                            )
                    except Exception as e:
                        print('An error with visualisation has occured.')
                        print(e)

                    #Explanations
                    if st.session_state.explain_status is True:

                        explanation = agent.explain()
                        st.write('**Explanation**')
                        st.write(explanation)

                        #Keep record of explanation
                        st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": explanation})

                        try:
                            code = response.last_code_generated
                            st.write(code)
                            
                            #Keep record of code
                            st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": code})
                        
                        except Exception as e:
                            print('No code generated.')
                            print(e)
                            
                    #st.write('*:red[An experimental AI produced this response. Please be cautious.]*')

                    #Display number of instructionsl left
                    st.session_state.instruction_left -= 1
                    instructions_left_text = f"*You have :orange[{st.session_state.instruction_left}] instructions left.*"
                    st.write(instructions_left_text)

                    #Keep record of instructions left
                    st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": instructions_left_text})


            else:
                no_more_instructions = 'You have reached the maximum number of instructions allowed during the pilot stage.'
                st.write(no_more_instructions)
                
                #Keep record of response
                st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": no_more_instructions})
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

    #Reset button
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

