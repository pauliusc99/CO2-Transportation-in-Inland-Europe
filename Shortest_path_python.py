import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

# trans refers to transition point when computing path using two tranpsortation methods. Then the transiion point is where you change from the first to the second method of transportation.

def init_network(row, df, G, gridsize):
    """
    Define the neighbors for each gridcell and add the connection to the neighbors as edges in the transportation graph.
    Edges to horizontal and vertical neighbors have weight 1, while diagonal neighbors have weigh 1.4(approx  sqrt(2)). 
    The horizontal/vertical/diagonal naming conventions are based on the 'x' and 'y' indices of the gridcells.

    Input:
        - row(pandas series): row of dataframe
        - df(pandas dataframe): dataframe that represents gridcells with a specified transportation method.
        - G(networkx graph): graph that stores the network for a specified transportation method
        - gridsize(flaot): length/width of each gridcell in km
    """
    idx, x, y = row[:3]
    horz = df.loc[(df['x'].isin([x-1, x+1])) & (df['y'] == y)] # Find the horizontal neighbors
    vert = df.loc[(df['x']==x) & (df['y'].isin([y-1,y+1]))] # Find the vertical neighbors
    diag = df.loc[(df['x'].isin([x-1,x+1])) & (df['y'].isin([y-1, y+1]))] # Find the diagonal neighbors
    horz['weight'] = 1; vert['weight'] = 1; diag['weight'] = 1.4 #Add the weights
    neighbors = pd.concat([horz, vert, diag], ignore_index=True) #Combine the three dataframes to a new one
    neighbors['weight'] *= gridsize 
    neighbors['id2'] = idx # Add the index of the row as a column
    arr = neighbors[['id', 'id2', 'weight']].values #Converting the selected columns to an array
    G.add_weighted_edges_from(arr)


def multiple_paths(row, both_method_df,dict_id,dict_to_trans,dict_from_trans, method2):
    """
    Compute the distance from a gridcell to the port using two transportation methods. 
    The transition point is the point which connects the first and second transportation method and that minimizes the distance along method1.

    Input:
        - row(pandas series): row of dataframe. Each row represents a gridcell
        - both_method_df(pandas dataframe): dataframe that represents gridcells with the first and second transportation method available
        - dict_id(dict): Source point id is the key. id of transition point between method 1 and 2 is the value. 
        - dict_to_trans(dict): source point id is the key. Distance from source to transition is the value.
        - dict_from_trans(dict): source point id is the key. Distance from transition to port is the value.
        - method2(str): name of the second transportation method. One of the following: road/rail/water.
    """
    dist_df = pd.DataFrame.from_dict(row['dict'], orient='index', columns=['dist']).reset_index().rename(columns={'index':'id'}).astype({'id':int}) #Change the index to its own column called id, with type int.
    int_df = pd.merge(dist_df, both_method_df, how='inner', on=['id']) #Intersects the two datasets based on id
    if int_df['dist'].size: 
        min_to_trans = int_df['dist'].min() #The shortest distance from source point to potential transition point
        min_to_trans_idx = int_df['dist'].idxmin() #Index of said transition point
        min_to_trans_id = int_df.loc[min_to_trans_idx, 'id'] #Find the id of the transition point
        min_to_trans_id = int(min_to_trans_id)
        min_from_trans = int_df.loc[min_to_trans_idx, 'distance_{}'.format(method2)] #Find the distance from transition point to the port using method2
        dict_id[row['id']] = min_to_trans_id; dict_to_trans[row['id']] = min_to_trans; dict_from_trans[row['id']] = min_from_trans #Variablene kunne hatt bedre navn

def pipe_water(row, water_df, gridsize, dict_id,dict_to_trans,dict_from_trans):
    """
    Computes the distance from grid to port using a pipeline from source point to river and then transporting along the river.
    Transition point is chosen as the point which minimizes the distance from source point to river using straight line distance.
    
    Input:
        - row(pandas series): row of dataframe. Each row represents a gridcell.
        - water_df(pandas dataframe): dataframe where each gridcell has river available.
        - gridsize(int): lenghth/width of each gridcell in km.
        - dict_id(dict): Keys are source points. Values are transition point ids.
        - dict_to_trans(dict): Keys are source points. Values are straight line distances from source point to transition points in km.
        - dict_from_trans(dict): Keys are source points. Values  are the distances along the rivers from transition point to port in km. 
    """
    id, x, y = row['id'], row['x'], row['y']
    water_df['pipe_dist'] = gridsize*np.sqrt((water_df['x']-x)**2 + (water_df['y']-y)**2) #Straight line/Euclidean distance
    min_to_trans = water_df['pipe_dist'].min() #distance from sourte to river
    min_to_trans_idx = water_df['pipe_dist'].idxmin()
    min_to_trans_id = water_df.loc[min_to_trans_idx, 'id'] # fetch id of transition points
    min_to_trans_id = int(min_to_trans_id)
    min_from_trans = water_df.loc[min_to_trans_idx, 'distance_water'] # Distance from transition point to port
    dict_id[id] = min_to_trans_id; dict_to_trans[id] = min_to_trans; dict_from_trans[id] = min_from_trans

def shortest_path_to_node(input_filename="Poland/Ze_points_5.0.csv", output_filename = "CSV_Distances.csv",id=7080, gridsize=5):
    """
    Compute shortest distances for various transportation methods and export the results in a CSV file.

    Input:
        -input_filename(str): filename of the CSV file with the data
        -output_filename(str): filename for the output CSV file
        -id(int): id of the point we want to travel to(the port)
        -gridsize(int): size of grid in km. Could be a float
    """
    #Initializing the dataframe
    data = pd.read_csv(input_filename)
    df = pd.DataFrame(data, columns=['id', 'xIndex', 'yIndex', 'BOOL_ROAD', 'BOOL_RAILWAY', 'BOOL_WATERCOURSE']) #extract the desired columns
    df.rename(columns = {'xIndex':'x', 'yIndex':'y', 'BOOL_ROAD':'road', 'BOOL_RAILWAY':'rail', 'BOOL_WATERCOURSE':'water'}, inplace = True) #change column names to something more convenient
    
    #add distances to port via road, rail, water from each gridcell
    graphs = {} # keys are the methods. values are the network for the given method of transportation
    for method in ['road', 'rail', 'water']:
        method_df = df.loc[df[method]] # extract gridcells with the method of transportation available
        G = nx.Graph()
        method_df.apply(init_network, axis=1, df=method_df, G=G, gridsize=gridsize) #Runs init_network for each row in method_df dataframe. Adds edges to the graph with weights
        graphs[method] = G # Storing the graphs
        distances = nx.single_source_dijkstra_path_length(G, id) # Computes the shortest distance from/to the node with the specified id. Output is a dictionary.
        distances = dict((int(key), value) for key,value in distances.items())
        col_name = 'distance_' + method
        df[col_name] = df['id'].map(distances) #Add a column with distances

    #Find the port/id gridcell
    port_node = df.loc[df['id']==id].values
    x, y = port_node[0,1:3] # x and y index for port node.
    #Creating new column with the straight-line distance from each gridcell to the port.
    df['straight_distance'] = np.sqrt((df['x']-x)**2 + (df['y']-y)**2)*gridsize 
    df = df.round({'straight_distance':2}) #rounding off to fewer digits for a nicer output

    #Computing the distances using two methods
    methods = [('road', 'water'), ('rail', 'water'), ('road', 'rail')]
    for method1, method2 in methods:
        method_df = df.loc[df[method1]] # extract the nodes with method1
        both_methods_df = method_df.loc[method_df[method2]]
        map_dict_trans_id = {} # dictionary with transition id
        map_dict_to_trans = {} # dictionary with distance from source gridcell to transition point
        map_dict_from_trans = {} # dictionary with distance from transition point to the goal/port gridcell
        G = graphs[method1] #access the graph of method1
        distances = nx.all_pairs_dijkstra_path_length(G) 
        df2 = pd.DataFrame(distances, columns=['id', 'dict']).astype({'id':int}) #Converts the dict to a dataframe
        df2.apply(multiple_paths, axis=1, both_method_df=both_methods_df,method2=method2, 
                  dict_id=map_dict_trans_id,dict_to_trans=map_dict_to_trans, dict_from_trans=map_dict_from_trans
        ) #Find the shortest path from each gridcell to port. multiple_paths applied to each row of df2
        #Adding columns
        col_name = '{}+{}_transition_id'.format(method1, method2)
        df[col_name] = df['id'].map(map_dict_trans_id)
        df = df.astype({col_name:'Int64'}) # We use Int64, because every other integer type doesn't work. Not sure between the difference of int64 and Int64. Doesn't work because of np.nan or np.inf values
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
    df.to_csv(output_filename, index=False)
    #It is possible to return the dataframe and graphs if wanted. Alternatively, we can just save it as files, as has been done and open those files in other functions

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

    #Modifying QGIS dataframe, till it looks nice
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
def make_contour(our_data_file='Fil_med_Avstand.csv', QGIS_data_file='Poland/distance_road_5.csv', method='road', multiplier=1.1, gridsize=5):
    """
    Creates a contour map for the relative error computed in error_analysis.

    Input:
        -our_data_file(str): CSV file produced by shortest_path_to_node
        -QGIS_data_file(str): CSV file with shortest distances computed by QGIS algorithm Shortest path from point to layer
        -method(str): transportation method. Alternatives: road/rail/water
        -multiplier(float): cost multiplier for our distances. This helps to deal with tortuosity of road for example.
        -gridsize(int): size of grid in km. Could be a float
    """
    error_df, mean_rel_error, rmse = error_analysis(our_data_file, QGIS_data_file, method, multiplier) #use only the error_df
    #error_df = error_df.loc[np.isfinite(error_df['rel_error'])] #removing nan from rel_error. Should already be done in error analysis
    #This step may be redundant for error_df
    #error_df = error_df.loc[np.isfinite(error_df['abs_error'])] #doing the same thing for abs_error, but I don't think that is necessary. If nan in abs_error then that should propagate to rel_error, as it uses abs_error. Also has been done in error_analysis.
    xmax = np.max(error_df['x'])
    ymax = np.max(error_df['y'])
    Z = np.full([ymax,xmax], None)
    #Find a quick way to fill up Z without double for loop.
    Z[error_df['y']-1, error_df['x']-1] = error_df['rel_error'] # fill up Z with relative errors. 
    plot_name = "relative_error_{}km_{}_{:.1f}_multiplier.png".format(gridsize, method, multiplier) # should depend on input
    plt.contourf(Z, origin='upper', levels = 10) #upper makes it interpret (0,0) as upper left corner.
    plt.colorbar()
    plt.xlabel("x index")
    plt.ylabel("y index")
    plt.title("relative error, gridsize:5km, multiplier:1.1, Transsport:road")
    plt.savefig(plot_name)
    plt.clf() #Clear the old figure

def error_analysis_multiple_grids(distance_filename='CSV_Distances.csv'):
    """
    Computes the mean relative error for one multiplier, but multiple gridsizes for the three transportation methods.
    Saves the results in a csv file.

    Input:
        - multiplier(float): cost multiplier
        - distance_filename(str): Name of the CSV file produced in shortest_path_to_node function
    """
    gridsizes = [i for i in range(5,51, 5)] # [5, 10, ..., 50]
    id_poland = {50:67, 45:86, 40:114, 35:146,30:192,25:278,20:437,15:760,10:1742, 5:7080} # keys are gridsizes, values are id of the port for the given gridsize.
    stats = np.zeros(shape=(len(gridsizes), 4))
    stats[:,0] = gridsizes
    for multiplier in np.linspace(1, 1.8, 9):
        for i, gridsize in enumerate(gridsizes):
            filename = 'Poland/Grid_Points_{:.1f}.csv'.format(gridsize) # Filename of the file with basic grid information from QGIS.
            shortest_path_to_node(filename, distance_filename, id_poland[gridsize], gridsize) # Det lages en fil som heter "CSV_Distances.csv"
            for j, method in enumerate(['road', 'rail', 'water']):
                distance_qgis_fn = "Poland/distance_new_{}_{:.1f}.csv".format(method, gridsize)
                error_df, mean_rel_error, rmse = error_analysis('CSV_Distances.csv',distance_qgis_fn,method,multiplier)
                stats[i,j+1] = mean_rel_error
        df = pd.DataFrame(stats, columns=['gridsize', 'road_mean_rel_error', 'rail_mean_rel_error', 'water_mean_rel_error'])
        df.to_csv("Error_Poland_multiplier_{:.1f}.csv".format(multiplier), index=False)

def error_analysis_multiplier(distance_filename='CSV_Distances.csv'):
    """
    For each gridsize, check what error different multipliers cause.

    Input:
        - distance_filename(str): CSV file name
    """
    #So what do we want to do? Do we want to create the error files, for each gridsize. Or how do we do it?
    gridsizes = [i for i in range(5,51, 5)] # [5, 10, ..., 50]
    id_poland = {50:67, 45:86, 40:114, 35:146,30:192,25:278,20:437,15:760,10:1742, 5:7080} # keys are gridsizes, values are id of the port for the given gridsize.
    stats = np.zeros(shape=(len(np.linspace(1, 1.8, 9)), 4))
    stats[:,0] = np.linspace(1, 1.8, 9)
    for i, gridsize in enumerate(gridsizes):
        filename = 'Poland/Grid_Points_{:.1f}.csv'.format(gridsize)
        shortest_path_to_node(filename, distance_filename, id_poland[gridsize], gridsize) # Det lages en fil som heter "Fil_med_Avstand.csv"
        for j, method in enumerate(['road', 'rail', 'water']):
            for idx, k in enumerate(np.linspace(1, 1.8, 9)):
                distance_qgis_fn = "Poland/distance_new_{}_{:.1f}.csv".format(method, gridsize)
                error_df, mean_rel_error, rmse = error_analysis(distance_filename,distance_qgis_fn,method,k)
                stats[idx, j+1] = mean_rel_error
        df = pd.DataFrame(stats, columns=['multiplier', 'road_mean_rel_error', 'rail_mean_rel_error', 'water_mean_rel_error'])
        df.to_csv("Error_Poland_{:.1f}km.csv".format(gridsize), index=False)




#shortest_path_to_node("Poland/Grid_Points_50.0.csv", "CSV_Distances.csv",id=67, gridsize=50)
#make_contour()
error_analysis_multiple_grids()
error_analysis_multiplier()


    

