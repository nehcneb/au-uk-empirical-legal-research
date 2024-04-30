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
#streamlit run Dropbox/Python/GitHub/au-uk-empirical-legal-research/Home.py

# %% [markdown] editable=true slideshow={"slide_type": ""}
# # Preliminaries

# %% editable=true slideshow={"slide_type": ""}
#Preliminary modules

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

# %% editable=true slideshow={"slide_type": ""}
#List of sources of information
sources_list = ["Judgments of select New South Wales courts", 
                "Judgments of the Federal Court of Australia", 
                "Judgments of select United Kingdom courts and tribunals", 
                "The Kercher Reports (decisions of the New South Wales superior courts from 1788 to 1900)", 
                "The English Reports (nearly all English case reports from 1220 to 1866)",
                "Your own files", 
                "Your own spreadsheet"
               ]


# %% editable=true slideshow={"slide_type": ""}
#Default values
if 'name' in st.session_state:
    default_name = st.session_state['name']
else:
    default_name = None

if 'email' in st.session_state:
    default_email = st.session_state['email']
else:
    default_email = None
    
if 'gpt_api_key' in st.session_state:
    default_gpt_api_key = st.session_state['gpt_api_key']
else:
    default_gpt_api_key = None

if 'source' in st.session_state:
    default_source_index = sources_list.index(st.session_state['source'])
else:
    default_source_index = None


# %% [markdown]
# # Form

# %% editable=true slideshow={"slide_type": ""}
#Create form

with st.form("GPT_input_form") as df_responses:
    st.title("The Empirical Legal Research Kickstarter")
    st.header("An Anglo-Australian Pilot")
    
    st.markdown("""*The Empirical Legal Research Kickstarter* is a web-based program designed to help kickstart empirical research involving judgments. It automates many costly, time-consuming and mundane tasks in empirical research.

This pilot version can automatically

(1) search for and collect judgments of select Anglo-Australian courts;

(2) extract and code information from the judgment headnotes (ie metadata); and

(3) use a generative AI as a research assistant to answer your questions about each judgment.

This program can also process your own files or spreadsheet of data.

**Complete this form to kickstart your project :green[for free]!** The results of the above tasks will be available for download.
""")
    st.caption('The Empirical Legal Research Kickstarter is the joint effort of Mike Lynch and Xinwei Luo of Sydney Informatics Hub and Ben Chen of Sydney Law School. It is partially funded by a University of Sydney Research Accelerator (SOAR) Prize awarded to Ben in 2022. Please send any enquiries to Ben at ben.chen@sydney.edu.au.')

    st.header("Start")

#    st.write("This program may not work on a mobile device or a tablet. Please use a desktop or a laptop.")

#    browser_entry = st.checkbox('Yes, I understand.', value = False)

#    st.subheader("What would you like to study?")

    st.markdown("""What would you like to study?""")
    source_entry = st.selectbox("Please select a source of information to collect, code and analyse.", sources_list, index = default_source_index)
#    gpt_api_key_entry = st.text_input("Your GPT API key")

    
    next_button = st.form_submit_button('Next')


# %% [markdown]
# # Buttons

# %% editable=true slideshow={"slide_type": ""}
if next_button:

#    if int(browser_entry) == 0:
#        st.write('You must confirm that you understand this program may not work on a mobile device or a tablet.')

#    elif source_entry == None:
    if source_entry == None:

        st.write('You must choose a source of information.')

    else:

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



