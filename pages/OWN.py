# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
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
import requests
import numpy as np
import re
import datetime
from datetime import date
from datetime import datetime
from dateutil import parser
from dateutil.relativedelta import *
from datetime import datetime, timedelta
import sys
import pause
import requests
import os
import io
import fitz

#Streamlit
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste

#OpenAI
import openai
import tiktoken

#Google
from google.oauth2 import service_account


# %%
#Get current directory
current_dir = os.getcwd()


# %%
#today
today_in_nums = str(datetime.now())[0:10]

# %%
# Generate placeholder list of errors
errors_list = set()


# %%
#Create function for saving responses and results
def convert_df_to_json(df):
    return df.to_json(orient = 'split', compression = 'infer')

def convert_df_to_csv(df):
   return df.to_csv(index=False).encode('utf-8')

# %%
#Title of webpage
st.set_page_config(
   page_title="Empirical Legal Research Kickstarter (OWN)",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Pause

scraper_pause = 5

print(f"\nThe pause between GPT prompting is {scraper_pause} second.")


# %% [markdown]
# # Own Files

# %%
#function to create dataframe
@st.cache_data
def create_df():

    #submission time
    timestamp = datetime.now()

    #Personal info entries
    
    name = name_entry
    email = email_entry
    gpt_api_key = gpt_api_key_entry

    #File counter bound
    
    files_counter_bound_ticked = files_counter_bound_entry
    if int(files_counter_bound_ticked) > 0:
        files_counter_bound = 10
    else:
        files_counter_bound = 10000

    #GPT choice and entry
    gpt_activation_status = gpt_activation_entry
    gpt_questions = gpt_questions_entry[0: 1000]

    #Get uploaded file names

    file_names_list = []

    for uploaded_file in uploaded_files:
        file_names_list.append(uploaded_file.name)

    new_row = {'Processed': '',
           'Timestamp': timestamp,
           'Your name': name, 
           'Your email address': email, 
           'Your GPT API key': gpt_api_key, 
            'Your uploaded files' : str(file_names_list), 
           'Maximum number of files': files_counter_bound, 
           'Enter your question(s) for GPT': gpt_questions, 
          }

    df_master_new = pd.DataFrame(new_row, index = [0])
    
#    df_master_new.to_json(current_dir + '/df_master.json', orient = 'split', compression = 'infer')
#    df_master_new.to_excel(current_dir + '/df_master.xlsx', index=False)

#    if len(df_master_new) > 0:
        
    return df_master_new

#    else:
#        return 'Error: spreadsheet of reponses NOT generated.' 


# %%
#Define format functions for GPT questions    

#Create function to split a string into a list by line
def split_by_line(x):
    y = x.split('\n')
    for i in y:
        if len(i) == 0:
            y.remove(i)
    return y

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
# Function to convert each uploaded file to file name, text
@st.cache_data
def file_to_text(uploaded_file):
    file_pair = {'File name' : '', 'file_text': ''}

    #Get file name
    file_pair['File name']=uploaded_file.name

    #Get file data
    bytes_data = uploaded_file.getvalue()

    #Convert file data to text

    #File extension

    extension = ''
    try:
        extension = file_pair['File name'].split('.')[-1].lower()
    except Exception as e:
        print(e)

    if extension in ['txt', 'cs', 'xml', 'json']:
        doc = fitz.open(stream=bytes_data, filetype="txt")

    else:
        doc = fitz.open(stream=bytes_data)
    
    text_list = ''
    for page in doc:
        text_page = '[Start of page] ' + page.get_text() + ' [End of page]' 
        text_list = text_list + text_page

    file_pair['file_text'] = text_list

    return file_pair


# %% [markdown]
# # GPT functions and parameters

# %%
#Module and costs

GPT_model = "gpt-3.5-turbo-0125"

GPT_input_cost = 1/1000*0.0005 
GPT_output_cost = 1/1000*0.0015

#Upperbound on number of engagements with GPT

GPT_use_bound = 3

print(f"\nPrior number of GPT uses is capped at {GPT_use_bound} times.")

#Upperbound on the length of questions for GPT

answers_characters_bound = 1000

print(f"\nQuestions for GPT are capped at {answers_characters_bound} characters.")

#Upperbound on number of Files to scrape

files_counter_bound = 10

print(f"\nNumber of files to process per request is capped at {files_counter_bound}.")

#Lowerbound on length of File text to proccess, in tokens

file_text_lower_bound = 500

print(f"\nThe lower bound on lenth of File text to process is {file_text_lower_bound} tokens.")


# %%
#Define function to determine eligibility for GPT use

#Define a list of privileged email addresses with unlimited GPT uses

privileged_emails = st.secrets["secrets"]["privileged_emails"].replace(' ', '').split(',')

def prior_GPT_uses(email_address, df_online):
    # df_online variable should be the online df_online
    prior_use_counter = 0
    for i in df_online.index:
        if ((df_online.loc[i, "Your email address"] == email_address) 
            and (len(df_online.loc[i, "Processed"])>0)
           ):
            prior_use_counter += 1
    if email_address in privileged_emails:
        return 0
    else:
        return prior_use_counter

#Define function to check whether email is educational or government
def check_edu_gov(email_address):
    #Return 1 if educational or government, return 0 otherwise
    end=email_address.split('@')[1]
    if (('.gov' in end) or ('.edu' in end) or ('.ac' in end)):
        return 1
    else:
        return 0



# %%
#Tokens estimate preliminaries
encoding = tiktoken.get_encoding("cl100k_base")
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
#Tokens estimate function
def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

#Define File input function for JSON approach

#Token limit covering both GTP input and GPT output is 16385, each token is about 4 characters
tokens_cap = int(16385 - 2500)

def file_prompt(file_pair):
                
    file_content = 'Based on the following document:  """'+ file_pair['file_text'] + '""",'

    file_content_tokens = num_tokens_from_string(file_content, "cl100k_base")
    
    if file_content_tokens <= tokens_cap:
        
        return file_content

    else:
                
        file_chars_capped = int(tokens_cap*4)
        
        file_string_trimmed = file_pair['file_text'][ :int(file_chars_capped/2)] + file_pair['file_text'][-int(file_chars_capped/2): ]
        
        file_content_capped = 'Based on the following document:  """'+ file_string_trimmed + '""",'
        
        return file_content_capped



# %%
#Define system role content for GPT
role_content = 'You are a legal research assistant helping an academic researcher to answer questions about a document. You will be provided with the document in text form. Please answer questions based only on information contained in the document. Where your answer comes from a specific page or section of the document, provide the page number or section as part of your answer. If you cannot answer any of the questions based on the document, do not make up information, but instead write "answer not found".'

intro_for_GPT = [{"role": "system", "content": role_content}]


# %%
#Define GPT answer function for answers in json form, YES TOKENS
#IN USE

def GPT_json_tokens(questions_json, file_pair, API_key):
    #'question_json' variable is a json of questions to GPT
    #'jugdment' variable is a file_pair   

    file_for_GPT = [{"role": "user", "content": file_prompt(file_pair) + 'you will be given questions to answer in JSON form.'}]
        
    #Create answer format
    
    q_keys = [*questions_json]
    
    answers_json = {}
    
    for q_index in q_keys:
        answers_json.update({q_index: 'Your answer to the question with index ' + q_index + '. State specific page numbers in the File or specific sections in the metadata.'})
    
    #Create questions, which include the answer format
    
    question_for_GPT = [{"role": "user", "content": str(questions_json).replace("\'", '"') + ' Give responses in the following JSON form: ' + str(answers_json).replace("\'", '"')}]
    
    #Create messages in one prompt for GPT
    messages_for_GPT = intro_for_GPT + file_for_GPT + question_for_GPT
    
#   return messages_for_GPT

    #os.environ["OPENAI_API_KEY"] = API_key

    openai.api_key = API_key
    
    #client = OpenAI()
    
    try:
        #completion = client.chat.completions.create(
        completion = openai.chat.completions.create(
            model=GPT_model,
            messages=messages_for_GPT, 
            response_format={"type": "json_object"}
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
            answers_json[q_index] = error
        
        return [answers_json, 0, 0]



# %%
#Define GPT function for each respondent's dataframe, index by File then question, with input and output tokens given by GPT itself
#IN USE

#The following function DOES NOT check for existence of questions for GPT
    # To so check, active line marked as #*
def engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, API_key):
    # Variable questions_json refers to the json of questions
    # Variable df_individual refers to each respondent's df
    # Variable activation refers to status of GPT activation (real or test)
    # The output is a new JSON for the relevant respondent with new columns re:
        # "File length in tokens (up to 14635 given to GPT)"
        # 'GPT cost estimate (USD excl GST)'
        # 'GPT time estimate (seconds)'
        # GPT questions/answers

    #os.environ["OPENAI_API_KEY"] = API_key

    openai.api_key = API_key
    
    #client = OpenAI()
    
    question_keys = [*questions_json]
    
    for file_index in df_individual.index:
        
        file_pair = df_individual.to_dict('index')[file_index]
        
        #Calculate and append number of tokens of File, regardless of whether given to GPT
        file_tokens = num_tokens_from_string(str(file_pair), "cl100k_base")
        df_individual.loc[file_index, "File length in tokens (up to 14635 given to GPT)"] = file_tokens       

        #Indicate whether File truncated
        
        df_individual.loc[file_index, "File truncated (if given to GPT)?"] = ''       
        
        if file_tokens <= tokens_cap:
            
            df_individual.loc[file_index, "File truncated (if given to GPT)?"] = 'No'
            
        else:
            
            df_individual.loc[file_index, "File truncated (if given to GPT)?"] = 'Yes'

        #Create columns for respondent's GPT cost, time
        df_individual.loc[file_index, 'GPT cost estimate (USD excl GST)'] = ''
        df_individual.loc[file_index, 'GPT time estimate (seconds)'] = ''
                
        #Calculate GPT start time

        GPT_start_time = datetime.now()

        #Depending on activation status, apply GPT_json function to each File, gives answers as a string containing a dictionary

        if int(GPT_activation) > 0:
            GPT_file_pair = GPT_json_tokens(questions_json, file_pair, API_key) #Gives [answers as a JSON, output tokens, input tokens]
            answers_dict = GPT_file_pair[0]
        
        else:
            answers_dict = {}    
            for q_index in question_keys:
                #Increases File index by 2 to ensure consistency with Excel spreadsheet
                answer = 'Placeholder answer for ' + ' File ' + str(int(file_index) + 2) + ' ' + str(q_index)
                answers_dict.update({q_index: answer})
            
            #Own calculation of GPT costs for Placeholder answer fors

            #Calculate capped File tokens

            file_capped_tokens = num_tokens_from_string(file_prompt(file_pair), "cl100k_base")

            #Calculate questions tokens and cost

            questions_tokens = num_tokens_from_string(str(questions_json), "cl100k_base")

            #Calculate other instructions' tokens

            other_instructions = role_content + 'you will be given questions to answer in JSON form.' + ' Give responses in the following JSON form: '

            other_tokens = num_tokens_from_string(other_instructions, "cl100k_base") + len(question_keys)*num_tokens_from_string("GPT question x:  Your answer to the question with index GPT question x. State specific page numbers in the File or specific sections in the metadata.", "cl100k_base")

            #Calculate number of tokens of answers
            answers_tokens = num_tokens_from_string(str(answers_dict), "cl100k_base")

            input_tokens = file_capped_tokens + questions_tokens + other_tokens
            
            GPT_file_pair = [answers_dict, answers_tokens, input_tokens]

        #Create GPT question headings and append answers to individual spreadsheets

        for question_index in question_keys:
            question_heading = question_index + ': ' + questions_json[question_index]
            df_individual.loc[file_index, question_heading] = answers_dict[question_index]

        #Calculate and append GPT finish time and time difference to individual df
        GPT_finish_time = datetime.now()
        
        GPT_time_difference = GPT_finish_time - GPT_start_time

        df_individual.loc[file_index, 'GPT time estimate (seconds)'] = GPT_time_difference.total_seconds()

        #Calculate GPT costs

        GPT_cost = GPT_file_pair[1]*GPT_output_cost + GPT_file_pair[2]*GPT_input_cost

        #Calculate and append GPT cost to individual df
        df_individual.loc[file_index, 'GPT cost estimate (USD excl GST)'] = GPT_cost
    
    return df_individual



# %%
#Obtain parameters

def run(df_master, uploaded_files):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['Enter your question(s) for GPT'] = df_master['Enter your question(s) for GPT'][0: answers_characters_bound].apply(split_by_line)
    df_master['questions_json'] = df_master['Enter your question(s) for GPT'].apply(GPT_label_dict)
    
    #Create Files file
    Files_file = []
    
    #Convert uploaded files to text
    
    files_counter_bound = int(df_master.loc[0, 'Maximum number of files'])

    file_counter = 0 
    
    for uploaded_file in uploaded_files:
        if file_counter <= files_counter_bound:
            file_pair = file_to_text(uploaded_file)
            Files_file.append(file_pair)
            file_counter += 1
    
    #Create and export json file with search results
    json_individual = json.dumps(Files_file, indent=2)
    
    df_individual = pd.read_json(json_individual)

#    df_individual.set_index('File name')
    
    #Instruct GPT
    
    API_key = df_master.loc[0, 'Your GPT API key'] 
    
    #apply GPT_individual to each respondent's File spreadsheet
    
    GPT_activation = gpt_activation_entry

    questions_json = df_master.loc[0, 'questions_json']
            
    #Engage GPT
    df_updated = engage_GPT_json_tokens(questions_json, df_individual, GPT_activation, API_key)

    df_updated.pop('file_text')
    
    return df_updated


# %% [markdown]
# # Streamlit form, functions and parameters

# %%
acceptable_types = ["pdf", "txt", "xps", "epub", "mobi", "fb2", "cbz", "svg", 
                   # "jpg", "jpeg", "png", "bmp", "gif", "tiff", "pnm", "pgm", "pbm", "ppm", "pam", "jxr", "jpx", "jp2", "psd"
                   ]


# %%
#Create form

with st.form("GPT_input_form") as df_responses:
    return_button = st.form_submit_button('RETURN to previous page')
    
    st.header(f"You have selected to study :blue[your own documents].")
    
    #Search terms

#    st.header("File Search Criteria")
    
    st.markdown("""**Please upload your files.** This program will 'read' up to 10 files and up to about 10,413 words per file.
""")

    st.markdown("""The following file formats are supported: **(searchable) PDF**, **TXT**, XPS, EPUB, MOBI, FB2, CBZ, SVG. :red[(Microsoft Word documents are not yet supported.)]
    """)

    uploaded_files = st.file_uploader("Choose your file(s)", type = acceptable_types, accept_multiple_files=True)

    st.caption('During the pilot stage, the number of files and the number of words per file to read are capped. Please reach out to Ben at ben.chen@sydney.edu.au should you wish to cover more files or more words per file.')

    files_counter_bound_entry = files_counter_bound

    st.header("Use GPT as Your Research Assistant")

    st.markdown("**GPT can answer your questions about each file uploaded by you.**")
    
#    st.markdown("**You have three (3) opportunities to engage with GPT through the Empirical Legal Research Kickstarter. Would you like to use one (1) of these opportunities now?**")

    #gpt_activation_entry = st.checkbox('Tick to use GPT', value = False)

    gpt_activation_entry = 1

    st.markdown("""You must enter your name and email address if you wish to use GPT.
""")
    #    st.markdown("""You must enter an API key if you wish to use GPT to analyse more than 10 Files. 
#To obtain an API key, first sign up for an account with OpenAI at 
#https://platform.openai.com/signup. You can then find your API key at https://platform.openai.com/api-keys.
#""")
    
    name_entry = st.text_input("Your name")
    email_entry = st.text_input("Your email address")
#    gpt_api_key_entry = st.text_input("Your GPT API key")

    st.caption("Released by OpenAI, GPT is a family of large language models (ie a generative AI that works on language). Engagement with GPT is costly and funded by a grant.  Ben's own experience suggests that it costs approximately USD \$0.003-\$0.008 (excl GST) per File. The exact cost for answering a question about a File depends on the length of the question, the length of the File, and the length of the answer produced (as elaborated at https://openai.com/pricing for model gpt-3.5-turbo-0125). You will be given ex-post cost estimates.")

    st.subheader("Enter your question(s) for GPT")
    
    st.markdown("""You may enter one or more questions. **Please enter one question per line or per paragraph.**

GPT is instructed to avoid giving answers which cannot be obtained from the relevant file itself. This is to minimise the risk of giving incorrect information (ie hallucination).

You may enter at most 1000 characters here.
    """)

    gpt_questions_entry = st.text_area("", height= 200, max_chars=1000) 

    st.caption("Answers to your questions will be generated by model gpt-3.5-turbo-0125. Due to a technical limitation, the model will be instructed to 'read' up to approximately 10,413 words from each file.")

    st.header("Consent")

    st.markdown("""By running the Empirical Legal Research Kickstarter, you agree that the data and/or information this form provides will be temporarily stored on one or more of Ben Chen's electronic devices and/or one or more remote servers for the purpose of producing an output containing data in relation to your uploaded file(s). Any such data and/or information may also be given to GPT for the same purpose should you choose to use GPT.
""")
    
    consent =  st.checkbox('Yes, I agree.', value = False)

    st.markdown("""If you do not agree, then please feel free to close this form. Any data or information this form provides will neither be received by Ben Chen nor be sent to GPT.
""")

    st.header("Next Steps")

    st.markdown("""**:orange[Once your files are uploaded,] you can run the Empirical Legal Research Kickstarter.** A spreadsheet which hopefully has the data you seek will be available for download in about 2-3 minutes.

You can also download a record of your responses.
    
""")

    run_button = st.form_submit_button('RUN the Empirical Legal Research Kickstarter')

    keep_button = st.form_submit_button('DOWNLOAD your form responses')

#    test_button = st.form_submit_button('Test')




# %% [markdown]
# # Save and run

# %%
#if test_button:
#    st.write(f"{len(uploaded_files)}")
#    for uploaded_file in uploaded_files:
#        output = file_to_text(uploaded_file)
#        st.write(output)


# %%
if run_button:

    if len(uploaded_files) == 0:

        st.write('You must upload some file(s).')

    elif int(consent) == 0:
        st.write("You must click on 'Yes, I agree.' to run the Empirical Legal Research Kickstarter.")

    elif len(gpt_questions_entry) < 5:

        st.write('You must enter some question(s) for GPT.')

    elif '@' not in str(email_entry):
        st.write('You must enter a valid email address to use GPT.')

    else:

        st.markdown("""Your results will be available for download soon. The estimated waiting time is about 2-3 minutes.

If the program produces an error (in red) or an unexpected spreadsheet, please double-check your uploaded file(s) and try again.
""")
        
        #Using own GPT
    
        gpt_api_key_entry = st.secrets["openai"]["gpt_api_key"]
    
        #Create spreadsheet of responses
        df_master = create_df()
    
        #Obtain google spreadsheet
    
       # conn = st.connection("gsheets_uk", type=GSheetsConnection)
        #df_google = conn.read()
        #df_google = df_google.fillna('')
        #df_google=df_google[df_google["Processed"]!='']
        
        #Upload placeholder record onto Google sheet
        #df_plaeceholdeer = pd.concat([df_google, df_master])
        #conn.update(worksheet="UK", data=df_plaeceholdeer, )

        #Produce results

        df_individual_output = run(df_master, uploaded_files)

        #Keep record on Google sheet
        
        df_master["Processed"] = datetime.now()

        df_master.pop("Your GPT API key")
        
        #df_to_update = pd.concat([df_google, df_master])
        
        #conn.update(worksheet="UK", data=df_to_update, )

        st.write("Your results are now available for download. Thank you for using the Empirical Legal Research Kickstarter.")
        
        #Button for downloading results
        output_name = df_master.loc[0, 'Your name'] + '_' + str(today_in_nums) + '_results'

        csv_output = convert_df_to_csv(df_individual_output)
        
        ste.download_button(
            label="Download your results as a CSV (for use in Excel etc)", 
            data = csv_output,
            file_name= output_name + '.csv', 
            mime= "text/csv", 
#            key='download-csv'
        )

        json_output = convert_df_to_json(df_individual_output)
        
        ste.download_button(
            label="Download your results as a JSON", 
            data = json_output,
            file_name= output_name + '.json', 
            mime= "application/json", 
        )





# %%
if keep_button:

    if len(uploaded_files) == 0:

        st.write('You must upload some file(s).')

    elif len(gpt_questions_entry) < 5:

        st.write('You must enter some question(s) for GPT.')

    else:

        #Using own GPT API key here
    
        gpt_api_key_entry = ''
        
        df_master = create_df()
    
        df_master.pop("Your GPT API key")
    
        df_master.pop("Processed")
    
        responses_output_name = df_master.loc[0, 'Your name'] + '_' + str(today_in_nums) + '_responses'
    
        #Produce a file to download
    
        csv = convert_df_to_csv(df_master)
        
        ste.download_button(
            label="Download as a CSV (for use in Excel etc)", 
            data = csv,
            file_name=responses_output_name + '.csv', 
            mime= "text/csv", 
    #            key='download-csv'
        )
    
        json = convert_df_to_json(df_master)
        
        ste.download_button(
            label="Download as a JSON", 
            data = json,
            file_name= responses_output_name + '.json', 
            mime= "application/json", 
        )


# %%
if return_button:

    st.switch_page("Home.py")
