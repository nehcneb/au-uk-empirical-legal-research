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
from dateutil import parser
from dateutil.relativedelta import *
from datetime import datetime, timedelta
import sys
import pause
import requests
from bs4 import BeautifulSoup, SoupStrainer
import httplib2
from urllib.request import urlretrieve
import os
import PyPDF2
import io
from io import BytesIO
import copy

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste
from streamlit_extras.stylable_container import stylable_container

#OpenAI
import openai
import tiktoken

#Google
#from google.oauth2 import service_account

#Excel
from pyxlsb import open_workbook as open_xlsb

# %%
#Import functions
from common_functions import own_account_allowed, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, str_to_int, pdf_judgment, streamlit_timezone
#Import variables
from common_functions import today_in_nums, today, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, list_range_check, au_date, streamlit_cloud_date_format, save_input

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")

print(f"The lower bound on lenth of judgment text to process is {judgment_text_lower_bound} tokens.\n")

# %%
#Import functions and variables
from common_functions import open_page, clear_cache_except_validation_df_master, clear_cache, tips, link

# %%
# Go back to home page if this page is the first page
if 'page_from' not in st.session_state:
    clear_cache()
    st.switch_page("Home.py")

# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from gpt_functions import split_by_line, GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from gpt_functions import question_characters_bound, role_content #, intro_for_GPT

# %%
#For checking questions and answers
from common_functions import check_questions_answers

from gpt_functions import questions_check_system_instruction, GPT_questions_check, checked_questions_json, answers_check_system_instruction

if check_questions_answers() > 0:
    print(f'By default, questions and answers are checked for potential privacy violation.')
else:
    print(f'By default, questions and answers are NOT checked for potential privacy violation.')

# %%
#Module, costs and upperbounds

#Initialize default GPT settings

if 'gpt_model' not in st.session_state:
    st.session_state['gpt_model'] = "gpt-4o-mini"

#Initialize API key
if 'gpt_api_key' not in st.session_state:

    st.session_state['gpt_api_key'] = st.secrets["openai"]["gpt_api_key"]

#if 'judgments_counter_bound' not in st.session_state:
    #st.session_state['judgments_counter_bound'] = default_judgment_counter_bound


# %%
#Jurisdiction specific instruction and functions

def gpt_run(jurisdiction_page, df_master):

    if jurisdiction_page == 'pages/HCA.py':
        
        system_instruction = role_content
        
        from pages.HCA import hca_run, hca_collections, hca_search, hca_search_results_to_judgment_links, hca_pdf_judgment, hca_meta_labels_droppable, hca_meta_judgment_dict, hca_meta_judgment_dict_alt, hca_mnc_to_link_browse, hca_citation_to_link, hca_mnc_to_link, hca_load_data, hca_data_url, hca_df, hca_judgment_to_exclude, hca_search_results_to_judgment_links_filtered_df
    
        run = copy.copy(hca_run)

    if jurisdiction_page == 'pages/NSW.py':
        
        system_instruction = role_content

        from nswcaselaw.search import Search
        
        from pages.NSW import nsw_run, nsw_meta_labels_droppable, nsw_courts, nsw_courts_positioning, nsw_default_courts, nsw_tribunals, nsw_tribunals_positioning, nsw_court_choice, nsw_tribunal_choice, nsw_date, nsw_link, nsw_short_judgment, nsw_tidying_up
    
        run = copy.copy(nsw_run)
    
    if jurisdiction_page == 'pages/FCA.py':
        
        system_instruction = role_content
        
        from pages.FCA import fca_run, fca_courts, fca_courts_list, fca_search, fca_search_url, fca_search_results_to_judgment_links, fca_link_to_doc, fca_metalabels, fca_metalabels_droppable, fca_meta_judgment_dict, fca_pdf_name_mnc_list, fca_pdf_name
    
        run = copy.copy(fca_run)

    if jurisdiction_page == 'pages/CA.py':
        
        system_instruction = role_content
        
        from pages.CA import ca_run, ca_courts, bc_courts, ab_courts, sk_courts, mb_courts, on_courts, qc_courts, nb_courts, ns_courts, pe_courts, nl_courts, yk_courts, nt_courts, nu_courts, all_ca_jurisdiction_court_pairs, ca_court_tribunal_types, all_subjects, ca_search, ca_search_url, ca_search_results_to_judgment_links, ca_meta_labels_droppable, ca_meta_dict, ca_date  
        
        run = copy.copy(ca_run)

    if jurisdiction_page == 'pages/UK.py':
        
        system_instruction = role_content
        
        from pages.UK import uk_run, uk_courts_default_list, uk_courts, uk_courts_list, uk_court_choice, uk_link, uk_search, uk_search_results_to_judgment_links, uk_meta_labels_droppable, uk_meta_judgment_dict
        
        run = copy.copy(uk_run)

    if jurisdiction_page == 'pages/AFCA.py':

        if streamlit_timezone() == True:

            st.warning('One or more Chrome window may be launched. It must be kept open.')

        system_instruction = role_content
                
        from pages.AFCA import afca_run, afca_old_run, afca_new_run, product_line_options, product_category_options, product_name_options, issue_type_options, issue_options, afca_search, afca_meta_judgment_dict,  afca_meta_labels_droppable, afca_old_element_meta, afca_old_search, afca_meta_labels_droppable
        
        run = copy.copy(afca_run)

    if jurisdiction_page == 'pages/ER.py':

        from pages.ER import er_run, er_run_b64, er_methods_list, er_method_types, er_search, er_search_results_to_case_link_pairs, er_judgment_text, er_meta_judgment_dict, role_content_er, er_judgment_tokens_b64, er_meta_judgment_dict_b64, er_GPT_b64_json, er_engage_GPT_b64_json

        from gpt_functions import get_image_dims, calculate_image_token_cost

        system_instruction = role_content_er

        run = copy.copy(er_run)

    if jurisdiction_page == 'pages/KR.py':

        system_instruction = role_content
                
        from pages.KR import kr_run, kr_methods_list, kr_method_types, kr_search, kr_search_results_to_case_link_pairs, kr_judgment_text, kr_meta_judgment_dict
        
        run = copy.copy(kr_run)

    if jurisdiction_page == 'pages/SCTA.py':

        system_instruction = role_content
                
        from pages.SCTA import scta_run, scta_methods_list, scta_method_types, scta_search, scta_search_results_to_case_link_pairs, scta_judgment_text, scta_meta_judgment_dict
        
        run = copy.copy(scta_run)
    
    intro_for_GPT = [{"role": "system", "content": system_instruction}]

    df_individual = run(df_master)

    return df_individual
    


# %% [markdown]
# # Streamlit form, functions and parameters

# %% [markdown]
# ## Initialize session states

# %%
if 'own_account' not in st.session_state:
    st.session_state['own_account'] = False

if 'need_resetting' not in st.session_state:
        
    st.session_state['need_resetting'] = 0

if 'df_master' not in st.session_state:

    #Generally applicable
    st.session_state['df_master'] = pd.DataFrame([])
    st.session_state['df_master'].loc[0, 'Your name'] = ''
    st.session_state['df_master'].loc[0, 'Your email address'] = ''
    st.session_state['df_master'].loc[0, 'Your GPT API key'] = ''
    st.session_state['df_master'].loc[0, 'Metadata inclusion'] = True
    st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound
    st.session_state['df_master'].loc[0, 'Enter your questions for GPT'] = ''
    st.session_state['df_master'].loc[0, 'Use GPT'] = False
    st.session_state['df_master'].loc[0, 'Use own account'] = False
    st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    
if 'df_individual' not in st.session_state:

    st.session_state['df_individual'] = pd.DataFrame([])

#Disable toggles
if 'disable_input' not in st.session_state:
    st.session_state["disable_input"] = True


# %%
#Only for return and run buttons

if st.session_state.page_from != 'pages/GPT.py':

    st.session_state['jurisdiction_page'] = st.session_state.page_from


# %% [markdown]
# ## Form for AI and account

# %%
return_button = st.button('RETURN to the previous page')

#st.header("Use GPT as your research assistant")

#st.markdown("**:green[Would you like GPT to answer questions about the judgments returned by your search terms?]**")

st.header(":blue[Would you GPT to answer questions about the judgments returned by your search terms?]")

st.markdown("""Please consider trying this app without asking GPT any questions first. You can, for instance, obtain the judgments satisfying your search criteria and extract the judgment metadata without using GPT.
""")

gpt_activation_entry = st.checkbox(label = 'Use GPT', value = st.session_state['df_master'].loc[0, 'Use GPT'])

if gpt_activation_entry:
    
    st.session_state['df_master'].loc[0, 'Use GPT'] = gpt_activation_entry

st.caption("Use of GPT is costly and funded by a grant. For the model used by default (gpt-4o-mini), Ben's own experience suggests that it costs approximately USD \$0.01 (excl GST) per judgment. The [exact cost](https://openai.com/pricing) for answering a question about a judgment depends on the length of the question, the length of the judgment, and the length of the answer produced. You will be given ex-post cost estimates.")

st.subheader("Enter your questions for each judgment")

st.markdown("""Please enter one question **per line or per paragraph**. GPT will answer your questions for **each** judgment based only on information from **that** judgment. """)

st.markdown("""GPT is instructed to avoid giving answers which cannot be obtained from the relevant judgment itself. This is to minimise the risk of giving incorrect information (ie hallucination).""")

#if st.toggle('See the instruction given to GPT'):
    #st.write(f"{intro_for_GPT[0]['content']}")

if st.toggle('Tips for using GPT'):
    tips()

gpt_questions_entry = st.text_area(label = f"You may enter at most {question_characters_bound} characters.", height= 200, max_chars=question_characters_bound, value = st.session_state['df_master'].loc[0, 'Enter your questions for GPT']) 

if gpt_questions_entry:
    
    st.session_state['df_master'].loc[0, 'Enter your questions for GPT'] = gpt_questions_entry

if check_questions_answers() > 0:
    
    st.write("Please do not try to obtain personally identifiable information. Your questions and GPT's answers will be checked for potential privacy violation.")

#Disable toggles while prompt is not entered or the same as the last processed prompt
if gpt_activation_entry:
    
    if gpt_questions_entry:
        
        st.session_state['disable_input'] = False
        
    else:
        
        st.session_state['disable_input'] = True
        
else:
    st.session_state['disable_input'] = False
    
st.caption(f"By default, answers to your questions will be generated by model gpt-4o-mini. Due to a technical limitation, this model will read up to approximately {round(tokens_cap('gpt-4o-mini')*3/4)} words from each judgment.")

if own_account_allowed() > 0:
    
    st.subheader(':orange[Enhance app capabilities]')
    
    st.markdown("""Would you like to increase the quality and accuracy of answers from GPT, or increase the maximum nunber of judgments to process? You can do so with your own GPT account.
    """)
    
    own_account_entry = st.toggle(label = 'Use my own GPT account',  disabled = st.session_state.disable_input, value = st.session_state['df_master'].loc[0, 'Use own account'])
    
    if own_account_entry:

        st.session_state['df_master'].loc[0, 'Use own account'] = own_account_entry
        
        st.session_state["own_account"] = True
    
        st.markdown("""**:green[Please enter your name, email address and API key.]** You can sign up for a GPT account and pay for your own usage [here](https://platform.openai.com/signup). You can then create and find your API key [here](https://platform.openai.com/api-keys).
    """)
            
        name_entry = st.text_input(label = "Your name", value = st.session_state['df_master'].loc[0, 'Your name'])

        if name_entry:
            
            st.session_state['df_master'].loc[0, 'Your name'] = name_entry
        
        email_entry = st.text_input(label = "Your email address", value =  st.session_state['df_master'].loc[0, 'Your email address'])

        if email_entry:
            
            st.session_state['df_master'].loc[0, 'Your email address'] = email_entry
        
        gpt_api_key_entry = st.text_input(label = "Your GPT API key (mandatory)", value = st.session_state['df_master'].loc[0, 'Your GPT API key'])
        
        if gpt_api_key_entry:
            
            st.session_state['df_master'].loc[0, 'Your GPT API key'] = gpt_api_key_entry

            if ((len(gpt_api_key_entry) < 40) or (gpt_api_key_entry[0:2] != 'sk')):
                
                st.warning('This key is not valid.')
 
        st.markdown("""**:green[You can use the flagship version of GPT model (gpt-4o),]** which is :red[about 30 times more expensive, per character] than the default model (gpt-4o-mini) which you can use for free.""")  
        
        gpt_enhancement_entry = st.checkbox('Use the flagship GPT model', value = st.session_state['df_master'].loc[0, 'Use flagship version of GPT'])
        
        st.caption('Click [here](https://openai.com/api/pricing) for pricing information on different GPT models.')

        if gpt_enhancement_entry:

            st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = True
            st.session_state.gpt_model = "gpt-4o-2024-08-06"

        else:
            
            st.session_state.gpt_model = 'gpt-4o-mini'
            st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
        
        st.write(f'**:green[You can increase the maximum number of judgments to process.]** The default maximum is {default_judgment_counter_bound}.')
        
        judgments_counter_bound_entry = st.number_input(label = 'Choose a number between 1 and 100', min_value = 1, max_value = 100, step = 1, value = str_to_int(st.session_state['df_master'].loc[0, 'Maximum number of judgments']))

        if judgments_counter_bound_entry:

            st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = judgments_counter_bound_entry
    
        st.write(f"*GPT model {st.session_state.gpt_model} will answer any questions based on up to approximately {round(tokens_cap(st.session_state.gpt_model)*3/4)} words from each judgment, for up to {st.session_state['df_master'].loc[0, 'Maximum number of judgments']} judgment(s).*")
    
    else:
        
        st.session_state["own_account"] = False

        st.session_state['df_master'].loc[0, 'Use own account'] = False
    
        st.session_state.gpt_model = "gpt-4o-mini"

        st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    
        st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound

# %% [markdown]
# ## Consent

# %%
st.header("Consent")

st.markdown("""By using this app, you agree that the data and/or information this form provides will be temporarily stored on one or more remote servers for the purpose of producing an output containing data in relation to judgments. Any such data and/or information may also be given to an artificial intelligence provider for the same purpose.""")

consent =  st.checkbox('Yes, I agree.', value = False, disabled = st.session_state.disable_input)

st.markdown("""If you do not agree, then please feel free to close this form.""")


# %% [markdown]
# ## Save entries

# %%
gpt_keep_button = st.button(label = 'DOWNLOAD entries')

if gpt_keep_button:
    st.success('Scroll down to download your entries.')


# %% [markdown]
# ## Next steps

# %%
st.header("Next steps")

st.markdown("""You can now press :green[PRODUCE data] to obtain a spreadsheet which hopefully has the data you seek.""")

#Warning
if st.session_state.gpt_model == 'gpt-4o-mini':
    st.warning('A low-cost GPT model will answer your questions. Please reach out to Ben Chen at ben.chen@sydney.edu.au if you would like to use the flagship model instead.')

if st.session_state.gpt_model == "gpt-4o-2024-08-06":
    st.warning('An expensive GPT model will answer your questions. Please be cautious.')

with stylable_container(
    "green",
    css_styles="""
    button {
        background-color: #00FF00;
        color: black;
    }""",
):
    run_button = st.button('PRODUCE data')

gpt_reset_button = st.button(label='REMOVE data', type = 'primary', disabled = not bool(st.session_state.need_resetting))

#Display need resetting message if necessary
if st.session_state.need_resetting == 1:
    if len(st.session_state.df_individual) > 0:
        st.warning('You must :red[REMOVE] the data previously produced before processing new search terms or questions.')

# %% [markdown]
# ## ER only

# %%
#if st.session_state.gpt_model == "gpt-4o":
if ((st.session_state.own_account == True) and (st.session_state.jurisdiction_page == 'pages/ER.py')):
    
    st.markdown("""The English Reports are available as PDFs. By default, this app will use an Optical Character Recognition (OCR) engine to extract text from the relevant PDFs, and then send such text to GPT.
    
Alternatively, you can send the relevant PDFs to GPT as images. This alternative approach may produce better responses for "untidy" PDFs, but tends to be slower and costlier than the default approach.
""")
    
    #st.write('Not getting the best responses for your images? You can try a more costly')
    #b64_help_text = 'GPT will process images directly, instead of text first extracted from images by an Optical Character Recognition engine. This only works for PNG, JPEG, JPG, GIF images.'
    er_run_button_b64 = st.button(label = 'SEND PDFs to GPT as images')


# %% [markdown]
# ## Previous responses and outputs

# %%
#Create placeholder download buttons if previous entries and output in st.session_state:

if len(st.session_state.df_individual)>0:
    
    #st.subheader('Looking for your previous entries and output?')
    st.subheader('Looking for your previously produced data?')

    df_master = st.session_state.df_master

    df_individual = st.session_state.df_individual
    
    #Load previous entries and output
    
    #st.write('Previous entries')

    #entries_output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_entries'

    #csv = convert_df_to_csv(df_master)

    #ste.download_button(
        #label="Download your previous entries as a CSV (for use in Excel etc)", 
        #data = csv,
        #file_name=entries_output_name + '.csv', 
        #mime= "text/csv", 
    #)

    #xlsx = convert_df_to_excel(df_master)
    
    #ste.download_button(label='Download your previous entries as an Excel spreadsheet (XLSX)',
                        #data=xlsx,
                        #file_name=entries_output_name + '.xlsx', 
                        #mime='application/vnd.ms-excel',
                       #)

    #json = convert_df_to_json(df_master)
    
    #ste.download_button(
        #label="Download your previous entries as a JSON", 
        #data = json,
        #file_name= entries_output_name + '.json', 
        #mime= "application/json", 
    #)

    #st.write('previously produced data')

    output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_output'

    csv_output = convert_df_to_csv(df_individual)
    
    ste.download_button(
        label="Download your previously produced data as a CSV (for use in Excel etc)", 
        data = csv_output,
        file_name= output_name + '.csv', 
        mime= "text/csv", 
    )

    excel_xlsx = convert_df_to_excel(df_individual)
    
    ste.download_button(label='Download your previously produced data as an Excel spreadsheet (XLSX)',
                        data=excel_xlsx,
                        file_name= output_name + '.xlsx', 
                        mime='application/vnd.ms-excel',
                       )
    
    json_output = convert_df_to_json(df_individual)
    
    ste.download_button(
        label="Download your previously produced data as a JSON", 
        data = json_output,
        file_name= output_name + '.json', 
        mime= "application/json", 
    )

    st.page_link('pages/AI.py', label="ANALYSE your previous spreadsheet with an AI", icon = '🤔')

# %% [markdown]
# # Run etc buttons

# %% [markdown]
# ## All except ER

# %%
if gpt_keep_button:

    df_master = st.session_state.df_master

    #df_master.pop("Your GPT API key")

    #df_master.pop("Processed")

    responses_output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_responses'

    #Produce a file to download

    csv = convert_df_to_csv(df_master)

    st.subheader('Your entries are now available for download.')
    
    ste.download_button(
        label="Download as a CSV (for use in Excel etc)", 
        data = csv,
        file_name=responses_output_name + '.csv', 
        mime= "text/csv", 
#            key='download-csv'
    )

    xlsx = convert_df_to_excel(df_master)
    
    ste.download_button(label='Download as an Excel spreadsheet (XLSX)',
                        data=xlsx,
                        file_name=responses_output_name + '.xlsx', 
                        mime='application/vnd.ms-excel',
                       )
    
    json = convert_df_to_json(df_master)
    
    ste.download_button(
        label="Download as a JSON", 
        data = json,
        file_name= responses_output_name + '.json', 
        mime= "application/json", 
    )

# %%
if run_button:
    
    if int(consent) == 0:
        st.warning("You must tick '[y]es, I agree[]' to use the app.")

    elif len(st.session_state.df_individual)>0:
        st.warning('You must :red[REMOVE] the data produced before processing new search terms or questions.')

        #st.session_state['need_resetting'] = 1
            
    else:

        if ((st.session_state.own_account == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                
            if is_api_key_valid(gpt_api_key_entry) == False:
                st.error('Your API key is not valid.')
                quit()
                
        #st.write('Your results should be available for download soon. The estimated waiting time is 3-5 minutes per 10 judgments.')
        #st.write('If this app produces an error or an unexpected spreadsheet, please double-check your search terms and try again.')

        
        with st.spinner(r"$\textsf{\normalsize \textbf{In progress...} The estimated waiting time is 3-5 minutes per 10 judgments.}$"):
            
            try:

                #Create spreadsheet of responses
                df_master = st.session_state.df_master

                #Activate user's own key or mine
                if st.session_state.own_account == True:
                    
                    API_key = df_master.loc[0, 'Your GPT API key']
    
                else:
                    API_key = st.secrets["openai"]["gpt_api_key"]
                
                openai.api_key = API_key

                #Produce results
                
                jurisdiction_page = st.session_state.jurisdiction_page
                
                df_individual = gpt_run(jurisdiction_page, df_master)

                if len(df_individual) == 0:
                    st.error('Your search terms may not return any judgments. Please return to the previous page and press the PREVIEW button to double-check.')
                
                else:
                    
                    #Keep results in session state
                    st.session_state["df_individual"] = df_individual
    
                    #Change session states
                    st.session_state['need_resetting'] = 1
                    st.session_state["page_from"] = 'pages/GPT.py'           
    
                    #Write results
            
                    st.success("Your data is now available for download. Thank you for using LawtoData!")
                    
                    #Button for downloading results
                    output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_results'
            
                    csv_output = convert_df_to_csv(df_individual)
                    
                    ste.download_button(
                        label="Download your data as a CSV (for use in Excel etc)", 
                        data = csv_output,
                        file_name= output_name + '.csv', 
                        mime= "text/csv", 
            #            key='download-csv'
                    )
            
                    excel_xlsx = convert_df_to_excel(df_individual)
                    
                    ste.download_button(label='Download your data as an Excel spreadsheet (XLSX)',
                                        data=excel_xlsx,
                                        file_name= output_name + '.xlsx', 
                                        mime='application/vnd.ms-excel',
                                       )
            
                    json_output = convert_df_to_json(df_individual)
                    
                    ste.download_button(
                        label="Download your data as a JSON", 
                        data = json_output,
                        file_name= output_name + '.json', 
                        mime= "application/json", 
                    )
            
                    st.page_link('pages/AI.py', label="ANALYSE your data with an AI", icon = '🤔')
    
                    #Keep record on Google sheet
                    #Obtain google spreadsheet       
                    #conn = st.connection("gsheets_nsw", type=GSheetsConnection)
                    #df_google = conn.read()
                    #df_google = df_google.fillna('')
                    #df_google=df_google[df_google["Processed"]!='']
                    #df_master["Processed"] = datetime.now()
                    #df_master.pop("Your GPT API key")
                    #df_to_update = pd.concat([df_google, df_master])
                    #conn.update(worksheet="CTH", data=df_to_update, )
                
            except Exception as e:
                
                st.error('Sorry, an error has arisen. Please press PRODUCE data again, or return to the previous page and check your search terms.')
                
                st.exception(e)
                


# %%
if return_button:
    
    st.session_state["page_from"] = 'pages/GPT.py'

    st.switch_page(st.session_state.jurisdiction_page)
    


# %%
if gpt_reset_button:

    st.session_state['df_individual'] = pd.DataFrame([])
    
    st.session_state['need_resetting'] = 0

    #To prevent GPT page from showing content of jurisdiction page
    st.session_state["page_from"] = st.session_state.jurisdiction_page
    
    #st.session_state['df_master'].loc[0, 'Your name'] = ''
    #st.session_state['df_master'].loc[0, 'Your email address'] = ''
    #st.session_state['df_master'].loc[0, 'Your GPT API key'] = ''
    #st.session_state['df_master'].loc[0, 'Maximum number of judgments'] = default_judgment_counter_bound
    #st.session_state['df_master'].loc[0, 'Enter your questions for GPT'] = ''
    #st.session_state['df_master'].loc[0, 'Use GPT'] = False
    #st.session_state['df_master'].loc[0, 'Use own account'] = False
    #st.session_state['df_master'].loc[0, 'Use flagship version of GPT'] = False
    
    #clear_cache_except_validation_df_master()
    
    st.rerun()


# %% [markdown]
# ## ER

# %%
if ((st.session_state.own_account == True) and (st.session_state.jurisdiction_page == 'pages/ER.py')):

    if er_run_button_b64:
        
        if int(consent) == 0:
            st.warning("You must tick '[y]es, I agree[]' to use the app.")
    
        elif len(st.session_state.df_individual)>0:
            st.warning('You must :red[REMOVE] the data produced before processing new search terms or questions.')
    
            #st.session_state['need_resetting'] = 1
                
        else:
    
            if ((st.session_state.own_account == True) and (st.session_state['df_master'].loc[0, 'Use GPT'] == True)):
                                    
                if is_api_key_valid(gpt_api_key_entry) == False:
                    st.error('Your API key is not valid.')
                    quit()
                    
            #st.write('Your results should be available for download soon. The estimated waiting time is 3-5 minutes per 10 judgments.')
            #st.write('If this app produces an error or an unexpected spreadsheet, please double-check your search terms and try again.')
                
            with st.spinner(r"$\textsf{\normalsize \textbf{In progress...} The estimated waiting time is 3-5 minutes per 10 judgments.}$"):
    
                try:

                    #Definitions and functions for ER
                    from pages.ER import er_run, er_run_b64, er_methods_list, er_method_types, er_search, er_search_results_to_case_link_pairs, er_judgment_text, er_meta_judgment_dict, role_content_er, er_judgment_tokens_b64, er_meta_judgment_dict_b64, er_GPT_b64_json, er_engage_GPT_b64_json

                    from gpt_functions import get_image_dims, calculate_image_token_cost
                    
                    system_instruction = role_content_er

                    #Create spreadsheet of responses
                    df_master = st.session_state.df_master
    
                    #Activate user's own key or mine
                    if st.session_state.own_account == True:
                        
                        API_key = df_master.loc[0, 'Your GPT API key']
        
                    else:
                        API_key = st.secrets["openai"]["gpt_api_key"]
                    
                    openai.api_key = API_key
    
                    #Produce results
                        
                    df_individual = er_run_b64(df_master)

                    if len(df_individual) == 0:
                        
                        st.error('Your search terms may not return any judgments. Please return to the previous page and press the PREVIEW button to double-check.')
                    
                    else:
                        #Keep results in session state
                        st.session_state["df_individual"] = df_individual#.astype(str)
                
                        #Change session states
                        st.session_state['need_resetting'] = 1
                        
                        st.session_state["page_from"] = 'pages/GPT.py'
                        
                        #Write results
                
                        st.success("Your data is now available for download. Thank you for using LawtoData!")
                        
                        #Button for downloading results
                        output_name = str(df_master.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_results'
                
                        csv_output = convert_df_to_csv(df_individual)
                        
                        ste.download_button(
                            label="Download your data as a CSV (for use in Excel etc)", 
                            data = csv_output,
                            file_name= output_name + '.csv', 
                            mime= "text/csv", 
                #            key='download-csv'
                        )
                
                        excel_xlsx = convert_df_to_excel(df_individual)
                        
                        ste.download_button(label='Download your data as an Excel spreadsheet (XLSX)',
                                            data=excel_xlsx,
                                            file_name= output_name + '.xlsx', 
                                            mime='application/vnd.ms-excel',
                                           )
                
                        json_output = convert_df_to_json(df_individual)
                        
                        ste.download_button(
                            label="Download your data as a JSON", 
                            data = json_output,
                            file_name= output_name + '.json', 
                            mime= "application/json", 
                        )
                
                        st.page_link('pages/AI.py', label="ANALYSE your spreadsheet with an AI", icon = '🤔')
        
                            
                        #Keep record on Google sheet
                        #Obtain google spreadsheet       
                        #conn = st.connection("gsheets_nsw", type=GSheetsConnection)
                        #df_google = conn.read()
                        #df_google = df_google.fillna('')
                        #df_google=df_google[df_google["Processed"]!='']
                        #df_master["Processed"] = datetime.now()
                        #df_master.pop("Your GPT API key")
                        #df_to_update = pd.concat([df_google, df_master])
                        #conn.update(worksheet="ER", data=df_to_update, )
                
                except Exception as e:
                    st.error('Sorry, an error has arisen. Please press PRODUCE data again, or return to the previous page and check your search terms.')
                    st.exception(e)


# %%
