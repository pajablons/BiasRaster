import arcpy
from osgeo import gdal
import math
import numpy
from datetime import datetime

arcpy.env.workspace = r"C:\Users\pajab\Documents\MSGIS\GEOG653\SampBias\SampBias.gdb"
arcpy.env.overwriteOutput = True
gdal.AllRegister()

pointCounts = {
    "Wetlands"      : 104364.0,
    "Water"         : 6615.0,
    "Industrial"    : 28.0,
    "Very Low Density Residential" : 2035.0,
    "Low Density Residential" : 11967.0,
    "Forest"        : 37653.0,
    "Agriculture"   : 70613.0,
    "Institutional" : 429.0,
    "Transportation": 0.0,
    "Commercial"    : 76.0,
    "Medium Density Residential" : 110.0,
    "Barren"        : 0.0,
    "High Density Residential"   : 0.0,
    "Other"         : 0.0
}

rp_layer_map = {
    "Wetlands"      : "RP_Wetlands",
    "Water"         : "RP_Water",
    "Industrial"    : "RP_Industrial",
    "Very Low Density Residential" : "RP_VL_Residential",
    "Low Density Residential" : "RP_LD_Residential",
    "Forest"        : "RP_Forest",
    "Agriculture"   : "RP_Agriculture",
    "Institutional" : "RP_Institutional",
    "Transportation": "RP_Transport",
    "Commercial"    : "RP_Commercial",
    "Medium Density Residential" : "RP_MD_Residential"
}

lu_code_map = {
    60  :   "Wetlands",
    50  :   "Water",
    15  :   "Industrial",
    191 :   "Very Low Density Residential",
    11  :   "Low Density Residential",
    42  :   "Forest",
    21  :   "Agriculture",
    16  :   "Institutional",
    14  :   "Commercial",
    12  :   "Medium Density Residential"
}

road_cache = {}
bldg_cache = {}
cache_range = 10

bison_dataset = "Observations_Proj"

lu_layer_map = {}
for key in rp_layer_map.keys():
    name = "in_memory/{}".format(key)
    arcpy.MakeFeatureLayer_management(bison_dataset, name, "Descriptio = '{}'".format(key))
    lu_layer_map[key] = name
    road_cache[key] = {}
    bldg_cache[key] = {}

def countWithinDistance(pointLayer, distance, distColumn):
    selection = arcpy.SelectLayerByAttribute_management(pointLayer, "NEW_SELECTION", "{} < {}".format(distColumn, distance))
    count = int(arcpy.GetCount_management(selection)[0])
    return count

def _calcBias(distance, landType, cache, distCol):
    pointSelection = lu_layer_map[landType]
    N = pointCounts[landType]
    pd, nd = -1, -1
    if distance in cache[landType].keys():
        return cache[landType][distance]
    else:
        pd = (1 + countWithinDistance(rp_layer_map[landType], distance, distCol)) / (N + 2)
        nd = (1 + countWithinDistance(pointSelection, distance, distCol))
        numer = nd - pd * N 
        denom = math.sqrt(pd * (1.0 - pd) * N)
        ret = numer / denom
        cache[landType][distance] = ret
        return ret

def calcBiasRoad(distance, landType):
    return _calcBias(distance, landType, road_cache, "Road_DIST")

def calcBiasBldg(distance, landType):
    return _calcBias(distance, landType, bldg_cache, "Bldg_DIST")

driver = gdal.GetDriverByName("GTiff")
road_dist_ds = gdal.Open("road_distance_raster.tiff")
bldg_dist_ds = gdal.Open("bldg_distance_raster.tiff")
lulc_ds = gdal.Open("lulc_raster.tiff")
roadBias = driver.CreateCopy("road_bias_raster.tiff", road_dist_ds, strict = 0)
bldgBias = driver.CreateCopy("bldg_bias_raster.tiff", road_dist_ds, strict = 0)

roadBand = roadBias.GetRasterBand(1)
bldgBand = bldgBias.GetRasterBand(1)

road_dist_arr = road_dist_ds.GetRasterBand(1).ReadAsArray()
bldg_dist_arr = bldg_dist_ds.GetRasterBand(1).ReadAsArray()
lulc_arr = lulc_ds.GetRasterBand(1).ReadAsArray()
road_arr = numpy.copy(road_dist_arr)
bldg_arr = numpy.copy(road_dist_arr)

print(datetime.now().strftime("%H:%M:%S"))
counter = 0

for x in range(numpy.size(road_dist_arr, 0) - 1):
    for y in range(numpy.size(road_dist_arr, 1) - 1):
        if not lulc_arr[x][y] in lu_code_map.keys():
            road_arr[x][y] = 0
            bldg_arr[x][y] = 0
        else:
            road_distance = cache_range + cache_range * round(road_dist_arr[x][y] / cache_range)
            bldg_distance = cache_range + cache_range * round(bldg_dist_arr[x][y] / cache_range)
            road_arr[x][y] = calcBiasRoad(road_distance, lu_code_map[lulc_arr[x][y]])
            bldg_arr[x][y] = calcBiasBldg(bldg_distance, lu_code_map[lulc_arr[x][y]])
        counter = counter + 1
        print(counter)
    print(datetime.now().strftime("%H:%M:%S"))

roadBand.WriteArray(road_arr, 0, 0)
roadBand.FlushCache()
roadBand.SetNoDataValue(-99)

bldgBand.WriteArray(bldg_arr, 0, 0)
bldgBand.FlushCache()
bldgBand.SetNoDataValue(-99)