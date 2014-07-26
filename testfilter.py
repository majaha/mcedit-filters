import time
import pymclevel.nbt as nbt
from pymclevel.nbt import *

displayName = "Test Filter"

foo = (
  ("Makes water in the region flood outwards and downwards, becoming full source blocks in the process. This is similar to Minecraft Classic water.", "label"),
  ("Flood Water", True),
  ("Flood Lava", False),
)

bar = (
  ("Depth", (4, -128, 128)),
  ("Pick a block:", "blocktype"),
  ("Fractal complexity", 15.0),
  ("Enable thrusters", True),
  ("Access method", ("Use blockAt", "Use temp schematic", "Use chunk slices")),
  ("Spam", "title")
)

baz = (
    ("foobar "*100, "label"),
)


bla = (("eggs", "string"),
    # Width is pixel width
    ("spam", ("string", "value=foobaz", "lines=5", "width=500"))
)

inputs = [foo, bar, baz, bla]

def perform(level, box, options):
    
    def foobar():
        #yield 2, 5, "bla"
        for i in xrange(1, 11):
            time.sleep(.4)
            yield i, 10, "foobar"+ str(i)
            #yield None
    
    #level.showProgress("Testingfoo...", foobar())
    
    
    #~ for (chunk, slices, point) in level.getChunkSlices(box):
        #~ for tileEnt in chunk.getTileEntitiesInBox(box):
            #~ print tileEnt["id"]
    #~ 
    #~ idcountsPath = level.worldFolder.getFilePath("data/idcounts.dat")
    #~ idcounts = nbt.load(idcountsPath)
    #~ print idcounts["map"].value
    
    def makeItemFrameEntity(x, y, z, facing, itemtag=None, itemRotation=0):
        itemFrame = TAG_Compound()
        itemFrame["id"] = TAG_String(u'ItemFrame')
        pos = TAG_List()
        pos.append(TAG_Double(x + 0.5 + 0.4375*[0, 1, 0, -1][facing]))
        pos.append(TAG_Double(y + 0.5))
        pos.append(TAG_Double(z + 0.5))# + 0.4375*[-1, 0, 1, 0][facing]))
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
    
    item = nbt.TAG_Compound()
    item["id"] = "minecraft:filled_map"
    item["Count"] = nbt.TAG_Byte(1)
    item["Damage"] = nbt.TAG_Short(1)
    
    for ent in level.getEntitiesInBox(box):
        print ent
    
    #level.addEntity(makeItemFrameEntity(box.minx, box.miny, box.minz, 0, item, 1))
