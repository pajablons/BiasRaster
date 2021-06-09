from osgeo import gdal, ogr, osr
import math
import numpy as np
import sys
import matplotlib.pyplot as plt

lu_code_map = {
    60  :   "Wetlands",
    50  :   "Water",
#    15  :   "Industrial",
    191 :   "Very Low Density Residential",
    11  :   "Low Density Residential",
    42  :   "Forest",
    21  :   "Agriculture",
    16  :   "Institutional",
#    14  :   "Commercial",
#    12  :   "Medium Density Residential"
}

cache_range = 50

gdal.AllRegister()
driver = gdal.GetDriverByName("GTiff")

road_dist_ds = gdal.Open("road_distance_raster.tiff")
bldg_dist_ds = gdal.Open("bldg_distance_raster.tiff")
lulc_ds = gdal.Open("lulc_raster.tiff")
road_bias_ds = gdal.Open("road_bias_raster.tiff")
bldg_bias_ds = gdal.Open("bldg_bias_raster.tiff")

road_dist_arr = road_dist_ds.GetRasterBand(1).ReadAsArray()
bldg_dist_arr = bldg_dist_ds.GetRasterBand(1).ReadAsArray()
lulc_arr = lulc_ds.GetRasterBand(1).ReadAsArray()
road_bias_arr = road_bias_ds.GetRasterBand(1).ReadAsArray()
bldg_bias_arr = bldg_bias_ds.GetRasterBand(1).ReadAsArray()

road_dists = {}
road_biases = {}
bldg_dists = {}
bldg_biases = {}
for key in lu_code_map.keys():
    road_dists[key] = []
    road_biases[key] = []
    bldg_dists[key] = []
    bldg_biases[key] = []

for x in range(np.size(lulc_arr, 0)):
    for y in range(np.size(lulc_arr, 1)):
        lu_code = lulc_arr[x][y]
        if not lu_code in lu_code_map.keys(): continue

        bldg_distance = cache_range + cache_range * round(bldg_dist_arr[x][y] / cache_range)
        road_distance = cache_range + cache_range * round(road_dist_arr[x][y] / cache_range)

        if not bldg_distance in bldg_dists[lu_code]:
            bldg_dists[lu_code] = np.append(bldg_dists[lu_code], [bldg_distance])
            bldg_biases[lu_code] = np.append(bldg_biases[lu_code], bldg_bias_arr[x][y])

        if not road_distance in road_dists[lu_code]:
            road_dists[lu_code] = np.append(road_dists[lu_code], [road_distance])
            road_biases[lu_code] = np.append(road_biases[lu_code], road_bias_arr[x][y])

def getRSE(rss, n):
    return math.sqrt(rss / (n - 2))

fig = plt.figure()
ax_big = fig.add_subplot(111)
axis = [fig.add_subplot(211), fig.add_subplot(212)]
tmpRange = np.arange(1200)
bldgRange = np.arange(600)
for key in lu_code_map.keys():
    (coeffs, rss, _, _, _) = np.polyfit(road_dists[key], road_biases[key], 3, full=True)
    rse = getRSE(rss[0], np.size(road_dists[key]))
    axis[0].plot(tmpRange, (coeffs[0] * (tmpRange**3)) + (coeffs[1] * (tmpRange**2)) + (coeffs[2] * tmpRange) + coeffs[3], label=lu_code_map[key])
    axis[0].set_title("Road Biases")

    (coeffs, rss, _, _, _) = np.polyfit(bldg_dists[key], bldg_biases[key], 3, full=True)
    print(rse)
    axis[1].plot(bldgRange, coeffs[0] * bldgRange**3 + coeffs[1] * bldgRange**2 + coeffs[2] * bldgRange + coeffs[3], label=lu_code_map[key])
    axis[1].set_title("Building Biases")

axis[0].legend()
axis[1].legend()
ax_big.set_xlabel('Distance from nearest access feature (meters)')
ax_big.set_ylabel('Bias')
for val in ['top', 'bottom', 'left', 'right']: ax_big.spines[val].set_color('none')
ax_big.tick_params(labelcolor='w', top=False, bottom=False, left=False, right=False)
plt.show()
