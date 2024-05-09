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


# %%
#Whether users are allowed to use their account
from extra_functions import own_account_allowed

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

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

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account')
else:
    print(f'By default, users are NOT allowed to use their own account')

# %% editable=true slideshow={"slide_type": ""}
#List of sources of information
sources_list = ["Judgments of the New South Wales courts and tribunals", 
                "Judgments of the Federal Court of Australia", 
                #"Judgments of the United Kingdom courts and tribunals", 
                "The Kercher Reports (decisions of the New South Wales superior courts from 1788 to 1900)", 
                "The English Reports (nearly all English case reports from 1220 to 1866)",
                "Your own files", 
                "Your own spreadsheet"
               ]


# %% editable=true slideshow={"slide_type": ""}
#Initialize source and understanding

if 'source' not in st.session_state:
    st.session_state['source'] = None

if st.session_state.source:
    default_source_index = sources_list.index(st.session_state['source'])
else:
    default_source_index = None

if 'i_understand' not in st.session_state:
    st.session_state['i_understand'] = False


# %% [markdown]
# # Form

# %% editable=true slideshow={"slide_type": ""}
#Create form

st.title("The Empirical Legal Research Kickstarter")
st.header("An Anglo-Australian Pilot")

st.markdown("""*The Empirical Legal Research Kickstarter* is a web-based program designed to help kickstart empirical research involving judgments. It automates many costly, time-consuming and mundane tasks in empirical research.

This pilot version can automatically

(1) search for and collect judgments of select Anglo-Australian courts;

(2) extract and code information from the judgment headnotes (ie metadata); and

(3) use a generative AI as a research assistant to answer your questions about each judgment.

This program can also process your own files or spreadsheet of data.

**Complete this form to kickstart your project :green[for free] or :orange[with your own GPT account]!** The results of the abovementioned tasks will be available for download.
""")
st.caption('The Empirical Legal Research Kickstarter is the joint effort of Mike Lynch and Xinwei Luo of Sydney Informatics Hub and Ben Chen of Sydney Law School. It is partially funded by a University of Sydney Research Accelerator (SOAR) Prize awarded to Ben in 2022. Please send any enquiries to Ben at ben.chen@sydney.edu.au.')

st.header("Start")


#    st.subheader("What would you like to study?")

st.markdown("""What would you like to study?""")
source_entry = st.selectbox("Please select a source of information to collect, code and analyse.", sources_list, index = default_source_index)
#    gpt_api_key_entry = st.text_input("Your GPT API key")

if source_entry:

    if source_entry != st.session_state.source:

        st.session_state.i_understand = False
    
    st.warning(f"This program is designed to help subject-matter experts who are able to evaluate the quality and accruacy of computer-generated information or data about {source_entry[0].lower()}{source_entry[1:]}. Please confirm that you understand.")

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

        st.session_state.i_understand = True

        st.session_state["page_from"] = "Home.py"
    
        if (('New South Wales' in source_entry) and ('Kercher' not in source_entry)):
            st.switch_page("pages/NSW.py")
    
        if 'Federal Court of Australia' in source_entry:
            
            st.switch_page("pages/CTH.py")
    
        if 'United Kingdom' in source_entry:
            
            st.switch_page("pages/UK.py")
            
        if 'Kercher' in source_entry:
            
            st.switch_page("pages/KR.py")

        if 'English Reports' in source_entry:
            
            st.switch_page("pages/ER.py")
            
        if ' own files' in source_entry:

            st.switch_page("pages/OWN.py")

        if ' own spreadsheet' in source_entry:
            st.switch_page('pages/AI.py')



