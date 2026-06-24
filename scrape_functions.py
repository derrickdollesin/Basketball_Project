import os
import re
import time
import requests 
import sqlite3
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

        df = df.replace("", pd.NA)
        df = df.dropna(thresh=df.shape[1] / 2)

        df["player"] = username

        if table_name is None:
            table_name = f"table_{i}"

            if table_name == "table_0" and df.shape[0] == 5:
                table_name = "past_5_games"
            elif table_name == "table_3" and df.shape[0] == 7:
                table_name = "stathead_insight"

        tables[table_name] = df

    ## For Testing May Remove
    for name, df in tables.items():
        print(f"{name}: {df.shape}")

    ### Insert to Database+

    with sqlite3.connect("nba.db", timeout=60) as conn:

        for key, df in tables.items():

            sql_table_name = f"{key}"

            # append if table exists, create if not
            df.to_sql(
                sql_table_name,
                conn,
                if_exists="append",
                index=False
            )

            # remove duplicate rows
            deduped_df = pd.read_sql_query(
                f'SELECT DISTINCT * FROM "{sql_table_name}"',
                conn
            )

            deduped_df.to_sql(
                sql_table_name,
                conn,
                if_exists="replace",
                index=False
            )

    return tables

def get_seasonal_stats(player_id):
    table_name = f"per_game_stats"

    with sqlite3.connect("nba.db") as conn:
        season_df = pd.read_sql_query(
            f"""
            SELECT * 
            FROM {table_name}
            WHERE player = '{player_id}'""",
            conn
        )

    player_years = (
        season_df["year_id"]
        .dropna()
        .astype(str)
        .str.split("-")
        .str[0]
        .astype(int)
        .add(1)
        .astype(str)
        .unique()
    )

    tables = {}

    for year in player_years:
        link = f"https://www.basketball-reference.com/players/{player_id[0]}/{player_id}/gamelog/{year}/"

        soup = get_soup(link)
        tbodies = soup.find_all("tbody")

        for i, tbody in enumerate(tbodies):
            rows_data = []
            table_name = None

            for row in tbody.find_all("tr"):
                # skip repeated header rows
                if "thead" in row.get("class", []):
                    continue

                row_id = row.get("id")

                if row_id and table_name is None:
                    table_name = row_id.split(".")[0]

                cells = row.find_all(["th", "td"])

                row_dict = {}
                for j, cell in enumerate(cells):
                    col_name = cell.get("data-stat")

                    if col_name is None:
                        col_name = f"col_{j}"

                    row_dict[col_name] = cell.get_text(strip=True)

                if row_dict:
                    rows_data.append(row_dict)

            df = pd.DataFrame(rows_data)

            if df.empty:
                continue

            df = df.replace("", pd.NA)

            # Keep rows where at least half the columns are filled
            min_non_empty = int(df.shape[1] / 2)
            df = df.dropna(thresh=min_non_empty)

            df["player"] = player_id
            df["year"] = year

            if table_name is None:
                table_name = f"table_{i}"

            # prevents overwriting seasons
            key = f"{year}_{table_name}"
            tables[key] = df

    for name, df in tables.items():
        print(f"{name}: {df.shape}")


    with sqlite3.connect("nba.db", timeout=60) as conn:
        for key, df in tables.items():
            sql_table_name = key

            # append if table exists, create if not
            df.to_sql(
                sql_table_name,
                conn,
                if_exists="append",
                index=False
            )

            # remove duplicate rows from the table
            deduped_df = pd.read_sql_query(
                f'SELECT DISTINCT * FROM "{sql_table_name}"',
                conn
            )

            deduped_df.to_sql(
                sql_table_name,
                conn,
                if_exists="replace",
                index=False
            )

            print(f"{sql_table_name}: {deduped_df.shape}")
            
    return tables