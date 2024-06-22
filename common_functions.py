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
#Preliminaries
import datetime
from datetime import date
from dateutil import parser
from dateutil.relativedelta import *
from datetime import datetime, timedelta
import pandas as pd

#Excel
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb

#Streamlit
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste


# %%
def own_account_allowed():
	return 0

# %%
#today
today_in_nums = str(datetime.now())[0:10]

# %%
# Generate placeholder list of errors
errors_list = set()

# %%
#Pause between judgment scraping

scraper_pause_mean = int((15-5)/2)

#print(f"The pause between judgment scraping is {scraper_pause_mean} second.\n")


# %%
#Lowerbound on length of judgment text to proccess, in tokens

judgment_text_lower_bound = 1000


# %%
#Create function for saving responses and results
def convert_df_to_json(df):
    return df.to_json(orient = 'split', compression = 'infer', default_handler=str)

def convert_df_to_csv(df):
   return df.to_csv(index=False).encode('utf-8')

def convert_df_to_excel(df):
    #Excel metadata
    excel_author = 'The Empirical Legal Research Kickstarter'
    excel_description = 'A 2022 University of Sydney Research Accelerator (SOAR) Prize partially funded the development of the Empirical Legal Research Kickstarter, which generated this spreadsheet.'
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


# %%
#Define function to determine eligibility for GPT use

#Define a list of privileged email addresses with unlimited GPT uses

def prior_GPT_uses(email_address, df_online):
    privileged_emails = st.secrets["secrets"]["privileged_emails"].replace(' ', '').split(',')
    # df_online variable should be the online df_online
    prior_use_counter = 0
    for i in df_online.index:
        if ((df_online.loc[i, "Your email address"] == email_address) 
            and (int(df_online.loc[i, "Use GPT"]) > 0) 
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
#Tidy up medium neutral citation
def mnc_cleaner(x):
    if '[' in x:
        x_clean=str(x).split("[")
        y = '[' + x_clean[1]
        return y
    else:
        return x



# %%
#Tidy up hyperlink
def link(x):
    value = '=HYPERLINK("' + str(x) + '")'
    return value



# %% [markdown]
# # Streamlit

# %%
#Function to open url
def open_page(url):
    open_script= """
        <script type="text/javascript">
            window.open('%s', '_blank').focus();
        </script>
    """ % (url)
    html(open_script)


# %%
def clear_cache_except_validation_df_master():
    keys = list(st.session_state.keys())
    if 'gpt_api_key_validity' in keys:
        keys.remove('gpt_api_key_validity')
    if 'df_master' in keys:
        keys.remove('df_master')
    for key in keys:
        st.session_state.pop(key)


# %%
def tips():
    st.markdown(""":green[**DO's**:]
- :green[Do break down complex tasks into simple sub-tasks.]
- :green[Do give clear and detailed instructions (eg specify steps required to complete a task).]
- :green[Do use the same terminology as the relevant judgments or files themselves.]
- :green[Do give exemplar answers.]
- :green[Do manually check some or all answers.]
- :green[Do revise questions to get better answers.]
- :green[Do evaluate answers on the same sample of judgments or files (ie the "training" sample).]
""")

    st.markdown(""":red[**Don'ts**:]
- :red[Don't ask questions which go beyond the relevant judgments or files themselves.]
- :red[Don't ask difficult maths questions.]
- :red[Don't skip manual evaluation.]
""")

    st.markdown(""":orange[**Maybe's**:]
- :orange[Maybe ask for reasoning.]
- :orange[Maybe re-run the same questions and manually check for inconsistency.]
""")

    st.caption('Click [here](https://platform.openai.com/docs/guides/prompt-engineering) for more tips.')
