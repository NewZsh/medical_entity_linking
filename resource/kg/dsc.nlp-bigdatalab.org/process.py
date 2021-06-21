
#!/usr/bin/python
# -*- coding: utf-8 -*-

import codecs
import numpy as np

def main():
    triples = []
    entities = {}
    relations = {}
    with codecs.open('dsc.nlp-bigdatalab.org.ttl', encoding='utf-8') as f:
        for line in f:
            line = line.strip().split('\t')
            if len(line) == 3:
                if 'ontology' in line[0]:
                    continue
                elif 'rdf-schema#label' in line[1]:
                    continue
                elif 'rdf-syntax-ns#type' in line[1]:
                    continue
                elif line[1] == 'rdfs:label':
                    continue
                elif line[1] == 'owl:sameAs':
                    continue

                line[2] = line[2].rsplit(' .', 1)[0]

                # line[0] = line[0].rsplit('>', 1)[0].rsplit('/', 1)[1]
                # line[1] = line[1].rsplit('>', 1)[0].rsplit('/', 1)[1]
                # line[2] = line[2].rsplit('>', 1)[0].rsplit('/', 1)[1]

                triples.append(line)
                if line[0] not in entities:
                    entities[line[0]] = len(entities)
                if line[2] not in entities:
                    entities[line[2]] = len(entities)
                if line[1] not in relations:
                    relations[line[1]] = len(relations)
    
    triples = np.array(triples)
    index = np.random.permutation(len(triples))
    split_index = [int(0.8 * len(index)), int(0.85 * len(index))]
    train_index = index[:split_index[0]]
    valid_index = index[split_index[0]:split_index[1]]
    test_index = index[split_index[1]:]
    
    with codecs.open('train.txt', mode='w', encoding='utf-8') as f:
        for triple in triples[train_index]:
            f.writelines('%s\t%s\t%s\n' % (triple[0], triple[1], triple[2]))
    with codecs.open('valid.txt', mode='w', encoding='utf-8') as f:
        for triple in triples[valid_index]:
            f.writelines('%s\t%s\t%s\n' % (triple[0], triple[1], triple[2]))
    with codecs.open('test.txt', mode='w', encoding='utf-8') as f:
        for triple in triples[test_index]:
            f.writelines('%s\t%s\t%s\n' % (triple[0], triple[1], triple[2]))
    
    with codecs.open('entities.dict', mode='w', encoding='utf-8') as f:
        for i, entity in enumerate(entities.keys()):
            f.writelines('%d\t%s\n' % (i, entity))
    with codecs.open('relations.dict', mode='w', encoding='utf-8') as f:
        for i, relation in enumerate(relations.keys()):
            f.writelines('%d\t%s\n' % (i, relation))

if __name__ == '__main__':
    main()