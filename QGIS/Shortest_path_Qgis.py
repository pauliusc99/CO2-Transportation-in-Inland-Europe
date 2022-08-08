import processing

# Need Road, rail and river layer. The river of interest should be extracted
# Need area of interest

# Script to generate grid over AOI for different gridsizes and to compute distances from each gridcell to the port gridcell.

gridsizes = [50000, 45000, 40000, 35000, 30000, 25000, 20000, 15000, 10000, 5000] # stepsize of the grid


#Reprojected transportation systems to EPSG:3035 - ETRS89-extended / LAEA Europe
road_layer1 = QgsProject.instance().mapLayersByName("RoadL")[0] #Bruk extracted, alternativ reprojected
rail_layer1 = QgsProject.instance().mapLayersByName("RailrdL")[0] #Bruk extracted, alternativ reprojected
water_layer1 = QgsProject.instance().mapLayersByName("Wisla")[0]

#Reprojecting to a projection with metric units
result1 = processing.run('native:reprojectlayer', {'INPUT': road_layer1, 'TARGET_CRS':'EPSG:3035', 'OUTPUT':'memory:Reprojected'})
road_layer1 = result1['OUTPUT']

result2 = processing.run('native:reprojectlayer', {'INPUT': rail_layer1, 'TARGET_CRS':'EPSG:3035', 'OUTPUT':'memory:Reprojected'})
rail_layer1 = result2['OUTPUT']

result3 = processing.run('native:reprojectlayer', {'INPUT': water_layer1, 'TARGET_CRS':'EPSG:3035', 'OUTPUT':'memory:Reprojected'})
water_layer1 = result3['OUTPUT']

AOI = QgsProject.instance().mapLayersByName("AOI")[0] #Area of interest

#Need to clip by extent
result = processing.runAndLoadResults("native:extractbyextent", {'INPUT': road_layer1,'EXTENT': AOI.extent(),'CLIP':False,'OUTPUT':'memory:Extracted'})
road_layer1 = result['OUTPUT']

result = processing.runAndLoadResults("native:extractbyextent", {'INPUT': rail_layer1,'EXTENT': AOI.extent(),'CLIP':False,'OUTPUT':'memory:Extracted'})
rail_layer1 = result['OUTPUT']


#Kan hende vi må kjøre alt dette på nytt siden vi har byttet road_layer. Tror vi brukte originalfilen som har med for mange gater.
for i in gridsizes:
    print("Creating grid {}km".format(i/1000))
    centroids_csv_file = 'C:/Users/pauliusc/OneDrive - SINTEF/Desktop/Kodemm/Poland/Grid_Points_{}.csv'.format(i/1000) #File to save the data to
    params = {'areaofinterest': AOI, 'horizontalspacing': i, 'railwaylayer': rail_layer1, 'roadlayer':road_layer1, 'watercourselayer':water_layer1, 
                'Save Attributes:Save Attributes as CSV_1:Centroid Data to CSV': centroids_csv_file, 'native:clip_1:Clipped Quadratic Grid':'TEMPORARY_OUTPUT',
                'native:deletecolumn_1:Finalized centroids':'TEMPORARY_OUTPUT'}
    processing.runAndLoadResults("model:create_grid_with_centroids", params) # Running our model
    #Renaming the output layer
    point_layer = QgsProject.instance().mapLayersByName("Finalized centroids")[0]
    point_layer.setName("Finalized_centroids_{}".format(int(i/1000)))


#Now we need to implement a shortest path 
layers = [road_layer1, rail_layer1, water_layer1]
dict = {road_layer1:"road", rail_layer1:"rail", water_layer1:"water"}
dict_id = {5:7080, 10:1742, 15:760, 20:437, 25:278, 30:192, 35:146, 40:114, 45:86, 50:67} #key gridsize, value: id of the gridcell with the port
for layer in layers:
    for gridsize in gridsizes:
        gridsize = gridsize / 1000 # change the units from m to km
        print("creating distance for {}, {}km".format(dict[layer], gridsize))
        point_layer = QgsProject.instance().mapLayersByName("Finalized_centroids_{}".format(int(gridsize)))[0] #Accessing the point layer

        point_layer.selectByExpression('"id" = {}'.format(dict_id[int(gridsize)])) # Choosing the right point in the grid
        selection = point_layer.selectedFeatures() 
        if selection:
            point = selection[0]
        else:
            print("selection went to hell, where them points at ???")
        csv_file = 'C:/Users/pauliusc/OneDrive - SINTEF/Desktop/Kodemm/Poland/distance_new_' + dict[layer] + '_' + str(gridsize) + '.csv'
        point = point.geometry().asPoint() #Get the coordinates of the point
        point = '{},{}'.format(point[0], point[1])
        print(point)
        #Nå er alt i LEAE CRS EPGS 3035, this has units of meters. Hence tolerence is now in meters
        inputs = {'INPUT':layer,'STRATEGY':0,'DIRECTION_FIELD':'','VALUE_FORWARD':'','VALUE_BACKWARD':'','VALUE_BOTH':'','DEFAULT_DIRECTION':2,
                'SPEED_FIELD':'','DEFAULT_SPEED':50,'TOLERANCE':1500,'START_POINTS':point_layer,'END_POINT':point,'OUTPUT':csv_file
        }
        processing.run("native:shortestpathlayertopoint", inputs)





