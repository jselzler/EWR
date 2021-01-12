from datetime import datetime
import numpy as np
import os
from pprint import pprint
from pysteps import io, motion, nowcasts, rcparams
from pysteps.utils import conversion, transformation
from pysteps.visualization import animations

data_source = rcparams.data_sources["ewr"]
n_leadtimes = 12

# Load data from source location
root_path = data_source["root_path"]
path_fmt = data_source["path_fmt"]
fn_pattern = data_source["fn_pattern"]
fn_ext = data_source["fn_ext"]
importer_name = data_source["importer"]
importer_kwargs = data_source["importer_kwargs"]
timestep = data_source["timestep"]

# get timestamp of latest file in directory
files = os.listdir(root_path)
latest_file = files[0]
for key in files:
    if os.path.getctime(root_path + "/" + key) > os.path.getctime(root_path + "/" + latest_file):
        latest = key
currentYear = datetime.now().year
year_index = latest.find(str(currentYear))
date = datetime.strptime(latest[year_index:year_index+12], "%Y%m%d%H%M")

# Find the input files from the archive
fns = io.archive.find_by_date(
    date, root_path, path_fmt, fn_pattern, fn_ext, timestep, num_prev_files=6
)

# Read the radar composites
importer = io.get_method(importer_name, "importer")
R, _, metadata = io.read_timeseries(fns, importer, **importer_kwargs)

# Convert to rain rate
R, metadata = conversion.to_rainrate(R, metadata)

# Store the last frame for plotting it later later
R_ = R[-1, :, :].copy()

# Log-transform the data to unit of dBR, set the threshold to 0.1 mm/h,
# set the fill value to -15 dBR
R, metadata = transformation.dB_transform(R, metadata, threshold=0, zerovalue=-15.0)

# Nicely print the metadata
pprint(metadata)

# Estimate the motion field with Lucas-Kanade
oflow_method = motion.get_method("LK")
V = oflow_method(R[-3:, :, :])

# Extrapolate the last radar observation
extrapolate = nowcasts.get_method("extrapolation")
R[~np.isfinite(R)] = metadata["zerovalue"]
R_f = extrapolate(R[-1, :, :], V, n_leadtimes)

# Back-transform to rain rate
R_f = transformation.dB_transform(R_f, threshold=0.1, inverse=True)[0]

# Plot the motion field
animations.animate(R, nloops=1, R_fct=R_f, timestep_min=5, motion_plot='quiver', geodata=None, UV=V,
                   colorscale='IRIS', units='mm/h', colorbar=True, plotanimation=False, savefig=True,
                   fig_format='png', path_outputs='/usr/iris_data/from_PYSTEPS/')
