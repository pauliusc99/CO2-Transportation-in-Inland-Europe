from math import dist
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

# Gridcell/point/node is probably used interchangebly. When we use x and y to compute distances its best to think of (x,y) as points
# in the center of each gridcell.
# Whenever I write water, I mean river.
# The word method refers to transportation method. In our case, primarily road/rail/river. Although, pipe is also used sometimes 
# trans refers to transition

print(np.__version__)
print('pandas', pd.__version__)
print('network', nx.__version__)
print()

def define_neighbors(row, df, G, gridsize):
    """
    Defines the neighbors for each gridcell and adds the connection to the neighbors as edges in the transportation graph.
    Edges to horizontal and vertical neighbors have weight 1, while diagonal neighbors have weigh 1.4(approx  sqrt(2)). 
    Horizontal/Vertical/Diagonal are based on the 'x' and 'y' indices of the gridcells.

    Input:
        - row(pandas series): row of dataframe
        - df(pandas dataframe): dataframe that represents gridcells with a specified transportation method.
        - G(networkx graph): graph that that stores the network for a specified transportation method
    """
    idx, x, y = row[:3] # 0th, 1st, 2nd columns are collected
    horz = df.loc[(df['x'].isin([x-1, x+1])) & (df['y'] == y)] # Find the horizontal neighbors
    vert = df.loc[(df['x']==x) & (df['y'].isin([y-1,y+1]))] # Find the vertical neighbors
    diag = df.loc[(df['x'].isin([x-1,x+1])) & (df['y'].isin([y-1, y+1]))] # Find the diagonal neighbors
    for i, dataf in enumerate([horz, vert, diag]):
        #Find the weight for edge based on the type of neighbor
        weight = 1
        if i < 2:
            weight = 1
        elif i == 2:
            weight = 1.4
        else:
            raise Exception("No weight was assigned for neighbors.")
        weight *= gridsize # Den er ikke nødvendig her. Dette kan egt gjøres et annet sted, etter at algoritmen er kjørt
        idx2 = dataf['id'].values # Extract the ids of the neighbors
        arr = np.zeros(shape=(len(idx2), 3))
        #We use the id of the gridcells to identify the nodes in the graph
        arr[:,0] = idx2 #Fill the first column with neighbor ids
        arr[:,1:] = np.array([idx, weight]) # Fill the second column with origin point ids. Third column with weight of edge from origin point to neighbor
        G.add_weighted_edges_from(arr)

def multiple_paths(row, method1_df, dict_id,dict_to_trans,dict_from_trans, method2):
    """
    Computes the distance from a gridcell to the port using two transportation methods. 
    The transition point is the point which connects method1 and method2 and that minimizes the distance along method1.

    Input:
        - row(pandas series): row of dataframe. Each row represents a gridcell
        - method1_df(pandas dataframe): dataframe that represents gridcells with transportation method1 available
        - dict_id(dict): Source point id is the key. id of transition point between method 1 and 2 is the value. 
        - dict_to_trans(dict): source point id is the key. Distance from source to transition is the value.
        - dict_from_trans(dict): source point id is the key. Distance from transition to port is the value.
        - method2(str): name of the second transportation method. One of the following: road/rail/water.
    """
    #Hva er dist_df. Rettere sagt hva er row['dict']
    dist_df = pd.DataFrame.from_dict(row['dict'], orient='index', columns=['dist']).reset_index().rename(columns={'index':'id'}).astype({'id':int}) #Cool stuff be happening. Don't worry bruv
    both_methods = method1_df.loc[method1_df[method2]] # Her definerer vi metode 2. Denne kan egentlig defineres utenfor denne funksjonen før vi kaller på på apply funksjonen, eller sendte den inn i funksjonen som et argument
    int_df = pd.merge(dist_df, both_methods, how='inner', on=['id']) #Intersects the two datasets based on id
    min_to_trans = int_df['dist'].min() #The shortest distance from source point to potential transition point
    min_to_trans_idx = int_df['dist'].idxmin() #Index of said transition point
    min_to_trans_id = int_df.loc[min_to_trans_idx, 'id'] #Find the id of the transition point
    min_to_trans_id = int(min_to_trans_id)
    min_from_trans = int_df.loc[min_to_trans_idx, 'distance_{}'.format(method2)] #Find the distance from transition point to the port using method2
    dict_id[row['id']] = min_to_trans_id; dict_to_trans[row['id']] = min_to_trans; dict_from_trans[row['id']] = min_from_trans

def pipe_water(row, water_df, gridsize, dict_id,dict_to_trans,dict_from_trans):
    """
    Computes the distance from grid to port using a pipeline from source point to river and then transporting along the river.
    Transition point is chosen as the point which minimizes the distance from source point to river using straight line distance
    
    Input:
        - row(pandas series): row of dataframe. Each row represents a gridcell
        - water_df(pandas dataframe): dataframe where each gridcell has river available
        - gridsize(int): the lenghth and width of each gridcell in km
        - dict_id(dict): Keys are source points. Values are transition point ids
        - dict_to_trans(dict): Keys are source points. Values are straight line distances from source point to transition points in km
        - dict_from_trans(dict): Keys are source points. Values  are the distances along the rivers from transition point to port in km 
    """
    id, x, y = row['id'], row['x'], row['y']
    water_df['pipe_dist'] = np.sqrt(((water_df['x']-x)*gridsize)**2 + ((water_df['y']-y)*gridsize)**2) #Straight line/Euclidean distance
    min_to_trans = water_df['pipe_dist'].min() #distance from sourte to river
    min_to_trans_idx = water_df['pipe_dist'].idxmin()
    min_to_trans_id = water_df.loc[min_to_trans_idx, 'id'] # fetch id of transition points
    min_to_trans_id = int(min_to_trans_id)
    min_from_trans = water_df.loc[min_to_trans_idx, 'distance_water'] # Distance from transition point to port
    dict_id[id] = min_to_trans_id; dict_to_trans[id] = min_to_trans; dict_from_trans[id] = min_from_trans

def shortest_path_to_node(filename="Poland/Ze_points_5.0.csv", id=7080, gridsize=5):
    """
    Imports the csv and computes shortest distances for various transportation methods and exports this data as a CSV

    Input:
        -filename(str): filename of the CSV file with the data
        -id(int): id of the point we want to travel to(the port)
        -gridsize(int): size of grid in km
    """
    #Initializing the dataframe
    data = pd.read_csv(filename)
    df = pd.DataFrame(data, columns=['id', 'xIndex', 'yIndex', 'BOOL_ROAD', 'BOOL_RAILWAY', 'BOOL_WATERCOURSE']) #extract the desired columns
    df.rename(columns = {'xIndex':'x', 'yIndex':'y', 'BOOL_ROAD':'road', 'BOOL_RAILWAY':'rail', 'BOOL_WATERCOURSE':'water'}, inplace = True) #change column names to something easier to type
    #add distances to port using road, rail, water
    graphs = {} # the keys are the methods. The values are the network for the given method of transportation
    for method in ['road', 'rail', 'water']:
        method_df = df.loc[df[method]] # extract the gridcells with method
        G = nx.Graph()
        method_df.apply(define_neighbors, axis=1, df=method_df, G=G, gridsize = gridsize) #Runs define neighbors for each row in method_df dataframe. Adds edges to the graph with weights
        graphs[method] = G # Storing the graphs
        distances = nx.single_source_dijkstra_path_length(G, id, weight='weight') # Computes the shortest distance from/to the node with the specified id. Output is a dictionary.
        distances = dict((int(key), value) for key,value in distances.items())
        col_name = 'distance_' + method
        df[col_name] = df['id'].map(distances) #Add a column with distances

    #Find the port/id gridcell
    holy_node = df.loc[df['id']==id].values
    x, y = holy_node[0,1:3]
    #Creating new column with the straight-line distance from each gridcell to the port.
    df['straight_distance'] = np.sqrt((df['x']-x)**2 + (df['y']-y)**2)*gridsize 
    df = df.round({'straight_distance':2}) #rounding off to fewer digits for a nicer file

    #Computing the distances using two methods
    methods = [('road', 'water'), ('rail', 'water'), ('road', 'rail')]
    for method1, method2 in methods:
        method_df = df.loc[df[method1]] # extract the nodes with method1
        map_dict_trans_id = {} # dictionary with transition id
        map_dict_to_trans = {} # dictionary with distance from source gridcell to transition point
        map_dict_from_trans = {} # dictionary with distance from transition point to the goal/port gridcell
        G = graphs[method1] #access the graph of method1
        distances = nx.all_pairs_dijkstra_path_length(G) 
        df2 = pd.DataFrame(distances, columns=['id', 'dict']).astype({'id':int}) #Converts the dict to a dataframe
        df2.apply(multiple_paths, axis=1, method1_df=method_df, method2=method2, 
                  dict_id=map_dict_trans_id,dict_to_trans=map_dict_to_trans,
                  dict_from_trans=map_dict_from_trans
        ) #Finds the shortest path from each gridcell to port. multiple_paths applied to each row of df2
        #Adding columns
        col_name = '{}+{}_transition_id'.format(method1, method2)
        df[col_name] = df['id'].map(map_dict_trans_id)
        df = df.astype({col_name:'Int64'}) # We use Int64, because every other integer type doesn't work. I don't know the difference between int64 and Int64. Doesn't work because of np.nan or np.inf values
        col_name2 = 'dist_{}+{}_to_trans'.format(method1, method2)
        df[col_name2] = df['id'].map(map_dict_to_trans)
        col_name3 = 'dist_{}+{}_from_trans'.format(method1, method2)
        df[col_name3] = df['id'].map(map_dict_from_trans)

    #Implementing pipe+water distance
    map_dict_trans_id = {}; map_dict_to_trans = {}; map_dict_from_trans = {}
    water_df = df.loc[df['water']] #extract all gridcells with river
    df.apply(pipe_water, axis=1, water_df=water_df, gridsize=gridsize, dict_id=map_dict_trans_id,dict_to_trans=map_dict_to_trans,dict_from_trans=map_dict_from_trans)
    col_name = 'pipe+water_transition_id'
    df[col_name] = df['id'].map(map_dict_trans_id)
    col_name2 = 'dist_pipe+water_to_trans'
    df[col_name2] = df['id'].map(map_dict_to_trans)
    col_name3 = 'dist_pipe+water_from_trans'
    df[col_name3] = df['id'].map(map_dict_from_trans)
    df = df.round({'dist_pipe+water_to_trans':2})
    #df.to_csv("Fil_med_Avstand3.csv", index=False)
    #Det er mulig å returnere dataframen og grafene hvis vi ønsker det. Alternativt så kan vi bare lagre det som filer og åpne de fra en annen funsksjon

def error_analysis(our_data_file, QGIS_data_file, method, multiplier):
    """
    Compute basic error statistics, like absolute error, relative error, mean relative error and root mean square error.
    These calculations compare results produced by the shortest_path_to_node function with values from QGIS.

    Input:
        -our_data_file(str): CSV file produced by shortest_path_to_node
        -QGIS_data_file(str): CSV file with shortest distances computed by QGIS algorithm Shortest path from point to layer
        -method(str): transportation method. Alternatives: road/rail/water
        -multiplier(float): cost multiplier for our distances. This helps to deal with tortuosity of road for example. 
    
    Output:
        -error_df(pandas dataframe): dataframe containing the absolute and relative error for each gridcell
        -mean_rel_error(float): Mean relative error of our model compared to QGIS
        -rmse(float): root mean square error for our model compared to QGIS
    """
    our_df = pd.read_csv(our_data_file) #This gives a dataframe automatically

    #Playing with QGIS dataframe, till it looks nice
    Qgis_df = pd.read_csv(QGIS_data_file) #read the file and convert it to pandas dataframe
    Qgis_df = Qgis_df[['id', 'xIndex', 'yIndex', 'BOOL_ROAD', 'BOOL_RAILWAY', 'BOOL_WATERCOURSE', 'cost']] #include only the wanted columns
    Qgis_df.rename(columns = {'xIndex':'x', 'yIndex':'y', 'BOOL_ROAD':'road', 'BOOL_RAILWAY':'rail', 'BOOL_WATERCOURSE':'water'}, inplace = True)#renaming columns
    Qgis_df['cost'] = Qgis_df['cost']/1000 #Convert distance from m to km 
    convert_dict = {'road':bool, 'rail':bool, 'water':bool} 
    Qgis_df = Qgis_df.astype(convert_dict) #Change type of columns as defined in convert_dict
    
    #Extracting the relevant parts of the dataframe to analyze
    Qgis_df = Qgis_df.loc[Qgis_df[method]] #choosing only the rows that have the given method of transportation available
    our_df = our_df.loc[our_df[method]]
    #creating error dataframe
    error_df = Qgis_df[['id','x','y']] #Storing the id, x and y values frpm QGIS dataframe
    err = np.array(Qgis_df['cost'] - our_df['distance_road']*multiplier)
    error_df.insert(3, 'abs_error', err, True) #Inserting absolute error into dataframe

    #Statistics being computed 
    abs_error = np.array(error_df['abs_error'])
    rel_error = abs_error/Qgis_df['cost']*100 #Convert relative error to per cent
    error_df.insert(4, 'rel_error', rel_error, True) # Insert the relative error as a column into error dataframe
    abs_error = abs_error[np.isfinite(abs_error)] #removing np.nan values
    rel_error = rel_error[np.isfinite(rel_error)] #removing np.nan values
    mean_rel_error = np.mean(np.abs(rel_error))
    rmse = np.sqrt(np.sum(abs_error**2)/np.size(abs_error)) #root mean square error
    return error_df, mean_rel_error, rmse

#More changes to be made
def make_contour(our_data_file='Fil_med_Avstand.csv', QGIS_data_file='Poland/distance_road_5.csv', method = 'road', multiplier=1.1):
    """
    Creates a contour map for the relative error computed in error_analysis

    Input:
        -
    """
    #Jeg lurer på om det er bedre å gi litt andre input slik at vi kaller på shortest_distance_To_node herfra?
    error_df, mean_rel_error, rmse = error_analysis(our_data_file, QGIS_data_file, method, multiplier) #use only the error_df
    error_df = error_df.loc[np.isfinite(error_df['rel_error'])] #removing nan from rel_error
    #This step may be redundant for error_df
    error_df = error_df.loc[np.isfinite(error_df['abs_error'])] #doing the same thing for abs_error, but I don't think that is necessary. If nan in abs_error then that should propagate to rel_error, as it uses abs_error
    xmax = np.max(error_df['x'])
    ymax = np.max(error_df['y'])
    Z = np.full([ymax,xmax], None)
    #Find a quick way to fill up Z without double for loop.
    Z[error_df['y']-1, error_df['x']-1] = error_df['rel_error'] # fill up Z with relative errors. 
    plot_name = "relative_error_5km_road_1.1_multiplier.png" # should depend on input
    plt.contourf(Z, origin='upper', levels = 10) #upper makes it interpret (0,0) as upper left corner.
    plt.colorbar()
    plt.xlabel("x index")
    plt.ylabel("y index")
    plt.title("relative error, gridsize:5km, multiplier:1.1, Transsport:road")
    plt.savefig(plot_name)
    plt.clf() #Clear the old figure

def error_analysis_multiple_grids():
    #This function is for one multiplier. Maybe we will expand this to include a different multiplier for each method
    gridsizes = [i for i in range(5,51, 5)] # [5, 10, ..., 50]
    id_poland = {50:67, 45:86, 40:114, 35:146,30:192,25:278,20:437,15:760,10:1742, 5:7080}
    multiplier = 1.1
    stats = np.zeros(shape=(len(gridsizes), 4))
    stats[:,0] = gridsizes
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


    

