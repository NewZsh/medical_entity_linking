from py2neo import Graph, Relationship, Node, NodeMatcher, RelationshipMatcher
import pandas as pd
import json

CFG_FILE = '../../resource/kg/kg.json'
SCHEMA_FILE = '../../resource/kg/schema.xml'

class graphDB_interface:
    def __init__(self):
        config_str = ''.join(open(CFG_FILE).readlines()).replace('\n', ' ')
        config = json.loads(config_str)
        self.graph = Graph(config['url'], name=config['name'], password=config['password'])
        self.nodematcher = NodeMatcher(self.graph)
        self.relmatcher = RelationshipMatcher(self.graph)

    def parse_schema(self):
        pass

    def searchNode(self, label, attrs):
        name = '_.name=' + '\'' + attrs['name'] + '\''
        node = self.nodematcher.match(label).where(name).first()
        return node

    def createNode(self, label, attrs):
        node = self.searchNode(label, attrs)
        if node is None:
            node = Node(label, **attrs)
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
    
    def searchRel_ontail(self, label, attrs, type):
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
        pass

if __name__ == '__main__':
    graphDB = graphDB_interface()

    Names = ["老师", "销售", "程序员"]
    action = ["传授", "卖", "敲"]
    things = ["知识", "产品", "代码"]
    data = pd.DataFrame({'Names': Names, 'action': action, 'things': things})


    # rel.nodes
    # Out[45]: (Node('1', 'Name', name='老师'), Node('things', name='知识'))

    # In [46]: rel.start_node
    # Out[46]: Node('1', 'Name', name='老师')

    # In [47]: rel.end_node

    print(graphDB.searchNode('Name', {'name': "学生"}))
    print(graphDB.searchNode('things', {'name': "学生"}))
    print(graphDB.searchRel('Name', {'name': "学生"}, action[0]))
    print(graphDB.searchRel('Name', {'name': "销售"}, action[0]))
    print(graphDB.searchRel('Name', {'name': "老师"}, action[0]))
    print(graphDB.searchRel('things', {'name': "知识"}, action[0]))
    exit()
    
    label1 = 'Name'
    label2 = 'things'
    for i, j in data.iterrows():
        attr1 = {'name': j.Names}
        graphDB.createNode(label1, attr1)
        attr2 = {'name': j.things}
        graphDB.createNode(label2, attr2)
        rtype = j.action
        re_value = graphDB.createRel(label1, attr1, label2, attr2, rtype)

    exit()
    for i, j in data.iterrows():
        attr1 = {'name': j.Names}
        node = graphDB.searchNode(label1, attr1)
        if node is not None:
            graphDB.graph.delete(node)
        attr2 = {'name': j.things}
        node = graphDB.searchNode(label2, attr2)
        if node is not None:
            graphDB.graph.delete(node)
