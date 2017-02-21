'''
THIS SCRIPT CALCULATES A FINAL RANKING FOR POTENTIAL CONSERVATION SITES ACCORDING TO ITS PROXIMITY AND CONNECTIVITY TO EXISTING CONSERVATION SITES. IT ALSO HAS THE ABILITY TO EXLCUDE A PORTION OF THE STUDY AREA.

Author: Lauren Payne-Riley
Current Status: DRAFT (see report for known issues and proposed additions)

To create an ArcToolbox tool with which to execute this script, do the following.
1   In  ArcMap > Catalog > Toolboxes > My Toolboxes, either select an existing toolbox
    or right-click on My Toolboxes and use New > Toolbox to create (then rename) a new one.
2   Drag (or use ArcToolbox > Add Toolbox to add) this toolbox to ArcToolbox.
3   Right-click on the toolbox in ArcToolbox, and use Add > Script to open a dialog box.
4   In this Add Script dialog box, use Label to name the tool being created, and press Next.
5   In a new dialog box, browse to the .py file to be invoked by this tool, and press Next.
6   In the next dialog box, specify the following inputs (using dropdown menus wherever possible)
    before pressing OK or Finish.
        DISPLAY NAME              DATA TYPE       PROPERTY>DIRECTION>VALUE       
        Context File              Shapefile       Input
        Analysis File             Shapefile       Input
        Exclusion File            Shapefile       Input
        Workspace                 Shapefile       Input
        Buffer Distanace (Meters) Linear Unit     Input
           
   To later revise any of this, right-click to the tool's name and select Properties.

'''
# #########################################################################
# Setting Up: Importing Packages and Setting the Environment
# #########################################################################

import sys, os, string, math, arcpy, traceback, numpy, time

# Allow output to overwite any existing grid of the same name
arcpy.env.overwriteOutput = True


# This ensures that when using a table join the original field names will be use and not appended by the name of each of the joining fields (this is necessary to ensure accurate field names can be called within the buffer function) 
arcpy.env.qualifiedFieldNames = False


# #########################################################################
# Defining Functions
# #########################################################################


# PERIMETER PERCENTAGE FUNCTION:
# This function calculates the % of the perimeter of the analysis site that is already under conservation, minus areas of exclusion
'''NOTES:
    Fieldnames inputs require quotation marks around them
    For simplicity I have chosen to name the output, context, and exclusion shapefile variables inputs as the exact same name as the actual files. This is not necessary.
'''
def PerimeterPercent_Fnx(nameOfOutputShapefile, ContextFile, ExclusionFile, PeriFieldName, PercentPeriContextFieldName):
    #Making Temporary Shapefiles
    PerimeterOnly                   = nameOfOutputShapefile[:-4] + "_temp1" + ".shp"    
    Perimeter_NoExclusion           = nameOfOutputShapefile[:-4] + "_temp2" + ".shp"
    Conxt_PeriOverlap               = nameOfOutputShapefile[:-4] + "_temp3"  + ".shp"
    Perimeter_NoExclusion2          = nameOfOutputShapefile[:-4] + "_temp4"  + ".shp"
    Conxt_PeriOverlap2              = nameOfOutputShapefile[:-4] + "_temp5"  + ".shp"
    Conxt_PeriOverlap3              = nameOfOutputShapefile[:-4] + "_temp6"  + ".shp"
    Peri_Join                       = nameOfOutputShapefile[:-4] + "_temp7"  + ".shp"
    SmartOutput2                    = nameOfOutputShapefile[:-4] + "_temp8"  + ".shp"
        
    # Converting the Analysis Sites to be only their Perimeters (this removes the issue of locations where segments of the land under consideration are cross-listed as already under conservation - although this data error is likely mostly due to how the sample data was processed, this will ensure that the problem does not arise in the future)
    arcpy.AddMessage(" ... converting polygon to line")
    arcpy.PolygonToLine_management(nameOfOutputShapefile, PerimeterOnly, "IGNORE_NEIGHBORS")

    #Erasing Exclusion file from buffer (input, erase features, output):
    arcpy.AddMessage(" ... erasing exclusion")
    arcpy.Erase_analysis(PerimeterOnly, ExclusionFile, Perimeter_NoExclusion)
    
    #Make area into a layer before using intersect:
    arcpy.MakeFeatureLayer_management (Perimeter_NoExclusion, "AnalysisPeri_lr")
    arcpy.MakeFeatureLayer_management (ContextFile, "ContextFile_lr")

    #Find Intersection (input, output)     
    arcpy.AddMessage(" ... intersecting")
    clusterTolerance = "" 
    arcpy.Intersect_analysis(["AnalysisPeri_lr", "ContextFile_lr"], Conxt_PeriOverlap, "", clusterTolerance, "LINE") #Notice the use of "LINE" here instead of "INPUT" in order to get a line as the output, instead of a polygon


    #Add Field and Calculate length of line for Perimeter (no exclusion)
    arcpy.AddMessage(" ... calculating areas")
    arcpy.Copy_management(Perimeter_NoExclusion, Perimeter_NoExclusion2)
    arcpy.AddField_management(Perimeter_NoExclusion2, "Peri_M", "DOUBLE", 10, 5)
    arcpy.CalculateField_management(Perimeter_NoExclusion2,"Peri_M","!shape.length@meters!","PYTHON_9.3")
    
    #Adding Field for Later
    arcpy.AddField_management(Perimeter_NoExclusion2, "Cnxt_Metrs", "DOUBLE", 10, 5,"","","NULLABLE","NON_REQUIRED","")
    # arcpy.CalculateField_management(QrtMile_Buff_NoExclusion_2,"Cnxt_Acr","0","PYTHON_9.3")

    #Repeat for Context Buffer Intersection
    arcpy.Copy_management(Conxt_PeriOverlap, Conxt_PeriOverlap2)
    arcpy.AddField_management(Conxt_PeriOverlap2, "Peri_Cnt", "DOUBLE", 10, 5)
    arcpy.CalculateField_management(Conxt_PeriOverlap2,"Peri_Cnt","!shape.length@meters!","PYTHON_9.3")
    
    
    #Dissolve the context interserction by Match_ID to reduce the number of columns (also makes multipart)
    arcpy.Dissolve_management (Conxt_PeriOverlap2, Conxt_PeriOverlap3, "Match_ID", [["Peri_Cnt", "SUM"]], "MULTI_PART", "")
 
    #Make area into a layer before joining:
    arcpy.MakeFeatureLayer_management (Perimeter_NoExclusion2, "SmartPerimeter_lr")
    arcpy.MakeFeatureLayer_management (Conxt_PeriOverlap3, "SmartIntersectPeri_lr")

    # Join the feature layer to buffer layer
    arcpy.AddMessage(" ... joining")
    arcpy.AddJoin_management ("SmartPerimeter_lr", "Match_ID", "SmartIntersectPeri_lr", "Match_ID")

    
    # Copy the layer to a new permanent feature class
    arcpy.CopyFeatures_management ("SmartPerimeter_lr", Peri_Join)
    
    # Time to join these values back into the final output table under their appropriate field names
    arcpy.AddMessage(" ... joining to Final Table")
    arcpy.MakeFeatureLayer_management (nameOfOutputShapefile, "OutputFile_lr")
    arcpy.MakeFeatureLayer_management (Peri_Join, "Peri_Join_lr")
    
    # Join the feature layer to buffer layer
    arcpy.AddJoin_management ("OutputFile_lr", "Match_ID", "Peri_Join_lr", "Match_ID")

    # Populate a field with values from the joined fields
    arcpy.AddMessage(" ... calculating final table fields")
    Calculation_Peri = "!Peri_M!"
    #Calculation_ContPeri = "!SUM_Peri_C!"
    Calculation_PcrtPeri = "(!SUM_Peri_C!/ !Peri_M!)*100"
    arcpy.CalculateField_management ("OutputFile_lr", PeriFieldName, Calculation_Peri, "PYTHON_9.3")
    #arcpy.CalculateField_management ("OutputFile_lr", ContextPeriFieldName, Calculation_ContPeri, "PYTHON_9.3")
    arcpy.CalculateField_management ("OutputFile_lr", PercentPeriContextFieldName, Calculation_PcrtPeri, "PYTHON_9.3")

    # Remove the join
    arcpy.AddMessage(" ... removing join")
    arcpy.RemoveJoin_management ("OutputFile_lr", "")
    
    # Copy the layer to a new permanent feature class
    arcpy.CopyFeatures_management ("OutputFile_lr", SmartOutput2)
   
    #Cleaning Up...
    arcpy.AddMessage(" ... deleting temporary files")
    arcpy.Delete_management(PerimeterOnly)
    arcpy.Delete_management(Perimeter_NoExclusion)
    arcpy.Delete_management(Conxt_PeriOverlap)
    arcpy.Delete_management(Perimeter_NoExclusion2)
    arcpy.Delete_management(Conxt_PeriOverlap2)
    arcpy.Delete_management(Conxt_PeriOverlap3)
    arcpy.Delete_management(Peri_Join)
    
    #Cleaning any cached memory (seemed to help prevent errors of overwriting internal variables)
    arcpy.ClearWorkspaceCache_management() 

    return SmartOutput2
    
    
# AREA PERCENTAGE FUNCTION:
# This function calculates the % of existing conservation land within a given buffer distance of land under analysis, minus areas of exclusion
'''NOTES:
    BuffDistance should be entered in the format of a linear unit and is quickest when measured in meters (the same unit as the maps)
    Fieldnames inputs require quotation marks around them
    For simplicity I have chosen to name the output, context, and exclusion shapefile variables inputs as the exact same name as the actual files. This is not necessary.
    Finally, I have left the variable names as I originally created them when I made a test run using a Quarter Mile Buffer. At the moment I am using this copy simply becuase I am certain that it runs, but I would like to clean up and streamline these names before I submit this more formally to TNC.
'''
def AreaPercent_Fnx(nameOfOutputShapefile, ContextFile, ExclusionFile, BuffDist, AreaFieldName, ContextAreaFieldName, PercentContextFieldName):
    #Making Temporary Shapefiles
    QrtMile_Buffer                  = nameOfOutputShapefile[:-4] + "_temp21" + ".shp"    
    QrtMile_Buff_NoExclusion        = nameOfOutputShapefile[:-4] + "_temp22" + ".shp"
    QrtMile_Buff_Conxt_Intsect      = nameOfOutputShapefile[:-4] + "_temp23"  + ".shp"
    QrtMile_Buff_Conxt_Intsect_2    = nameOfOutputShapefile[:-4] + "_temp24"  + ".shp"
    QrtMile_Buff_Conxt_Intsect_3    = nameOfOutputShapefile[:-4] + "_temp25"  + ".shp"
    QrtMile_Buff_NoExclusion_2      = nameOfOutputShapefile[:-4] + "_temp26"  + ".shp"
    Buff_Join                       = nameOfOutputShapefile[:-4] + "_temp27"  + ".shp"
    SmartOutput                     = nameOfOutputShapefile[:-4] + "_temp28"  + ".shp"
        
    #Buffer by Quarter Mile (input, output, distance, type)
    arcpy.AddMessage(" ... buffering")
    arcpy.Buffer_analysis(nameOfOutputShapefile, QrtMile_Buffer, BuffDist, "OUTSIDE_ONLY", "ROUND", "NONE", "", "")

    #Erasing Exclusion file from buffer (input, erase features, output):
    arcpy.AddMessage(" ... erasing exclusion")
    arcpy.Erase_analysis(QrtMile_Buffer, ExclusionFile, QrtMile_Buff_NoExclusion)

    #Make area into a layer before using intersect:
    arcpy.MakeFeatureLayer_management (QrtMile_Buff_NoExclusion, "QrtMiBuf_NoE_lr")
    arcpy.MakeFeatureLayer_management (ContextFile, "ContextFile_lr")

    #Find Intersection (input, output)     
    arcpy.AddMessage(" ... intersecting")
    clusterTolerance = "" 
    arcpy.Intersect_analysis(["QrtMiBuf_NoE_lr", "ContextFile_lr"], QrtMile_Buff_Conxt_Intsect, "", clusterTolerance, "INPUT")
    
    #Add Field and Calculate Area for buffer
    arcpy.AddMessage(" ... calculating areas")
    arcpy.Copy_management(QrtMile_Buff_NoExclusion, QrtMile_Buff_NoExclusion_2)
    arcpy.AddField_management(QrtMile_Buff_NoExclusion_2, "B1_Acr", "DOUBLE", 10, 5)
    arcpy.CalculateField_management(QrtMile_Buff_NoExclusion_2,"B1_Acr","!shape.area@acres!","PYTHON_9.3")
    
    #Adding Field for Later
    arcpy.AddField_management(QrtMile_Buff_NoExclusion_2, "Cnxt_Acr", "DOUBLE", 10, 5,"","","NULLABLE","NON_REQUIRED","")
    # arcpy.CalculateField_management(QrtMile_Buff_NoExclusion_2,"Cnxt_Acr","0","PYTHON_9.3")

    #Repeat for Context Buffer Intersection
    arcpy.Copy_management(QrtMile_Buff_Conxt_Intsect, QrtMile_Buff_Conxt_Intsect_2)
    arcpy.AddField_management(QrtMile_Buff_Conxt_Intsect_2, "B1_Acr_Cnt", "DOUBLE", 10, 5)
    arcpy.CalculateField_management(QrtMile_Buff_Conxt_Intsect_2,"B1_Acr_Cnt","!shape.area@acres!","PYTHON_9.3")
    
    
    #Dissolve the context interserction by Match_ID to have only one acreage sum per original analysis buffer
    arcpy.Dissolve_management (QrtMile_Buff_Conxt_Intsect_2, QrtMile_Buff_Conxt_Intsect_3, "Match_ID", [["B1_Acr_Cnt", "SUM"]], "MULTI_PART", "")

    #Make area into a layer before joining:
    arcpy.MakeFeatureLayer_management (QrtMile_Buff_NoExclusion_2, "QrtMiBuf_NoE_2_lr")
    arcpy.MakeFeatureLayer_management (QrtMile_Buff_Conxt_Intsect_3, "BufContIntersect_lr")

    # Join the feature layer to buffer layer
    arcpy.AddMessage(" ... joining")
    arcpy.AddJoin_management ("QrtMiBuf_NoE_2_lr", "Match_ID", "BufContIntersect_lr", "Match_ID")
     
    # Copy the layer to a new permanent feature class
    arcpy.CopyFeatures_management ("QrtMiBuf_NoE_2_lr", Buff_Join)
    
    # Time to join these values back into the final output table under their appropriate field names
    arcpy.AddMessage(" ... joining to Final Table")
    arcpy.MakeFeatureLayer_management (nameOfOutputShapefile, "OutputFile_lr")
    arcpy.MakeFeatureLayer_management (Buff_Join, "Buff_Join_lr")
    
    # Join the feature layer to buffer layer
    arcpy.AddJoin_management ("OutputFile_lr", "Match_ID", "Buff_Join_lr", "Match_ID")

    # Populate a field with values from the joined fields
    arcpy.AddMessage(" ... calculating final table fields")
    Calculation_Area = "!B1_Acr!"
    Calculation_ContArea = "!SUM_B1_Acr!"
    Calculation_PcrtArea = "(!SUM_B1_Acr!/ !B1_Acr!)*100"
    arcpy.CalculateField_management ("OutputFile_lr", AreaFieldName, Calculation_Area, "PYTHON_9.3")
    arcpy.CalculateField_management ("OutputFile_lr", ContextAreaFieldName, Calculation_ContArea, "PYTHON_9.3")
    arcpy.CalculateField_management ("OutputFile_lr", PercentContextFieldName, Calculation_PcrtArea, "PYTHON_9.3")

    # Remove the join
    arcpy.AddMessage(" ... removing join")
    arcpy.RemoveJoin_management ("OutputFile_lr", "")
    
    # Copy the layer to a new permanent feature class
    arcpy.CopyFeatures_management ("OutputFile_lr", SmartOutput)
   
    #Cleaning Up...
    arcpy.AddMessage(" ... deleting temporary files")
    arcpy.Delete_management(QrtMile_Buffer)
    arcpy.Delete_management(QrtMile_Buff_NoExclusion)
    arcpy.Delete_management(QrtMile_Buff_Conxt_Intsect)
    arcpy.Delete_management(QrtMile_Buff_Conxt_Intsect_2)
    arcpy.Delete_management(QrtMile_Buff_Conxt_Intsect_3)
    arcpy.Delete_management(QrtMile_Buff_NoExclusion_2)
    arcpy.Delete_management(Buff_Join)
    
    #Cleaning any cached memory (seemed to help prevent errors of overwriting internal variables)
    arcpy.ClearWorkspaceCache_management() 

    return SmartOutput


# #########################################################################
# Running the Script
# #########################################################################
    
try:
    # #########################################################################
    # Requesting User Input
    # #########################################################################

    # Request user input of data type = Shapefile and direction = Input
    ContextFile = arcpy.GetParameterAsText(0)

    # Potential Sites (Analysis File):
    # Request user input of data type = Shapefile and direction = Input
    AnalysisFile = arcpy.GetParameterAsText(1)

    # Area to Eliminate (Exclusion Area):
    # Request user input of data type = Shapefile and direction = Input
    ExclusionFile = arcpy.GetParameterAsText(2)
    
    # Setting Workspace in which to store files
    # Request user input of data type = File and direction = Input
    Workspace = arcpy.GetParameterAsText(3)
    arcpy.env.workspace = Workspace
    arcpy.env.scratchWorkspace = Workspace
    
    
    #Hard-coded alternatives to user input (faster):
    #AnalysisFile = r"C:\Users\LaurenPR\Dropbox\670_Geospatial_Software\ArcPython\FinalProject_TNC\PCAT Analysis Data\PCAT_Analysis_File.shp"
    #ContextFile = r"C:\Users\LaurenPR\Dropbox\670_Geospatial_Software\ArcPython\FinalProject_TNC\PCAT Analysis Data\PCAT_Context_File.shp"
    #ExclusionFile = r"C:\Users\LaurenPR\Dropbox\670_Geospatial_Software\ArcPython\FinalProject_TNC\PCAT Analysis Data\PCAT_Exclusion_File.shp"
    # Workspace = r"C:\Users\LaurenPR\Dropbox\670_Geospatial_Software\ArcPython\FinalProject_TNC\ScratchFolder"
    # arcpy.env.workspace = Workspace
    # arcpy.env.scratchWorkspace = Workspace

    # Output File:
    nameOfOutputShapefile = AnalysisFile[:-4] + "_PCAT"  + ".shp"
    arcpy.AddMessage("The output shapefile name is " + nameOfOutputShapefile + "\n")
    
    
    # #######################################################################
    # I. Adding fields
    # #######################################################################
    
    # Replicate the input shapefile to add new fields to the replica
    arcpy.Copy_management(AnalysisFile, nameOfOutputShapefile)
    arcpy.AddMessage(" ... adding field names")

    # Add a series of fields to replica (Name, Type, Size):
    arcpy.AddField_management(nameOfOutputShapefile, "Match_ID", "Long", 8)
    arcpy.AddField_management(nameOfOutputShapefile, "SP_Acr", "Double", 9,2)
    arcpy.AddField_management(nameOfOutputShapefile, "SP_Lng", "Double", 9,2)
    arcpy.AddField_management(nameOfOutputShapefile, "SP_Adj_Pct", "Float", 5,2)
    arcpy.AddField_management(nameOfOutputShapefile, "QMi_Acr", "Double", 9,2)
    arcpy.AddField_management(nameOfOutputShapefile, "QMi_Pr_Acr", "Double", 9,2)
    arcpy.AddField_management(nameOfOutputShapefile, "QMi_Pr_Pct", "Float", 5,2)
    arcpy.AddField_management(nameOfOutputShapefile, "HMi_Acr", "Double", 9,2)
    arcpy.AddField_management(nameOfOutputShapefile, "HMi_Pr_Acr", "Double", 9,2)
    arcpy.AddField_management(nameOfOutputShapefile, "HMi_Pr_Pct", "Float", 5,2)
    arcpy.AddField_management(nameOfOutputShapefile, "Mi1_Acr", "Double", 9,2)
    arcpy.AddField_management(nameOfOutputShapefile, "Mi1_Pr_Acr", "Double", 9,2)
    arcpy.AddField_management(nameOfOutputShapefile, "Mi1_Pr_Pct", "Float", 5,2)
    arcpy.AddField_management(nameOfOutputShapefile, "Mi2_Acr", "Double", 9,2)
    arcpy.AddField_management(nameOfOutputShapefile, "Mi2_Pr_Acr", "Double", 9,2)
    arcpy.AddField_management(nameOfOutputShapefile, "Mi2_Pr_Pct", "Float", 5,2)
    arcpy.AddField_management(nameOfOutputShapefile, "PCAT_Scr", "Float", 5,2)
    
    # Populate the Match_ID with the a random sequential number (similar to FID)
    arcpy.CalculateField_management(nameOfOutputShapefile,"Match_ID","!FID! +1","PYTHON_9.3")
      
    # Calculating the area (in acres) of the analysis sites:    
    arcpy.CalculateField_management(nameOfOutputShapefile,"SP_Acr","!shape.area@acres!","PYTHON_9.3")
   
    # #######################################################################
    # II. Calculating Percentage of Conserved PERIMETER (minus Exclusion Areas)
    # #######################################################################
    
    # Percentage of Perimeter Under Conservation Protection (minus Exclusion)
    arcpy.AddMessage("Calculating Conservation of Perimeter")
    PERI =  PerimeterPercent_Fnx(nameOfOutputShapefile, ContextFile, ExclusionFile, "SP_Lng", "SP_Adj_Pct")
    arcpy.Copy_management(PERI, nameOfOutputShapefile)
    
    # #######################################################################
    # III. Calculating Percentage of Conserved AREA w/in Buffers (minus Exclusion Areas)
    # #######################################################################
    
    # Quarter Mile Buffer
    arcpy.AddMessage("Calculating Conservation within Quarter Mile Buffer")
    QRTMIBUFF =  AreaPercent_Fnx(nameOfOutputShapefile, ContextFile, ExclusionFile, "402.3300", "QMi_Acr", "QMi_Pr_Acr", "QMi_Pr_Pct")
    arcpy.Copy_management(QRTMIBUFF, nameOfOutputShapefile)
    
    # Half Mile Buffer
    arcpy.AddMessage("Calculating Conservation within Half Mile Buffer")
    HLFMIBUFF =  AreaPercent_Fnx(nameOfOutputShapefile, ContextFile, ExclusionFile, "804.6720", "HMi_Acr", "HMi_Pr_Acr", "HMi_Pr_Pct")
    arcpy.Copy_management(HLFMIBUFF, nameOfOutputShapefile)
    
    # One Mile Buffer
    arcpy.AddMessage("Calculating Conservation within One Mile Buffer")
    ONEMIBUFF =  AreaPercent_Fnx(nameOfOutputShapefile, ContextFile, ExclusionFile, "1609.34", "Mi1_Acr", "Mi1_Pr_Acr", "Mi1_Pr_Pct")
    arcpy.Copy_management(ONEMIBUFF, nameOfOutputShapefile)
    
    # Two Mile Buffer
    arcpy.AddMessage("Calculating Conservation within Two Mile Buffer")
    TWOMIBUFF =  AreaPercent_Fnx(nameOfOutputShapefile, ContextFile, ExclusionFile, "3218.69", "Mi2_Acr", "Mi2_Pr_Acr", "Mi2_Pr_Pct")
    arcpy.Copy_management(TWOMIBUFF, nameOfOutputShapefile)

    
    # ####################################################################
    # IV. Finding "Connectivity" Potential of Conservation Sites
    ####################################################################
    
    arcpy.AddMessage("Calculating Connectivity Potential")
    
    # Creating temporary GIS files:
    ConvexHull_temp                 = nameOfOutputShapefile[:-4] + "_temp31" + ".shp"
    StudyArea_temp                  = nameOfOutputShapefile[:-4] + "_temp32" + ".shp"
    NegSpacebtwConservation_temp    = nameOfOutputShapefile[:-4] + "_temp33"  + ".shp"
    InnerBuffer_temp                = nameOfOutputShapefile[:-4] + "_temp34"  + ".shp"
    OutterBuffer_temp               = nameOfOutputShapefile[:-4] + "_temp35"  + ".shp"
    NarrowAreas_temp                = nameOfOutputShapefile[:-4] + "_temp36"  + ".shp"
    NarrowAreas_NoBuffer_temp       = nameOfOutputShapefile[:-4] + "_temp37"  + ".shp"
    NearConnectivity_temp           = nameOfOutputShapefile[:-4] + "_temp38"  + ".shp"
    Connectivity2_temp              = nameOfOutputShapefile[:-4] + "_temp39"  + ".shp"
    NearConnectivity2_temp          = nameOfOutputShapefile[:-4] + "_temp40"  + ".shp"
    ConnectivityMeasure_temp        = nameOfOutputShapefile[:-4] + "_temp41"  + ".shp"
    ConnectivityMeasure_temp2       = nameOfOutputShapefile[:-4] + "_temp42"  + ".shp"
    SmartFinal                      = nameOfOutputShapefile[:-4] + "_temp43"  + ".shp"

    
    # Start timing
    timeStart_C           = time.clock()
    
    ### 1) create a "study area" layer, from which to determine the "negative space" (all the land that is not under conservation easement) around existing conservation sites.
    
    # Creat a Convex Hull around study area(note that a minimum enclosing rectangle, circle, etc. could also work but would include additional area):
    arcpy.AddMessage(" ... creating convex hull")
    arcpy.MinimumBoundingGeometry_management(ContextFile, ConvexHull_temp, "CONVEX_HULL", "NONE")

    # Buffer out from the Convex Hull to include some extra space around the outside conservation sites (otherwise the connectivity of sites located on the outskirts of the study area gets skewed)
    arcpy.AddMessage(" ... buffering")
    Distance2 = "0.25 Miles" #note: this parameter could be easily changed given the study area size
    arcpy.Buffer_analysis(ConvexHull_temp, StudyArea_temp, Distance2, "FULL", "ROUND", "NONE")

    
    # Create a shapefile of the "negative space" around conservation sites    
    arcpy.AddMessage(" ... creating negative space")
    xyTol = "1 Meters"
    arcpy.Erase_analysis(StudyArea_temp, ContextFile, NegSpacebtwConservation_temp, xyTol)

    # #### 2) Next we will find areas of "narrowness" between the conservation sites using the negative space shapefile generated above. This is an important step that will help identify potential conservation sites that will 
    
    # Read user-specified width and generate a negative version of it as well
    arcpy.AddMessage(" ... finding narrowness (this is slow)")
    positiveWidth           = arcpy.GetParameterAsText(3) #Linear Unit, input
    negativeWidth           = "-" + positiveWidth
    # arcpy.AddMessage(negativeWidth)

    # positiveWidth             = "25 Meters"
    # negativeWidth             = "-25 Meters"

    # Buffer into each input polygon and then back out from what's left to remove "narrow" areas  
    arcpy.Buffer_analysis(NegSpacebtwConservation_temp,  InnerBuffer_temp, negativeWidth, "FULL", "ROUND", "NONE")
    # NOTE "If the negative buffer distance is large enough to collapse the polygon to nothing, a null geometry will be generated. A warning message will be given, and any null geometry features will not be written to the output feature class." ~ ESRI
    
    arcpy.Buffer_analysis(InnerBuffer_temp, OutterBuffer_temp, positiveWidth, "FULL", "ROUND", "NONE")
    
    # Subtract the original negative space shapefile from the above shapefile without 
    # narrowness, to generate a file with only narrow areas between conservation sites
    arcpy.AddMessage(" ... selecting only narrow areas")
    arcpy.Erase_analysis(OutterBuffer_temp, NegSpacebtwConservation_temp, NarrowAreas_temp, "")
    
    #Clip away the extra buffer around the study area (otherwise all the area surrounding the outside buffer appears to have a high connectivity score):
    arcpy.Clip_analysis(NarrowAreas_temp, ConvexHull_temp, NarrowAreas_NoBuffer_temp)

    # #### 3) The above layer shows all the areas that would help increase the connectivity between existing conservation sites. You may want to also give a weight to a distance away from one of these areas. In which case the following buffer could be used: 

    # Distance to Connectivity     = arcpy.GetParameterAsText(5)
    arcpy.AddMessage(" ... calculating another buffer (this can take even longer)")
    # Distance3 = "25 Meters" #note: this parameter could be easily changed given the study area size
    arcpy.Buffer_analysis(NarrowAreas_NoBuffer_temp, NearConnectivity_temp, positiveWidth, "OUTSIDE_ONLY", "ROUND", "NONE")
    # NOTE, could also generate a distance to grid but I imagine that at a certain cutoff point being close to a "narrow" area of connectivity is no longer benefitial. 

    # Give the connectivity a score (In this case )
    arcpy.AddMessage(" ... calculating connectivity score")
    ConnectivityScore_Connected   = "5"  # = arcpy.GetParameterAsText(6) #STRING
    ConnectivityScore_Near        = "1"  # = arcpy.GetParameterAsText(7) #STRING

    CommonConnectivityScoreName   = "Con_Score" # = arcpy.GetParameterAsText(8) #STRING
    
    
    # Replicate the input shapefile and add a new field to the replica
    arcpy.Copy_management(NarrowAreas_NoBuffer_temp, Connectivity2_temp)
    arcpy.AddField_management(Connectivity2_temp, CommonConnectivityScoreName, "SHORT", 6)
    arcpy.CalculateField_management(Connectivity2_temp, CommonConnectivityScoreName, ConnectivityScore_Connected,"PYTHON_9.3")

    # Replicate the input shapefile and add a new field to the replica
    arcpy.Copy_management(NearConnectivity_temp, NearConnectivity2_temp)
    arcpy.AddField_management(NearConnectivity2_temp, CommonConnectivityScoreName, "SHORT", 6)
    arcpy.CalculateField_management(NearConnectivity2_temp, CommonConnectivityScoreName, ConnectivityScore_Near,"PYTHON_9.3")
    
    # MERGE these layers based on their new common connecitity score name:
    arcpy.AddMessage(" ... merging connectivity score")
    arcpy.Merge_management([Connectivity2_temp, NearConnectivity2_temp], ConnectivityMeasure_temp)
    
    arcpy.AddMessage(" ... dissolving connectivity score") # to reduce columns as I was overwhelmed by field mapping in merge
    arcpy.Dissolve_management (ConnectivityMeasure_temp, ConnectivityMeasure_temp2, "FID", [["Con_Score", "FIRST"]], "MULTI_PART", "")

    # In order to combine this information with the final output layer, we must use join
    # However, join requires that we make a feature layer first of the data we want to use:
    arcpy.AddMessage(" ... joining connectivity score to final tabulation")
    
    arcpy.MakeFeatureLayer_management (ConnectivityMeasure_temp2, "Connectivity")
    arcpy.MakeFeatureLayer_management (nameOfOutputShapefile, "Analysis2_ly")

    
    # Join the feature layer to a table
    arcpy.SpatialJoin_analysis ("Analysis2_ly", "Connectivity", SmartFinal, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")
    
    # Stop timing
    timeStop_C        = time.clock()
    timeTaken_C       = (timeStop_C - timeStart_C)/60
    arcpy.AddMessage("\nElapsed time for Connectivity Calculation = " + str(timeTaken_C) + " minutes\n")

   
    # Since each shapefile-generating method (unlike grid-generating metdhods) immediately writes its output to disk, final results need not be explicitly saved, but intermediate results must be explicitly deleted.
    '''
    arcpy.AddMessage(" ... deleting temporary files")
    arcpy.Delete_management(ConvexHull_temp)
    arcpy.Delete_management(StudyArea_temp)
    arcpy.Delete_management(NegSpacebtwConservation_temp)
    arcpy.Delete_management(InnerBuffer_temp)
    arcpy.Delete_management(OutterBuffer_temp)
    arcpy.Delete_management(NarrowAreas_temp)
    arcpy.Delete_management(NarrowAreas_NoBuffer_temp)
    arcpy.Delete_management(NearConnectivity_temp)
    arcpy.Delete_management(Connectivity2_temp)
    arcpy.Delete_management(NearConnectivity2_temp)
    arcpy.Delete_management(ConnectivityMeasure_temp)
    arcpy.Delete_management(ConnectivityMeasure_temp2)
    arcpy.Delete_management(SmartFinal)
    '''
    
    # ####################################################################
    # V. Final Site Ranking
    ####################################################################
    arcpy.AddMessage("Calculating Final Score!")
    
    #Making another Layer
    arcpy.MakeFeatureLayer_management (SmartFinal, "Final_lr")
    
    #Final Calculation
    FinalCalculation = "(!SP_Adj_Pct! * .2) + (!QMi_Pr_Pct! * .35) + (!HMi_Pr_Pct! * .25) + (!Mi1_Pr_Pct! * .15) + (!Mi2_Pr_Pct! * .05) + (!FIRST_Con_! * 0.3)"
    
    arcpy.CalculateField_management("Final_lr", "PCAT_Scr", FinalCalculation, "PYTHON_9.3")

    #Copying to Final Output
    arcpy.CopyFeatures_management ("Final_lr", nameOfOutputShapefile)

    
except Exception as e:
    # If unsuccessful, end gracefully by indicating why
    arcpy.AddError('\n' + "Script failed because: \t\t" + e.message )
    # ... and where
    exceptionreport = sys.exc_info()[2]
    fullermessage   = traceback.format_tb(exceptionreport)[0]
    arcpy.AddError("at this location: \n\n" + fullermessage + "\n")


    
    
# #######################################################################
# #######################################################################
# TOOLS USED: SYNTAX STRUCTURE REFERENCES FOR EDITING
# #######################################################################

# Data management:
    # arcpy.AddField_management(table, fieldname, type, precision, scale, length, alias, nullability, required, domain) 
    # arcpy.CalculateField_management(in_table, field, expression, {expression_type}, {code_block})
    # arcpy.MakeFeatureLayer_management(in_features, out_layer, {where_clause}, {workspace}, {field_info})
    # arcpy.AddJoin_management(in_layer_or_view, in_field, join_table, join_field, {join_type})
    # arcpy.Merge_management([Connectivity2_temp, NearConnectivity2_temp], ConnectivityMeasure_temp, fieldMappings)


# Shapefile manipulation:
    # arcpy.Intersect_analysis(in_features, out_feature_class, {join_attributes}, {cluster_tolerance}, {output_type})
    # arcpy.Erase_analysis(in_features, erase_features, out_feature_class, {cluster_tolerance})
    # arcpy.PolygonToLine_management(in_features, out_feature_class, {neighbor_option})
    # arcpy.Buffer_analysis(in_features, out_feature_class, buffer_distance_or_field, {line_side}, {line_end_type}, {dissolve_option}, {dissolve_field}, {method})
    # arcpy.Clip_analysis (in_features, clip_features, out_feature_class, {cluster_tolerance})
    # arcpy.Dissolve_management (in_features, out_feature_class, {dissolve_field}, {statistics_fields}, {multi_part}, {unsplit_lines})
    # arcpy.SpatialJoin_analysis (target_features, join_features, out_feature_class, {join_operation}, {join_type}, {field_mapping}, {match_option}, {search_radius}, {distance_field_name})
