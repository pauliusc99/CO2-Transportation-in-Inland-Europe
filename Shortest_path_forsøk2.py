import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import time
from tqdm import tqdm

def define_neighbors(row, df, G):
    idx, x, y = row[:3] # 0th, 1st, 2nd columns are collected
    horz = df.loc[(df['x'].isin([x-1, x+1])) & (df['y'] == y)] # Dette bør gi de vertikale naboene
    vert = df.loc[(df['x']==x) & (df['y'].isin([y-1,y+1]))] # Dette bør gi de horizontale naboene
    diag = df.loc[(df['x'].isin([x-1,x+1])) & (df['y'].isin([y-1, y+1]))] # Dette bør gi de diagonale naboene
    for i, dataf in enumerate([horz, vert, diag]):
        weight = 1
        if i <2:
            weight=1*5
        elif i == 2:
            weight=1.4*5
        else:
            raise Exception("No weight was assigned for neighbors.")
        idx2 = dataf['id'].values
        arr = np.zeros(shape=(len(idx2), 3))
        arr[:,0] = idx2
        arr[:,1:] = np.array([idx, weight])
        G.add_weighted_edges_from(arr)

def shortest_path_to_node(filename="Poland/Ze_points_5.0.csv", id=7080):
    #Initializing the dataframe
    data = pd.read_csv(filename)
    df = pd.DataFrame(data, columns=['id', 'xIndex', 'yIndex', 'BOOL_ROAD', 'BOOL_RAILWAY', 'BOOL_WATERCOURSE']) #extract the desired columns
    df.rename(columns = {'xIndex':'x', 'yIndex':'y', 'BOOL_ROAD':'road', 'BOOL_RAILWAY':'rail', 'BOOL_WATERCOURSE':'water'}, inplace = True) #change column names to something easier to type

    for method in ['road', 'rail', 'water']:
        method_df = df.loc[df[method]] # extract the nodes with method
        G = nx.Graph()
        method_df.apply(define_neighbors, axis=1, df=method_df, G=G) #Adds edges to the graph with weights
        distances = nx.single_source_dijkstra_path_length(G, id) # Computes the shortest distance from/to the node with the specified id. Output is a dictionary.
        distances = dict((int(key), value) for key,value in distances.items())
        col_name = 'distance_' + method
        df[col_name] = df['id'].map(distances)
    df.to_csv('Fil_med_Avstand.csv')

shortest_path_to_node()
