# Verify the quality of topic vector generated by LDA,
# cluster tables based on topic vector and check overlapping of table headers.

import pandas as pd
import os
from os.path import join
import numpy as np
import json
from collections import OrderedDict
from itertools import islice
from sklearn.cluster import KMeans
from utils import get_valid_types
from collections import Counter


TYPENAME = os.environ['TYPENAME']
valid_types = get_valid_types(TYPENAME)


topic_no = 100

path = '~/col2type/extract/out/'



def expand(XX):
    # expand the topic string to columns
    XX['table_topic'] = XX['table_topic'].fillna(str([1.0/topic_no]*topic_no))
    XX['table_topic'] = XX['table_topic'].apply(lambda x: eval(x))
    XX[['topic_vec_{}'.format(i) for i in range(topic_no)]] = pd.DataFrame(XX.table_topic.values.tolist(), index=XX.index)
    XX = XX.drop(columns=['table_topic'])
    return XX

def overlap(l):
    # calculate pairwise overlapping coefficients
    # Not sets, there could be duplicate column headers
    co_li = []
    for outter, t_o in enumerate(l):
        for inner, t_i in enumerate(l[outter+1:]):
            
            tc_o = Counter(eval(t_o))
            tc_i = Counter(eval(t_i))
            overlap = list((tc_o & tc_i).elements())
            overlap_co = len(overlap)/ min(len(eval(t_o)), len(eval(t_o)))
            co_li.append(overlap_co)
    return np.mean(co_li)

def overalldist(l):
    # generate the histogram of types
    dic = {}
    for sl in l:
        for t in eval(sl):
            dic[valid_types[t]] = dic.get(valid_types[t],0)+1
    dic = OrderedDict(sorted(dic.items(), key=lambda item: item[1], reverse=True))
    return dic

def print_dic(dic):
    for i, item in dic.items():
        print("Cluster # {}, number of tables {}. Overlapping co-eff {}".format(i, item['cluster_size'], item['overlap'] ))
        print("\tTop 5 types")
        for t, c in islice(item['type_dist'].items(),5):
            print('\t', t,c)
        print()



corpus = 'webtables1-p1'
header_file = 'headers/{}_{}_header_valid.csv'.format(corpus,TYPENAME)
feature_file = 'features/{}_topic_thr-50_num-placeholder_features.csv'.format(corpus)
topic = pd.read_csv(join(path, feature_file))
header = pd.read_csv(join(path, header_file))


df = pd.merge(header, topic, how='left', on=['locator', 'dataset_id'])
# filtering out multi-column tables
multi_col = df[df.apply(lambda x: len(eval(x['field_names']))>1, axis=1)]
multi_col = expand(multi_col).fillna(1.0/topic_no) 
# !!!Note: some LDA outputs are less than 100 in length. Figure out why
X = np.array(multi_col[['topic_vec_{}'.format(i) for i in range(topic_no)]])
y = np.array(multi_col['field_names'])

# generate cluster label
kmeans = KMeans(n_clusters=20)
kmeans.fit(X)
cluster = kmeans.predict(X)
multi_col.loc[:,'cluster']= cluster
clustered_df = multi_col.groupby('cluster').apply(lambda x: list(x['field_names'])).reset_index()
clustered_df.columns = ['cluster', 'types']


cluster_dic = {}
new_df = pd.DataFrame(columns =['type','count','cluster'])
for idx, row in clustered_df.iterrows():
    #print("Cluster # {}, number of tables {}".format(row['cluster'], ))
    cluster_dic[row['cluster']] = {"type_dist": overalldist(row.types), 'overlap': overlap(row.types), 'cluster_size':len(row['types'])}
    
 
# Sort clusters based on overlapping value
cluster_dic = OrderedDict(sorted(cluster_dic.items(), key=lambda item: item[1]['overlap'], reverse=True))


print_dic(cluster_dic)