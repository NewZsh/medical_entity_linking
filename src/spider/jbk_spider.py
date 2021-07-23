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
from graph_db import graphDB_interface
from graph_db import fuzzyMatchStr

HEADERS = {'User-Agent': 'User-Agent:Mozilla/5.0'}
SCHEMA_FILE = '../../resource/kg/schema.txt'
TRIPLETS_FILE = '../../resource/kg/triplets.txt'
CONCEPTS_FILE = '../../resource/kg/concepts.txt'

class kg_constructor():
    def __init__(self):
        super().__init__()
        self.new_concepts = []
        self.new_triplets = []
        self.graphDB = graphDB_interface()

    def accept_new_concept(self, concept, fuzzymatcher=None):
        name = concept[0]
        label = concept[2]
        node = self.graphDB.searchNode(label, {'name': name})
        if node is None:
            candidates = self.graphDB.fuzzySearchNode(label, {'name': name}, fuzzymatcher=fuzzymatcher)
            if len(candidates) == 0:
                return True
            else:
                # to do
                # throw to human annotator to check
                return False
        else:
            return False


    def accept_new_triplet(self, triplet):
        return True

    def filter_intodb(self):
        for concept in self.new_concepts:
            if self.accept_new_concept(concept):
                name = concept[0]
                label = concept[2]
                self.graphDB.createNode(label, {'name': name})

        for triplet in self.new_triplets:
            if self.accept_new_triplet(triplet):
                self.graphDB.createRel('entity:部位', {'name': triplet[0]}, 'entity:部位', {'name': triplet[2]}, triplet[1])


class kgOrgan_constructor(kg_constructor):
    def __init__(self):
        super().__init__()

    def parse(self):
        url = 'https://jbk.39.net/'
        req = request.Request(url, headers=HEADERS)
        response = request.urlopen(req)
        html = response.read()
        xml = etree.HTML(html)

        organ_level1 = xml.xpath('//*[@class="menu_ul_bw"]')[0].xpath('.//a/text()')
        organ_level2 = xml.xpath('//*[@class="menu_item_all"]')[1].xpath('./*')
        for i, items in enumerate(organ_level2):
            organ = organ_level1[i]
            self.new_concepts.append([organ, 'rdfs:subClassOf', 'entity:部位'])
            for sub_organ in items.xpath('.//*[@class="menu_item_box_tit"]//a/text()')[:-2]:
                self.new_concepts.append([sub_organ, 'rdfs:subClassOf', 'entity:部位'])
                self.new_triplets.append([sub_organ, 'relation:PartOf', organ])


def parse_single_disease(href):
    req = request.Request(href, headers=HEADERS)
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
            
            req = request.Request(page, headers=HEADERS)
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
    req = request.Request(href, headers=HEADERS)
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
            
            req = request.Request(page, headers=HEADERS)
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
    constructor = kgOrgan_constructor()
    constructor.graphDB.empty()

    constructor.parse()
    constructor.filter_intodb()

    print(constructor.graphDB.searchNode('entity:部位', {'name': "肠"}))
    print(constructor.graphDB.fuzzySearchNode('entity:部位', {'name': "肠"}))
    print(constructor.graphDB.fuzzySearchNode('entity:部位', {'name': "肠道"}))

    # parse_all_disease()
    # parse_all_examination()