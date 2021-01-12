import numpy as np
import os
from datetime import datetime
from pprint import pprint
from pysteps import io, nowcasts, rcparams
from pysteps.motion.lucaskanade import dense_lucaskanade
from pysteps.postprocessing.ensemblestats import excprob
from pysteps.utils import conversion, transformation
from pysteps.visualization import plot_precip_field
from pysteps.visualization import animations

# Set nowcast parameters
n_ens_members = 10
n_leadtimes = 12
data_source = rcparams.data_sources["ewr"]

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
# Find the radar files in the archive
fns = io.find_by_date(
    date, root_path, path_fmt, fn_pattern, fn_ext, timestep, num_prev_files=6
)

# Read the data from the archive
importer = io.get_method(importer_name, "importer")
R, _, metadata = io.read_timeseries(fns, importer, **importer_kwargs)

# Convert to rain rate
R, metadata = conversion.to_rainrate(R, metadata)

# Upscale data to 2 km to limit memory usage
# R, metadata = dimension.aggregate_fields_space(R, metadata, 2000)

# Plot the rainfall field
plot_precip_field(R[-1, :, :], geodata=metadata)

# Log-transform the data to unit of dBR, set the threshold to 0.1 mm/h,
# set the fill value to -15 dBR
R, metadata = transformation.dB_transform(R, metadata, threshold=0.1, zerovalue=-15.0)

# Set missing values with the fill value
R[~np.isfinite(R)] = -15.0

# Nicely print the metadata
pprint(metadata)

# Estimate the motion field
V = dense_lucaskanade(R)
# The STEPS nowcast
nowcast_method = nowcasts.get_method("steps")
R_f = nowcast_method(
    R[-3:, :, :],
    V,
    n_leadtimes,
    n_ens_members,
    n_cascade_levels=6,
    R_thr=-10.0,
    kmperpixel=2.0,
    timestep=timestep,
    noise_method="nonparametric",
    vel_pert_method="bps",
    mask_method="incremental",
    num_workers=5,
    fft_method='pyfftw',
    domain='spectral'
)

# Back-transform to rain rates
R_f = transformation.dB_transform(R_f, threshold=-10.0, inverse=True)[0]

# Compute exceedence probabilities for a 0.5 mm/h threshold
P = excprob(R_f[:, -1, :, :], 0.5)

# Plot the motion field
animations.animate(R, nloops=1, R_fct=R_f, timestep_min=5, motion_plot='quiver', geodata=None, UV=V, prob_thr=5,
                   type='prob', colorscale='IRIS', units='mm/h', colorbar=True, plotanimation=False, savefig=True,
                   fig_format='png', path_outputs='/usr/iris_data/from_PYSTEPS/')
