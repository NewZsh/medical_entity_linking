#!/bin/env python
# -*- coding: utf-8 -*-

from py2neo import Graph, Relationship, Node, NodeMatcher, RelationshipMatcher
import pandas as pd
import json

CFG_FILE = '../../resource/kg/kg.json'

def fuzzyMatchStr(str1, str2):
    if str1.startswith(str2):
        return True
    if str2.startswith(str1):
        return True
    if str1.endswith(str2):
        return True
    if str2.endswith(str1):
        return True
    if len(set(str1).intersection(set(str2))) / min(len(str1), len(str2)) >= 0.6:
        return True
    
    return False

class graphDB_interface:
    def __init__(self):
        config_str = ''.join(open(CFG_FILE).readlines()).replace('\n', ' ')
        config = json.loads(config_str)
        self.graph = Graph(config['url'], name=config['name'], password=config['password'])
        self.nodematcher = NodeMatcher(self.graph)
        self.relmatcher = RelationshipMatcher(self.graph)

    def fuzzySearchNode(self, labels, attrs, fuzzymatcher=fuzzyMatchStr, mode=0):
        '''
        mode = 0, confident on labels (though maybe partial), allow fuzzy matching for attrs
        '''
        if isinstance(labels, str):
            labels = [labels]

        candidates = []
        for node in self.nodematcher.match(*labels):
            for key, value in attrs.items():
                v = node[key]

                if fuzzymatcher(v, value):
                    candidates.append(node)
        
        return candidates

    def fuzzySearchRels(self, label1, attrs1, label2, attrs2, rtype):
        pass

    def searchNode(self, labels, attrs):
        if isinstance(labels, str):
            labels = [labels]

        name = '_.name=' + '\'' + attrs['name'] + '\''
        node = self.nodematcher.match(*labels).where(name).first()
        # for index in graphDB.graph.nodes:
        #     node = graphDB.graph.nodes[index]
        #     print(node.labels, node.keys())
        return node

    def createNode(self, labels, attrs):
        if isinstance(labels, str):
            labels = [labels]

        node = self.searchNode(labels, attrs)
        if node is None:
            node = Node(*labels, **attrs)
            self.graph.create(node)
            return True

        print('node {} is already exists.'.format(attrs))
        return False

    def searchRel_onhead(self, label, attrs, rtype):
        node = self.searchNode(label, attrs)
        if node is None:
            print('node {} does not exists. Search relation from it returns nothing.'.format(attrs))
            return None

        rel = self.relmatcher.match((node, None), rtype).first()
        return rel
    
    def searchRel_ontail(self, label, attrs, rtype):
        node = self.searchNode(label, attrs)
        if node is None:
            print('node {} does not exists. Search relation to it returns nothing.'.format(attrs))
            return None

        rel = self.relmatcher.match((None, node), rtype).first()
        return rel
    
    def searchRel(self, label1, attrs1, label2, attrs2, rtype):
        node1 = self.searchNode(label1, attrs1)
        node2 = self.searchNode(label1, attrs1)
        if node1 is None or node2 is None:
            print('node {} or {} does not exists. Search relation between them returns nothing'.format(attrs1, attrs2))
            return None

        rel = self.relmatcher.match((node1, node2), rtype).first()
        return rel

    def createRel(self, label1, attrs1, label2, attrs2, rtype):
        node1 = self.searchNode(label1, attrs1)
        node2 = self.searchNode(label2, attrs2)
        if node1 is None or node2 is None:
            print('node {} or {} does not exists. Please create them first.'.format(attrs1, attrs2))
            return False
        
        rel = self.searchRel(label1, attrs1, label2, attrs2, rtype)
        if rel is not None:
            print('relation {} is already exists.'.format(rel))
            return False

        rel = Relationship(node1, rtype, node2)
        self.graph.create(rel)
        return True

    def empty(self):
        self.graph.delete_all()

if __name__ == '__main__':
    graphDB = graphDB_interface()

    Names = ["老师", "销售", "程序员"]
    action = ["传授", "卖", "敲"]
    action2 = ["吃", "丢", "删"]
    things = ["知识", "产品", "代码"]
    data = pd.DataFrame({'Names': Names, 'action': action, 'things': things})

    graphDB.empty()
    # exit()
    print('test search on an empty graph ...')
    print(graphDB.searchNode('Name', {'name': "老师"}))
    print(graphDB.searchNode('things', {'name': "学生"}))
    print(graphDB.searchRel_onhead('Name', {'name': "学生"}, action[0]))
    print(graphDB.searchRel_onhead('Name', {'name': "销售"}, action[1]))
    print(graphDB.searchRel_onhead('Name', {'name': "老师"}, action[0]))
    print(graphDB.searchRel_ontail('things', {'name': "知识"}, action[0]))
    
    print()
    print('test search on a built graph ...')
    
    label1 = ['a', 'Name']
    label2 = 'things'
    for i, j in data.iterrows():
        attr1 = {'name': j.Names}
        graphDB.createNode(label1, attr1)
        attr2 = {'name': j.things}
        graphDB.createNode(label2, attr2)
        rtype = j.action
        re_value = graphDB.createRel(label1, attr1, label2, attr2, rtype)
        re_value = graphDB.createRel(label1, attr1, label2, attr2, action2[i])

    print(graphDB.searchNode(['Name'], {'name': "老师"}))
    print(graphDB.searchNode('things', {'name': "学生"}))
    print(graphDB.searchRel_onhead(['Name'], {'name': "学生"}, action[0]))
    print(graphDB.searchRel_onhead(['Name'], {'name': "销售"}, action[1]))
    print(graphDB.searchRel_onhead(['Name'], {'name': "老师"}, action[0]))
    print(graphDB.searchRel_ontail('things', {'name': "知识"}, action[0]))

    rel = graphDB.searchRel_ontail('things', {'name': "知识"}, action[0])
    
    print(rel.nodes)
    print(rel.start_node)
    print(rel.end_node)

    print()
    print('test fuzzy search on a built graph ...')
    print(graphDB.fuzzySearchNode('Name', {'name': "师"}))