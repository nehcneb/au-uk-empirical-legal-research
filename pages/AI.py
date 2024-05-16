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
import openpyxl

#Import matplotlib for use in Streamlit
import matplotlib
#matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
# #echo "backend: TkAgg" >> ~/.matplotlib/matplotlibrc

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
#from streamlit.components.v1 import html
import streamlit_ext as ste

#OpenAI
import openai
#from openai import OpenAI
#import tiktoken

#PandasAI
#from dotenv import load _dotenv
from pandasai import SmartDataframe
from pandasai import Agent
#from pandasai.llm import BambooLLM
from pandasai.llm.openai import OpenAI
import pandasai as pai
from pandasai.responses.streamlit_response import StreamlitResponse
from pandasai.helpers.openai_info import get_openai_callback as pandasai_get_openai_callback

#langchain
#from langchain_community.chat_models import ChatOpenAI
#from langchain_experimental.agents import create_pandas_dataframe_agent
#from langchain.agents.agent_types import AgentType
#from langchain_community.callbacks import get_openai_callback as langchain_get_openai_callback

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
    return df.to_json(orient = 'split', compression = 'infer', default_handler=str)

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
#Per token cost

def gpt_input_cost(gpt_model):
    
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_input_cost = 1/1000000*0.5
        
    if gpt_model == "gpt-4o":
        gpt_input_cost = 1/1000000*5
    return gpt_input_cost

def gpt_output_cost(gpt_model):
    if gpt_model == "gpt-3.5-turbo-0125":
        gpt_output_cost = 1/1000000*1.5
        
    if gpt_model == "gpt-4o":
        gpt_output_cost = 1/1000000*15
        
    return gpt_output_cost


# %%
#Check validity of API key
def is_api_key_valid(key_to_check):
    openai.api_key = key_to_check
    
    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[{"role": "user", "content": '1+1='}], 
            max_tokens = 1
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
        #if gpt_model_choice == 'gpt-4o':
            #gpt_model_choice = 'gpt-4o'
        
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

        #if gpt_model_choice == 'gpt-3.5-turbo-0125':
            
        agent = Agent(df, 
                      config={"llm": llm, 
                              "verbose": True, 
                              "response_parser": StreamlitResponse, 
                              'enable_cache': True, 
                              'use_error_correction_framework': True, 
                              'max_retries': 5
                             }, 
                      memory_size = default_instructions_bound, 
                      description = pandasai_agent_description
                     )
            #agent = SmartDataframe(st.session_state.edited_df, config={"llm": llm, "verbose": True, "response_parser": StreamlitResponse, 'enable_cache': True}, description = pandasai_agent_description)

        #else: #For GPT 4, StreamlitResponse doesn't 'hold' images
            #agent = Agent(df, 
                          #config={"llm": llm, 
                                  #"verbose": True, 
                                  #"response_parser": StreamlitResponse, 
                                  #'enable_cache': True, 
                                  #'use_error_correction_framework': True, 
                                  #'max_retries': 5
                                 #}, 
                          #memory_size = default_instructions_bound, 
                          #description = pandasai_agent_description
                         #)
            
    if ai_choice == 'LangChain':

        agent_kwargs={"system_message": default_agent_description, #+ langchain_pandasai_further_instructions, 
                    "handle_parsing_errors": True,
                      'streaming' : True, 
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

You must not remove the columns entitiled "Case name" and "Medium neutral citation" from the spreadsheet. 
"""

#If you need to use any modules to execute a code, import such modules first. 

#If you are asked to visualise your answer, provide the code for visualisation using Matplotlib. 

#If there are values which are "nonetype" objects, you ignore such values first. 

#If there are values which are "list" objects, you convert such values to "string" objects first. 


#visualisation = ' Everytime you are given a question or an instruction, try to provide the code to visualise your answer using Matplotlib.'

pandasai_agent_description = default_agent_description + pandasai_further_instructions
#If want to minimize technicality
#pandasai_agent_description = 'You are a data analyst. Your main goal is to help non-technical users to clean, analyse and visualise data. You will be given a spreadsheet of data. Each column starting with "GPT question" was previously entered by you. You will be given questions or instructions about the spreadsheet.'

#Common errors:
#Value type <class 'list'> must match with type dataframe

# %%
#For testing purposes

def pandasai_ask_test():

    with pandasai_get_openai_callback() as cb, st.spinner("Running..."):

        #Get response and keep in session state

        response = agent.chat(prompt)
        st.session_state.response = response
    
        #Show response
        st.subheader(f'{st.session_state.ai_choice} Response')
        st.caption(spreadsheet_caption)
    
        if agent.last_error is not None:
            st.error(response)

        else:
            st.write(response)

        if '.png' in response:
            st.image(response)

        #Show any figure generated
        st.write('**Visualisation**')

        st.write('List')
        st.write(plt.get_fignums())
        
        for fig_num in plt.get_fignums():
            
            fig_to_plot = plt.figure(fig_num)
            
            st.pyplot(fig = fig_to_plot)

        st.write('Labels')
        st.write(plt.get_figlabels())

        for fig_label in plt.get_figlabels():
            
            fig_to_plot = plt.figure(fig_label)

            st.pyplot(fig = fig_to_plot)


# %%
def pandasai_ask():
    
    with pandasai_get_openai_callback() as cb, st.spinner("Running..."):

        #Proess prompt
        
        prompt = st.session_state.prompt

        #Get response and keep in session state

        response = agent.chat(prompt)
        st.session_state.response = response

        #Keep record of prompt cost and tokens
        prompt_tokens = cb.prompt_tokens
        prompt_cost = prompt_tokens*gpt_input_cost(st.session_state.gpt_model)
        st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": prompt_cost, "tokens": prompt_tokens,   "role": "user", "content": {"prompt": prompt}})
        
        #Obtain response cost and tokens
        response_cost = cb.total_cost - prompt_cost
        response_tokens = cb.completion_tokens

        #Show response
        st.subheader(f'{st.session_state.ai_choice} Response')    
        #st.write('*If you see an error, please modify your instructions or click :red[RESET] below and try again.*') # or :red[RESET] the AI.')

        if agent.last_error is not None:
            st.error(response)
            #Keep record of response, cost and tokens
            st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": response_cost, "tokens": response_tokens,   "role": "assistant", "content": {'error': response}})

        else:
            st.write(response)
            #Keep record of response, cost and tokens
            st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": response_cost, "tokens": response_tokens,   "role": "assistant", "content": {'answer': response}})

        #Display caption if response is a dataframe
        if isinstance(response, pd.DataFrame):
            
            st.caption(spreadsheet_caption)

        #Check if any df produced
        #if isinstance(st.session_state.response, pd.DataFrame):
    
            #col1b, col2b = st.columns(2, gap = 'small')
    
            #with col1b:
                #pandasai_analyse_button = st.button('ANALYSE the spreadsheet produced only')
            
            #with col2b:
                #pandasai_merge_button = st.button('MERGE with your spreadsheet')
    
            #if pandasai_analyse_button:                
                #pandasai_analyse_df_produced()
    
            #if pandasai_merge_button:
                
                #pandasai_merge_df_produced()

        #For all GPT models, show any figure generated
        #st.write(f'The number of figures is {plt.get_fignums()}')

        #if '.png' in str(response)[-4:]:
        if plt.get_fignums():
            try:
                #st.write('**Visualisation**')
        
                fig_to_plot = plt.gcf()
                st.pyplot(fig = fig_to_plot)
                
                #Keep record of response, cost and tokens
                st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": float(0), "tokens": float(0),   "role": "assistant", "content": {'matplotlib figure': fig_to_plot}})

                #Enable downloading
                pdf_to_download = io.BytesIO()
                png_to_download = io.BytesIO()

                col1e, col2e = st.columns(2, gap = 'small')
                
                with col1e:
            
                    plt.savefig(pdf_to_download, bbox_inches='tight', format = 'pdf')
                    
                    pdf_button = ste.download_button(
                       label="DOWNLOAD as a PDF",
                       data=pdf_to_download,
                       file_name='chart.pdf',
                       mime="image/pdf"
                    )
                with col2e:
                    plt.savefig(png_to_download, bbox_inches='tight', format = 'png')
                    
                    png_button = ste.download_button(
                       label="DOWNLOAD as a PNG",
                       data=png_to_download,
                       file_name='chart.png',
                       mime="image/png"
                    )
                
                #st.write('image') #If st.pyplot doesn't work
                
                #st.image(response)
                
                #st.caption('Right click to save this image.')
    
                #Keep record of response, cost and tokens
                #st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": response_cost, "tokens": response_tokens,   "role": "assistant", "content": {'image': response}})
    
            except Exception as e:
                st.error('Image produced but failed to visualise.')
                print(e)
            
        #For GPT-3.5, show any figure generated
        #if plt.get_fignums(): #This returns a list of figure numbers produced
            #try:
                #st.write('**Visualisation**')
                #st.write('Charts may appear in a popped up window. ')
                #fig_to_plot = plt.gcf()
                #st.pyplot(fig = fig_to_plot)

                #for fig_num in plt.get_fignums(): #Alternatively, use this if wants to show every figure produced. Can be repetitive.
                    #fig_num = plt.get_fignums()
                    #fig_to_plot = plt.figure(fig_num)                
                    #st.pyplot(fig = fig_to_plot)

                #Keep record of response, cost and tokens
                #st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": response_cost, "tokens": response_tokens,   "role": "assistant", "content": {'matplotlib figure': fig_to_plot}})
            
                #Enable downloading
                #pdf_to_download = io.BytesIO()
                #png_to_download = io.BytesIO()

                #col1e, col2e = st.columns(2, gap = 'small')
                
                #with col1e:
            
                    #plt.savefig(pdf_to_download, bbox_inches='tight', format = 'pdf')
                    
                    #pdf_button = ste.download_button(
                       #label="DOWNLOAD as a PDF",
                       #data=pdf_to_download,
                       #file_name='chart.pdf',
                       #mime="image/pdf"
                    #)
                #with col2e:
                    #plt.savefig(png_to_download, bbox_inches='tight', format = 'png')
                    
                    #png_button = ste.download_button(
                       #label="DOWNLOAD as a PNG",
                       #data=png_to_download,
                       #file_name='chart.png',
                       #mime="image/png"
                    #)
    
            #except Exception as e:
                #st.error('An error with visualisation has occured.')
                #print(e)
    
        #For displaying logs
        #st.subheader('Logs')
        #df_logs = agent.logs
        #st.dataframe(df_logs)
        
        #default explanation/cost cost and tokens
        explanation_cost = float(0)
        explanation_tokens = float(0)
        code_cost = float(0)
        code_tokens = float(0)
        
        #Explanations
        if st.session_state.explain_status is True:
    
            explanation = agent.explain()
            st.write('**Explanation**')
            st.write(explanation)

            #Display cost and tokens
            explanation_cost = cb.total_cost - response_cost - prompt_cost
            explanation_tokens = cb.total_tokens - response_tokens - prompt_tokens
            
            #Keep record of explanation
            st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": explanation_cost, "tokens": explanation_tokens,   "role": "assistant", "content": {'answer': explanation}})

        #Code
        if st.session_state.code_status is True:
            try:
                code = agent.generate_code(prompt)
                
                st.write('**Code**')
                st.code(code)
    
                #Display cost and tokens
                code_cost = cb.total_cost - explanation_cost - response_cost - prompt_cost
                code_tokens = cb.total_tokens -  explanation_tokens  - response_tokens - prompt_tokens
    
                #Keep record of code
                st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": code_cost, "tokens": code_tokens,   "role": "assistant", "content": {'code': code}})
            
            except Exception as e:
                st.warning(f'{st.session_state.ai_choice} failed to produce a code.')
                print(e)
    
        #Acivate if want to display tokens and costs only if own account active
        #if st.session_state['own_account'] == True:
        total_cost_tokens = f'(This exchange costed approximately USD $ {round(cb.total_cost, 5)} and totalled {cb.total_tokens} tokens.)'
        st.write(total_cost_tokens)
        st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": float(0), "tokens": float(0),   "role": "assistant", "content": {'answer': total_cost_tokens}})
        


# %%
#Buttons for importing any df produced    

#For Pandasai

def pandasai_analyse_df_produced():
    st.session_state.df_produced = st.session_state.response
    st.session_state.df_uploaded_key += 1
    #st.session_state.df_uploaded = pd.DataFrame([])
    #st.session_state.df_individual_output = pd.DataFrame([])
    st.session_state.response = {}
    #st.session_state["analyse_df_produced"] = False
    st.rerun()       

def pandasai_merge_df_produced():

    current_pd = st.session_state.edited_df
    df_to_add = pd.DataFrame(data = st.session_state.response)
    st.session_state.df_produced = current_pd.merge(df_to_add, on = 'Case name', how = 'left')
    st.session_state.df_produced = st.session_state.df_produced.loc[:,~st.session_state.df_produced.columns.duplicated()].copy()
    st.session_state.df_uploaded_key += 1
    #st.session_state.df_uploaded = pd.DataFrame([])
    #st.session_state.df_individual_output = pd.DataFrame([])
    st.session_state.response = []
    #st.session_state["merge_df_produced"] = False
    st.rerun()



# %% [markdown]
# ## LangChain

# %%
#Got some ideas from https://dev.to/ngonidzashe/chat-with-your-csv-visualize-your-data-with-langchain-and-streamlit-ej7

langchain_further_instructions = """

If you need to use any modules to execute a code, import such modules first. 

Your output should be in JSON form with three fields: "text", "dataframe" and "code". These are the only possible fields.

If you are required to produce a table, format the table as a Pandas dataframe, and then place the dataframe in the "dataframe" field. Specifcially: {"dataframe": the Pandas dataframe from your ouput}.

If you are required to produce a code,  provide the code in the "code" field. Specifcially: {"code": the code from your output}.

Any output that is not a dataframe or a code should be placed in the "text" field. Specifically: {"text": anything that is not a dataframe or a code}.

If you do not know how to answer the questions or instructions given, write {"text": "Answer not found."}.

You must not remove the columns entitiled "Case name" and "Medium neutral citation" from the spreadsheet. 

The questions or instructions are as follows: 
"""

#Return all output as a string.


# %%
def langchain_write(response_json):

    if "text" in response_json:
    
        if response_json["text"]:
            
            st.write(response_json["text"])
    
    if "dataframe" in response_json:
        
        if response_json["dataframe"]:
        
            st.dataframe(response_json["dataframe"])

            col1c, col2c = st.columns(2, gap = 'small')

            with col1c:
                langchain_analyse_button = st.button('ANALYSE the spreadsheet produced only')
            
            with col2c:
                langchain_merge_button = st.button('MERGE with your spreadsheet')
    
            if langchain_analyse_button:
                langchain_analyse_df_produced()
    
            if langchain_merge_button:
                langchain_merge_df_produced()

    if "code" in response_json:
        
        if response_json["code"]:

            #if st.session_state.explain_status == True:
            
            st.write("**Code**")
        
            st.code(response_json["code"])



# %%
#Langchain ask function

def langchain_ask():
    with langchain_get_openai_callback() as cb, st.spinner("Running..."):

        #Process prompt

        prompt = st.session_state.prompt

        prompt_to_process = langchain_further_instructions + prompt

        if st.session_state.explain_status == True:
            
            prompt_to_process += ' Explain your answer in detail. '

        if st.session_state.code_status == True:

            prompt_to_process += ' Offer a code for obtaining your answer. '

        response = agent.invoke(prompt_to_process)

        #Keep record of tokens and costs
        cost_tokens = f'(Cost: USD $ {round(cb.total_cost, 5)} Tokens: {cb.total_tokens})'

        st.subheader(f'{st.session_state.ai_choice} Response')

        #st.session_state.response = response.__str__()

        #Keep record of prompt
        st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": float(0), "tokens": float(0),   "role": "user", "content": {"prompt": prompt}})

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

        
        #st.write('*If you see an error, please modify your instructions or click :red[RESET] below and try again.*') # or :red[RESET] the AI.')
    
        #Display tokens and costs
        st.write(cost_tokens)


# %%
#Buttons for importing or merging df produced

def langchain_analyse_df_produced():
    st.session_state.df_produced = pd.DataFrame(data = st.session_state.response_json["dataframe"])
    st.session_state.df_uploaded_key += 1
    #st.session_state.df_uploaded = pd.DataFrame([])
    #st.session_state.df_individual_output = pd.DataFrame([])
    st.session_state.response_json["dataframe"] = pd.DataFrame([])
    st.rerun()

def langchain_merge_df_produced():
    
    current_pd = st.session_state.edited_df
    df_to_add = pd.DataFrame(data = st.session_state.response_json["dataframe"])
    st.session_state.df_produced = current_pd.merge(df_to_add, on = 'Case name', how = 'left')
    st.session_state.df_produced = st.session_state.df_produced.loc[:,~st.session_state.df_produced.columns.duplicated()].copy()
    st.session_state.df_uploaded_key += 1
    #st.session_state.df_uploaded = pd.DataFrame([])
    #st.session_state.df_individual_output = pd.DataFrame([])
    st.session_state.response_json["dataframe"] = pd.DataFrame([])
    st.rerun()


# %% [markdown]
# # Streamlit form, functions and parameters

# %% [markdown]
# ## Function definitions

# %%
#Obtain columns with hyperlinks

def link_headings_picker(df):
    link_headings = []
    for heading in df.columns:
        if 'Hyperlink' in str(heading):
            link_headings.append(heading)
    return link_headings #A list of headings with hyperlinks

#Reverse hyperlink display
def reverse_link(x):
    value = str(x).replace('=HYPERLINK("', '').replace('")', '')
    return value

def clean_link_columns(df):
        
    link_headers_list = link_headings_picker(df)

    for link_header in link_headers_list:
        df[link_header] = df[link_header].apply(reverse_link)
        
    return df
    


# %%
#Excel to df with hyperlinks

def excel_to_df_w_links(uploaded_file):

    df = pd.read_excel(uploaded_file)
    
    wb = openpyxl.load_workbook(uploaded_file)
    
    sheets = wb.sheetnames
    
    ws = wb[sheets[0]]

    columns_w_links = link_headings_picker(df)

    for column in columns_w_links:
        
        column_index = list(df.columns).index(column) + 1 #Adding 1 because excel column starts with 1 not 0
        
        row_length = len(df)

        for row in range(0, row_length):
            
            row_index = row + 2 #Adding 1 because excel non-heading row starts with 2 while pandas at 0
            
            try:
	            new_cell = ws.cell(row=row_index, column=column_index).hyperlink.target
            
            except:

	            new_cell = (str(ws.cell(row=row_index, column=column_index).value))
            
            df.loc[row, column] = new_cell
            
    return df


# %%
# For NSW, function for columns which are lists to strings:
#NOT IN USE

nsw_list_columns = ['Catchwords', 'Legislation cited', 'Cases cited', 'Texts cited', 'Parties', 'Representation', 'Decision under appeal'] 

#'Decision under appeal' is a dictionary but the values of some keys are lists

def nsw_df_nsw_list_columns(df):
    df_new = df.copy()

    for heading in nsw_list_columns:
        if heading in df.columns:
            df_new[heading] = df[heading].astype(str)

    return df_new
    


# %%
#Obtain columns of lists

def list_cols_picker(df):

    list_columns = [] #Return list of columns which have list types
    
    columns_to_make_into_string_raw = df.applymap(lambda x: isinstance(x, list)).all()

    columns_to_make_into_string = columns_to_make_into_string_raw.index[columns_to_make_into_string_raw].tolist()

    for column in columns_to_make_into_string:
        list_columns.append(column)
    
    return list_columns
    
def list_col_to_str(df):
    
    for column in list_cols_picker(df):

        df[column] = df[column].astype(str)
    
    return df
    


# %%
#Capture columns with numerical data only and columns with non-numerical data only

def num_non_num_headings_picker(df):
    #Returns dictionary of numerical columns and non-numerical columns

    num_non_num_cols_dict = {"Numerical columns": [], "Non-numerical columns": []}

    nums_columns_raw = df.applymap(lambda x: isinstance(x, np.float32) or isinstance(x, float) or isinstance(x, int)).all()
    
    nums_columns = nums_columns_raw.index[nums_columns_raw].tolist()

    non_nums_columns_raw = list(df.columns)

    #Fill numerical columns with empty integer type
    
    for col in nums_columns:
        
        #df[col].fillna(int(), inplace = True) #Activate if wannt to replace nonetype cells in numerical columns with 0
        
        non_nums_columns_raw.remove(col)

        num_non_num_cols_dict["Numerical columns"].append(col)
    
    for column in non_nums_columns_raw:

        num_non_num_cols_dict["Non-numerical columns"].append(column)
        
    return num_non_num_cols_dict



# %%
def non_num_fill_blank(df):

    non_nums_columns = num_non_num_headings_picker(df)["Non-numerical columns"]  
    
    #Fill non-numerical columns with empty string type

    for column in non_nums_columns:
        
        df[column].fillna('', inplace = True)

    return df



# %%
def non_num_fill_blank(df):

    nums_columns = num_non_num_headings_picker(df)["Numerical columns"]

    #Fill numerical columns with integer type 0
    for col in nums_columns:
        
        df[col].fillna(int(0), inplace = True) #Activate if wannt to replace nonetype cells in numerical columns with 0

    return df



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

if 'df_master' not in st.session_state:

    st.session_state['df_master'] = pd.DataFrame([])

if 'df_individual_output' not in st.session_state:

    st.session_state['df_individual_output'] = pd.DataFrame([])

#Initalize df_uploaded:
if 'df_uploaded' not in st.session_state:

    st.session_state['df_uploaded'] = pd.DataFrame([])

#Initalize df_uploaded_key for the purpose of removing uploaded spreadsheets programatically
if "df_uploaded_key" not in st.session_state:
    st.session_state["df_uploaded_key"] = 0

#Initalize df_produced:
if 'df_produced' not in st.session_state:

    st.session_state['df_produced'] = pd.DataFrame([])

#Initalize df_to_analyse:
if 'df_to_analyse' not in st.session_state:

    st.session_state['df_to_analyse'] = pd.DataFrame([])

#Initalize edited_df:
if 'edited_df' not in st.session_state:

    st.session_state['edited_df'] = pd.DataFrame([])

#Initialize default instructions bound

default_instructions_bound = 10

print(f"The default maximum number of instructions per thread is {default_instructions_bound}.\n")

#Initialize instructions cap

if 'instructions_bound' not in st.session_state:
    st.session_state['instructions_bound'] = default_instructions_bound

#Initialize instructions counter

if 'instruction_left' not in st.session_state:

    st.session_state["instruction_left"] = default_instructions_bound

#Initialize default explain status

if 'explain_status' not in st.session_state:
    st.session_state["explain_status"] = False

#Initialize default show code status

if 'code_status' not in st.session_state:
    st.session_state["code_status"] = False

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
    st.session_state["response"] = ''

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
    st.session_state['q_and_a_provided'] = False

#Initialize clarifying questions and answers toggle
if 'q_and_a_toggle' not in st.session_state:
    st.session_state["q_and_a_toggle"] = False

#initialize spreadsheet produced to analyse or merge

#if 'analyse_df_produced' not in st.session_state:
    #st.session_state["analyse_df_produced"] = False

#if 'merge_df_produced' not in st.session_state:
    #st.session_state["merge_df_produced"] = False

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
extra_spreadsheet_warning = 'Another spreadsheet has already been imported. Please :red[REMOVE] that one first.'
spreadsheet_success = 'Your spreadsheet has been imported. Please scroll down.'



# %%
if st.button('RETURN to previous page'):

    st.switch_page(st.session_state.page_from)

st.header("You have chosen to :blue[analyse your spreadsheet].")

st.caption(f'PandasAI, [an open-source Python library](https://github.com/Sinaptik-AI/pandas-ai), provides the framework for analysing your spreadsheet with AI.')

#Open spreadsheet and personal details

if len(st.session_state.df_individual_output) > 0:
    
    if len(st.session_state.df_produced) == 0:

        st.success(spreadsheet_success)

    else:

        st.warning(extra_spreadsheet_warning)
        
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
            
            #df_uploaded = pd.read_excel(uploaded_file)
            
            df_uploaded = excel_to_df_w_links(uploaded_file)
    
        if extension == 'json':
            
            df_uploaded = pd.read_json(uploaded_file, orient= 'split')

        st.session_state.df_uploaded = df_uploaded

        if len(st.session_state.df_produced) == 0:
        
            st.success(spreadsheet_success)

        else:

            st.warning(extra_spreadsheet_warning)


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
            
            st.session_state['own_account'] = True
        
            st.markdown("""**:green[Please enter your name, email address and API key.]** You can sign up for a GPT account and pay for your own usage at https://platform.openai.com/signup. You can then find your API key at https://platform.openai.com/api-keys.
""")
                
            name_entry = st.text_input(label = "Your name", value = st.session_state.name_entry)
    
            if name_entry:
                st.session_state.df_master.loc[0, 'Your name'] = name_entry
            else:
                st.session_state.df_master.loc[0, 'Your name'] = st.session_state.name_entry
            
            email_entry = st.text_input(label = "Your email address", value = st.session_state.email_entry)

            if email_entry:
                st.session_state.df_master.loc[0, 'Your email address'] = email_entry
            else:
                st.session_state.df_master.loc[0, 'Your email address'] = st.session_state.email_entry

            gpt_api_key_entry = st.text_input(label = "Your GPT API key (mandatory)", value = st.session_state.gpt_api_key_entry)

            if gpt_api_key_entry:
                st.session_state.df_master.loc[0, 'Your GPT API key'] = gpt_api_key_entry
            else:
                st.session_state.df_master.loc[0, 'Your GPT API key'] = st.session_state.gpt_api_key_entry
            
            valdity_check = st.button('VALIDATE your API key')
        
            if valdity_check:
                
                api_key_valid = is_api_key_valid(gpt_api_key_entry)
                        
                if api_key_valid == False:
                    st.session_state['gpt_api_key_validity'] = False
                    st.error('Your API key is not valid.')
                    
                else:
                    st.session_state['gpt_api_key_validity'] = True
                    st.success('Your API key is valid.')
        
            st.markdown("""**:green[You can use the latest version of GPT model (gpt-4o),]** which is :red[10 times more expensive, per character] than the default model (gpt-3.5-turbo) which you can use for free.""")  
            
            gpt_enhancement_entry = st.checkbox('Use the latest GPT model', value = False)
        
            st.caption('For more on pricing for different GPT models, please see https://openai.com/api/pricing.')
            
            if gpt_enhancement_entry == True:
                #Reset AI first
                pai.clear_cache()
            
                st.session_state.gpt_model = "gpt-4o"
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
            st.session_state['own_account'] = False
        
            st.session_state.gpt_model = "gpt-3.5-turbo-0125"
        
            st.session_state.instructions_bound = default_instructions_bound
        
            st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]
            
            print('User GPT API key not entered. Using own API key instead.')
    
    else:
        st.session_state['own_account'] = False
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
#Order of spreadsheet to analyse
if len(st.session_state.df_produced) > 0:
    st.session_state.df_to_analyse = st.session_state.df_produced
    
elif len(st.session_state.df_individual_output) > 0:
    
    st.session_state.df_to_analyse = st.session_state.df_individual_output

else: #len(st.session_state.df_uploaded) > 0:
    
    st.session_state.df_to_analyse = st.session_state.df_uploaded

#Check if any spreadsheet is available for analysis
if len(st.session_state.df_to_analyse) > 0:

    df_to_analyse = st.session_state.df_to_analyse
    
else:
    st.warning('Please upload a spreadsheet.')
    quit()

st.subheader('Your spreadsheet')

#AI warning
if st.session_state.ai_choice == 'GPT':

    if st.session_state.gpt_model == 'gpt-3.5-turbo-0125':
        st.warning("A low-cost GPT model will process your spreadsheet and instructions. This model is *not* optimised for data analysis. Please email Ben Chen at ben.chen@sydney.edu.au if you'd like to use a better model.")

    if st.session_state.gpt_model == "gpt-4o":
        st.warning(f'An expensive GPT model will process your spreadsheet and instructions.')
    
else: #if st.session_state.ai_choice == 'BambooLLM':
    st.warning('An experimental AI model will process your spreadsheet and instructions. Please be cautious.')

spreadsheet_caption = 'To download, search within or maximise any spreadsheet, hover your mouse/pointer over its top right-hand corner and click the appropriate button.'

st.caption(spreadsheet_caption)

#Convert columns which are list type to string type
#Must do this, or pandasai won't work
#try:
df_to_analyse = list_col_to_str(df_to_analyse)

if len(list_cols_picker(df_to_analyse)) > 0:
    
    st.session_state["edited_df"] = st.data_editor(df_to_analyse,  column_config=link_heading_config)

    #conversion_msg_to_show += 'Lists have been converted to plain text. '
    
#except Exception_list as e_list:

    #print('Cannot display df without converting non-numeric data to string.' )

    #print(e_list)

#Errors to show later

conversion_msg_to_show = ''

#Last resort error, unlikely displayed
everything_error_to_show = 'Failed to make spreadsheet editable. '

#Obtain clolumns with hyperlinks

link_heading_config = {} 

link_headings_list = link_headings_picker(df_to_analyse)

#if len(link_headings_list) > 0:

    #try:
        
for link_heading in link_headings_list:
    
    link_heading_config[link_heading] = st.column_config.LinkColumn(display_text = 'Click')

df_to_analyse = clean_link_columns(df_to_analyse)

    #except Exception as e:

        #links_error = 'Hyperlinks have not been made clickable. '

        #conversion_msg_to_show += links_error
        
        #print(links_error)
        
        #print(e)

#Try to display df without converting lists or everything to string
try:
    
    st.session_state["edited_df"] = st.data_editor(df_to_analyse,  column_config=link_heading_config)

except Exception as e:

    print('Cannot display df without some conversion.' )
    
    print(e)

    #Try to convert all numerical data to string type

    try:

        non_num_cols = num_non_num_headings_picker(df_to_analyse)["Non-numerical columns"]

        df_to_analyse[non_num_cols] = df_to_analyse[non_num_cols].astype(str)
    
        non_num_error_msg ='Non-numeric data have been converted to plain text. '

        conversion_msg_to_show += non_num_error_msg

        #Activate below if wants to convert non-numerical columns with nonetype cells to empty string type
        
        #df_to_analyse = non_num_fill_blank(df_to_analyse)
        
        #if len(num_non_num_headings_picker(df_to_analyse)["Non-numerical columns"]) > 0:
    
            #non_num_cols_error = 'Nonetype cells in non-numerical columns have been converted to empty strings. '
                    
            #conversion_msg_to_show += non_num_cols_error

    except Exception as e_numeric:
        
        print('Cannot display df without converting everything to string.' )

        print(e_numeric)

        try:
        
            df_to_analyse = df_to_analyse.astype(str)
    
            st.session_state["edited_df"] = st.data_editor(df_to_analyse,  column_config=link_heading_config)
    
            non_textual_error_to_show = 'Non-textual data have been converted to plain text. '
        
            conversion_msg_to_show += non_textual_error_to_show

        except Exception as e_non_text:

            print('Cannot display df at all.' )
    
            print(e_numeric)

            st.session_state["edited_df"] = st.dataframe(df_to_analyse,  column_config=link_heading_config)
    
            conversion_msg_to_show += everything_error_to_show

#Tell users that the spreadsheet is editable if it indeed is

if everything_error_to_show not in conversion_msg_to_show:

    st.write('You can directly edit this spreadsheet.')

#New spreadsheet button

#if st.button('UPLOAD a new spreadsheet'):
    #st.session_state.df_uploaded_key += 1
    #clear_most_cache()
    #st.rerun()

#Show remove button
if st.button('REMOVE this spreadsheet', type = 'primary'):
    
    st.session_state.df_uploaded_key += 1
    
    for df_key in {'df_produced', 'df_individual_output', 'df_uploaded'}:
        
        if isinstance(st.session_state[df_key], pd.DataFrame):

            if st.session_state[df_key].equals(st.session_state.edited_df):
            #if st.session_state[df_key].sort_index(inplace=True) == st.session_state.edited_df.sort_index(inplace=True):
                st.session_state.pop(df_key)
                st.write(f'{df_key} removed.')
                #pause.seconds(5)

    #Disable unnecessary buttons and pre-filled prompt
    conversion_msg_to_show = ''
    st.session_state['prompt_prefill'] = ''
    st.session_state['q_and_a_provided'] = False
    st.session_state.q_and_a_toggle = False

    st.rerun()

#Display error or success messages
if ((len(conversion_msg_to_show) > 0) or (len(st.session_state.df_produced) > 0) or ( st.session_state.q_and_a_provided == True)):
    
    if st.toggle(label = 'Display messages', value = True):
    
        if len(conversion_msg_to_show) > 0:
            st.warning(conversion_msg_to_show)
    
        #Note importation of AI produced spreadsheet
        if len(st.session_state.df_produced) > 0:
            st.success(f'The spreadsheet produced by {st.session_state.ai_choice} has been imported.')
    
        if st.session_state.q_and_a_provided == True:
            st.success('Your clarifying answers have been added to your instructions. Please click ASK again.')

#Disable toggle for clarifying questions and answers BEFORE asking AI again
if st.session_state.q_and_a_provided == True:
    st.session_state.q_and_a_toggle = False
    #Remove prefill after importation
    #st.session_state['prompt_prefill'] = ''


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
    agent = agent(ai_choice = st.session_state.ai_choice, 
                  key = st.session_state.gpt_api_key, 
                  gpt_model_choice = st.session_state.gpt_model, 
                  instructions_bound = st.session_state.instructions_bound, 
                  df = st.session_state.edited_df,
                 )

except Exception as e:
    st.error('Please double-check your API key.')
    st.exception(e)
    quit()

#Area for entering instructions
st.subheader(f'Enter your instructions for {st.session_state.ai_choice}')

st.write(f':green[Please give your instructions in sequence.] {ai_model_printing(st.session_state.ai_choice, st.session_state.gpt_model)} will respond to at most {st.session_state.instructions_bound} instructions. It will **only** use  the data and/or information from your spreadsheet.')

prompt = st.text_area(f'You may enter at most 1000 characters.', value = st.session_state.prompt_prefill, height= 200, max_chars=1000) 

st.session_state.prompt = prompt

st.caption("Please reach out to Ben at ben.chen@sydney.edu.au if you'd like give more or longer instructions.")

#Generate explain button
if st.session_state.ai_choice in {'GPT', 'LangChain'}:

    col1, col2, col3, col4 = st.columns(4, gap = 'small')

    with col1:
        #Explain 
        explain_toggle = st.toggle('Explain', help = f'Get {st.session_state.ai_choice} to explain its response.')
    
        if explain_toggle:
            st.session_state.explain_status = True
        else:
            st.session_state.explain_status = False

    with col2:
        #Get code 
        code_toggle = st.toggle('Code', help = f'Get {st.session_state.ai_choice} to produce a code.')
    
        if code_toggle:
            st.session_state.code_status = True
        else:
            st.session_state.code_status = False
    with col3:
        #Clarification questions toggle
        if st.session_state.ai_choice in {'GPT', 'BambooLLM'}:
            #if len(str(st.session_state.response)) > 0:
            clarification_questions_toggle = st.toggle(label = 'Suggestions', key = 'q_and_a_toggle', help = f'Get clarifying questions to help draft your questions or instructions.')
        
history_on = st.toggle(label = 'Display all instructions and responses')

#else:
    #st.session_state.explain_status = False
    #st.session_state.code_status = False


# %% [markdown]
# ## Buttons

# %%
#col1a, col2a, col3a, col4a = st.columns(4, gap = 'small')

#with col1a:
ask_button = st.button("ASK")

#with col2a:
reset_button = st.button('RESET to get fresh responses', type = 'primary')#, help = f"Get fresh responses from {st.session_state.ai_choice}")


# %%
# Generate output

#if st.button('Test'):

    #pandasai_ask_test()

    #st.dataframe(st.session_state.edited_df)

    #non_num_cols = num_non_num_headings_picker(df_to_analyse)["Non-numerical columns"]

    #st.session_state.edited_df[non_num_cols] = st.session_state.edited_df[non_num_cols].astype(str)

    #st.dataframe(st.session_state.edited_df)


#if st.button("ASK"):

if ask_button:

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
        st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": float(0), "tokens": float(0),   "role": "assistant", "content": {'error': no_more_instructions}})

        quit()

    elif len(st.session_state.prompt) == 0:
        st.warning("Please enter some instruction.")

        quit()

    else:
        #Close question and answer section 

        #Change q_and_a_provided status
        st.session_state['q_and_a_provided'] = False
        #Close clarifying questions form brielif
        #st.session_state["q_and_a_toggle"] = False
        clarification_questions_toggle = False

        if st.session_state.ai_choice in {'GPT', 'BambooLLM'}:
            
            pandasai_ask()

        else: #if st.session_state.ai_choice == 'LangChain':

            langchain_ask()
                        
        #Display number of instructionsl left
        st.session_state.instruction_left -= 1
        instructions_left_text = f"*You have :orange[{st.session_state.instruction_left}] instructions left.*"
        st.write(instructions_left_text)

        #Keep record of instructions left
        st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": float(0), "tokens": float(0),   "role": "assistant", "content": {'answer': instructions_left_text}})


# %%
#Buttons for importing any df produced    

#For Pandasai
if st.session_state.ai_choice in {'GPT', 'BambooLLM'}:

    if isinstance(st.session_state.response, pd.DataFrame):

        col1b, col2b = st.columns(2, gap = 'small')

        with col1b:
            pandasai_analyse_button = st.button('ANALYSE the spreadsheet produced only')
        
        with col2b:
            pandasai_merge_button = st.button('MERGE with your spreadsheet')

        if pandasai_analyse_button:
            pandasai_analyse_df_produced()

        if pandasai_merge_button:
            pandasai_merge_df_produced()

#For Langchain,
if st.session_state.ai_choice == 'LangChain':

    if "dataframe" in st.session_state.response_json:
        
        if st.session_state.response_json["dataframe"]:

            col1c, col2c = st.columns(2, gap = 'small')

            with col1c:
                langchain_analyse_button = st.button('ANALYSE the spreadsheet produced only')
            
            with col2c:
                langchain_merge_button = st.button('MERGE with your spreadsheet')
    
            if langchain_analyse_button:
                langchain_analyse_df_produced()
    
            if langchain_merge_button:
                langchain_merge_df_produced()


# %%
#Reset button

#if st.button('RESET to get fresh responses', type = 'primary'):#, help = "click to engage with the AI afresh."):
if reset_button:
    pai.clear_cache()
    st.session_state['response'] = '' #Adding this to hide clarifying questions and answers toggle upon resetting
    #clear_most_cache()
    st.rerun()


# %%
#Clarifying questions form

if st.session_state.ai_choice in {'GPT', 'BambooLLM'}:
    #if len(str(st.session_state.response)) > 0:
    #if st.toggle(label = 'Suggestions', key = 'q_and_a_toggle', help = f'Get clarifying questions from {st.session_state.ai_choice} to help draft your instructions.'):
    if clarification_questions_toggle:
    
        with pandasai_get_openai_callback() as cb, st.spinner("Running..."):
            prompt = st.session_state.prompt

            #if len(prompt) > 0:
        
            clarifying_questions = agent.clarification_questions(prompt)

            st.session_state.clarifying_questions = clarifying_questions

            #Keep record of clarifying questions
            st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": cb.total_cost, "tokens": {cb.total_tokens},   "role": "assistant", "content": {'answer': clarifying_questions}})
                        
        if len(clarifying_questions) == 0:
            st.error(f'{st.session_state.ai_choice} did not have any clarifying questions. Please amend your instructions and try again.')
        
        else: #if len(clarifying_questions) > 0:
            with st.form("clarifying_questions_form"):
        
                st.write(f'Please consider the following clarifying questions from {st.session_state.ai_choice}. You may answer them here, or redraft your questions or instructions in light of them.')
    
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
        
                #Acivate if want to display tokens and costs only if own account active
                #if st.session_state['own_account'] == True:
                    
                clarifying_questions_cost_tokens = f'(These clarifying questions costed USD $ {round(cb.total_cost, 5)} to produce and totalled {cb.total_tokens} tokens.)'
                st.write(clarifying_questions_cost_tokens)
                st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": cb.total_cost, "tokens": {cb.total_tokens},   "role": "assistant", "content": {'answer': clarifying_questions_cost_tokens}})

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
                    st.session_state.messages.append({"time": str(datetime.now()), "cost (usd)": cb.total_cost, "tokens": {cb.total_tokens},   "role": "user", "content": {"prompt": st.session_state.clarifying_answers}})
                    
                    #Change clarifying questions and answers status
                    st.session_state['q_and_a_provided'] = True
    
                    st.rerun()
                    


# %%
#Displaying chat history
#history_on = st.toggle(label = 'Display all instructions and responses')

if history_on:
#if st.toggle(label = 'Display all instructions and responses'):

    #Check if history exists
    if len(st.session_state.messages) == 0:
        st.warning("You haven't given any instructions or questions yet.")
        
    #Check if history exists
    else: #if len(st.session_state.messages) > 0:

        st.subheader('Conversation')

        st.write('Instructions and responses are displayed from earliest to latest.')

        st.caption(spreadsheet_caption)

        # Display chat messages from history on app rerun
        for message in st.session_state.messages:
            st.caption(' ')
            st.caption(message["time"][0:19])
            with st.chat_message(message["role"]):

                #For pandas ai responses
                if st.session_state.ai_choice in {'GPT', 'BambooLLM'}:
                    
                    if isinstance(message["content"], dict):

                        if 'prompt' in message["content"]:
                            st.write(message["content"]['prompt'])
                        
                        if 'answer' in message["content"]:                           
                            st.write(message["content"]['answer'])

                            #Display caption if response is a dataframe
                            if isinstance(message["content"]['answer'], pd.DataFrame):
                                
                                st.caption(spreadsheet_caption)

                        if 'error' in message["content"]:                           
                            st.error(message["content"]['error'])

                        if 'image' in message["content"]:                           
                            st.image(message["content"]['image'], use_column_width = "never")
                            st.caption('Right click to save this image.')

                        if 'matplotlib figure' in message["content"]:
                            st.pyplot(fig = message["content"]['matplotlib figure'])
                            st.caption('Right click to save this image.')
                            
                        if 'code' in message["content"]:
                            st.code(message["content"]['code'])

                        #else:                           
                            #st.write(message["content"])
                    else:
                        st.write(message["content"])
                
                else: #if st.session_state.ai_choice == 'LangChain':
                    if isinstance(message["content"], dict):
                        langchain_write(message["content"])
                    else: #not isinstance(message["content"], str)
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
