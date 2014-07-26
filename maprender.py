import pymclevel
import pymclevel.nbt as nbt
from pymclevel import TAG_List, TAG_Byte, TAG_Int, TAG_Compound, TAG_Short
from pymclevel import TAG_Double, TAG_Float, TAG_String, TAG_Long, TAG_Int_Array, TAG_Byte_Array
import os
import collections
import itertools
import numpy

import line_profiler
import cProfile
import pstats

displayName = "Render Maps"

actionTab = (
    ("Action", "title"),
    ("Pick Action", (
        "Render Maps In Box",
        "Update All Maps",
        "Render Map by Number",
        "Generate Wall Map"
        )
    ),
    ("Map to Render", (0, 0, 65536))
)

wallMapTab = (
    ("Wall Map", "title"),
    ("Scale",(0, 4)),
    ("Centre of the Wall Map:", "label"),
    ("x", 0),
    ("z", 0),
    ("Selects whether to align maps to the grid default maps align to.", "label"),
    ("Align with Grid", True),
    ("Up is", ("North", "East", "South", "West")),
    ("Render Maps", True),
    ("Make Map Copies Chest", True) # Should I do this?
)

inputs = [actionTab, wallMapTab]

def perform(level, box, options):
    performLine(level, box, options)

def performProf(level, box, options):
    pr = cProfile.Profile()
    pr.enable()
    performfoo(level, box, options)
    pr.disable()
    ps = pstats.Stats(pr)
    ps.sort_stats("tottime")
    ps.print_stats(30)
    

def performLine(level, box, options):
    profiler = line_profiler.LineProfiler(render_map)
    profiler.runctx("performfoo(level, box, options)", globals(), locals())
    profiler.print_stats()

# try to make spelling consistant

# Use slices to run down block columns perhaps?
# make sure there is a backing in wall map gen
# think about 1.7 - 1.8 id compatability

# it seems in 1.8 (snapshot) the item frame TileX, Y, Z are of the block
# the item frame is in, not the one it's on.
# 1.8 fixes 1.7-made item frame entities when they are loaded
# it tells 1.7 ones apart from 1.8 ones by whether the item frame entity
# has a "Direction" tag or not. I think it removes these in 1.8, replacing
# it with "Facing". Might need to make two scripts/ an option for pre-1.8/1.8
# "Dir" is also removed in 1.8


def performfoo(level, box, options):
    operation = options["Pick Action"]
    
    if operation == "Render Maps In Box":
        level.showProgress("Rendering Maps in box", renderMapsInBox(level, box))
    elif operation == "Update All Maps":
        level.showProgress("Rendering All Maps", renderAllMaps(level))
    elif operation == "Render Map by Number":
        mapID = options["Map to Render"]
        level.showProgress("Rendering Map Number "+str(mapID), renderMapByNum(level, mapID))
    elif operation == "Generate Wall Map":
        level.showProgress("Generating Wall Map", genWallMap(level, box, options))

def renderMapsInBox(level, box):
    mapIDSet = set()
    for chunk, slices, point in level.getChunkSlices(box):
        for tileEnt in chunk.getTileEntitiesInBox(box):
            if "Items" in tileEnt:
                for item in tileEnt["Items"]:
                    if item["id"].value in (358, "minecraft:filled_map"):
                        mapIDSet.add(item["Damage"].value)
    
    for ent in level.getEntitiesInBox(box):
        if "Item" in ent and ent["Item"]["id"].value in (358, "minecraft:filled_map"):
            mapIDSet.add(ent["Item"]["Damage"].value)
    
    
    numMaps = len(mapIDSet)
    mapCount = 0
    for mapid in mapIDSet:
        maptag = loadMapTag(level, mapid)
        if maptag:
            for col in render_map(level, maptag):
                yield mapCount*128 + col, numMaps * 128, "Maps: "+str(mapCount)+"/"+str(numMaps)
            saveMapTag(level, maptag, mapid)
        mapCount += 1
            
def renderAllMaps(level):
    import re
    dataPath = level.worldFolder.getFilePath("data")
    mapIDSet = set()
    for f in os.listdir(dataPath):
        match = re.match(r"map_([0-9]+)\.dat$", f)
        if match:
            set.add(int(match.group(1)))
    
    mapCount = 0
    numMaps = len(mapIDSet)
    for mapID in mapIDSet:
        maptag = nbt.load(os.path.join(dataPath, f))
        for col in render_map(level, maptag):
            yield mapCount*128 + col, numMaps*128, "Maps: "+str(mapCount)+"/"+str(numMaps)
        saveMapTag(level, maptag, mapID)
        mapCount += 1

def renderMapByNum(level, mapid):
    mapTag = loadMapTag(level, mapid)
    if mapTag is not None:
        for cols in render_map(level, maptag):
            yield cols, 128
        saveMapTag(level, maptag, mapid)

def genWallMap(level, box, options):
    mapScale = options["Scale"]
    wallMapCentreX = options["x"]
    wallMapCentreZ = options["z"]
    gridAlign = options["Align with Grid"]
    makeCopiesChest = options["Make Map Copies Chest"]
    renderMaps = options["Render Maps"]
    
    dataFolder = level.worldFolder.getFilePath("data")
    
    if os.path.exists(os.path.join(dataFolder, "idcounts.dat")):
        idcountsTag = nbt.load(os.path.join(dataFolder, "idcounts.dat"))
        # Value of last existing map, new map should be map_(mapCount+1)
        mapCount = idcountsTag["map"].value
    else:
        mapCount = -1
        #something
        
    if gridAlign:
        wallMapCentreX = int(round(wallMapCentreX/8.0))*8
        wallMapCentreZ = int(round(wallMapCentreZ/8.0))*8
    
    # if the box is not 1 thick
    if box.width != 1 and box.length != 1:
        raise Exception("The box needs to be 1 thick")
    
    for chunk, slices, point in level.getChunkSlices(box):
        if chunk.Blocks[slices].any():
            raise Exception("The box should be air")
    
    # facing
    # 0 : south, +x map left to right
    # 1 : west, +z
    # 2 : north, -x
    # 3 : east, -z
    
    positive = 0
    negative = 0
    if box.width == 1:
        # wall map along y-z plane
        for chunk, slices, point in level.getChunkSlices(pymclevel.box.BoundingBox(box.origin + (1, 0, 0), box.size)):
            positive += chunk.Blocks[slices][chunk.Blocks[slices] != 0].size
        for chunk, slices, point in level.getChunkSlices(pymclevel.box.BoundingBox(box.origin + (-1, 0, 0), box.size)):
            negative += chunk.Blocks[slices][chunk.Blocks[slices] != 0].size
        if positive > negative:
            facing = 1
        else:
            facing = 3
        wallMapWidth = box.length
    else:
        # wall map along x-y plane
        for chunk, slices, point in level.getChunkSlices(pymclevel.box.BoundingBox(box.origin + (0, 0, 1), box.size)):
            positive += chunk.Blocks[slices][chunk.Blocks[slices] != 0].size
        for chunk, slices, point in level.getChunkSlices(pymclevel.box.BoundingBox(box.origin + (0, 0, -1), box.size)):
            negative += chunk.Blocks[slices][chunk.Blocks[slices] != 0].size
        if positive > negative:
            facing = 2
        else:
            facing = 0
        wallMapWidth = box.width
    wallMapHeight = box.height
    
    print "Facing: ", facing
    
    def itemFramePosIter(box, facing):
        if facing == 0:
            return ((x, y, box.minz) for y in xrange(box.maxy-1, box.miny-1, -1) for x in xrange(box.minx, box.maxx))
        elif facing == 1:
            return ((box.minx, y, z) for y in xrange(box.maxy-1, box.miny-1, -1) for z in xrange(box.minz, box.maxz))
        elif facing == 2:
            return ((x, y, box.minz) for y in xrange(box.maxy-1, box.miny-1, -1) for x in xrange(box.maxx-1, box.minx-1, -1))
        elif facing == 3:
            return ((box.minx, y, z) for y in xrange(box.maxy-1, box.miny-1, -1) for z in xrange(box.maxz-1, box.minz-1, -1))
    
    
    def mapCentreIter(wallMapCentreX, wallMapCentreZ, wallMapWidth, wallMapHeight, mapScale, upDir):
        mapWidthInBlocks = 128 * 2**mapScale
        
        if upDir == 2:
            topLeftMapCentreX = wallMapCentreX - wallMapWidth*mapWidthInBlocks/2 + mapWidthInBlocks/2
            topLeftMapCentreZ = wallMapCentreZ - wallMapHeight*mapWidthInBlocks/2 + mapWidthInBlocks/2
            
            for h in xrange(wallMapHeight):
                for w in xrange(wallMapWidth):
                    yield (topLeftMapCentreX + w * mapWidthInBlocks, topLeftMapCentreZ + h * mapWidthInBlocks)
            
        elif upDir == 3:
            topLeftMapCentreX = wallMapCentreX + wallMapHeight*mapWidthInBlocks/2 - mapWidthInBlocks/2
            topLeftMapCentreZ = wallMapCentreZ - wallMapWidth*mapWidthInBlocks/2 + mapWidthInBlocks/2
            
            for h in xrange(wallMapHeight):
                for w in xrange(wallMapWidth):
                    yield (topLeftMapCentreX - h * mapWidthInBlocks, topLeftMapCentreZ + w * mapWidthInBlocks)
            
        elif upDir == 0:
            topLeftMapCentreX = wallMapCentreX + wallMapWidth*mapWidthInBlocks/2 - mapWidthInBlocks/2
            topLeftMapCentreZ = wallMapCentreZ + wallMapHeight*mapWidthInBlocks/2 - mapWidthInBlocks/2
            
            for h in xrange(wallMapHeight):
                for w in xrange(wallMapWidth):
                    yield (topLeftMapCentreX - w * mapWidthInBlocks, topLeftMapCentreZ - h * mapWidthInBlocks)
            
        elif upDir == 1:
            topLeftMapCentreX = wallMapCentreX - wallMapHeight*mapWidthInBlocks/2 + mapWidthInBlocks/2
            topLeftMapCentreZ = wallMapCentreZ + wallMapWidth*mapWidthInBlocks/2 - mapWidthInBlocks/2
            
            for h in xrange(wallMapHeight):
                for w in xrange(wallMapWidth):
                    yield (topLeftMapCentreX + h * mapWidthInBlocks, topLeftMapCentreZ - w * mapWidthInBlocks)
    
    
    upDir = {"North":2, "East":3, "South":0, "West":1}[options["Up is"]]
    
    # Map rotations go up to 7 even though visually there are
    # only 4 rotations
    itemRotation = [2, 1, 0, 3][upDir]
    progressBarMapCount = 0
    numMaps = wallMapWidth * wallMapHeight
    numCols = numMaps * 128
    for itemFramePos, mapCentre in itertools.izip(itemFramePosIter(box, facing), mapCentreIter(wallMapCentreX, wallMapCentreZ, wallMapWidth, wallMapHeight, mapScale, upDir)):
        mapCount += 1
        mapTag = makeMapTag(*mapCentre, scale=mapScale)
        if renderMaps:
            for column in render_map(level, mapTag):
                yield progressBarMapCount * 128 + column, numCols, "Map: "+str(progressBarMapCount)+"/"+str(numMaps)
        saveMapTag(level, mapTag, mapCount)
        
        mapItem = makeMapItemTag(mapCount)
        
        itemFrame = makeItemFrameEntity(*itemFramePos, facing=facing, itemtag=mapItem, itemRotation=itemRotation)
        level.addEntity(itemFrame)
        progressBarMapCount += 1
    
    if mapCount >= 0:
        idcountsTag = TAG_Compound()
        idcountsTag["map"] = TAG_Short(mapCount)
        idcountsTag.save(os.path.join(dataFolder, "idcounts.dat"))
    
def loadMapTag(level, mapid):
    mapPath = level.worldFolder.getFilePath("data/map_{}.dat".format(mapid))
    if os.path.exists(mapPath):
        return nbt.load(mapPath)
    else:
        return None

def saveMapTag(level, maptag, mapid):
    maptag.save(level.worldFolder.getFilePath("data/map_{}.dat".format(mapid)))

def makeMapTag(xCentre, zCentre, scale):
    mapdata = TAG_Compound()
    mapdata["scale"] = TAG_Byte(scale)
    mapdata["dimension"] = TAG_Byte(0)
    mapdata["height"] = TAG_Short(128)
    mapdata["width"] = TAG_Short(128)
    mapdata["xCenter"] = TAG_Int(xCentre)
    mapdata["zCenter"] = TAG_Int(zCentre)
    mapdata["colors"] = TAG_Byte_Array(numpy.zeros(16384, numpy.dtype('uint8')))
    maptag = TAG_Compound()
    maptag["data"] = mapdata
    return maptag


def makeItemFrameEntity(x, y, z, facing, itemtag=None, itemRotation=0):
    itemFrame = TAG_Compound()
    itemFrame["id"] = TAG_String(u'ItemFrame')
    pos = TAG_List()
    pos.append(TAG_Double(x + 0.5 + 0.4375*[0, 1, 0, -1][facing]))
    pos.append(TAG_Double(y + 0.5))
    pos.append(TAG_Double(z + 0.5 + 0.4375*[-1, 0, 1, 0][facing]))
    itemFrame["Pos"] = pos
    motion = TAG_List()
    motion.append(TAG_Double(0.0))
    motion.append(TAG_Double(0.0))
    motion.append(TAG_Double(0.0))
    itemFrame["Motion"] = motion
    rotation = TAG_List()
    rotation.append(TAG_Float(0.0))
    rotation.append(TAG_Float(0.0))
    itemFrame["Rotation"] = rotation
    itemFrame["FallDistance"] = TAG_Float(0.0)
    itemFrame["Fire"] = TAG_Short(0)
    itemFrame["Air"] = TAG_Short(300)
    itemFrame["OnGround"] = TAG_Byte(0)
    itemFrame["Dimension"] = TAG_Int(0)
    itemFrame["Invulnerable"] = TAG_Byte(0)
    itemFrame["PortalCooldown"] = TAG_Int(0)
    itemFrame["UUIDLeast"] = TAG_Long(0)
    itemFrame["UUIDMost"] = TAG_Long(0)
    itemFrame["TileX"] = TAG_Int(x + [0, 1, 0, -1][facing])
    itemFrame["TileY"] = TAG_Int(y)
    itemFrame["TileZ"] = TAG_Int(z + [-1, 0, 1, 0][facing])
    itemFrame["Facing"] = TAG_Byte(facing)
    itemFrame["Direction"] = TAG_Byte(facing)
    if itemtag:
        itemFrame["Item"] = itemtag
        itemFrame["ItemDropChance"] = TAG_Float(1)
        itemFrame["ItemRotation"] = TAG_Byte(itemRotation)
    return itemFrame

def makeMapItemTag(mapID):
    itemTag =  TAG_Compound()
    itemTag["id"] = TAG_Short(358) # Note: ids!
    itemTag["Damage"] = TAG_Short(mapID)
    itemTag["Count"] = TAG_Byte(1)
    return itemTag

def render_map(level, maptag):
    scale = maptag["data"]["scale"].value
    dimension = maptag["data"]["dimension"].value
    xCenter = maptag["data"]["xCenter"].value
    zCenter = maptag["data"]["zCenter"].value
    colors = maptag["data"]["colors"].value
    
    if level.dimNo != 0:
        level = level.parentWorld
    
    blocksPerPixel = 1 << scale
    
    # Hack to stop garbage collection of chunks
    chunkHolder = set()

    for xPixel in xrange(128):
        yield xPixel
        prevAverageColumnHeight = 0.0
        for zPixel in xrange(-1, 128):
            xPixelStartBlock = (xCenter // blocksPerPixel + xPixel - 64) * blocksPerPixel
            zPixelStartBlock = (zCenter // blocksPerPixel + zPixel - 64) * blocksPerPixel
            
            xChunkStartBlock = xPixelStartBlock & 15
            zChunkStartBlock = zPixelStartBlock & 15

            subBlockPixelAverage = 0
            averageColumnHeight = 0.0

            colorCounter = collections.Counter()
            
            try:
                chunk = level.getChunk(xPixelStartBlock >> 4, zPixelStartBlock >> 4)
            except pymclevel.mclevelbase.ChunkNotPresent:
                colors[xPixel + 128*zPixel] = 0
                prevAverageColumnHeight = 0.0
                continue
            
            heightMap = chunk.HeightMap
            
            # Part of garbage collection hack
            chunkHolder.add(chunk)
            
            if dimension in (-1, 1):
                num = xPixelStartBlock + zPixelStartBlock * 231871
                num = num * num * 31287121 + num * 11
                
                if (num >> 20 & 1) == 0:
                    # Dirt
                    colorCounter[getMapColorIndex(3)] = 10
                else:
                    # Stone
                    colorCounter[getMapColorIndex(1)] = 100
            else:
                for i in xrange(blocksPerPixel):
                    for j in xrange(blocksPerPixel):
                        # Assuming minecraft and mcedit heightmaps are the same.
                        # I beleive they are.
                        
                        columnHeight = heightMap[j + zChunkStartBlock, i + xChunkStartBlock] + 1
                        block = 0
                        data = 0
                        
                        if columnHeight > 1:
                            while True:
                                columnHeight -= 1
                                block = getBlockChunk(chunk, i + xChunkStartBlock, columnHeight, j + zChunkStartBlock)
                                data = getBlockDataChunk(chunk, i + xChunkStartBlock, columnHeight, j + zChunkStartBlock)
                                if not (getMapColorIndex(block, data) == 0 and columnHeight > 0):
                                    break
                            
                            # Sub-surface stuff
                            if (columnHeight > 0 and block in liquids):
                                subHeight = columnHeight - 1
                                
                                while True:
                                    subBlock = getBlockChunk(chunk, i + xChunkStartBlock, subHeight, j + zChunkStartBlock)
                                    subHeight -= 1
                                    subBlockPixelAverage += 1
                                    if not (subHeight > 0 and subBlock in liquids):
                                        break
                                        
                        # Make sure this stuff is floats
                        averageColumnHeight += float(columnHeight) / (blocksPerPixel * blocksPerPixel)
                        colorCounter[getMapColorIndex(block, data)] += 1
                        
            subBlockPixelAverage /= blocksPerPixel * blocksPerPixel

            brightnessValue = (averageColumnHeight - prevAverageColumnHeight) * 4.0 / (blocksPerPixel + 4) + ((xPixel + zPixel & 1) - 0.5) * 0.4

            brightnessIndex = 1

            if brightnessValue > 0.6:
                brightnessIndex = 2
            if brightnessValue < -0.6:
                brightnessIndex = 0

            # The maps are not perfect because when there is a draw
            # pythons Counter does not give the same order as
            # Guava's HashMultiet
            baseColor = colorCounter.most_common(1)[0][0]

            # Water
            if baseColor == 12:
                brightnessValue = subBlockPixelAverage * 0.1 + (xPixel + zPixel & 1) * 0.2
                
                brightnessIndex = 1
                
                if brightnessValue < 0.5:
                    brightnessIndex = 2
                if brightnessValue > 0.9:
                    brightnessIndex = 0

            prevAverageColumnHeight = averageColumnHeight
            
            
            mapColor = baseColor * 4 + brightnessIndex                    
            colors[xPixel + 128*zPixel] = mapColor

def getBlockChunk(chunk, x, y, z):
    # [x, z, y]
    # Assuming anvil, might not work for others
    return chunk.Blocks[x, z, y]

def getBlockDataChunk(chunk, x, y, z):
    return chunk.Data[x, z, y]

# Maps id, data to their map colour
def getMapColorIndex(blockid, data=0):
    #~ try:
        #~ return colorMap[(blockid, data)]
    #~ except KeyError:
        #~ try:
            #~ return colorMap[(blockid, 0)]
        #~ except KeyError:
            #~ # Default of stone colour
            #~ return 11
    return mapColours[blockid, data]

colorMap = {
    (0, 0) : 0,
    (1, 0) : 11,
    (2, 0) : 1,
    (3, 0) : 10,
    (4, 0) : 11,
    (5, 0) : 13,
    (6, 0) : 7,
    (7, 0) : 11,
    (8, 0) : 12,
    (9, 0) : 12,
    (10, 0) : 4,
    (11, 0) : 4,
    (12, 0) : 2,
    (12, 1) : 10,
    (13, 0) : 2,
    (14, 0) : 11,
    (15, 0) : 11,
    (16, 0) : 11,
    (17, 0) : 13,
    (18, 0) : 7,
    (19, 0) : 3,
    (20, 0) : 0,
    (21, 0) : 11,
    (22, 0) : 32,
    (23, 0) : 11,
    (24, 0) : 11,
    (25, 0) : 13,
    (26, 0) : 3,
    (27, 0) : 0,
    (28, 0) : 0,
    (29, 0) : 11,
    (30, 0) : 3,
    (31, 0) : 7,
    (32, 0) : 7,
    (33, 0) : 11,
    (34, 0) : 11,
    (35, 0) : 8,
    (35, 1) : 15,
    (35, 2) : 16,
    (35, 3) : 17,
    (35, 4) : 18,
    (35, 5) : 19,
    (35, 6) : 20,
    (35, 7) : 21,
    (35, 8) : 22,
    (35, 9) : 23,
    (35, 10) : 24,
    (35, 11) : 25,
    (35, 12) : 26,
    (35, 13) : 27,
    (35, 14) : 28,
    (35, 15) : 29,
    (36, 0) : 11,
    (37, 0) : 7,
    (38, 0) : 7,
    (39, 0) : 7,
    (40, 0) : 7,
    (41, 0) : 30,
    (42, 0) : 6,
    (43, 0) : 11,
    (44, 0) : 11,
    (45, 0) : 11,
    (46, 0) : 4,
    (47, 0) : 13,
    (48, 0) : 11,
    (49, 0) : 34,
    (50, 0) : 0,
    (51, 0) : 4,
    (52, 0) : 11,
    (53, 0) : 13,
    (54, 0) : 13,
    (55, 0) : 0,
    (56, 0) : 11,
    (57, 0) : 31,
    (58, 0) : 13,
    (59, 0) : 7,
    (60, 0) : 10,
    (61, 0) : 11,
    (62, 0) : 11,
    (63, 0) : 13,
    (64, 0) : 13,
    (65, 0) : 0,
    (66, 0) : 0,
    (67, 0) : 11,
    (68, 0) : 13,
    (69, 0) : 0,
    (70, 0) : 11,
    (71, 0) : 6,
    (72, 0) : 13,
    (73, 0) : 11,
    (74, 0) : 11,
    (75, 0) : 0,
    (76, 0) : 0,
    (77, 0) : 0,
    (78, 0) : 8,
    (79, 0) : 5,
    (80, 0) : 8,
    (81, 0) : 7,
    (82, 0) : 9,
    (83, 0) : 7,
    (84, 0) : 13,
    (85, 0) : 13,
    (86, 0) : 7,
    (87, 0) : 35,
    (88, 0) : 2,
    (89, 0) : 2,
    (90, 0) : 0,
    (91, 0) : 7,
    (92, 0) : 0,
    (93, 0) : 0,
    (94, 0) : 0,
    (95, 0) : 0,
    (96, 0) : 13,
    (97, 0) : 9,
    (98, 0) : 11,
    (99, 0) : 13,
    (100, 0) : 13,
    (101, 0) : 6,
    (102, 0) : 0,
    (103, 0) : 7,
    (104, 0) : 7,
    (105, 0) : 7,
    (106, 0) : 7,
    (107, 0) : 13,
    (108, 0) : 11,
    (109, 0) : 11,
    (110, 0) : 1,
    (111, 0) : 7,
    (112, 0) : 11,
    (113, 0) : 11,
    (114, 0) : 11,
    (115, 0) : 7,
    (116, 0) : 11,
    (117, 0) : 6,
    (118, 0) : 6,
    (119, 0) : 34,
    (120, 0) : 11,
    (121, 0) : 11,
    (122, 0) : 7,
    (123, 0) : 0,
    (124, 0) : 0,
    (125, 0) : 13,
    (126, 0) : 13,
    (127, 0) : 7,
    (128, 0) : 11,
    (129, 0) : 11,
    (130, 0) : 11,
    (131, 0) : 0,
    (132, 0) : 0,
    (133, 0) : 33,
    (134, 0) : 13,
    (135, 0) : 13,
    (136, 0) : 13,
    (137, 0) : 6,
    (138, 0) : 0,
    (139, 0) : 11,
    (140, 0) : 0,
    (141, 0) : 7,
    (142, 0) : 7,
    (143, 0) : 0,
    (144, 0) : 0,
    (145, 0) : 6,
    (146, 0) : 13,
    (147, 0) : 6,
    (148, 0) : 6,
    (149, 0) : 0,
    (150, 0) : 0,
    (151, 0) : 13,
    (152, 0) : 4,
    (153, 0) : 11,
    (154, 0) : 6,
    (155, 0) : 14,
    (156, 0) : 14,
    (157, 0) : 0,
    (158, 0) : 11,
    (159, 0) : 8,
    (159, 1) : 15,
    (159, 2) : 16,
    (159, 3) : 17,
    (159, 4) : 18,
    (159, 5) : 19,
    (159, 6) : 20,
    (159, 7) : 21,
    (159, 8) : 22,
    (159, 9) : 23,
    (159, 10) : 24,
    (159, 11) : 25,
    (159, 12) : 26,
    (159, 13) : 27,
    (159, 14) : 28,
    (159, 15) : 29,
    (160, 0) : 0,
    (161, 0) : 7,
    (162, 0) : 13,
    (163, 0) : 13,
    (164, 0) : 13,
    (170, 0) : 1,
    (171, 0) : 3,
    (172, 0) : 15,
    (173, 0) : 11,
    (174, 0) : 5,
    (175, 0) : 7
}

placedIDsMask = numpy.zeros((256, 16), bool)
mapColours = numpy.zeros((256, 16), numpy.ubyte)
for (blockID, data), mapColour in colorMap.iteritems():
    mapColours[blockID, data] = mapColour
    placedIDsMask[blockID, data] = True

for (blockID, data), mask in numpy.ndenumerate(placedIDsMask):
    if not mask:
        if placedIDsMask[blockID, 0]:
            mapColours[blockID, data] = mapColours[blockID, 0]
        else:
            mapColours[blockID, data] = 11

# List of liquid ids
liquids = (8, 9, 10, 11)
