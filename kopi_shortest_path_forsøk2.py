from math import dist
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

def define_neighbors(row, df, G, gridsize):
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
            weight=1
        elif i == 2:
            weight=1.4
        else:
            raise Exception("No weight was assigned for neighbors.")
        weight *= gridsize
        idx2 = dataf['id'].values
        arr = np.zeros(shape=(len(idx2), 3))
        arr[:,0] = idx2
        arr[:,1:] = np.array([idx, weight])
        G.add_weighted_edges_from(arr)

def multiple_paths(row, method1_df, dict_id,dict_to_trans,dict_from_trans, method2):
    #Takes in rows from from df2
    #Create new dataframe from dict
    dist_df = pd.DataFrame.from_dict(row['dict'], orient='index', columns=['dist']).reset_index().rename(columns={'index':'id'}).astype({'id':int}) #Cool stuff be happening. Don't worry bruv
    both_methods = method1_df.loc[method1_df[method2]] # Her definerer vi metode 2. Denne kan egentlig defineres utenfor denne funksjonen før vi kaller på på apply funksjonen, eller sendte den inn i funksjonen som et argument
    int_df = pd.merge(dist_df, both_methods, how='inner', on=['id'])
    min_to_trans = int_df['dist'].min()
    min_to_trans_idx = int_df['dist'].idxmin()
    min_to_trans_id = int_df.loc[min_to_trans_idx, 'id']
    min_to_trans_id = int(min_to_trans_id)
    min_from_trans = int_df.loc[min_to_trans_idx, 'distance_{}'.format(method2)]
    dict_id[row['id']] = min_to_trans_id; dict_to_trans[row['id']] = min_to_trans; dict_from_trans[row['id']] = min_from_trans

def pipe_water(row, water_df, gridsize, dict_id,dict_to_trans,dict_from_trans):
    id, x, y = row['id'], row['x'], row['y']
    water_df['pipe_dist'] = np.sqrt(((water_df['x']-x)*gridsize)**2 + ((water_df['y']-y)*gridsize)**2)
    min_to_trans = water_df['pipe_dist'].min()
    min_to_trans_idx = water_df['pipe_dist'].idxmin()
    min_to_trans_id = water_df.loc[min_to_trans_idx, 'id']
    min_to_trans_id = int(min_to_trans_id)
    min_from_trans = water_df.loc[min_to_trans_idx, 'distance_water']
    dict_id[id] = min_to_trans_id; dict_to_trans[id] = min_to_trans; dict_from_trans[id] = min_from_trans

def shortest_path_to_node(filename="Poland/Ze_points_5.0.csv", id=7080, gridsize=5):
    """
    Given a dataset(filename) we convert it into a pandas dataframe. Then we define the network through the use of define negihbors.
    Lastly, we compute the shortest distance to a node from every other node.

    Input:
        -filename(str): filename of the file with the data. Should be a CSV file.
        -id(int): id of the point we want to travel to.
        -gridsize(int): size of grid
    
    """
    #Initializing the dataframe
    data = pd.read_csv(filename)
    df = pd.DataFrame(data, columns=['id', 'xIndex', 'yIndex', 'BOOL_ROAD', 'BOOL_RAILWAY', 'BOOL_WATERCOURSE']) #extract the desired columns
    df.rename(columns = {'xIndex':'x', 'yIndex':'y', 'BOOL_ROAD':'road', 'BOOL_RAILWAY':'rail', 'BOOL_WATERCOURSE':'water'}, inplace = True) #change column names to something easier to type
    #add distances to port using road, rail, water
    graphs = {} # key method, value graph for method
    for method in ['road', 'rail', 'water']:
        method_df = df.loc[df[method]] # extract the nodes with method
        G = nx.Graph()
        method_df.apply(define_neighbors, axis=1, df=method_df, G=G, gridsize = gridsize) #Adds edges to the graph with weights
        graphs[method] = G # Storing the graphs
        distances = nx.single_source_dijkstra_path_length(G, id, weight='weight') # Computes the shortest distance from/to the node with the specified id. Output is a dictionary.
        distances = dict((int(key), value) for key,value in distances.items())
        col_name = 'distance_' + method
        df[col_name] = df['id'].map(distances)
    edges = graphs['road'].edges()

    #Finn noden du skal ha avstanden til
    holy_node = df.loc[df['id']==id].values
    x, y = holy_node[0,1:3]
    #Implementer straight line distance mellom punktene.
    df['straight_distance'] = np.sqrt(((df['x']-x)*gridsize)**2 + ((df['y']-y)*gridsize)**2) #Dette var ikke så ille som først fryktet. Max avstanden passer greit inn
    df = df.round({'straight_distance':2}) #rounding off to fewer digits for a nicer file

    methods = [('road', 'water'), ('rail', 'water'), ('road', 'rail')]
    for method1, method2 in methods:
        #Simply use df
        method_df = df.loc[df[method1]] # extract the nodes with method1
        map_dict_trans_id = {}
        map_dict_to_trans ={}
        map_dict_from_trans = {}
        G = graphs[method1]
        distances = nx.all_pairs_dijkstra_path_length(G)
        df2 = pd.DataFrame(distances, columns=['id', 'dict']).astype({'id':int}).apply(multiple_paths, axis=1, method1_df=method_df, method2=method2, dict_id=map_dict_trans_id,dict_to_trans=map_dict_to_trans,dict_from_trans=map_dict_from_trans)
        col_name = '{}+{}_transition_id'.format(method1, method2)
        df[col_name] = df['id'].map(map_dict_trans_id)
        df = df.astype({col_name:'Int64'}) # We use Int64, because every other integer type doesn't work. I don't know the difference between int64 and Int64
        col_name2 = 'dist_{}+{}_to_trans'.format(method1, method2)
        df[col_name2] = df['id'].map(map_dict_to_trans)
        col_name3 = 'dist_{}+{}_from_trans'.format(method1, method2)
        df[col_name3] = df['id'].map(map_dict_from_trans)

    #Remains to implement pipe+water
    map_dict_trans_id = {}
    map_dict_to_trans ={}
    map_dict_from_trans = {}
    water_df = df.loc[df['water']]
    df.apply(pipe_water, axis=1, water_df=water_df, gridsize=gridsize, dict_id=map_dict_trans_id,dict_to_trans=map_dict_to_trans,dict_from_trans=map_dict_from_trans)
    col_name = 'pipe+water_transition_id'
    df[col_name] = df['id'].map(map_dict_trans_id)
    col_name2 = 'dist_pipe+water_to_trans'
    df[col_name2] = df['id'].map(map_dict_to_trans)
    col_name3 = 'dist_pipe+water_from_trans'
    df[col_name3] = df['id'].map(map_dict_from_trans)
    df = df.round({'dist_pipe+water_to_trans':2})
    print(df.dtypes)
    df.to_csv("Fil_med_Avstand3.csv", index=False)
    #Det er mulig å returnere dataframen og grafene hvis vi ønsker det. Alternativt så kan vi bare lagre det som filer og åpne de fra en annen funsksjon

def error_analysis(our_data_file, QGIS_data_file, method, multiplier):
    our_df = pd.read_csv(our_data_file) #This gives a dataframe automatically

    #Playing with QGIS dataframe, till it looks nice.
    Qgis_df = pd.read_csv(QGIS_data_file) #read the file and convert it to pandas dataframe
    Qgis_df = Qgis_df[['id', 'xIndex', 'yIndex', 'BOOL_ROAD', 'BOOL_RAILWAY', 'BOOL_WATERCOURSE', 'cost']] #include only the wanted columns
    Qgis_df.rename(columns = {'xIndex':'x', 'yIndex':'y', 'BOOL_ROAD':'road', 'BOOL_RAILWAY':'rail', 'BOOL_WATERCOURSE':'water'}, inplace = True)#renaming columns
    Qgis_df['cost'] = Qgis_df['cost']/1000 #Convert distance from m to km 
    convert_dict = {'road':bool, 'rail':bool, 'water':bool} 
    Qgis_df = Qgis_df.astype(convert_dict) #Change type of columns as defined in convert_dict
    
    #Finding the relevant parts of the dataframe to analyze
    Qgis_df = Qgis_df.loc[Qgis_df[method]] #choosing only the rows that has road available
    our_df = our_df.loc[our_df[method]] # same as above only for another dataframe

    #creating error dataframe
    error_df = Qgis_df[['id','x','y']] #Storing the id, x and y values frpm QGIS dataframe
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
    return error_df, mean_rel_error, rmse


def make_contour():
    error_df, mean_rel_error, rmse = error_analysis('Fil_med_Avstand.csv', 'Poland/distance_road_5.csv', 'road', 1.1) #use only the error_df
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
    plt.savefig(plot_name)
    plt.clf() #Clear the old figure

def error_analysis_multiple_grids():
    #This function is for one multiplier. Maybe we will expand this to include a different multiplier for each method
    gridsizes = [i for i in range(0,51, 5) if i!= 0] # [5, 10, ..., 50]
    id_poland = {50:67, 45:86, 40:114, 35:146,30:192,25:278,20:437,15:760,10:1742, 5:7080}
    multiplier = 1.1
    stats = np.zeros(shape=(len(gridsizes), 4))
    stats[:,0] = gridsizes
    print(stats)
    for i, gridsize in enumerate(gridsizes):
        filename = 'Poland/Ze_points_{:.1f}.csv'.format(gridsize)
        shortest_path_to_node(filename, id_poland[gridsize], gridsize) # Det lages en fil som heter "Fil_med_Avstand.csv"
        for j, method in enumerate(['road', 'rail', 'water']):
            distance_qgis_fn = "Poland/distance_{}_{}.csv".format(method, gridsize)
            error_df, mean_rel_error, rmse = error_analysis('Fil_med_Avstand.csv',distance_qgis_fn,method,multiplier)
            stats[i,j+1] = mean_rel_error
    df = pd.DataFrame(stats, columns=['gridsize', 'road mean rel error', 'rail mean rel error', 'water mean rel error'])
    df.to_csv("Error_Poland_multiplier_1.1.csv", index=False)

def error_analysis_multiplier():
    #So what do we want to do? Do we want to create the error files, for each gridsize. Or how do we do it?
    gridsizes = [i for i in range(0,51, 5) if i!= 0] # [5, 10, ..., 50]
    id_poland = {50:67, 45:86, 40:114, 35:146,30:192,25:278,20:437,15:760,10:1742, 5:7080}
    stats = np.zeros(shape=(len(np.linspace(1, 1.8, 9)), 4))
    stats[:,0] = np.linspace(1, 1.8, 9)
    for i, gridsize in enumerate(gridsizes):
        filename = 'Poland/Ze_points_{:.1f}.csv'.format(gridsize)
        shortest_path_to_node(filename, id_poland[gridsize], gridsize) # Det lages en fil som heter "Fil_med_Avstand.csv"
        for j, method in enumerate(['road', 'rail', 'water']):
            for idx, k in enumerate(np.linspace(1, 1.8, 9)):
                distance_qgis_fn = "Poland/distance_{}_{}.csv".format(method, gridsize)
                error_df, mean_rel_error, rmse = error_analysis('Fil_med_Avstand.csv',distance_qgis_fn,method,k)
                stats[idx, j+1] = mean_rel_error
        df = pd.DataFrame(stats, columns=['gridsize', 'road mean rel error', 'rail mean rel error', 'water mean rel error'])
        df.to_csv("Error_Poland_{}.csv".format(gridsize), index=False)




#shortest_path_to_node()
shortest_path_to_node(filename="Poland/Ze_points_50.0.csv", id=67, gridsize=50)
#make_contour()
#error_analysis_multiplier()


    

