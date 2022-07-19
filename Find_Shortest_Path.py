import numpy as np
import matplotlib.pyplot as plt
import csv

from pkg_resources import to_filename

# Create Class for points
class Points:
    def __init__(self, id, x, y, hasRoad=False, hasRail=False, hasWater=False):
        """
        Initialize the variables hasRoad(bool), hasRail(bool), hasWater(bool), gridval(tuple), id(int).
        Neighbor(lst) is a list of the neighboring gridcells, including the diagonal, horizontal and vertical neighbors.
        Neighbor_road/rail/water is a subset of the neighbor list and contains the neighbor iff both cells have 
        the transportation system available. 
        """
        self.hasRoad = hasRoad
        self.hasRail = hasRail
        self.hasWater = hasWater
        self.gridval = (x, y)
        self.id = id
        self.neighbor = []
        self.neighbor_road = []
        self.neighbor_rail = []
        self.neighbor_water = []

    def __str__(self):
        """
        The string that gets printed if a gridcell is printed
        """
        return 'id={}, grid=({},{}), hasRoad={}, hasRail={}, hasWater={}'.format(self.id, self.gridval[0], self.gridval[1], self.hasRoad, self.hasRail, self.hasWater)

def define_neighbors(point_list):
    """
    Define the neighbors for each point, i.e., fills up the neighbor list for each point.

    Input:
        - point_list(lst): list of instances of the Points class.
    """
    #The first two if-statements could be excahnged using the distance_taxi_cab, while checking if the distance is 1.
    for Point in point_list:
        x, y = Point.gridval
        for Candidate_Point in point_list:
            x_cand, y_cand = Candidate_Point.gridval
            if x == x_cand and (abs(y - y_cand) == 1): #Checks for the vertical neighbors
                Point.neighbor.append(Candidate_Point)
            elif y_cand == y and (abs(x - x_cand) == 1): # Checks for the horizontal neighbors
                Point.neighbor.append(Candidate_Point)
            elif (abs(x - x_cand) == 1) and (abs(y - y_cand) == 1): # Checks for the diagonal neighbor.
                Point.neighbor.append(Candidate_Point)

def read_CSV(datafile):
    """
    Read CSV file of the Centroids, (Tyskland_xxkm_grid.csv) and add them as point class objects. Then
    store the points in a list and return the list.

    Input:
        - datafile(str): the file with the centroid data as a csv file

    Output:
        - (lst): the elements are the Points class objects
    """
    dict = {'True':True, 'False':False}
    with open(datafile) as reader:
        lst = []
        reader.readline()
        lines = reader.readlines()
        prev_id = 0
        for line in lines:
            words = line.strip().split(',')
            id = int(words[0])
            xIndex = int(words[1])
            yIndex = int(words[2])
            hasRoad = dict[words[6]] #It could be nice to check that the values here are actually 0 and 1
            hasRail = dict[words[7]]
            hasWater = dict[words[8]]
            #Would be nice to give these Points but whatever I guess...
            if prev_id != id:
                Point = Points(id, xIndex, yIndex, hasRoad, hasRail, hasWater)
                lst.append(Point)
            prev_id = id
    return lst

def distance_taxi_cab(P1, P2):
    """
    Assume quadratic(same size in x and y) grid.
    Return the taxicab metric distance.

    Input:
        - P1(Points class object)
        - P2(Points class object)
    
    Output:
        - (int/float): The sum of the vertical and horizontal distance between P1 and P2.
    """
    x1, y1 = P1.gridval 
    x2, y2 = P2.gridval
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)

    return dx + dy

def neighbor_connection(point_list):
    """
    Define the neighbor points that are connected by the specified method of transportation.

    Input:
        - point_list(lst): list of Point class objects
    
    Output: 
        - Nada. Just fills up the neighbor_road/rail/water lists based on the chosen method.
                Rule: Both the from and to node has to have the specified mode of transportation.
    """
    #First check that define_neighbor has been run.
    if not point_list[0].neighbor: #If neighbor list is empty then
        define_neighbors(point_list)

    dict = {"hasRoad":"neighbor_road", "hasRail":"neighbor_rail", "hasWater":"neighbor_water"} # used to access the neighbor_road/rail/water lists. 
    for method in dict.keys():
        for Point in point_list:
            if Point.__dict__[method]: #Checks whether the Point.hasRoad/Rail/Water is true. 
                for Neighbor_Point in Point.neighbor:
                    if Neighbor_Point.__dict__[method]: # Checks if the neighbor has the method of transportation available. Same as above 
                        if distance_taxi_cab(Point, Neighbor_Point)==1: #Checks if the Neighbor_Point is the vertical or horizontal neighbor. This does not catch the diagonal neighbors
                            Point.__dict__[dict[method]].append(Neighbor_Point) # This appends the neighbor point to the relevant transporation system neighbors list
                        x1, y1 = Point.gridval; x2, y2 = Neighbor_Point.gridval
                        if (abs(x1 - x2) == 1) and (abs(y1 - y2) == 1): # Checks for the diagonal neighbor.
                            intersection = list(set(Neighbor_Point.neighbor) & set(Point.neighbor)) # Finds the common vertical and horizontal neighbors
                            for intersect_point in intersection:
                                if intersect_point.__dict__[method]: # Checks whether the vertical and horizontal neighbors shared by the Point and Neighbor_Point has the wanted mode of transportion. 
                                    Point.__dict__[dict[method]].append(Neighbor_Point)
                                    break
            
def path_points(P1, P2, point_list, method="hasRoad", multiplier=1.2):
    """
    Perform a BFS(breadth first search), where we prioritize the diagonal paths rather than the vertical/horizontal. 
    This means that we move diagonally till we reach the right x- or y-value and then go horizontally or vertically to P2.

    Input:
        - P1(Points class object): start point
        - P2(Points class object): end point
        - point_list(lst): List containing the controids as Points class objects
        - method(str): hasRoad, hasRail, hasWater
        - multiplier(float): cost multiplier, needed due the tortuosity
    
    Output:
        - (float/bool): If there exists a path, then the cost is returned. If no path exists, then return False
        - (lst): If path exists returns the path beginning at P2 and ending at P1. If no path exists returns empty list. 
                 Also adds method to the path for some retarded reason.... Can we remove it or will it be useful later on, when we implement multiple methods.
    """
    dict = {"hasRoad":"neighbor_road", "hasRail":"neighbor_rail", "hasWater":"neighbor_water"}
    pred = {P1:0} #For each discovered node we store which node discovered that node. For P1 we set the predecessor to 0.
    Layer0 = [P1] #Layer 0
    explored = [P1] #Explored nodes
    Layers = [Layer0] #This will be a list of lists, i.e. [L_0, L_1, L_2, ..., L_n], where L_i is the i-th Layer.
    layerNo = 0 #layer number
    while Layers[layerNo]: #while the layers are nonempty, we can go deeper
        Layer = [] #New layer
        for v in Layers[layerNo]: # Parsing through the nodes in a layer
            for w in v.__dict__[dict[method]]: #Parsing through the neighbor_road/rail/water lists
                if not w in explored: #Checks whether the node has been visited before or not
                    Layer.append(w)
                    explored.append(w)
                    pred[w] = v
                if w == P2: #Have found a path
                    path = [(w, method)] # Why do we include method in here?? 
                    key = w
                    cost_approx = 0 
                    while pred[key] != 0:
                        path.append((pred[key], method))
                        if distance_taxi_cab(key, pred[key]) == 1:
                            cost_approx += 1
                        else:
                            cost_approx += np.sqrt(2)
                        key = pred[key]
                    return cost_approx*multiplier, path
        sort_func = lambda Point : distance_taxi_cab(Point, P2) # Sort function to sort the layer by the distance to our finish point by the taxi-cab metric
        Layer.sort(key = sort_func)
        Layers.append(Layer)        
        layerNo += 1
    return False, []


def distance_func(P1, point_list, method="hasRoad", multiplier=1.2, gridsize=30):
    """
    Computes the distance from the point P1 to all other points in point_list. 
    
    Input:
        - P1(Points class object): the source point
        - point_list(lst): list containing all the centroids as Points class objects
        - method(str): hasRoad, hasRail, hasWater
        - multiplier(float): cost multiplier
        - gridsize(float): grid size in km

    Output:
        - (dict): Returns a dict where the keys are the centroids as Points class objects and the values are the distances between P1 and that point in km(?)
    """
    dict = {}
    for point in point_list:
        cost_approx, path = path_points(P1, point, point_list, method, multiplier)
        if cost_approx != 0: #Basically not equal to False
            dict[point] = cost_approx*gridsize 
        else:
            dict[point] = None # If there is no path store None
    return dict

def read_dist(filename):
    """
    Reades the distance files that are generated from QGIS. Names as "Avstand_fil_Tyskland_....csv".
    The bool values in these files are stored as 1 or 0. So these csv files are not quite like the previous because not sure why. But they aint used so really doesnt matter
    So not sure if these functions are quite the same. 

    Input:
        -filename(str): csv file name as a string.
    
    Output:
        -(lst): list of distances for each point. The numbering of the points is the same here as in the other files, so will be no issue retrieving these points. 
                Distances are measured in metres. So there is a discrepancy in the units. 
    """
    lst = []
    with open(filename) as reader:
        reader.readline() #Skip the header line
        lines = reader.readlines()
        prev_id = 0
        for line in lines:
            words = line.split(',') #Is it okay not to strip?
            id = int(words[0])
            if prev_id != id:
                if len(words) != 14:
                    lst.append(None)
                else:
                    cost = float(words[-1]) #distance in meters
                    lst.append(cost)
            prev_id = id
    return lst

def error_analysis(P1, point_list, filename="Avstand_fil_Tyskland.csv", method="hasRoad", multiplier=1, gridsize=30):
    """
    Finds the error between our method and the distances in QGIS from the shortest path algorithm. Note that in Qgis there is no cost for snapping to grid. We might want/need that.
    We store the root mean square error, relative error, and the absolute errors.

    Input:
        - P1(Points class object): the source point
        - point_list(lst): list containing all the centroids as Points class objects
        - filename(str): The csv file that contains the precalculated distances
        - method(str): hasRoad, hasRail, hasWater
        - multiplier(float): cost multiplier
        - gridsize(float): grid size in km
    
    Output:
        - (float): root mean square error
        - (dict): relative error dict. Keys are the centroids as Points class objects and the values are the relative errors between approximated distances and distances from QGIS.
        - (lst): diff_list. The absolute errors in km. This is not really navigable, as you skip over entries that are None.
    """
    qgis_dist_list = read_dist(filename) 
    our_dist_dict = distance_func(P1, point_list, method, multiplier, gridsize)
    dist_arr = np.array(list(our_dist_dict.items())) # Convert dict to arrayt 
    our_dist_list = dist_arr[:,1]
    diff_list = []
    rel_error_dict = {}
    for i in range(len(qgis_dist_list)): #Lengden er ikke problemet her
        if qgis_dist_list[i] == None or our_dist_list[i] == None:
            continue
        else:
            diff = qgis_dist_list[i]/1000 - our_dist_list[i] # Note this line that we divide by 1000 to convert to km. This will so fuck up everything at some point.
            diff_list.append(diff)
            err = diff/(qgis_dist_list[i]/1000)*100
            rel_error_dict[dist_arr[i,0]] = err
    diff_arr = np.asarray(diff_list)
    rmse = np.sqrt(np.sum(diff_arr**2)/np.size(diff_arr))
    return rmse, rel_error_dict, diff_list

def write_csv_error(from_filename, to_filename, P1, point_list, method="hasRoad",gridsize=30):
    """
    Writes the error computed in error_analysis to a csv file of the form "feil_Tyskland_....csv

    Input:
        - from_filename(str): The csv file that contains the precalculated distances
        - to_filename(str): The csv file name that you want to write the data into
        - P1(Points class object): the source point
        - point_list(lst): list containing all the centroids as Points class objects
        - method(str): hasRoad, hasRail, hasWater
        - gridsize(float): grid size in km
    """
    data = []
    for i in np.linspace(1, 1.8, 9):#[1, 1.1, ..., 1.8]
        rmse, rel_error_dict, diff_list = error_analysis(P1, point_list, from_filename, method, i, gridsize)
        rel_error = np.array(list(rel_error_dict.items()))[:,1]
        str = '{:.1f}, {:.2f}, {:.2f}, {:.2f}, {:.2f}'.format(i, rmse, np.mean(np.abs(rel_error)), np.max(np.abs(rel_error)), np.max(np.abs(diff_list)))
        row = str.split(',')
        data.append(row)
    #Extra things taken out of for loop to show what happens. Not essential
    rmse, rel_error_dict, diff_list = error_analysis(P1, point_list, from_filename, method, 1.2, gridsize)
    rel_error = np.array(list(rel_error_dict.items()))[:,1]
    abs_rel_err = np.abs(rel_error)
    plt.hist(abs_rel_err)
    plt.show()
    for i in range(len(rel_error)):
        if rel_error[i] > 50 or rel_error[i]<-50:
            print(i, rel_error[i], diff_list[i])
    header = ['multiplier','Root_mean_square_error', 'mean_relative_error', 'max_relative_error', 'max_absolute_error']
    """ with open(to_filename, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data) """

def make_contour(P1, point_list, filename="Avstand_til_Tyskland.csv", method="hasRoad", gridsize = 30):
    """          
    Input:
        - P1(Points class object): the source point
        - point_list(lst): list containing all the centroids as Points class objects
        - filename(str): The csv file that contains the precalculated distances
        - method(str): hasRoad, hasRail, hasWater
        - gridsize(float): grid size in km 
    """
    #Find the max index of x and y
    xmax = 0; ymax = 0
    for Point in point_list:
        xcand, ycand = Point.gridval
        if xcand > xmax:
            xmax = xcand
        if ycand > ymax:
            ymax = ycand

    Z = np.full([ymax, xmax], None)#Note that no. of rows corresponds to the y values, while the no. of columns correspond to x 
    for i in np.linspace(1, 1.8, 9): # i values are the multipliers
        rmse, rel_error_dict, diff_list = error_analysis(P1,point_list,filename, method, i, gridsize)
        rel_arr = np.array(list(rel_error_dict.items()))
        for Point, rel_err in rel_arr:
            x,y = Point.gridval
            Z[y-1,x-1]= rel_err #Indexing starts at 0 so have to subtract one.
        #Plot and save contours. Q: Do we want them as pdf or pgn files?
        """ plot_name = "plots/relative_error_{}km_{}_{:.1f}_multiplier.pdf".format(gridsize, method, i)
        plt.contourf(Z, origin='upper', levels = 10)
        plt.colorbar()
        plt.xlabel("x index")
        plt.ylabel("y index")
        plt.title("relative error, gridsize:{}km, multiplier:{:.1f}, Transsport:{}".format(gridsize, i, method))
        plt.savefig(plot_name)
        plt.clf() #Clear the old figure """
    
def all_of_it(gridsizes, methods):
    """
    Computes and writes the error to a csv file. Also makes and saves the contours
    
    Input:
        - gridsizes(lst): list of gridsizes of interest
        - methods(lst): list of names of the transportation methods to be analyzed. Options: hasRoad, hasRail, hasWater
    """
    idx_road_rail = {20: 272, 30:136, 50:53} #These should probably be sent in as arguments
    idx_water = {20: 71, 30:40, 50:9} #These should probably be sent in as arguments
    idx_method = {"hasRoad":idx_road_rail, "hasRail":idx_road_rail, "hasWater":idx_water}
    method_dict = {"hasRoad": "Road", "hasRail": "Rail", "hasWater":"Water"}
    for gridsize in gridsizes:
        for method in methods:
            centroids_filename = "csv_filer/Tyskland_" + gridsizes + "km_grid.csv" #filename for the file with the centroid data
            Points = read_CSV(centroids_filename)
            define_neighbors(Points)
            neighbor_connection(Points)
            Qgis_dist_filename = "csv_filer/Avstand_fil_Tyskland_" + gridsize + "km_" + method_dict[method] + ".csv" # road should be method
            error_filename = "csv_filer/feil_filer/feil_Tyskland_" + gridsize + "km_" + method_dict[method] + ".csv"
            idx_point = idx_method[method][gridsize]
            write_csv_error(Qgis_dist_filename, error_filename, Points[idx_point], Points,method,gridsize) #Points has to be slightly rearranged
            make_contour(Points[idx_point], Points, Qgis_dist_filename, method, gridsize)

if __name__ == '__main__':
    filename = "csv_filer/Tyskland_50km_grid.csv"
    Points = read_CSV(filename)
    define_neighbors(Points)
    neighbor_connection(Points)
    print("neighbors")
    """ for neighbor in point.neighbor:
        print(neighbor)
    print("\n \n road connection")
    for neighbor in point.neighbor_road:
        print("rlly?", neighbor) """
    for point in Points:
        if len(point.neighbor_road) == 0:
            print("Ze Point", point)
            for neighbor in point.neighbor:
                print(neighbor)
        if len(point.neighbor) == 9:
            print("The point itself:", point)
            for neighbor in point.neighbor:
                print(neighbor)

        #print(len(point.neighbor), len(point.neighbor_road))
