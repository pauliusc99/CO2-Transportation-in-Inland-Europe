import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

def define_neighbors(row, df, G):
    """
    Function used to define gridcell neighbors. After neighbors are found the edge from point to neighbor is added to a network. In this network
    edges to horizontal and vertical neighbors have weight 1, while diagonal neighbors have 1.4(approx sqrt(2)). The graph has to be initiated
    before running this function on our dataframe.

    Input:
        - row(hva er typen her?): row of dataframe
        - df(pandas dataframe): dataframe that represents node with chosen transportation method.
        - G(nx graph): graph that will store how our network looks for given transportaion method.

    Output:
        - Nada
    """
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
    """
    Given a dataset(filename) we convert it into a pandas dataframe. Then we define the network through the use of define negihbors.
    Lastly, we compute the shortest distance to a node from every other node.

    Input:
        -filename(str): filename of the file with the data. Should be a CSV file.
        -id(int): id of the point we want to travel to.
    
    """
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
    df.to_csv('Fil_med_Avstand.csv', index=False)
    #Det er mulig å returnere dataframen og grafene hvis vi ønsker det. Alternativt så kan vi bare lagre det som filer og åpne de fra en annen funsksjon

def error_analysis(our_data_file, QGIS_data_file):
    our_df = pd.read_csv(our_data_file) #This gives a dataframe automatically

    #Playing with QGIS dataframe, till it looks nice.
    Qgis_df = pd.read_csv(QGIS_data_file) #read the file and convert it to pandas dataframe
    Qgis_df = Qgis_df[['id', 'xIndex', 'yIndex', 'BOOL_ROAD', 'BOOL_RAILWAY', 'BOOL_WATERCOURSE', 'cost']] #include only the wanted columns
    Qgis_df.rename(columns = {'xIndex':'x', 'yIndex':'y', 'BOOL_ROAD':'road', 'BOOL_RAILWAY':'rail', 'BOOL_WATERCOURSE':'water'}, inplace = True)#renaming columns
    Qgis_df['cost'] = Qgis_df['cost']/1000 #Convert distance from m to km 
    convert_dict = {'road':bool, 'rail':bool, 'water':bool} 
    Qgis_df = Qgis_df.astype(convert_dict) #Change type of columns as defined in convert_dict
    
    #Finding the relevant parts of the dataframe to analyze
    Qgis_df = Qgis_df.loc[Qgis_df['road']] #choosing only the rows that has road available
    our_df = our_df.loc[our_df['road']] # same as above only for another dataframe

    #creating error dataframe
    error_df = Qgis_df[['id','x','y']] #Storing the id, x and y values frpm QGIS dataframe
    multiplier = 1.1 #1.1 funker best for 5km road 
    err = np.array(Qgis_df['cost'] - our_df['distance_road']*multiplier) # Hvorfor klager de så jævlig på denne linja
    error_df.insert(3, 'abs_error', err, True) #Finally

    #Statistics being computed 
    abs_error = np.array(error_df['abs_error'])
    rel_error = abs_error/Qgis_df['cost']*100 #Convert relative error to per cent
    error_df.insert(4, 'rel_error', rel_error, True) # Insert the relative error as a column in error dataframe
    abs_error = abs_error[np.isfinite(abs_error)] #removing np.nan values
    rel_error = rel_error[np.isfinite(rel_error)] #removing np.nan values
    mean_rel_error = np.mean(np.abs(rel_error))
    rmse = np.sqrt(np.sum(abs_error**2)/np.size(abs_error)) #root mean square error
    print(mean_rel_error, rmse)
    #Hvis jeg vil bruke make contour så trenger jeg indeksene. Hvordan kan jeg gjøre det da?
    return error_df


def make_contour():
    error_df = error_analysis('Fil_med_Avstand.csv', 'Poland/distance_road_5.csv')
    #How do we remove the rows that are np.nan?
    error_df = error_df.loc[np.isfinite(error_df['rel_error'])] #removing nan from rel_error
    error_df = error_df.loc[np.isfinite(error_df['abs_error'])] #doing the same thing for abs_error, but I don't think that is necessary. If nan in abs_error then that should propagate to rel_error, as it uses abs_error
    xmax = np.max(error_df['x'])
    ymax = np.max(error_df['y'])
    Z = np.full([ymax,xmax], None)
    #Find a quick way to fill up Z without double for loop.
    Z[error_df['y']-1, error_df['x']-1] = error_df['abs_error'] # Jesus I'm impressed that I'm writing this and it works. Wild
    #Ze plot is popping
    plot_name = "relative_error_5km_road_1.1_multiplier.png"
    plt.contourf(Z, origin='upper', levels = 10)
    plt.colorbar()
    plt.xlabel("x index")
    plt.ylabel("y index")
    plt.title("relative error, gridsize:5km, multiplier:1.1, Transsport:road")
    plt.show()
    #plt.savefig(plot_name)
    plt.clf() #Clear the old figure






shortest_path_to_node()
make_contour()