#!/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import os
import logging
import time
import json
from urllib import request
import datetime
from lxml import etree
import codecs
import http

headers = {'User-Agent': 'User-Agent:Mozilla/5.0'}

def parse_single_disease(href):
    req = request.Request(href, headers=headers)
    response = request.urlopen(req)
    html = response.read()
    xml = etree.HTML(html)

    disease_infobox = {}
    for prop, obj in zip(xml.xpath('//ul[@class="information_ul"]/li/i'), \
                        xml.xpath('//ul[@class="information_ul"]/li/span')):
        obj_value = obj.xpath('./a')
        if len(obj_value) == 0:
            obj_value = obj.text
        else:
            value = []
            for item in obj_value:
                v = item.text
                item = item.attrib
                vlink = item['href']
                value.append([v, vlink])
            obj_value = value

        disease_infobox[prop.text] = obj_value

    return disease_infobox

def parse_all_disease():
    page_prefix = 'http://jbk.39.net/bw/t1'
    
    with codecs.open('medical.kg', encoding='utf-8', mode='a') as f:
        for i in range(1, 101):
            if i > 1:
                page = page_prefix + '_p%d/' % i
            else:
                page = page_prefix + '/'
            
            req = request.Request(page, headers=headers)
            response = request.urlopen(req)
            html = response.read()
            xml = etree.HTML(html)
            for element in xml.xpath('//div[@class="result_item_top"]/p[1]/a'):
                element = element.attrib
                disease = element['title']
                href = element['href']

                disease_infobox = parse_single_disease(href)
                # 暂时使用href作为实体的ID
                f.writelines('\t'.join([href, '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>', 'disease']) + '\n')
                f.writelines('\t'.join([href, '<http://www.w3.org/2000/01/rdf-schema#label>', disease]) + '\n')
                for key, value in disease_infobox.items():
                    if isinstance(value, list):
                        for v in value:
                            f.writelines('\t'.join([href, key, json.dumps({'href': v[1], 'name': v[0]})]) + '\n')
                    else:
                        f.writelines('\t'.join([href, key, value]) + '\n')
            
            print('finished spying page %d' % i)

def parse_single_examination(href):
    req = request.Request(href, headers=headers)
    response = request.urlopen(req)
    html = response.read()
    xml = etree.HTML(html)

    examination_infobox = {}
    for item in xml.xpath('//ul[@class="infolist"]/li'):
        prop_text = item.xpath('./span//b//text()')
        if len(prop_text) == 0:
            continue
        prop_text = prop_text[0]
        obj_value = item.xpath('./span//a')
        if len(obj_value) == 0:
            obj_value = item.xpath('./span/text()')
            obj_value = ''.join(obj_value).strip()
            if len(obj_value) > 0:
                obj_value = obj_value.split('\xa0\r\n')				
                examination_infobox[prop_text] = obj_value
        else:
            value = []
            for obj in obj_value:
                v = obj.text
                obj = obj.attrib
                vlink = obj['href']
                if '#ref' in vlink:
                    continue
                value.append([v, vlink])
            obj_value = value

            examination_infobox[prop_text] = obj_value

    return examination_infobox

def parse_all_examination():
    page_prefix = 'http://jbk.39.net/bw/t3'
    
    with codecs.open('medical.kg', encoding='utf-8', mode='a') as f:
        for i in range(1, 101):
            if i > 1:
                page = page_prefix + '_p%d/' % i
            else:
                page = page_prefix + '/'
            
            req = request.Request(page, headers=headers)
            response = request.urlopen(req)
            html = response.read()
            xml = etree.HTML(html)
            for element in xml.xpath('//div[@class="result_item_top"]/p[1]/a'):
                element = element.attrib
                examination = element['title']
                href = element['href']

                try:
                    examination_infobox = parse_single_examination(href)
                except http.client.HTTPException as e:
                    continue

                # 暂时使用href作为实体的ID
                f.writelines('\t'.join([href, '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>', 'examination']) + '\n')
                f.writelines('\t'.join([href, '<http://www.w3.org/2000/01/rdf-schema#label>', examination]) + '\n')
                for key, value in examination_infobox.items():
                    for v in value:
                        if isinstance(v, list):
                            f.writelines('\t'.join([href, key, json.dumps({'href': v[1], 'name': v[0]})]) + '\n')
                        else:
                            f.writelines('\t'.join([href, key, v]) + '\n')
            
            print('finished spying page %d' % i)

if __name__ == '__main__':
    parse_all_disease()
    parse_all_examination()