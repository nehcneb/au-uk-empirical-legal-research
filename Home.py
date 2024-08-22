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
   page_title="LawtoData: an Empirical Legal Research Kickstarter",
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
                #'judgments of the Canadian courts, boards and tribunals', 
                'Decisions of the Australian Financial Complaints Authority', 
                #'Decisions of the Superannuation Complaints Tribunal of Australia', 
                "The English Reports (nearly all English case reports from 1220 to 1866)",
                "The Kercher Reports (judgments of the New South Wales superior courts from 1788 to 1900)", 
                "Your own files", 
                "Your own spreadsheet"
               ]

source_pages = ["pages/HCA.py",
                "pages/FCA.py", 
                "pages/NSW.py", 
                #"pages/UK.py", 
                #"pages/CA.py", 
                "pages/AFCA.py", 
                #"pages/SCTA.py", 
                "pages/ER.py", 
                "pages/KR.py", 
                "pages/OWN.py", 
                'pages/AI.py']


# %%
def source_index(page_from):
    try:
        index = source_pages.index(page_from)
        return index
        
    except:
        
        return None



# %% editable=true slideshow={"slide_type": ""}
#Initialize

if 'page_from' not in st.session_state:
    
    st.session_state['page_from'] = 'Home.py'

#if 'source' not in st.session_state:
    #st.session_state['source'] = None

#if st.session_state.page_from:
    #default_source_index = sources_list.index(st.session_state['source'])
#else:
    #default_source_index = None

if 'i_understand' not in st.session_state:
    st.session_state['i_understand'] = False


# %% [markdown]
# # Form

# %% editable=true slideshow={"slide_type": ""}
#Create form

st.title(":blue[LawtoData]")

st.subheader("An Empirical Legal Research Kickstarter")

st.markdown("""*LawtoData* is an open-source program designed to help kickstart empirical projects involving judgments. It automates many costly, time-consuming and mundane tasks in empirical research.

This pilot version can automatically

(1) search for and collect judgments of select Anglo-Australian courts; and

(2) extract and code information or data from judgments, partially using a generative AI.

This program can also process your own files or spreadsheet of data.
""")

if own_account_allowed() > 0:
    st.markdown("""**Complete this form to kickstart your project :green[for free] or :orange[with your own GPT account]!** The results of the abovementioned tasks will be available for download.
""")

else:
    st.markdown("""**Use this program to kickstart your project :green[for free]!** A spreadsheet which hopefully has the data or information you seek will be available for download.
""")

#st.caption('The Empirical Legal Research Kickstarter is the joint effort of Mike Lynch and Xinwei Luo of Sydney Informatics Hub and Ben Chen of Sydney Law School. It is partially funded by a University of Sydney Research Accelerator (SOAR) Prize awarded to Ben in 2022. Please direct any enquiries to Ben at ben.chen@sydney.edu.au.')

st.caption('The developer Ben Chen acknowledges and greatly appreciates the exemplary technical assistance of Mike Lynch and Xinwei Luo of the Sydney Informatics Hub, a Core Research Facility of the University of Sydney, as well as the financial support provided by a University of Sydney Research Accelerator (SOAR) Prize. Please direct any enquiries to Ben at ben.chen@sydney.edu.au.')

st.header("Start")

#    st.subheader("What would you like to study?")

st.markdown("""What would you like to study?""")
source_entry = st.selectbox(label = "Please select a source of information to collect, code and analyse.", options = sources_list, index = source_index(st.session_state.page_from))
#    gpt_api_key_entry = st.text_input("Your GPT API key")

if source_entry:

    st.warning(f"This program is designed to help subject-matter experts who are able to evaluate the quality and accuracy of computer-generated data and/or information about {source_entry[0].lower()}{source_entry[1:]}. Please confirm that you understand.")

    if sources_list.index(source_entry) != source_index(st.session_state.page_from):

        st.session_state['i_understand'] = False
    
    i_unstanding_tick = st.checkbox('Yes, I understand.', value = st.session_state.i_understand)

home_next_button = st.button(label = 'NEXT', disabled = not (bool(source_entry)), help = 'To use this program, you must select a source of information and tick "[y]es, I understand[]".')

if source_entry:

    if sources_list.index(source_entry) != source_index(st.session_state.page_from):

        if ((source_index(st.session_state.page_from) != None) and ('df_master' in st.session_state)):
            #If page_from == CA or UK, for now, source_index(st.session_state.page_from) == None

            #page_from_index = source_pages.index(st.session_state.page_from)

            page_from_name = sources_list[source_index(st.session_state.page_from)]

            st.warning(f'Pressing NEXT will :red[erase] any earlier entries and data produced. To download such entries or data, please select {page_from_name[0].lower()}{page_from_name[1:]} instead.')



# %% [markdown]
# # Buttons

# %% editable=true slideshow={"slide_type": ""}
if home_next_button:

    if source_entry == None:

        st.write('You must select a source of information.')

    elif i_unstanding_tick == False:
        st.write('You must tick "Yes, I understand."')

    else:

        source_entry_index = sources_list.index(source_entry)

        #Clear df_master if one has been generated from another page
            
        if 'df_master' in st.session_state:

            if source_pages[source_entry_index] != st.session_state.page_from:

                st.session_state.pop('df_master')

        st.session_state.i_understand = i_unstanding_tick

        st.session_state["page_from"] = "Home.py"

        page_to = source_pages[source_entry_index]

        st.switch_page(page_to)


# %%
