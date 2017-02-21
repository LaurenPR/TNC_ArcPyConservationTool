# TNC_ArcPyConservationTool
Python script for GIS that provides a ranking of potential conservation sites regarding their proximity to existing conservation and ability to link to existing conservation sites. This script was developed for The Nature Conservancy.

As of February 2017 the model is still in a draft format, althought it runs currently without errors when workspace is saved to a local folder (see below for known issues). 

# Objectives
1 - Identify and rank potential parcels that lie close to existing conservation land that could help create large, contiguous conservation projects (best for habitat preservation), while excluding water from the calculation of nearby conservation (or any other specified shapefile) 

2 - Identify and rank potential parcels that would help improve the connectivity of existing conservation land

The script currently takes a little over 8 minutes to run and has been successful at completing both goals. The output table has the desired fields completed, as specified by my conversations with Rich Johnson at TNC.


# Final weight given to each calculated value:
(% Shared Perimeter * .2) + (% Area within 0.25 Mile * .35) + (% Area within 0.25 Mile * .5) + (% Area within 1 Mile* .15) + (% Area within 2 Miles * .05)

# Known Issues
When saved to a dropbox folder, the script has encountered errors with setting the workspace and adding fields. When isolated these portions of the script work fine, and the rest of the script runs (minus user input errors) when whe workspace is not set. When saved to a local folder these errors do not occcur.

Another error has been the inability to erase interim files, although I have no problems overwriting them. The result is messy whereas I would like to have only one additional file created with the script. This is a work in progress.

# Future Steps
Planned additions to the model include adding a Boolean input value that would determine whether the model also calculated the connectivity score in addition to the other percentage calculations. This would be especially helpful as this section of the script takes over 75% of the run-time, more if a larger buffer distance is chosen.

Not every potential user input has been added to the model, such as allowing a user to change the weights associated with each buffer distance. This is partly due to the above errors with setting workspaces. Future steps will involve adding these parameters and hard-coding the tool set-up so the script can be imported into ArcMaps as a python toolbox.
