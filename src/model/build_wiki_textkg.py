#!/bin/env python
# -*- coding: utf-8 -*-
########################################################################
# 
# Copyright (c) 2019Sogou.com, Inc. All Rights Reserved
# 
########################################################################
 
"""
File Name: build_wiki_textkg.py
Author: Wang Shuai <wangshuai93@sogou-inc.com>
Create Time: 2019/12/27 17:46:14
Brief:      
"""

import codecs
import json
import sys
import requests
from urllib.request import Request, urlopen
from lxml import etree

# note that a freebase-mid may correspond to multiple wiki-id
entities_fb2wiki = {}
fb_entities = {}
with open('entities.dict') as f:
    for line in f:
        line = line.strip().split('\t')
        fb_entities[line[1]] = int(line[0])

with open('fb2w.nt') as f:
    for line in f:
        line = line.strip().split('\t')
        if len(line) != 3:
            continue
        fb_entity = line[0].rsplit('/', 1)[1].rsplit('>', 1)[0]
        fb_entity = '/' + '/'.join(fb_entity.split('.'))
        
        if fb_entity not in fb_entities:
            continue
        wiki_entity = line[2].rsplit('/', 1)[1].rsplit('>', 1)[0]

        if fb_entity in entities_fb2wiki:
            entities_fb2wiki[fb_entity].append(wiki_entity)
        else:
            entities_fb2wiki[fb_entity] = [wiki_entity]

def get_wikipedia_url_from_wikidata_id(wikidata_id, lang='en', debug=False):
    url = (
        'https://www.wikidata.org/w/api.php'
        '?action=wbgetentities'
        '&props=sitelinks/urls'
        f'&ids={wikidata_id}'
        '&format=json')
    json_response = requests.get(url).json()
    if debug: print(wikidata_id, url, json_response) 

    entities = json_response.get('entities')    
    if entities:
        entity = entities.get(wikidata_id)
        if entity:
            sitelinks = entity.get('sitelinks')
            if sitelinks:
                if lang:
                    # filter only the specified language
                    sitelink = sitelinks.get(f'{lang}wiki')
                    if sitelink:
                        wiki_url = sitelink.get('url')
                        if wiki_url:
                            return requests.utils.unquote(wiki_url)
                else:
                    # return all of the urls
                    wiki_urls = {}
                    for key, sitelink in sitelinks.items():
                        wiki_url = sitelink.get('url')
                        if wiki_url:
                            wiki_urls[key] = requests.utils.unquote(wiki_url)
                    return wiki_urls
    return None

def filter_text(text):
    import re
    text = re.sub('\xa0', '', text)
    text = re.sub('\xe1', '', text)
    text = re.sub('\[\d+\]', '', text)

    text = re.sub('\n', ' ', text)
    text = re.sub('\s+', ' ', text)

    return text

url2abstract = {}
for mid in entities_fb2wiki:
    for wiki_id in entities_fb2wiki[mid]:
        url = get_wikipedia_url_from_wikidata_id(wikidata_id=wiki_id)
        if url is None:
            continue

        req = Request(url)
        html = urlopen(req).read()
        xml = etree.HTML(html)
        
        segment = xml.xpath('//*[@id="toc"]')[0]
        segments = segment.xpath('./preceding::*')

        abstract = [segment.xpath('string()') for segment in segments 
                    if segment.tag == 'p' and len(segment.keys()) == 0]
        abstract = ''.join(abstract)
        abstract = filter_text(abstract).encode('utf-8')
        url2abstract[url] = abstract