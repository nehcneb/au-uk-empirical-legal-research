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
import numpy as np
import re
import datetime
from datetime import date
from dateutil import parser
#from dateutil.relativedelta import *
from datetime import datetime, timedelta
import sys
import pause
import requests
from bs4 import BeautifulSoup, SoupStrainer
import httplib2
from urllib.request import urlretrieve
import os
from io import BytesIO
import ast
import math
import copy

#Streamlit
import streamlit as st
#from streamlit_gsheets import GSheetsConnection
from streamlit.components.v1 import html
#import streamlit_ext as ste
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
from functions.common_functions import own_account_allowed, pop_judgment, convert_df_to_json, convert_df_to_csv, convert_df_to_excel, list_range_check, date_parser, save_input
#Import variables
from functions.common_functions import today_in_nums, errors_list, scraper_pause_mean, judgment_text_lower_bound, default_judgment_counter_bound, no_results_msg


# %% [markdown]
# # UK Courts search engine

# %% [markdown]
# ### Definitions

# %%
#Initialize default courts

uk_courts_default_list = ['United Kingdom Supreme Court',
 'Privy Council',
 'Court of Appeal Civil Division',
 'Court of Appeal Criminal Division',
 'High Court (England & Wales) Administrative Court',
 'High Court (England & Wales) Admiralty Court',
 'High Court (England & Wales) Chancery Division',
 'High Court (England & Wales) Commercial Court',
 'High Court (England & Wales) Family Division',
 'High Court (England & Wales) Intellectual Property Enterprise Court',
 "High Court (England & Wales) King's/Queen's Bench Division",
 'High Court (England & Wales) Mercantile Court',
 'High Court (England & Wales) Patents Court',
 'High Court (England & Wales) Senior Courts Costs Office',
 'High Court (England & Wales) Technology and Construction Court'
]


# %%
#Define format functions for courts choice, and GPT questions

#auxiliary lists and variables
uk_courts ={'United Kingdom Supreme Court': 'uksc',
'Privy Council': 'ukpc',  
'Court of Appeal Civil Division': 'ewca/civ', 
 'Court of Appeal Criminal Division':  'ewca/crim',  
'High Court (England & Wales) Administrative Court': 'ewhc/admin',
'High Court (England & Wales) Admiralty Court': 'ewhc/admlty',  
'High Court (England & Wales) Chancery Division': 'ewhc/ch',  
'High Court (England & Wales) Commercial Court': 'ewhc/comm',  
'High Court (England & Wales) Family Division': 'ewhc/fam',  
'High Court (England & Wales) Intellectual Property Enterprise Court': 'ewhc/ipec',  
"High Court (England & Wales) King's/Queen's Bench Division" : 'ewhc/kb',
'High Court (England & Wales) Mercantile Court': 'ewhc/mercantile',  
'High Court (England & Wales) Patents Court': 'ewhc/pat',  
'High Court (England & Wales) Senior Courts Costs Office': 'ewhc/scco',  
'High Court (England & Wales) Technology and Construction Court': 'ewhc/tcc',  
'Court of Protection': 'ewcop',  
'Family Court': 'ewfc',  
'Employment Appeal Tribunal': 'eat',  
'Administrative Appeals Chamber': 'ukut/aac',  
'Immigration and Asylum Chamber': 'ukut/iac',
'Lands Chamber': 'ukut/lc',  
'Tax and Chancery Chamber': 'ukut/tcc',  
'General Regulatory Chamber': 'ukftt/grc',  
'Tax Chamber' : 'ukftt/tc'
}

uk_courts_list = list(uk_courts.keys())

def uk_court_choice(chosen_list):

    chosen_indice = []

    if isinstance(chosen_list, str):
        chosen_list = ast.literal_eval(chosen_list)

    for i in chosen_list:
        chosen_indice.append(uk_courts[i])
    
    return chosen_indice



# %%
uk_order_dict = {'Relevance': '', 'Newest': '-date', 'Oldest': 'date'}

# %%
uk_meta_labels_droppable = ['Date', 
                         'Court', 
                         'Case number', 
                         'Judge(s) (non-exhaustive)', 
                         'Parties', 
                         'Header'
                        ]

# %% [markdown]
# ### Search engine

# %%
from functions.common_functions import link


# %%
class uk_search_tool:
    """
    Refactor of:
      - uk_search
      - uk_search_results_to_judgment_links
      - uk_meta_judgment_dict

    Workflow:
      tool = uk_search_tool(query="...", court=[...], judgment_counter_bound=50)
      tool.search()
      tool.get_case_infos()         # parses results pages -> self.case_infos
      tool.get_judgments()          # fetches metadata+judgment -> self.case_infos_w_judgments
    """

    BASE_URL = "https://caselaw.nationalarchives.gov.uk/judgments/search"
    UK_URL_START = "https://caselaw.nationalarchives.gov.uk"

    def __init__(
        self,
        query="",
        from_day="",
        from_month="",
        from_year="",
        to_day="",
        to_month="",
        to_year="",
        court=None,
        party="",
        judge="",
        order = list(uk_order_dict.keys())[0],
        judgment_counter_bound=default_judgment_counter_bound,
        *,
        session=None,
        timeout=30,
        headers=None,
        pause_between_pages_range=(10, 20),
        pause_between_judgments_range=(10, 20),
    ):
        
        # --- search params ---
        self.query = query
        self.from_day = from_day
        self.from_month = from_month
        self.from_year = from_year
        self.to_day = to_day
        self.to_month = to_month
        self.to_year = to_year
        self.court = court or []
        self.party = party
        self.judge = judge
        self.order = order

        # --- scraping controls ---
        self.judgment_counter_bound = judgment_counter_bound
        self.timeout = timeout
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (compatible; uk_search_tool/1.0)"
        }

        self.pause_between_pages_range = pause_between_pages_range
        self.pause_between_judgments_range = pause_between_judgments_range

        # --- requests session ---
        self.session = session or requests.Session()

        # --- outputs / state ---
        self.results_url = ""
        self.results_count = 0
        self.soup = None

        self.case_infos = []
        self.case_infos_w_judgments = []

    # -------------------------
    # 1) Search -> results_url, results_count, soup
    # -------------------------
    def search(self):
        """
        Equivalent of uk_search().
        Populates:
          - self.results_url
          - self.results_count
          - self.soup
        Returns dict like original for convenience.
        """
        params = {
            "per_page": 50,
            "order": "relevance",
            "query": self.query,
            "from_date_0": self.from_day,
            "from_date_1": self.from_month,
            "from_date_2": self.from_year,
            "to_date_0": self.to_day,
            "to_date_1": self.to_month,
            "to_date_2": self.to_year,
            "court": uk_court_choice(self.court),  # external helper in your codebase
            "party": self.party,
            "judge": self.judge,
        }

        if self.order != list(uk_order_dict.keys())[0]:

            params.update({'order': uk_order_dict[self.order]})

        resp = self.session.get(
            self.BASE_URL,
            params=params,
            headers=self.headers,
            timeout=self.timeout
        )
        resp.raise_for_status()

        self.results_url = resp.url
        self.results_count = 0
        self.soup = None

        try:
            self.soup = BeautifulSoup(resp.content, "lxml")
            results_count_raw = self.soup.find("p", {"class": "results__results-intro"})
            if results_count_raw:
                cleaned = results_count_raw.get_text(strip=True)
                self.results_count = int(float(cleaned.split(" ")[0].replace(",", "")))
        except Exception as e:
            print(f"No results found or failed parsing results_count due to error: {e}")

        return {
            "results_url": self.results_url,
            "results_count": self.results_count,
            "soup": self.soup,
        }

    # -------------------------
    # 2) Results pages -> case_infos
    # -------------------------
    def get_case_infos(self):
        if self.soup is None or not self.results_url:
            self.search()
    
        self.case_infos = []
    
        # Ensure soup type (for page 1)
        if self.soup is not None and not isinstance(self.soup, BeautifulSoup):
            self.soup = BeautifulSoup(self.soup, "lxml")
    
        page_total = math.ceil(self.results_count / 50) if self.results_count else 0
        page_counter = 1
        counter = 0
    
        while page_counter <= max(page_total, 1):
    
            if page_counter > 1:

                pause.seconds(np.random.randint(*self.pause_between_pages_range))
    
                url_next_page = self.results_url + f"&page={page_counter}"
                print(
                    f"Getting case_infos from search results page "
                    f"{page_counter}/{page_total}. url_next_page == {url_next_page}"
                )
    
                page_resp = self.session.get(
                    url_next_page,
                    headers=self.headers,
                    timeout=self.timeout
                )
                page_resp.raise_for_status()
    
                # IMPORTANT: update self.soup to the new page
                self.soup = BeautifulSoup(page_resp.content, "lxml")
    
            else:
                print(
                    f"Getting case_infos from search results page "
                    f"{page_counter}/{page_total}. results_url == {self.results_url}"
                )
    
            # Now always parse from self.soup
            table = self.soup.find("div", class_="documents-table")
            if not table:
                break
    
            tbodies = table.find_all("tbody")
    
            for tbody in tbodies:
                if counter >= min(self.judgment_counter_bound, self.results_count or self.judgment_counter_bound):
                    page_counter = page_total + 1
                    break
    
                rows = tbody.find_all("tr")
    
                title = ""
                url = ""
                court = ""
                citation = ""
                handed_down = ""
    
                try:
                    link = rows[0].find("a")
                    title = link.get_text(strip=True)
                    url = link.get("href", "")
                except (IndexError, AttributeError):
                    pass
    
                try:
                    tds = rows[1].find_all("td")
                except IndexError:
                    tds = []
    
                try:
                    court = tds[0].contents[0].strip()
                except (IndexError, AttributeError):
                    pass
    
                try:
                    citation = (
                        tds[1]
                        .get_text(strip=True)
                        .replace("Neutral citation", "")
                        .strip()
                    )
                except (IndexError, AttributeError):
                    pass
    
                try:
                    handed_down = (
                        tds[2]
                        .get_text(strip=True)
                        .replace("Handed down", "")
                        .strip()
                    )
                except (IndexError, AttributeError):
                    pass
    
                self.case_infos.append({
                    "Case name": title,
                    "Medium neutral citation": citation,
                    "Hyperlink to The National Archives": f"{self.UK_URL_START}{url}",
                    "Court": court,
                    "Date": handed_down
                })
    
                counter += 1
    
            page_counter += 1
    
        return self.case_infos

    # -------------------------
    # 3) Helpers for judgment xml/html
    # -------------------------
    @staticmethod
    def to_xml_url(judgment_html_or_xml_url: str) -> str:
        """
        The metadata XML is usually at: <case_url>/data.xml
        If user passed HTML URL, convert it.
        """
        if not judgment_html_or_xml_url:
            return ""
        if judgment_html_or_xml_url.endswith("/data.xml"):
            return judgment_html_or_xml_url
        # If it already contains 'data.xml' elsewhere, leave it
        if "data.xml" in judgment_html_or_xml_url:
            return judgment_html_or_xml_url
        # Otherwise append
        return judgment_html_or_xml_url.rstrip("/") + "/data.xml"

    # -------------------------
    # 4) One judgment -> dict (meta + judgment text)
    # -------------------------
    
    def get_judgment_dict(self, case_info: dict):
    
        judgment_url_xml = self.to_xml_url(case_info["Hyperlink to The National Archives"])
        judgment_url_html = judgment_url_xml.replace("/data.xml", "")
    
        judgment_dict = copy.deepcopy(case_info)
        judgment_dict.update({
            "Case number": "",
            "Judge(s) (non-exhaustive)": [],
            "Parties": [],
            "Header": "",
            "judgment": "",
        })
    
        # -------------------------
        # Judgment text + HEADER METADATA (HTML page)
        # -------------------------
        soup_html = None
        try:
            page_html = self.session.get(
                judgment_url_html,
                headers=self.headers,
                timeout=self.timeout
            )
            page_html.raise_for_status()
            soup_html = BeautifulSoup(page_html.content, "lxml")
    
            # Full judgment text
            judgment_text = soup_html.get_text(separator="\n", strip=True)
            try:
                before_end = judgment_text.split("End of document")[0]
                after_skip = before_end.split("Skip to end")[1]
                judgment_text = after_skip
            except Exception:
                pass
            judgment_dict["judgment"] = judgment_text
    
            # Header block (rendered)
            header_block = soup_html.select_one("article.judgment > header.judgment-header")
            if header_block:
                judgment_dict["Header"] = header_block.get_text("\n", strip=True)
    
            # -------------------------
            # 1) Case number (HTML)
            # -------------------------
            # Example: <div class="judgment-header__case-number">Case No: PT-2024-000665</div> [1](https://unisyd-my.sharepoint.com/personal/ben_chen_sydney_edu_au/Documents/Microsoft%20Copilot%20Chat%20Files/output.xml)
            cn = soup_html.select_one("div.judgment-header__case-number")
            if cn:
                cn_text = cn.get_text(" ", strip=True)
                cn_text = re.sub(r"^Case\s*No:\s*", "", cn_text, flags=re.I).strip()
                judgment_dict["Case number"] = cn_text
    
            # -------------------------
            # 2) Judges (HTML)
            # -------------------------
            # In your example, judge appears after "Before:" in centered <p> with <u> text. [1](https://unisyd-my.sharepoint.com/personal/ben_chen_sydney_edu_au/Documents/Microsoft%20Copilot%20Chat%20Files/output.xml)
            judges = []
    
            # Robust: find the "Before" marker then take subsequent centered underlined names
            before_ps = soup_html.select("p.judgment-header__pr-center")
            before_index = None
            for i, p in enumerate(before_ps):
                if "before" in p.get_text(" ", strip=True).lower():
                    before_index = i
                    break
    
            if before_index is not None:
                # collect underlined names following "Before" until we hit "Between" or line separator
                for p in before_ps[before_index+1:]:
                    text = p.get_text(" ", strip=True)
                    if "between" in text.lower():
                        break
                    u = p.find("u")
                    if u:
                        name = u.get_text(" ", strip=True)
                        # Filter out role lines like "SITTING AS..." if you want only personal name:
                        if name and "sitting as" not in name.lower():
                            judges.append(name)
    
            # fallback: any underlined centered b/u entries near top
            if not judges:
                for u in soup_html.select("header.judgment-header p.judgment-header__pr-center b u"):
                    name = u.get_text(" ", strip=True)
                    if name and "sitting as" not in name.lower():
                        judges.append(name)
    
            # de-dupe
            if judges:
                judgment_dict["Judge(s) (non-exhaustive)"] = list(dict.fromkeys(judges))
    
            # -------------------------
            # 3) Parties (HTML)
            # -------------------------
            # Example table: <table class="pr-two-column"> contains claimant + defendants in bold. [1](https://unisyd-my.sharepoint.com/personal/ben_chen_sydney_edu_au/Documents/Microsoft%20Copilot%20Chat%20Files/output.xml)
            parties = []
            party_table = soup_html.select_one("table.pr-two-column")
            if party_table:
                # Extract bold text entries; filter out noise like "(1)", "(2)", "- and –"
                bolds = [b.get_text(" ", strip=True) for b in party_table.select("b")]
                noise = {"(1)", "(2)", "- and –", "- and -", "and", "Between :", "Between:"}
                for txt in bolds:
                    t = txt.strip()
                    if not t or t in noise:
                        continue
                    # also skip role labels
                    if t.lower() in {"claimant", "defendant", "defendants"}:
                        continue
                    parties.append(t)
    
            if parties:
                judgment_dict["Parties"] = list(dict.fromkeys(parties))
    
        except Exception as e:
            print(f"[HTML] failed for {judgment_url_html}: {e}")
    
        # Pause (your existing behaviour)
        pause.seconds(np.random.randint(*self.pause_between_judgments_range))
    
        # -------------------------
        # XML metadata (fallback only)
        # -------------------------
        # Only attempt to fill if still missing after HTML.
        try:
            resp = self.session.get(
                judgment_url_xml,
                headers={**self.headers, "Accept": "application/xml,text/xml,*/*"},
                timeout=self.timeout
            )
            resp.raise_for_status()
            soup_xml = BeautifulSoup(resp.content, "xml")
    
            def first_tag_endswith(suffix: str):
                suffix = suffix.lower()
                return soup_xml.find(lambda t: getattr(t, "name", "") and t.name.lower().endswith(suffix))
    
            def all_tags_endswith(suffix: str):
                suffix = suffix.lower()
                return soup_xml.find_all(lambda t: getattr(t, "name", "") and t.name.lower().endswith(suffix))
    
            # Case number fallback (XML)
            if not judgment_dict["Case number"]:
                frbrnumber = first_tag_endswith("frbrnumber")
                if frbrnumber and frbrnumber.has_attr("value"):
                    judgment_dict["Case number"] = frbrnumber["value"].strip()
    
            # Judges/Parties fallback (XML)
            if not judgment_dict["Judge(s) (non-exhaustive)"] or not judgment_dict["Parties"]:
                judges_xml = []
                parties_xml = []
                persons = all_tags_endswith("tlcperson")
                for p in persons:
                    showas = p.get("showAs") or p.get("showas") or ""
                    if not showas:
                        continue
                    eid = (p.get("eId") or p.get("eid") or "").lower()
                    if "judge" in eid:
                        judges_xml.append(showas)
                    else:
                        parties_xml.append(showas)
    
                if not judgment_dict["Judge(s) (non-exhaustive)"] and judges_xml:
                    judgment_dict["Judge(s) (non-exhaustive)"] = list(dict.fromkeys(judges_xml))
                if not judgment_dict["Parties"] and parties_xml:
                    judgment_dict["Parties"] = list(dict.fromkeys(parties_xml))
    
        except Exception as e:
            print(f"[XML metadata] failed for {judgment_url_xml}: {e}")
    
        # Make hyperlink clickable (your existing logic)
        for key in judgment_dict:
            if "Hyperlink" in key:
                direct_link = judgment_dict[key]
                if isinstance(direct_link, str) and "?" in direct_link:
                    direct_link = direct_link.split("?")[0]
                judgment_dict[key] = link(direct_link)
                break
    
        return judgment_dict

    # -------------------------
    # 5) Many judgments -> list
    # -------------------------
    def get_judgments(self):
        """
        Convenience method:
          - ensure case_infos exist
          - for each case, pull xml+html and attach judgment text
        Populates:
          - self.case_infos_w_judgments
        """
        if not self.case_infos:
            self.get_case_infos()

        self.case_infos_w_judgments = []

        #Get judgments from cases shown on the initial page (page 1)
        for case_info in self.case_infos:
            
            if len(self.case_infos_w_judgments) < min(self.results_count, self.judgment_counter_bound):

                #Attach judgment text etc to case_info dict
                case_info_w_judgment = self.get_judgment_dict(case_info)
        
                self.case_infos_w_judgments.append(case_info_w_judgment)

                pause.seconds(np.random.randint(*self.pause_between_judgments_range))
                
                print(f"Scraped {len(self.case_infos_w_judgments)}/{min(self.results_count, self.judgment_counter_bound)} judgments.")

        return self.case_infos_w_judgments


# %%
#@st.cache_data(show_spinner=False, ttl=600)
def uk_search_function(
    query,
    from_day,
    from_month,
    from_year,
    to_day,
    to_month,
    to_year,
    court,
    party,
    judge,
    order, 
    judgment_counter_bound,
):
    """
    Thin wrapper around uk_search_tool that:
      1) creates the tool with the provided inputs
      2) runs .search()
      3) returns the tool instance (like hk_search_function)
    """

    uk_search = uk_search_tool(
        query=query,
        from_day=from_day,
        from_month=from_month,
        from_year=from_year,
        to_day=to_day,
        to_month=to_month,
        to_year=to_year,
        court=court,
        party=party,
        judge=judge,
        order = order,
        judgment_counter_bound=judgment_counter_bound,
    )

    uk_search.search()

    uk_search.get_case_infos()    
    
    return uk_search


# %%
def uk_search_preview(df_master):
    
    df_master = df_master.fillna('')
            
    #Conduct search

    uk_search = uk_search_tool(query= df_master.loc[0, 'Free text'], 
                               from_day= df_master.loc[0, 'From day'],
                               from_month=df_master.loc[0, 'From month'], 
                               from_year=df_master.loc[0, 'From year'], 
                               to_day=df_master.loc[0, 'To day'], 
                               to_month=df_master.loc[0, 'To month'], 
                               to_year=df_master.loc[0, 'To year'], 
                               court= df_master.loc[0, 'Courts'], 
                               party = df_master.loc[0, 'Party'], 
                               judge = df_master.loc[0, 'Judge'],
                               order = df_master.loc[0, 'Order results by'],
                               judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments']),                               
                              )

    uk_search.search()

    uk_search.get_case_infos()    
    
    results_count = uk_search.results_count
    case_infos = uk_search.case_infos

    results_url = uk_search.results_url

    #st.write(results_url)
    
    return {'results_url': results_url, 'results_count': results_count, 'case_infos': case_infos}


# %% [markdown]
# ### Functions from before changing to a class structure

# %%
#Function turning search terms to search results url
#NOT IN USE

#@st.cache_data(show_spinner = False)
def uk_search(query= '', 
              from_day= '',
              from_month='', 
              from_year='', 
              to_day='', 
              to_month='', 
              to_year='', 
              court = [], 
              party = '', 
              judge = ''
             ):
    base_url = "https://caselaw.nationalarchives.gov.uk/judgments/search?per_page=50&order=relevance"
    params = {'query' : query, 
              'from_date_0' : from_day,
              'from_date_1' : from_month, 
              'from_date_2' : from_year, 
              'to_date_0' : to_day, 
              'to_date_1' : to_month, 
              'to_date_2' : to_year, 
              'court' : uk_court_choice(court), 
              'party' : party, 
              'judge' : judge}

    response = requests.get(base_url, params=params)
    response.raise_for_status()

    #Get results count

    results_count = 0

    try:
        soup = BeautifulSoup(response.content, "lxml")
        results_count_raw = soup.find('p', {'class': "results__results-intro"})
        results_count_cleaned = results_count_raw.get_text(strip = True)
        results_count = int(float(results_count_cleaned.split(' ')[0].replace(',', '')))

    except Exception as e:
        
        print(f'No results found due to error: {e}')


    #Get soup
    #soup = BeautifulSoup(response.content, "lxml")

    return_dict = {'results_url': response.url, 'results_count': results_count, 'soup': soup}

    #st.write(return_dict)
    
    return return_dict


# %%
#Define function turning search results url to case_infos to judgments
#NOT IN USE

#@st.cache_data(show_spinner = False, ttl=600)
def uk_search_results_to_judgment_links(_soup, results_url, results_count, judgment_counter_bound):

    #Initialise list of results to return
    case_infos = []

    #_soup is from scraping per uk_search
    if not isinstance(_soup, BeautifulSoup):

        _soup = BeautifulSoup(_soup, "lxml")
        
    #Get total number of pages; 50 results per page
    page_total = math.ceil(results_count/50)

    #st.write(f'page_total == {page_total}')
    
    #Start counters
    page_counter = 1
    
    counter = 0

    #Beginning of url
    uk_url_start = 'https://caselaw.nationalarchives.gov.uk'
    
    #Start looping through pages
    
    while page_counter <= page_total:
    
        if page_counter > 1:
            
            pause.seconds(np.random.randint(10, 20))

            url_next_page = results_url + f"&page={page_counter}"

            print(f"Getting case_infos from search results page {page_counter}/{page_total}. url_next_page == {url_next_page}")
            
            page_judgment_next_page = requests.get(url_next_page)
            
            _soup = BeautifulSoup(page_judgment_next_page.content, "lxml")

        else:
        
            print(f"Getting case_infos from search results page {page_counter}/{page_total}. results_url == {results_url}")
            
        #Results from page {page_counter}
        results = _soup.find("div", class_="documents-table") \
                       .find_all("tbody")

        for result in results:

            if counter < min(judgment_counter_bound, results_count):
                
                rows = result.find_all("tr")
                
                # --- defaults ---
                title = ""
                url = ""
                court = ""
                citation = ""
                handed_down = ""
                
                # --- title + link (first row) ---
                try:
                    link = rows[0].find("a")
                    title = link.get_text(strip=True)
                    url = link.get("href", "")
                except (IndexError, AttributeError):
                    pass
                
                # --- details (second row) ---
                try:
                    tds = rows[1].find_all("td")
                except IndexError:
                    tds = []
                
                try:
                    court = tds[0].contents[0].strip()
                except (IndexError, AttributeError):
                    pass
                
                try:
                    citation = (
                        tds[1]
                        .get_text(strip=True)
                        .replace("Neutral citation", "")
                        .strip()
                    )
                except (IndexError, AttributeError):
                    pass
                
                try:
                    handed_down = (
                        tds[2]
                        .get_text(strip=True)
                        .replace("Handed down", "")
                        .strip()
                    )
                except (IndexError, AttributeError):
                    pass
                
                case_infos.append({
                    "Case name": title,
                    "Medium neutral citation": citation,
                    "Hyperlink to The National Archives": f'{uk_url_start}{url}',
                    "Court": court,
                    "Date": handed_down
                })
                
                                
                counter += 1

                #print(f"Scrapped {counter}/{min(judgment_counter_bound, results_count)} judgments")
                
            else:

                page_counter += page_total
                
                break
        
        page_counter += 1

    #st.write(case_infos)
                
    return case_infos

# %%
#Meta labels and judgment combined
#NOT IN USE


#Tidy up hyperlink
def uk_link(x):
    y =str(x).replace('.uk/id', '.uk')
    value = '=HYPERLINK("' + y + '")'
    return value

#@st.cache_data(show_spinner = False)
def uk_meta_judgment_dict(judgment_url_xml):

    judgment_dict = {'Case name': '',
                 'Medium neutral citation': '',
                'Hyperlink to The National Archives' : '', 
                'Date' : '',
                'Court' : '', 
                'Case number': '',
                'Judge(s) (non-exhaustive)' : [], 
                'Parties' : [],
                'Header' : '',
                'judgment': ''
                }

    #Get metadata

    try:
        
        page = requests.get(judgment_url_xml)
        soup = BeautifulSoup(page.content, "lxml")
    
        judgment_dict['Case name'] = soup.find("frbrname")['value']
        judgment_dict['Medium neutral citation'] = soup.find("uk:cite").getText()
        judgment_dict['Hyperlink to The National Archives'] = uk_link(soup.find("frbruri")['value'])
        judgment_dict['Date'] = soup.find("frbrdate")['date']
        judgment_dict['Court'] = soup.find("uk:court").getText()
        judgment_dict['Header'] = soup.find('header').getText()
        
        if judgment_dict['Header'][0:1] == '\n':
            judgment_dict['Header'] = judgment_dict['Header'][1: ]
            
        judgment_dict['Case number'] = soup.find("docketnumber").getText()
    except:
        pass
    
    for person in soup.find_all("tlcperson"):
        if 'judge' in str(person):
            judgment_dict['Judge(s) (non-exhaustive)'].append(person["showas"])
        else:
            judgment_dict['Parties'].append(person["showas"])

    #Get judgment

    pause.seconds(np.random.randint(5, 10))

    try:
        html_link = judgment_url_xml.replace('/data.xml', '')
        page_html = requests.get(html_link)
        soup_html = BeautifulSoup(page_html.content, "lxml")
        
        judgment_text = soup_html.get_text(separator="\n", strip=True)
    
        try:
            before_end_of_doc = judgment_text.split('End of document')[0]
            after_skip_to_end = before_end_of_doc.split('Skip to end')[1]
            judgment_text = after_skip_to_end
            
        except:
            pass
    
        judgment_dict['judgment'] = judgment_text

    except Exception as e:
        print(f"judgment_dict['Case name']: can't scrape judgment")
        
    return judgment_dict


# %%
#NOT IN USE

def uk_search_url(df_master):

    df_master = df_master.fillna('')

    #df_master['Courts'] = df_master['Courts'].apply(uk_court_choice)
    
    #Combining catchwords into new column
    
    #Conduct search
    
    results_url_count = uk_search(query= df_master.loc[0, 'Free text'], 
                                   from_day= df_master.loc[0, 'From day'],
                                   from_month=df_master.loc[0, 'From month'], 
                                   from_year=df_master.loc[0, 'From year'], 
                                   to_day=df_master.loc[0, 'To day'], 
                                   to_month=df_master.loc[0, 'To month'], 
                                   to_year=df_master.loc[0, 'To year'], 
                                   court= df_master.loc[0, 'Courts'], 
                                   party = df_master.loc[0, 'Party'], 
                                   judge = df_master.loc[0, 'Judge']
                                  )

    results_url = results_url_count['results_url']

    results_count = results_url_count['results_count']

    search_results_soup = results_url_count['soup']
    
    return {'results_url': results_url, 'results_count': results_count, 'soup': search_results_soup}



# %%
#Obtain parameters
#NOT IN USE

@st.cache_data(show_spinner = False, ttl=600)
def uk_run_old(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)

    #st.write(f"Before apply, df_master['Courts'] == {df_master['Courts']}")
    
    #df_master['Courts'] = df_master['Courts'].apply(uk_court_choice)

    #st.write(f"After apply, df_master['Courts'] == {df_master['Courts']}")
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search
    
    search_results_url_soup = uk_search(query= df_master.loc[0, 'Free text'], 
                                   from_day= df_master.loc[0, 'From day'],
                                   from_month=df_master.loc[0, 'From month'], 
                                   from_year=df_master.loc[0, 'From year'], 
                                   to_day=df_master.loc[0, 'To day'], 
                                   to_month=df_master.loc[0, 'To month'], 
                                   to_year=df_master.loc[0, 'To year'], 
                                   court= df_master.loc[0, 'Courts'], 
                                   party = df_master.loc[0, 'Party'], 
                                   judge = df_master.loc[0, 'Judge']
                                  )
    
    search_results_soup = search_results_url_soup['soup']

    results_url = search_results_url_soup['results_url']

    results_count = search_results_url_soup['results_count']
    
    judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments'])

    case_infos = uk_search_results_to_judgment_links(search_results_soup, results_url, results_count, judgment_counter_bound)

    for case_info in case_infos:

        judgment_dict = uk_meta_judgment_dict(case_info['Hyperlink to The National Archives'])
        judgments_file.append(judgment_dict)        
        pause.seconds(np.random.randint(10, 20))

        print(f"Scrapped {len(judgments_file)}/{max(judgment_counter_bound, results_count)} judgments.")
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual, convert_dates = False)

    #For UK, convert date to string so as to avoid Excel producing random numbers for dates
    if 'Date' in df_individual.columns:
        df_individual['Date'] = df_individual['Date'].astype(str)
    
    #GPT model

    #if df_master.loc[0, 'Use flagship version of GPT'] == True:
        #gpt_model = flagship_model
    #else:        
        #gpt_model = basic_model

    gpt_model = df_master.loc[0, 'gpt_model']

    temperature = df_master.loc[0, 'temperature']

    reasoning_effort = df_master.loc[0, 'reasoning_effort']
    
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)

    if (pop_judgment() > 0) and ('judgment' in df_updated.columns):
        df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in uk_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated


# %% [markdown]
# # GPT functions and parameters

# %%
#Import functions
from functions.gpt_functions import GPT_label_dict, is_api_key_valid, gpt_input_cost, gpt_output_cost, tokens_cap, max_output, num_tokens_from_string, judgment_prompt_json, GPT_json, engage_GPT_json  
#Import variables
from functions.gpt_functions import basic_model#, flagship_model#, role_content


# %%
#Jurisdiction specific instruction
#system_instruction = role_content

#intro_for_GPT = [{"role": "system", "content": system_instruction}]

# %%
#Obtain parameters

@st.cache_data(show_spinner = False, ttl=600)
def uk_run(df_master):
    df_master = df_master.fillna('')

    #Apply split and format functions for headnotes choice, court choice and GPT questions
     
    df_master['questions_json'] = df_master['Enter your questions for GPT'].apply(GPT_label_dict)

    #st.write(f"Before apply, df_master['Courts'] == {df_master['Courts']}")
    
    #df_master['Courts'] = df_master['Courts'].apply(uk_court_choice)

    #st.write(f"After apply, df_master['Courts'] == {df_master['Courts']}")
    
    #Create judgments file
    judgments_file = []
    
    #Conduct search

    uk_search = uk_search_function(query= df_master.loc[0, 'Free text'], 
                               from_day= df_master.loc[0, 'From day'],
                               from_month=df_master.loc[0, 'From month'], 
                               from_year=df_master.loc[0, 'From year'], 
                               to_day=df_master.loc[0, 'To day'], 
                               to_month=df_master.loc[0, 'To month'], 
                               to_year=df_master.loc[0, 'To year'], 
                               court= df_master.loc[0, 'Courts'], 
                               party = df_master.loc[0, 'Party'], 
                               judge = df_master.loc[0, 'Judge'],
                               order = df_master.loc[0, 'Order results by'],
                               judgment_counter_bound = int(df_master.loc[0, 'Maximum number of judgments']),                               
                              )

    uk_search.get_judgments()

    for judgment_json in uk_search.case_infos_w_judgments:

        judgments_file.append(judgment_json)
    
    #Create and export json file with search results
    json_individual = json.dumps(judgments_file, indent=2)
    
    df_individual = pd.read_json(json_individual, convert_dates = False)

    #For UK, convert date to string so as to avoid Excel producing random numbers for dates
    if 'Date' in df_individual.columns:
        df_individual['Date'] = df_individual['Date'].astype(str)
    
    #GPT model

    #if df_master.loc[0, 'Use flagship version of GPT'] == True:
        #gpt_model = flagship_model
    #else:        
        #gpt_model = basic_model

    gpt_model = df_master.loc[0, 'gpt_model']

    temperature = df_master.loc[0, 'temperature']

    reasoning_effort = df_master.loc[0, 'reasoning_effort']
    
    #apply GPT_individual to each respondent's judgment spreadsheet
    
    GPT_activation = int(df_master.loc[0, 'Use GPT'])

    questions_json = df_master.loc[0, 'questions_json']

    system_instruction = df_master.loc[0, 'System instruction']
    
    #Engage GPT
    df_updated = engage_GPT_json(questions_json = questions_json, df_example = df_master.loc[0, 'Example'], df_individual = df_individual, GPT_activation = GPT_activation, gpt_model = gpt_model, temperature = temperature, reasoning_effort = reasoning_effort, system_instruction = system_instruction)

    if (pop_judgment() > 0) and ('judgment' in df_updated.columns):
        df_updated.pop('judgment')

    #Drop metadata if not wanted

    if int(df_master.loc[0, 'Metadata inclusion']) == 0:
        for meta_label in uk_meta_labels_droppable:
            try:
                df_updated.pop(meta_label)
            except:
                pass
    
    return df_updated

