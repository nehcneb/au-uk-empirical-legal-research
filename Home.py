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
#streamlit run Dropbox/Python/GitHub/lawtodata/Home.py

# %% [markdown] editable=true slideshow={"slide_type": ""}
# # Preliminaries

# %% editable=true slideshow={"slide_type": ""}
#Streamlit
import streamlit as st


# %% editable=true slideshow={"slide_type": ""}
#Title of webpage
st.set_page_config(
   page_title="LawtoData: An Empirical Legal Research Kickstarter",
   page_icon="🧊",
   layout="centered",
   initial_sidebar_state="collapsed",
)

# %%
#Determine whether to allow user to use own account
from functions.common_functions import own_account_allowed

if own_account_allowed() > 0:
    print(f'By default, users are allowed to use their own account.')
else:
    print(f'By default, users are NOT allowed to use their own account.')

# %%
#Determine whether to allow user to use batch mode
from functions.common_functions import batch_mode_allowed

if batch_mode_allowed() > 0:
    print(f'By default, users are allowed to use batch mode.')
else:
    print(f'By default, users are NOT allowed to use batch mode.')

# %%
#Dict of available sources
page_dict = {"pages/HCA.py": "Judgments of the High Court of Australia",
            "pages/FCA.py": "Judgments of the Federal Court of Australia", 
            "pages/NSW.py": "Judgments of the New South Wales courts and tribunals", 
            #"pages/UK.py": "Judgments of select United Kingdom courts and tribunals", 
            #"pages/CA.py": 'judgments of the Canadian courts, boards and tribunals', 
            "pages/AFCA.py": 'Decisions of the Australian Financial Complaints Authority', 
            #"pages/SCTA.py": 'Decisions of the Superannuation Complaints Tribunal of Australia', 
            "pages/ER.py": "The English Reports (nearly all English case reports from 1220 to 1866)", 
            "pages/KR.py": "The Kercher Reports (judgments of the New South Wales superior courts from 1788 to 1900)", 
            "pages/OWN.py": "Your own files", 
            'pages/AI.py': "Your own spreadsheet"
            }

#List of pages
page_list = [*page_dict.keys()]

#List of sources
source_list = [*page_dict.values()]


# %%
#Return index of page if available, none otherwise
def page_index(page_from):
    try:
        index = page_list.index(page_from)
        return index
        
    except: 
        return None



# %% editable=true slideshow={"slide_type": ""}
#Initialize

if 'page_from' not in st.session_state:
    st.session_state['page_from'] = 'Home.py'

if 'i_understand' not in st.session_state:
    st.session_state['i_understand'] = False


# %% [markdown]
# # Form

# %% editable=true slideshow={"slide_type": ""}
#Create form

st.title(":blue[LawtoData]")

st.subheader("An Empirical Legal Research Kickstarter")

st.markdown("""*LawtoData* is an [open-source](https://github.com/nehcneb/au-uk-empirical-legal-research) web app designed to help kickstart empirical projects involving judgments. It automates the most costly and time-consuming aspects of empirical research. 

This pilot version can **automatically**

(1) search for and collect judgments of select Anglo-Australian courts; and

(2) extract and code **your** choice of data or information from judgments, partially using GPT.

This app can also process your own files or spreadsheet of data.
""")

if own_account_allowed() > 0:
    st.markdown("""**Get started below :green[for free] or :orange[with your own GPT account]!** A spreadsheet which hopefully has the data or information you seek will be available for download.
""")

else:
    st.markdown("""**Get started below :green[for free]!** A spreadsheet which hopefully has the data or information you seek will be available for download.
""")

st.caption('The developer Ben Chen acknowledges and greatly appreciates the exemplary technical assistance of Mike Lynch and Xinwei Luo of the Sydney Informatics Hub, a Core Research Facility of the University of Sydney, as well as the financial support provided by a University of Sydney Research Accelerator (SOAR) Prize. Please direct any enquiries to Ben at ben.chen@sydney.edu.au.')

st.header("Start")

st.markdown("""You will be asked to

(1) select a court, tribunal, or another source of information to research; 

(2) enter search terms to identify your preferred judgments, or upload your own files; 

(3) enter questions about each judgment or file for GPT to answer.
""")

st.subheader(""":green[What would you like to research?]""")

source_entry = st.selectbox(label = "Please select a source of information to collect, code and analyse.", options = source_list, index = page_index(st.session_state.page_from))

if source_entry:

    st.warning(f"This app is designed to help subject-matter experts who are able to evaluate the quality and accuracy of computer-generated data and/or information about {source_entry[0].lower()}{source_entry[1:]}. Please confirm that you understand.")

    if source_list.index(source_entry) != page_index(st.session_state.page_from):

        st.session_state['i_understand'] = False
    
    i_unstanding_tick = st.checkbox('Yes, I understand.', value = st.session_state.i_understand)

home_next_button = st.button(label = 'NEXT', disabled = not (bool(source_entry)), help = 'To use this app, you must select a source of information and tick "[y]es, I understand[]".')

if source_entry:

    if source_list.index(source_entry) != page_index(st.session_state.page_from):

        if ((page_index(st.session_state.page_from) != None) and ('df_master' in st.session_state)):

            page_from_name = source_list[page_index(st.session_state.page_from)]

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

        source_entry_index = source_list.index(source_entry)

        #Clear df_master if one has been generated from another page
        if 'df_master' in st.session_state:

            if page_list[source_entry_index] != st.session_state.page_from:

                st.session_state.pop('df_master')

        st.session_state.i_understand = i_unstanding_tick

        st.session_state["page_from"] = "Home.py"

        page_to = page_list[source_entry_index]

        st.switch_page(page_to)

