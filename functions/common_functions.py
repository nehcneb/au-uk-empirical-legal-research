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
def own_account_allowed():
    return 0


# %%
def check_questions_answers():
    return 1


# %%
def batch_mode_allowed():
    return 1


# %%
huggingface = True

#if depends on director

huggingface_directory = 0

if huggingface_directory > 1:
    
    current_dir = ''
    try:
        current_dir = os.getcwd()
        print(f"current_dir == {current_dir}")
    except Exception as e:
        print(f"current_dir not generated.")
        print(e)
    
    if 'Users/Ben' not in current_dir: #If running on Huggingface or Github Actions
        huggingface = True
        
print(f'huggingface == {huggingface}')


# %%
#Preliminaries
import datetime
from datetime import date
from dateutil import parser
from dateutil.relativedelta import *
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests
import pypdf
import io
from io import BytesIO
import pause

#Excel
from io import BytesIO
from pyxlsb import open_workbook as open_xlsb
import xlsxwriter

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
import streamlit_ext as ste

#AWS
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# %% [markdown]
# # Scraper, GPT etc

# %%
#Default judgment counter bound
default_judgment_counter_bound = 10

# %%
#Default page bound for OWN.py
default_page_bound = 50


# %%
#Check if string is date

#From https://stackoverflow.com/questions/25341945/check-if-string-has-date-any-format

def is_date(string, fuzzy=False):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try: 
        parser.parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False



# %%
def date_parser(string):
    try:
        date = parser.parse(string, dayfirst=True)
        return date
    except:
        return None



# %%
#today
today_in_nums = str(datetime.now())[0:10]
today = datetime.now().strftime("%d/%m/%Y")

# %%
# Generate placeholder list of errors
errors_list = set()


# %%
#Split title and mnc from full case full title

def split_title_mnc(full_title):
    #Returns a list where first item is full_title and second item mnc

    full_title = str(full_title)
    
    #Get rid of extra spaces
    while '  ' in full_title:
        full_title = full_title.replace('  ', ' ')

    #Get mnc with potentially extra words after
    mnc = full_title
    if '[' in full_title:
        mnc = '[' + full_title.split('[')[-1]

    #Get rid of extra words after mnc
    mnc_list = mnc.split(' ')
    
    if len(mnc_list) > 3:
        mnc = f"{mnc_list[0]} {mnc_list[1]} {mnc_list[2]}"

    #Get title 
    if mnc in full_title:
        
        title = full_title.split(mnc)[0]

        if len(title) > 0:
            
            while title[-1] == ' ':
                title = title[:-1]
    else:
        title = full_title
    
    return [title, mnc]



# %%
#Pause between judgment scraping
scraper_pause_mean = int(10)



# %%
#Lowerbound on length of judgment text to proccess without trying to download directly from official database, in tokens
judgment_text_lower_bound = 4000 #~3000 words


# %%
#Tidy up hyperlink
def link(x):
    value = '=HYPERLINK("' + str(x) + '")'
    return value



# %%
#Define function for judgment link containing PDF
def pdf_judgment(url):
    headers = {'User-Agent': 'whatever'}
    r = requests.get(url, headers=headers)
    remote_file_bytes = io.BytesIO(r.content)
    pdfdoc_remote = pypdf.PdfReader(remote_file_bytes)
    text_list = []

    for page in pdfdoc_remote.pages:
        text_list.append(page.extract_text())
    
    return str(text_list)



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

    st.write('Click [here](https://platform.openai.com/docs/guides/prompt-engineering) for more tips.')


# %%
def list_value_check(some_list, some_value):
    try:
        index = some_list.index(some_value)
        return index
    except:
        return None


# %%
def list_range_check(some_list, some_string):
    selected_list = []
    try:
        raw_list = some_string.split(',')

        for item in raw_list:

            while item[0] == ' ':
                item = item[1:]
            
            if item in some_list:
                selected_list.append(item)

    except:
        print(f'List {str(some_list)} does not contain {some_string}')
 
    return selected_list



# %%
def au_date(x):
    try:
        return parser.parse(x, dayfirst=True)
    except:
        return None


# %%
#String to integer
def str_to_int(string):
    try:
        output = int(float(string))
        return output
    except:
        return int(default_judgment_counter_bound)


# %%
#String to integer
def str_to_int_page(string):
    try:
        output = int(float(string))
        return output
    except:
        return int(default_page_bound)


# %%
#Save jurisdiction specific input
def save_input(df_master):

    keys_to_carry_over = ['Your name', 
                        'Your email address', 
                        'Your GPT API key', 
                        'Maximum number of judgments', 
                        'Maximum number of files',
                        'Maximum number of pages per file',
                        'Language choice',
                        'Enter your questions for GPT', 
                        'Use GPT', 
                        'Use own account', 
                        'Use flagship version of GPT', 
                         'submission_time', 
                         'status', 
                          'jurisdiction_page', 
                          'Consent',
                          #'CourtListener API token' #US specific
                         ]
    
    df_master = df_master.replace({np.nan: None})
    
    for key in st.session_state.df_master.keys():
        
        if key not in keys_to_carry_over:
            try:            
                st.session_state.df_master.loc[0, key]  = df_master.loc[0, key]
            except Exception as e:
                print(f'{key} not saved.')
                print(e)



# %%
#Function to hide own token

def hide_own_token(user_token, own_token):
    if user_token:
        if user_token == own_token:
            return None
        else:
            return user_token
    else:
        return None



# %%
#Reverse hyperlink display
def reverse_link(x):
    value = str(x).replace('=HYPERLINK("', '').replace('")', '')
    return value


# %%
#Display error for scraping
search_error_display = 'The database from which this app sources cases is not responding. Please try again in a few hours.'


# %%
#Note error for scraping
search_error_note = 'The database from which this app sources cases did not respond. This case was not sent to GPT.'


# %%
#Note truncation
truncation_note = "The full file is too long for GPT. It was (or will be) truncated if sent to GPT."


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
def clear_cache():
    
    keys = list(st.session_state.keys())
    
    for key in keys:
        st.session_state.pop(key)



# %%
def clear_cache_except_validation_df_master():
    keys = list(st.session_state.keys())
    if 'df_master' in keys:
        keys.remove('df_master')
    if 'page_from' in keys:
        keys.remove('page_from')
    if 'jurisdiction_page' in keys:
        keys.remove('jurisdiction_page')
    for key in keys:
        st.session_state.pop(key)


# %%
def streamlit_timezone():
    local_now = datetime.now().astimezone()
    time_zone = local_now.tzname()
    if time_zone in ['AEST', 'AEDT', 'ACST', 'AWST', 'BST']:
        return True
    else:
        return False


# %%
def streamlit_cloud_date_format(date):
    local_now = datetime.now().astimezone()
    time_zone = local_now.tzname()
    if time_zone in ['AEST', 'ACST', 'AWST', 'BST']:
        date_to_send = parser.parse(date, dayfirst=True).strftime("%d/%m/%Y")
    else:
        date_to_send = parser.parse(date, dayfirst=True).strftime("%m/%d/%Y")
    return date_to_send


# %%
#No results msg
no_results_msg = 'Your search terms returned 0 results. Please change your search terms and try again.'

# %%
#Default spinner_text

spinner_text = r"$\textsf{\normalsize In progress... }$"


# %%
#Funder
funder_msg = "Lawtodata is partially funded by a 2022 University of Sydney Research Accelerator (SOAR) Prize and a 2023 Discovery Early Career Researcher Award (DECRA). Please kindly acknowledge this if you use your requested data to produce any research output. "


# %%
#Create function for saving responses and results
def convert_df_to_json(df):
    return df.to_json(orient = 'split', compression = 'infer', default_handler=str, indent=4)

def convert_df_to_csv(df):
   return df.to_csv(index=False).encode('utf-8')

def convert_df_to_excel(df):
    #Excel metadata
    excel_author = 'LawtoData'
    excel_description = 'A 2022 University of Sydney Research Accelerator (SOAR) Prize and a 2023 Discovery Early Career Researcher Award (DECRA) partially funded the development of LawtoData, which generated this spreadsheet.'
    output = BytesIO()
    #writer = pd.ExcelWriter(output, engine='xlsxwriter', engine_kwargs={'options': {'strings_to_urls': False}})
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
#Download entries and results

def download_buttons(df_master, df_individual = [], saving = False, previous = False):
    #Enable the saving argument if want to allow saving of entries
    #Enable the previous argument if want to allow saving of last produced results
    #Default df_individual is empty to ensure no buttons for downloading data is shown
    
    #Create a copy of df_master to avoid exposing secrets
    df_master_to_show = df_master.copy(deep = True)

    #For downloading entries
    if saving:

        if 'Your GPT API key' in df_master_to_show.columns:
            df_master_to_show["Your GPT API key"] = ''

        if 'CourtListener API token' in df_master_to_show.columns:
            #Essential to avoiding both default and user secrets
            df_master_to_show["CourtListener API token"] = ''

        if previous:
            
            st.warning('Looking for your entries?')
            
            previous_str = 'your last produced '
            
        else:
            
            st.success('Your entries are now available for download.')
        
        responses_output_name = str(df_master_to_show.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_responses'
        
        xlsx = convert_df_to_excel(df_master_to_show)
        
        ste.download_button(label='DOWNLOAD your entries as an Excel spreadsheet (XLSX)',
                            data=xlsx,
                            file_name=responses_output_name + '.xlsx', 
                            mime='application/vnd.ms-excel',
                           )
    
        csv = convert_df_to_csv(df_master_to_show)
    
        ste.download_button(
            label="DOWNLOAD your entries as a CSV", 
            data = csv,
            file_name=responses_output_name + '.csv', 
            mime= "text/csv", 
        )
    
        json = convert_df_to_json(df_master_to_show)
        
        ste.download_button(
            label="DOWNLOAD your entries as a JSON", 
            data = json,
            file_name= responses_output_name + '.json', 
            mime= "application/json", 
        )
    
    #For downloading data
    if len(df_individual) > 0:

        #Determine whether to note previous results
        previous_str = ''
        
        if previous:
            st.warning('Looking for your last produced data?')
            
            previous_str = 'last produced '
            
        else:
            
            st.success("Your data is now available for download. Thank you for using *LawtoData*!")

        #Produce output spreadsheets
        output_name = str(df_master_to_show.loc[0, 'Your name']) + '_' + str(today_in_nums) + '_output'

        excel_xlsx = convert_df_to_excel(df_individual)
        
        ste.download_button(label=f'DOWNLOAD your {previous_str}data as an Excel spreadsheet (XLSX)',
                            data=excel_xlsx,
                            file_name= output_name + '.xlsx', 
                            mime='application/vnd.ms-excel',
                           )
    
        csv_output = convert_df_to_csv(df_individual)
        
        ste.download_button(
            label=f'DOWNLOAD your {previous_str}data as a CSV', 
            data = csv_output,
            file_name= output_name + '.csv', 
            mime= "text/csv", 
        )
        
        json_output = convert_df_to_json(df_individual)
        
        ste.download_button(
            label=f'DOWNLOAD your {previous_str}data as a JSON', 
            data = json_output,
            file_name= output_name + '.json', 
            mime= "application/json", 
        )
    
        st.page_link('pages/AI.py', label=f"ANALYSE your {previous_str}data with an AI", icon = '🤔')

    #For noting a lack of data
    if ((not saving) and (len(df_individual) == 0)):
        
        st.error('Sorry, no data was produced. Please return to the previous page, check your search terms and try again.')



# %%
#Obtain columns with hyperlinks

def link_headings_picker(df):
    link_headings = []
    for heading in df.columns:
        if (('hyperlink' in str(heading).lower()) or (str(heading).lower() == 'uri') or (str(heading).lower() == 'url')):
            link_headings.append(heading)
    return link_headings #A list of headings with hyperlinks

def clean_link_columns(df):
        
    link_headers_list = link_headings_picker(df)

    for link_header in link_headers_list:
        if 'hyperlink' in str(link_header).lower():
            df[link_header] = df[link_header].apply(reverse_link)
        
    return df
    


# %%
#Function for preparing df for display with clickable links

def display_df(df):

    #Obtain clolumns with hyperlinks
    
    link_heading_config = {} 
    
    link_headings_list = link_headings_picker(df)
            
    for link_heading in link_headings_list:
        
        link_heading_config[link_heading] = st.column_config.LinkColumn(display_text = 'Click')

    #Reverse columns with clickable links to raw uri
    df = clean_link_columns(df)

    return {'df': df, 'link_heading_config': link_heading_config}
    


# %%
#For checking whether date entered is within allowable range

def date_range_check(date_start, date_end, date_entry):
    #All arguments are datetime objects

    try:
        if ((date_start <= date_entry) and (date_entry <= date_end)):
            return date_entry
        else:
            return None
    except:
        return None


# %% [markdown]
# # AWS

# %%
#AWS email
#Define send email function

def send_notification_email(ULTIMATE_RECIPIENT_NAME, ULTIMATE_RECIPIENT_EMAIL):

    ses = boto3.client('ses',region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"], aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"], aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"])
    
    #Based on the following upon substituting various arguments, https://docs.aws.amazon.com/ses/latest/dg/send-an-email-using-sdk-programmatically.html
    
    # Replace sender@example.com with your "From" address.
    # This address must be verified with Amazon SES.
    SENDER = st.secrets["email_notifications"]["email_sender"]
    
    # Replace recipient@example.com with a "To" address. If your account 
    # is still in the sandbox, this address must be verified.
    RECIPIENT = st.secrets["email_notifications"]["email_receiver_personal"]
    
    # The subject line for the email.
    SUBJECT = f"LawtoData: {ULTIMATE_RECIPIENT_NAME} has requested data"
    
    BODY_TEXT = (
    
    f"{ULTIMATE_RECIPIENT_NAME} at {ULTIMATE_RECIPIENT_EMAIL} has requested data via LawtoData."
    
    )
      
    # The character encoding for the email.
    CHARSET = "UTF-8"

    # Try to send the email.
    try:
        #Provide the contents of the email.
        response = ses.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER,
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    #else:
        #print("Email sent! Message ID:"),
        #print(response['MessageId'])


# %% [markdown]
# # [NOT IN USE] Google Sheets

# %%
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
