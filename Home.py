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

# %% editable=true slideshow={"slide_type": ""}
#streamlit run Dropbox/Python/GitHub/au-uk-empirical-legal-research-unlimited/Home.py

# %% [markdown] editable=true slideshow={"slide_type": ""}
# # Preliminaries

# %% editable=true slideshow={"slide_type": ""}
#Streamlit
import streamlit as st


# %% editable=true slideshow={"slide_type": ""}
#Title of webpage
st.set_page_config(
   page_title="Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Determine whether to allow user to use own account
from common_functions import own_account_allowed

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

# %% editable=true slideshow={"slide_type": ""}
#List of sources of information
sources_list = ["Judgments of the High Court of Australia", 
                 "Judgments of the Federal Court of Australia", 
                "Judgments of the New South Wales courts and tribunals", 
                #"Judgments of select United Kingdom courts and tribunals", 
                "The Kercher Reports (decisions of the New South Wales superior courts from 1788 to 1900)", 
                "The English Reports (nearly all English case reports from 1220 to 1866)",
                "Your own files", 
                "Your own spreadsheet"
               ]

source_pages = ["pages/HCA.py",
                "pages/FCA.py", 
                "pages/NSW.py", 
                #"pages/UK.py", 
                "pages/KR.py", 
                "pages/ER.py", 
                "pages/OWN.py", 
                'pages/AI.py']


# %%
def source_index(source):
    if source == None:
        index = None
    else:
        index = sources_list.index(source)
    return index



# %% editable=true slideshow={"slide_type": ""}
#Initialize source and understanding

if 'source' not in st.session_state:
    st.session_state['source'] = None

#if st.session_state.source:
    #default_source_index = sources_list.index(st.session_state['source'])
#else:
    #default_source_index = None

if 'i_understand' not in st.session_state:
    st.session_state['i_understand'] = False


# %% [markdown]
# # Form

# %% editable=true slideshow={"slide_type": ""}
#Create form

st.title("The Empirical Legal Research Kickstarter")
st.header("An Anglo-Australian Pilot")

st.markdown("""*The Empirical Legal Research Kickstarter* is an [open-source](https://github.com/nehcneb/au-uk-empirical-legal-research/tree/main) program designed to help kickstart empirical projects involving judgments. It automates many costly, time-consuming and mundane tasks in empirical research.

This pilot version can automatically

(1) search for and collect judgments of select Anglo-Australian courts;

(2) extract and code information from the judgment headnotes (ie metadata); and

(3) use a generative AI as a research assistant to answer your questions about each judgment.

This program can also process your own files or spreadsheet of data.
""")

if own_account_allowed() > 0:
    st.markdown("""**Complete this form to kickstart your project :green[for free] or :orange[with your own GPT account]!** The results of the abovementioned tasks will be available for download.
""")

else:
    st.markdown("""**Complete this form to kickstart your project :green[for free]!** A spreadsheet which hopefully has the data or information you seek will be available for download.
""")

st.caption('The Empirical Legal Research Kickstarter is the joint effort of Mike Lynch and Xinwei Luo of Sydney Informatics Hub and Ben Chen of Sydney Law School. It is partially funded by a University of Sydney Research Accelerator (SOAR) Prize awarded to Ben in 2022. Please direct any enquiries to Ben at ben.chen@sydney.edu.au.')

st.header("Start")

#    st.subheader("What would you like to study?")

st.markdown("""What would you like to study?""")
source_entry = st.selectbox("Please select a source of information to collect, code and analyse.", sources_list, index = source_index(st.session_state.source))
#    gpt_api_key_entry = st.text_input("Your GPT API key")

if source_entry:

    if source_entry != st.session_state.source:

        st.session_state.i_understand = False
        
    st.warning(f"This program is designed to help subject-matter experts who are able to evaluate the quality and accuracy of computer-generated information and/or data about {source_entry[0].lower()}{source_entry[1:]}. Please confirm that you understand.")
    
    browser_entry = st.checkbox('Yes, I understand.', value = st.session_state['i_understand'])

next_button = st.button('Next')


# %% [markdown]
# # Buttons

# %% editable=true slideshow={"slide_type": ""}
if next_button:

    if source_entry == None:

        st.write('You must choose a source of information.')

    elif browser_entry == False:
        st.write('You must tick "Yes, I understand." to use this program.')

    else:

        st.session_state.source = source_entry

        st.session_state.i_understand = browser_entry

        st.session_state["page_from"] = "Home.py"

        page_to = source_pages[sources_list.index(st.session_state.source)]

        st.switch_page(page_to)


