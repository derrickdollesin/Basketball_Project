import os
import re
import time
import requests 
import numpy as np
import pandas as pd
import urllib.request
from bs4 import BeautifulSoup




def get_soup(url):
    '''
    Create a soup object of a web url

    Args: 
        url - String (ex. https://basketball-reference.com/)

    Returns:
        soup - BeautifulSoup object
    '''
    try:
        with urllib.request.urlopen(url) as response:
            html = response.read()
    except urllib.error.URLError as e:
        print(f"Error fetching URL: {e.reason}")

    ### create the soup object
    soup = BeautifulSoup(html, 'html.parser')

    return soup



def get_player_ids(team, year):
    url = f'https://www.basketball-reference.com/teams/{team}/{year}.html'

    soup = get_soup(url)

    ids = []
    players = {}

    rows = soup.find("tbody").find_all("tr")

    for row in rows:
        player_cell = row.find("td", {"data-stat": "player"})
        
        if player_cell:
            link = player_cell.find("a")
            
            if link:
                name = link.text
                href = link.get("href")
                split = href.split('/')[-1]
                if '.html' in split:
                    split = split[0:split.find('.')]
                    players[name] = split
                else:
                    players[name] = href
                    print('Check Player List')

    if not players:
        print('No Team Found')
    else:
        # print(ids)
        return players
    


def get_player_data(username):
    url = f"https://www.basketball-reference.com/players/{username[0]}/{username}.html"
    soup = get_soup(url)
    tbodies = soup.find_all("tbody")

    tables = {} 

    for i, tbody in enumerate(tbodies):
        
        rows_data = []
        table_name = None
        
        for row in tbody.find_all("tr"):
            row_id = row.get("id")
            
            if row_id and table_name is None:
                table_name = row_id.split(".")[0]
            
            cells = row.find_all(["th", "td"])
            
            row_dict = {}
            for j, cell in enumerate(cells):
                col_name = cell.get("data-stat")
                text = cell.get_text(strip=True)
                
                if col_name is None:
                    col_name = f"col_{j}"
                
                row_dict[col_name] = text
            
            if row_dict:
                rows_data.append(row_dict)

        df = pd.DataFrame(rows_data)
        
        if table_name is None:
            table_name = f"table_{i}"

            if table_name == 'table_0' and df.shape[0] == 5:
                table_name = 'past_5_games'
            elif table_name == 'table_3' and df.shape[0] == 7:
                table_name = 'stathead_insight'
        
        tables[table_name] = df

    for name, df in tables.items():
        print(f"{name}: {df.shape}")
    
    return tables

