# -*- coding: utf-8 -*-
"""
Created Apr 2020

Requirements:
    chromedriver (https://chromedriver.chromium.org/downloads)

@author: Benjamin R. Kanter
"""

from bokeh.io import output_file
import numpy as np
import pandas as pd
import csv
import requests

scrapeCoords = False # True to scrape GoogleMap coordinates, False to read them from csv file

def scrapeGmapCoords(df):
    """Use Chrome to search Google Maps"""
    
    from selenium import webdriver
    
    Url_With_Coordinates = []
    
    option = webdriver.ChromeOptions()
    prefs = {'profile.default_content_setting_values': {'images':2, 'javascript':2}}
    option.add_experimental_option('prefs', prefs)
    
    driver = webdriver.Chrome("chromedriver.exe", options=option)
    
    for url in df.Url:
        driver.get(url)
        Url_With_Coordinates.append(driver.find_element_by_css_selector('meta[itemprop=image]').get_attribute('content'))
        
    driver.close()
    
    df['Url_With_Coordinates'] = Url_With_Coordinates
    
    return df, Url_With_Coordinates

def getWebsites(url):
    """Find institution website from Wikipedia page"""
    
    try:
        r = requests.get(url, auth=('user', 'pass'))
        website = r.text
        db = pd.read_html(website,match='Website',encoding="UTF-8")
        db = pd.DataFrame(db[0])
        db.columns = ['Label','Data']
        # print('success: ' + url)
        return 'https://' + db.loc[(db.loc[:,'Label'] == 'Website'),'Data'].iloc[0]
        
    except:
        print('FAIL: ' + url)

#%% get list of R1 schools from Wiki and find them on GoogleMaps
url = 'https://en.wikipedia.org/wiki/Research_I_university'
df = pd.read_html(url)[0]
result = df.copy()

# create URLs
result['Institution+'] = result['Institution']
result['Institution+'] = [ i.replace(" ", "+") for i in result['Institution']]
result['Institution_'] = result['Institution']
result['Institution_'] = [ i.replace(" ", "_") for i in result['Institution']]
result['Url'] = ['https://www.google.com/maps/search/' + i for i in result['Institution+'] ]
result['Wiki'] = ['https://en.wikipedia.org/wiki/' + i for i in result['Institution_'] ]

# get GoogleMap coords
if scrapeCoords:
    
    result, Url_With_Coordinates = scrapeGmapCoords(result)
    
    with open('Url_With_Coordinates.csv','w') as file:
        wr = csv.writer(file)
        wr.writerow(Url_With_Coordinates)
    
else:
    with open('Url_With_Coordinates.csv', 'r') as f:
        reader = csv.reader(f, delimiter=',')
        for i in reader:
            Url_With_Coordinates = i
            break
        result['Url_With_Coordinates'] = Url_With_Coordinates

result['lat'] = [ url.split('?center=')[1].split('&zoom=')[0].split('%2C')[0] for url in result['Url_With_Coordinates'] ]
result['long'] = [url.split('?center=')[1].split('&zoom=')[0].split('%2C')[1] for url in result['Url_With_Coordinates'] ]

# fix Reno coords that were retrieved incorrectly
result.loc[(result.loc[:,'City'] == 'Reno'),'lat'] = 39.533
result.loc[(result.loc[:,'City'] == 'Reno'),'long'] = -119.813

# get school websites      
result['Website'] = [ getWebsites(url) for url in result['Wiki'] ]

# drop unneeded columns
result = result.drop(columns=['Institution+','Institution_','Url','Wiki'])

#%% make the map
import folium
import webbrowser
import re
import branca

m = folium.Map(location=[38, -97], zoom_start=5)

# popup school website links 
for lat, long, name, site in zip(result.lat, result.long, result.Institution, result.Website):
    
    html = '<a style="font-size:110%;font-name:Arial;text-align:center;"href="' + site + '" target="_blank">' + name + '</a>'
    el = branca.element.IFrame(html=html, width=250, height=60)
    popup = folium.Popup(el)
    folium.Marker([lat, long], popup=popup, size=3, icon=folium.Icon(color='darkblue',icon='circle')).add_to(m) 

# write and open
output_file = "USA_R1_map.html"
m.save(output_file)
webbrowser.open(output_file, new=2)