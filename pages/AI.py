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

#Module, costs and upperbounds



# %%
#Initialize default GPT settings

#Initialize API key

if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

#Initialize key validity check

if 'gpt_api_key_validity' not in st.session_state:
    st.session_state['gpt_api_key_validity'] = False


# %%
#Default choice of AI

default_ai = 'GPT'
#default_ai = 'BambooLLM'

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

#API_key = st.session_state.gpt_api_key

def ai_model_setting(ai_choice, key, gpt_model_choice):

    if gpt_model_choice == 'gpt-4-turbo':
        gpt_model_choice = 'gpt-4-0125-preview'
    
    if ai_choice == 'GPT': #llm.type == 'GPT':

        llm = OpenAI(api_token=key, model = gpt_model_choice)

    if ai_choice == 'BambooLLM': #llm.type == 'Bamboollm':

        llm = BambooLLM(api_key = st.secrets["pandasai"]["bamboollm_api_key"])

    return llm
        
#llm = OpenAI(api_token=st.secrets["openai"]["gpt_api_key"], model = 'gpt-3.5-turbo-0125')

#llm = BambooLLM(api_key=st.secrets["pandasai"]["bamboollm_api_key"])

#if 'openai_key' not in st.session_state:
#    st.session_state.openai_key = st.secrets["openai"]["gpt_api_key"]

def ai_model_printing(ai_choice, gpt_model_choice):

    output = 'BambooLLM'

    if ai_choice == 'GPT':
        
        output = 'GPT model ' + gpt_model_choice

    return output



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
#Agent description

default_agent_description = 'You are a data analyst. Your main goal is to help clean, analyse and visualise data. You will be given a spreadsheet of data. Each column starting with "GPT question" was previously entered by you. You will be given questions or instructions about the spreadsheet.'

#visualisation = ' Everytime you are given a question or an instruction, try to provide the code to visualise your answer using Matplotlib.'

visualisation = ' If you are asked to visualise your answer, try to provide the code for visualisation using Matplotlib.'

agent_description = default_agent_description + visualisation
#If want to minimize technicality
#agent_description = 'You are a data analyst. Your main goal is to help non-technical users to clean, analyse and visualise data. You will be given a spreadsheet of data. Each column starting with "GPT question" was previously entered by you. You will be given questions or instructions about the spreadsheet.'

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

#Initalize response:
if 'response' not in st.session_state:

    st.session_state['response'] = ''

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

    #st.session_state['df_to_analyse'] = st.session_state.df_individual_output

    st.success('Your spreadsheet has been imported. Please scroll down.')

else: #if 'df_individual_output' not in st.session_state:

    st.markdown("""**:green[Please upload a spreadsheet.]** Supported formats: CSV, XLSX, JSON.""")
    
    uploaded_file = st.file_uploader("You may upload a spreadsheet generated by the Empirical Legal Research Kickstarter. The CSV format is preferred.", 
                                     type=['csv', 'xlsx', 'json'], 
                                     accept_multiple_files=False, 
                                     key = st.session_state["df_uploaded_key"])

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
        
        #st.session_state["df_to_analyse"]=df_uploaded

        st.success('Your spreadsheet has been imported. Please scroll down.')




# %% [markdown]
# ## Choice of AI and GPT account

# %%
st.subheader('Choose an AI')

st.markdown("""Please choose an AI to help with data cleaning, analysis and visualisation.
""")

ai_choice = st.selectbox(label = f'{default_ai} is selected by default.', options = ai_list, index=0)

if ai_choice != st.session_state.ai_choice:
    pai.clear_cache()
    st.session_state['ai_choice'] = ai_choice

st.markdown("""GPT can explain its reasoning. BambooLLM is developed with data analysis in mind (see https://docs.pandas-ai.com/en/stable/).""")

if st.toggle('See the instruction given to the chosen AI'):
    st.write(f"*{agent_description}*")


if own_account_allowed() > 0:

    if st.session_state.ai_choice == 'GPT':
    
        st.subheader(':orange[Enhance program capabilities]')
        
        st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or increase the maximum nunber of instructions to process? You can do so with your own GPT account.
        """)
        
        own_account_entry = st.toggle('Use my own GPT account')
        
        if own_account_entry:
            #Reset AI first
            pai.clear_cache()
            
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
            
                st.session_state.gpt_model = "gpt-4-turbo"
                st.session_state.gpt_enhancement_entry = True
    
            else:
                
                st.session_state.gpt_model = "gpt-3.5-turbo-0125"
                st.session_state.gpt_enhancement_entry = False
            
            st.write(f'**:green[You can remove the cap on the number of instructions to process.]** The default cap is {default_instructions_bound}.')
        
            #st.session_state.instructions_bound = round(st.number_input(label = 'Enter the maximum number of instructions', min_value=1, value=default_instructions_bound))
        
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
        #st.session_state.ai_choice = default_ai
    
else:
    print('Users are NOT allowed to use their own accounts.')

# %% [markdown]
# ## Consent

# %%
st.subheader("Consent")

st.markdown("""By running the Empirical Legal Research Kickstarter, you agree that the data and/or information this form provides will be temporarily stored on one or more remote servers for the purpose of producing an output containing data. Any such data and/or information may also be given to an artificial intelligence provider for the same purpose.""")

consent =  st.checkbox('Yes, I agree.', value = False)

st.markdown("""If you do not agree, then please feel free to close this form.""")



# %% [markdown]
# ## Spreadsheet analysis

# %%
#Determine which spreadsheet to analyse

if len(st.session_state.df_produced) > 0:
    st.session_state.df_to_analyse = st.session_state.df_produced
    
elif len(st.session_state.df_uploaded) > 0:
    st.session_state.df_to_analyse = st.session_state.df_uploaded
    
else: #elif len(st.session_state.df_individual_output) > 0:
    st.session_state.df_to_analyse = st.session_state.df_individual_output

if len(st.session_state.df_to_analyse) > 0:

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

    #New spreadsheet button

    if st.button('UPLOAD a new spreadsheet'):
        st.session_state.df_uploaded_key += 1
        clear_most_cache()
        st.rerun()

    #Remove button for carried-over spreadsheets only; doesn't work for uploaded spreadsheets

    #if 'df_individual_output' in st.session_state:
        #if st.button('UPLOAD a spreadsheet instead'):
            #clear_cache_except_validation_history_df_produced()
            #st.rerun()

    #Activate AI
    try:
        llm = ai_model_setting(st.session_state.ai_choice, st.session_state.gpt_api_key, st.session_state.gpt_model)
    except Exception as e:
        st.error('Please double-check your API key.')
        #st.exception(e)
        quit()

    agent = Agent(st.session_state.edited_df, config={"llm": llm, "verbose": True, "response_parser": StreamlitResponse, 'enable_cache': True}, memory_size=st.session_state.instructions_bound, description = agent_description)
    #agent = SmartDataframe(st.session_state.edited_df, config={"llm": llm, "verbose": True, "response_parser": StreamlitResponse, 'enable_cache': True}, description = agent_description)

    st.subheader(f'Enter your instruction(s) for {st.session_state.ai_choice}')

    st.write(f':green[Please give your instruction(s) one by one.] {ai_model_printing(st.session_state.ai_choice, st.session_state.gpt_model)} will respond to at most {st.session_state.instructions_bound} instructions.')
            
    #prompt = st.text_area(ai_model_description(st.session_state.ai_choice), height= 200, max_chars=1000) 
    prompt = st.text_area(f'Each instruction must not exceed 1000 characters.', height= 200, max_chars=1000) 

    st.caption('During the pilot stage, the number of instructions and the number of characters per instruction are capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to give more instructions or longer instructions.')

    #Generate explain button
    if st.session_state.ai_choice == 'GPT':
    
        #Explain 
        code_show = st.toggle('Explain reasoning')
    
        if code_show:
            st.session_state.explain_status = True
        else:
            st.session_state.explain_status = False

    else:
        st.session_state.explain_status = False

    #AI warning
    if st.session_state.ai_choice == 'GPT':
    
        if st.session_state.gpt_model == 'gpt-3.5-turbo-0125':
            st.warning('A low-cost AI will respond to your instruction(s). Beware that it is not designed for data analysis.')
    
        if st.session_state.gpt_model == "gpt-4-turbo":
            st.warning(f'An expensive AI will respond to your instruction(s). Please be cautious.')
            
    else: #if st.session_state.ai_choice == 'BambooLLM':
        st.warning('An experimental AI will respond to your instruction(s). Please be cautious.')

    # Generate output

    if st.button("ASK"):
        if not prompt:
            st.warning("Please enter some instruction.")
        else:
            #Keep record of prompt
            st.session_state.messages.append({"time": str(datetime.now()), "role": "user", "content": prompt})

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
                st.write(no_more_instructions)
                
                #Keep record of response
                st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": no_more_instructions})
            
            else:
                # call pandas_ai.run(), passing dataframe and prompt
                with st.spinner("Running..."):

                    response = agent.chat(prompt)

                    st.session_state.response = response
                    
                    st.write('If you see an error, please modify your instruction(s) or press :red[RESET] below and try again.') # or :red[RESET] the AI.')

                    st.subheader(f'{st.session_state.ai_choice} Response')
                    
                    st.write(response)

                    #Keep record of response
                    st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": response})

                    if isinstance(st.session_state.response, pd.DataFrame):
                        st.write('To download, search or maximise any spreadsheet produced, hover your mouse/pointer over its top right-hand corner and press the appropriate button.')

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
                               label="DOWNLOAD the figure as a PDF",
                               data=pdf_to_download,
                               file_name='Figure.pdf',
                               mime="image/pdf"
                            )

                            plt.savefig(png_to_download, bbox_inches='tight', format = 'png')
                            
                            png_button = ste.download_button(
                               label="DOWNLOAD the figure as a PNG",
                               data=png_to_download,
                               file_name='Figure.png',
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
                        
                    #Display number of instructionsl left
                    st.session_state.instruction_left -= 1
                    instructions_left_text = f"*You have :orange[{st.session_state.instruction_left}] instructions left.*"
                    st.write(instructions_left_text)

                    #Keep record of instructions left
                    st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": instructions_left_text})
            

    #Show code and clarification are not working yet
    #if len(st.session_state.messages) > 0:
        #if st.button('SHOW code'):
            #explanation = agent.explain()
            #st.write(explanation)
            #st.session_state.messages.append({"time": str(datetime.now()), "role": "assistant", "content": explanation})

        #if st.button('Clarify'):
            #instructions = agent.clarification_instructions(prompt)
            #for instruction in instructions:
                #st.write(instruction)
    
    #Button for analysis of any df_produced    
    if isinstance(st.session_state.response, pd.DataFrame):
        #st.write(st.session_state.df_to_analyse.compare(response))
        
        if st.button('ANALYSE this spreadsheet'):
            st.session_state.df_produced = st.session_state.response
            st.session_state.df_uploaded_key += 1
            #clear_most_cache()
            st.rerun()

    #Reset button
    #if len(str(st.session_state.response)) >0:
    if st.button('RESET to get fresh responses', type = 'primary'):#, help = "Press to engage with the AI afresh."):
        pai.clear_cache()
        st.session_state['response'] = ''
        #clear_most_cache()
        st.rerun()

    #Button for displaying chat history
    history_on = st.toggle(label = 'See all instructions and responses')

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
