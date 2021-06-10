#!/bin/env python
# -*- coding: utf-8 -*-
########################################################################
# 
# Copyright (c) 2019Sogou.com, Inc. All Rights Reserved
# 
########################################################################
 
"""
File Name: name2sogouId_mapper.py
Author: Wang Shuai <wangshuai93@sogou-inc.com>
Create Time: 2019/12/27 17:46:14
Brief:      
"""

import codecs
import json
import collections
import jieba
import numpy as np
import tensorflow as tf
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

def read_data():
    '''
    collect all text related to each entities
    
    returned
    descriptions: dictionary, entity_id -- text
    triples: list, each item is a triple [sid, relation, oid]
    all_entities: dictionary, entity_id -- index
    all_relations: dictionary, relation -- index
    '''
    stop_words = []
    with codecs.open('stop_words.txt', encoding='utf-8') as f:
        for line in f:
            stop_words.append(line.strip())
    stop_words = set(stop_words)
    # print 'finish reading %d stop words' % len(stop_words)

    learning_id = {}
    with codecs.open('disam.txt', encoding='utf-8') as f:
        for line in f:
            line = line.strip().split('\t', 1)[1]
            for _id in line.split('|'):
                learning_id[_id] = True

    descriptions = {}
    all_entities = {}
    num_entities = 0
    all_relations = {}
    num_relations = 0
    triples = []
    with codecs.open('kg_text.txt', encoding='utf-8') as f:
        for line in f:
            line = line.strip().split('\t')

            # related_id: sid_lemmaId, oid_lemmaId, [all_link_lemmaId]
            related_id = [line[0], line[4]] + [item[1] for item in json.loads(line[8])['link']]
            to_use = False
            for _id in related_id:
                if learning_id.get(_id, False):
                    to_use = True
                    break
            
            if not to_use:
                continue
            else:
                tmp_f = codecs.open('used.txt', encoding='utf-8', mode='a')
                tmp_f.writelines('\t'.join(line) + '\n')
                tmp_f.close()

            sid = line[0]
            sname = line[1]
            rel = line[3]
            oid = line[4]
            oname = line[5]

            for _id in related_id:
                if _id not in all_entities:
                    all_entities[_id] = num_entities
                    num_entities += 1

            if 'reverse-' not in rel:
                triples.append([sid, rel, oid])
                if rel not in all_relations:
                    all_relations[rel] = num_relations
                    num_relations += 1

            text = json.loads(line[7])['text']
            text = ''.join(text.split(' '))          
            raw_words = list(jieba.cut(text, cut_all=False))
            descriptions[sid] = raw_words

    return descriptions, triples, all_entities, all_relations

def build_dataset(descriptions, triples, all_entities, all_relations, vocabulary_size = 50000):
    all_words = []
    for words in descriptions.values():
        all_words.extend(words)

    count = [['UNK', -1]]
    count.extend(collections.Counter(all_words).most_common(vocabulary_size - 1))
    # print len(count)

    dictionary = dict()
    num_words = 0
    for word, _ in count:
        if word not in all_entities:
            dictionary[word] = num_words
            num_words += 1
    for entity in all_entities.keys():
        dictionary[entity] = num_words
        num_words += 1

    data = {}
    unk_count = 0 # 本行多余
    for _id, words in descriptions.items():
        tmp = []
        for word in words:
            if word in dictionary:
                index = dictionary[word]
            else:
                index = 0  
                count[0][1] += 1
            tmp.append(index)
        
        data[dictionary[_id]] = np.array(tmp)

    triples = np.array([[dictionary[triple[0]], all_relations[triple[1]], dictionary[triple[2]]]
                        for triple in triples], dtype=np.int32)
    reverse_dictionary = dict(zip(dictionary.values(), dictionary.keys()))
    return data, triples, count, dictionary, reverse_dictionary

def generate_kg_batch(triples, dictionary, all_entities, batch_ID_size, negative_ratio=32):
    all_entities = np.array(all_entities.keys())
    batch_labels = np.zeros(batch_ID_size*(1+negative_ratio))
    batch_labels[:batch_ID_size] = 1
    batch_labels[batch_ID_size:] = 0
    index = np.random.choice(len(triples), batch_ID_size, replace=False)
    batch_triples = np.zeros((batch_ID_size*(1+negative_ratio), 3), dtype=np.int32)
    batch_triples[:batch_ID_size,] = triples[index,]
    for i in range(batch_ID_size):
        corrupt_s = negative_ratio // 2
        corrupt_o = negative_ratio - corrupt_s
        neg_s = np.random.choice(len(all_entities), corrupt_s, replace=False)
        neg_s = [item for item in neg_s if item != batch_triples[i,0]]  # avoid false negative
        while len(neg_s) < corrupt_s:
            neg_s += neg_s[:corrupt_s - len(neg_s)]
        neg_s = [dictionary[entity] for entity in all_entities[np.array(neg_s)]]

        neg_o = np.random.choice(len(all_entities), corrupt_o, replace=False)
        neg_o = [item for item in neg_o if item != batch_triples[i,2]]  # avoid false negative
        while len(neg_o) < corrupt_o:
            neg_o += neg_o[:corrupt_s - len(neg_o)]
        neg_o = [dictionary[entity] for entity in all_entities[np.array(neg_o)]]

        pos = batch_ID_size + i * negative_ratio
        batch_triples[pos:pos+corrupt_s, 0] = neg_s
        batch_triples[pos:pos+corrupt_s, 1] = batch_triples[i, 1]
        batch_triples[pos:pos+corrupt_s, 2] = batch_triples[i, 2]
        pos += corrupt_s
        batch_triples[pos:pos+corrupt_o, 0] = batch_triples[i, 0]
        batch_triples[pos:pos+corrupt_o, 1] = batch_triples[i, 1]
        batch_triples[pos:pos+corrupt_o, 2] = neg_o

    perm = np.random.permutation(len(batch_labels))
    batch_labels = batch_labels[perm]
    batch_triples = batch_triples[perm]

    return batch_triples, batch_labels

def generate_text_batch(related_text, window=5, text_ratio=5):
    batch_text = []
    batch_target = []
    for text in related_text:
        if len(text) <= text_ratio:
            center_index = np.arange(len(text))
        else:
            center_index = np.random.choice(len(text), text_ratio, replace=False)

        for index in center_index:
            start_pos = max(0, index - window)
            left_len = index - start_pos
            end_pos = min(len(text), index + window + 1)
            right_len = end_pos - (index+1)
            phrase = np.zeros([2*window])
            phrase[window - left_len : window] = text[start_pos : index]
            phrase[window : window + right_len] = text[index+1 : end_pos]
            batch_text.append(phrase)
            batch_target.append(text[index])

    batch_text = np.array(batch_text)
    batch_target = np.atleast_2d(np.array(batch_target)).T
    
    return batch_text, batch_target

class kg_embedding:
    def __init__(self, n_entities, n_relations, embedding_size=50):
        self.entity_embeddings = tf.Variable(tf.random_uniform([n_entities, embedding_size], -.5, .5))
        self.relation_embeddings = tf.Variable(tf.random_uniform([n_relations, embedding_size], -.5, .5))

        self.s = tf.placeholder(tf.int32, shape=[None])
        self.p = tf.placeholder(tf.int32, shape=[None])
        self.o = tf.placeholder(tf.int32, shape=[None])
        self.labels = tf.placeholder(tf.float32, shape=[None])

        # embedding layer        
        s_embedding = tf.nn.embedding_lookup(self.entity_embeddings, self.s)
        p_embedding = tf.nn.embedding_lookup(self.relation_embeddings, self.p)
        o_embedding = tf.nn.embedding_lookup(self.entity_embeddings, self.o)

        # l1-norm
        logits = 1. - tf.norm(s_embedding * p_embedding - o_embedding, ord=1, axis=1)
        self.loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(labels=self.labels, logits=logits))

class text_embedding:
    def __init__(self, n_vocabs, n_entities, embedding_size=50, num_sampled=200, window=5):
        self.entity_embeddings = tf.Variable(tf.zeros([n_entities, embedding_size]))
        word_embeddings = tf.concat([tf.Variable(tf.random_uniform([n_vocabs - n_entities, embedding_size], -.5, .5)),
                                        self.entity_embeddings], axis=0)
        mask = tf.concat([tf.ones([n_vocabs - n_entities, 1]), tf.zeros([n_entities, 1])], axis=0)
        self.word_embeddings = tf.stop_gradient((1.-mask) * word_embeddings) + (1.-mask) * word_embeddings

        self.text = tf.placeholder(tf.int32, shape=[None, 2*window])
        self.target = tf.placeholder(tf.int32, shape=[None, 1])

        self.nce_weight = tf.Variable(tf.truncated_normal([n_vocabs, embedding_size], stddev=1.0 / np.sqrt(embedding_size)))
        self.nce_bias = tf.Variable(tf.zeros([n_vocabs]), dtype=tf.float32)

        # embedding layer        
        text_embedding = tf.nn.embedding_lookup(self.word_embeddings, self.text)

        # average layer --> nce loss of text part
        average = tf.reduce_mean(text_embedding, axis=1, keepdims=False)
        self.loss = tf.reduce_mean(tf.nn.nce_loss(weights=self.nce_weight, biases=self.nce_bias, 
                        inputs=average, labels=self.target, 
                        num_sampled=num_sampled, num_classes=n_vocabs))

if __name__ == '__main__':
    '''
    hyper-params
    '''
    WINDOW = 5

    descriptions, triples, all_entities, all_relations = read_data()
    data, triples, count, dictionary, reverse_dictionary = build_dataset(descriptions, triples, all_entities, all_relations)
    del descriptions  # save memory

    with tf.device('/gpu:0'):
        show_every_steps = 500

        model = kg_embedding(len(all_entities), len(all_relations))
        optimizer = tf.train.GradientDescentOptimizer(1e-3).minimize(model.loss)
        num_steps = 30000
        
        average_loss = 0.
        with tf.Session(config=tf.ConfigProto(allow_soft_placement=False)) as session:
            session.run(tf.global_variables_initializer())

            for step in range(num_steps+1):
                batch_triples, batch_labels = generate_kg_batch(triples, dictionary, all_entities, batch_ID_size=16)

                feed_dict = {model.s: batch_triples[:, 0],
                            model.p: batch_triples[:, 1],
                            model.o: batch_triples[:, 2],
                            model.labels: batch_labels}
                _, loss_val = session.run([optimizer, model.loss], feed_dict=feed_dict)
                
                average_loss += loss_val
                if step % show_every_steps == 0 and step > 0:
                    average_loss /= show_every_steps
                    print("Average kg loss at step %d: %.6f" % (step, average_loss))
                    average_loss = 0.

            entity_embeddings = model.entity_embeddings.eval()
            relation_embeddings = model.relation_embeddings.eval()

        np.save('result/entity_embeddings.npy', entity_embeddings)

        model = text_embedding(len(dictionary), len(all_entities), window=WINDOW)
        optimizer = tf.train.GradientDescentOptimizer(1e-3).minimize(model.loss)
        num_steps = 100000

        average_loss = 0.
        with tf.Session(config=tf.ConfigProto(allow_soft_placement=True)) as session:
            session.run(tf.global_variables_initializer())
            session.run(tf.assign(model.entity_embeddings, entity_embeddings))
            tf.stop_gradient(model.entity_embeddings)

            for step in range(num_steps+1):    
                batch_text, batch_target = generate_text_batch(data.values(), window=5, text_ratio=5)

                feed_dict = {model.text: batch_text, 
                            model.target: batch_target}
                _, loss_val = session.run([optimizer, model.loss], feed_dict=feed_dict)
                
                average_loss += loss_val
                if step % show_every_steps == 0 and step > 0:
                    average_loss /= show_every_steps
                    print("Average text loss at step %d: %.6f" % (step, average_loss))
                    average_loss = 0.

            word_embeddings = model.word_embeddings.eval()

        np.save('result/text_data.npy', data)
        np.save('result/embeddings.npy', word_embeddings)
        np.save('result/dictionary.npy', dictionary)
        np.save('result/entities.npy', all_entities)
        np.save('result/relation_embeddings.npy', relation_embeddings)
        np.save('result/relations.npy', all_relations)