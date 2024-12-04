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

# %% [markdown] editable=true slideshow={"slide_type": ""}
# # Preliminaries

# %% editable=true slideshow={"slide_type": ""}
from PIL import Image

#Streamlit
import streamlit as st


# %%
#Initialise image counter
if 'image_index' not in st.session_state:
    st.session_state['image_index'] = 0


# %% [markdown]
# # Fig specifications

# %%
#Image list
image_list = ['figs/relationship.png', 
             'figs/age.png', 
              'figs/gender.png', 
              'figs/outcome.png',
              'figs/1p1d_total_costs_proportion.png'
            'figs/1p1d_costs_relative_female.png', 
              'figs/1p1d_costs_relative_male.png', 
             ]

# %%
#Initialise default image to show
if 'image_to_show' not in st.session_state:
    
    st.session_state['image_to_show'] = Image.open(image_list[0])


# %%
def next():
            
    st.session_state.image_index += 1
    
def prev():
    
    st.session_state.image_index -= 1



# %% [markdown]
# # Show heading

# %%
st.header("Family Provision Cases: Preliminary Results")


# %% [markdown]
# # Show figs

# %%
st.session_state['image_to_show'] = Image.open(image_list[st.session_state.image_index])

st.image(st.session_state['image_to_show'])


# %% [markdown]
# # Show buttons

# %%
cols = st.columns(2)

with cols[1]:
    st.button("Next ➡️", on_click=next, disabled = bool(st.session_state.image_index >= len(image_list) - 1), use_container_width=True)
    
with cols[0]:
    st.button("⬅️ Previous", on_click=prev, disabled = bool(st.session_state.image_index <= 0), use_container_width=True)    



# %%
