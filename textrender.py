import pymclevel #etc...

# should think about redifining direction in all my scripts, so as to match up
# with in-game direction.

import string

displayName = "Create Text"
inputs = (
    ("Text", "string"),
    ("Block Type", ("Stone Brick",
                    "Cobblestone",
                    "Sandstone",
                    "Brick",
                    "Nether Brick",
                    "Quartz",
                    "Oak Planks",
                    "Spruce Planks",
                    "Birch Planks",
                    "Jungle Planks",
                    )
     ),
    ("Direction", ("North", "East", "South", "West"))
)
    
def perform(level, box, options):
    text = options["Text"]
    texId = options["Block Type"]
    direction = {"North":2,"East":3,"South":0,"West":1}[options["Direction"]]
    canvas = MCEditCanvas(level, box, direction)
    printText(canvas, text, texId)

class MCEditCanvas:
    def __init__(self, level, box, direction):
        if not ((box.maxz-box.minz == 1 and direction in (0, 2))
                or (box.maxx-box.minx == 1 and direction in (1, 3))):
            raise CanvasError("Box or direction incorrect.")
        self.level = level
        self.box = box
        self.direction = direction
        self.height = box.height
        if direction in (0, 2):
            self.width = box.width
        elif direction in (1, 3):
            self.width = box.length

        self.y0 = box.maxy - 1
        if direction == 0:
            self.x0 = box.maxx - 1
            self.z0 = box.minz
        elif direction == 1:
            self.x0 = box.minx
            self.z0 = box.maxz - 1
        elif direction == 2:
            self.x0 = box.minx
            self.z0 = box.minz
        elif direction == 3:
            self.x0 = box.minx
            self.z0 = box.minz
            
        

    def inCanvas(self, w, h):
        return 0 <= w < self.width and 0 <= h < self.height

    def getBlock(self, w, h):
        if self.inCanvas(w, h):
            return self.level.blockAt(self.getWorldCoords(w, h))
        else:
            raise CanvasError("Block access out of bounds")

    def getBlockWithData(self, w, h):
        if self.inCanvas(w, h):
            return (self.level.blockAt(*self.getWorldCoords(w, h)),
                    self.level.blockDataAt(*self.getWorldCoords(w, h)))
        else:
            raise CanvasError("Block access out of bounds")

    def setBlock(self, w, h, blockId, data=0):
        if self.inCanvas(w, h):
            self.level.setBlockAt(*self.getWorldCoords(w, h), blockID=blockId)
            self.level.setBlockDataAt(*self.getWorldCoords(w, h), newdata=data)
        else:
            raise CanvasError("Block access out of bounds")

    def setBlocks(self, w0, h0, w1, h1, blockId, data=0):
        if self.inCanvas(w, h):
            origin = self.getWorldCoords(w0, h0)
            size = tuple(b - a for a, b in zip(self.getWorldCoords(w0, h0),
                                               self.getWorldCoords(w1, h1)))
            fillbox = pymclevel.BoundingBox(origin, size)
            self.level.fillBlocks(fillbox, level.materials.blockWithID(blockID, data))
        else:
            raise CanvasError("Block access out of bounds")

    def getWorldCoords(self, w, h):
        if self.direction % 4 == 0:
            return (self.x0 - w, self.y0 - h, self.z0) # decreasing x
        elif self.direction % 4 == 1:
            return (self.x0, self.y0 - h, self.z0 - w) # decreasing z
        elif self.direction % 4 == 2:
            return (self.x0 + w, self.y0 - h, self.z0) # increasing x
        elif self.direction % 4 == 3:
            return (self.x0, self.y0 - h, self.z0 + w) # increasing z

class CanvasError(Exception):
    pass

def printText(canvas, text, texture=4):
    text = text.lower()
    
    dWidth = 0
    for char in text:
        for i in xrange(0, len(characters[char])):
            for j in xrange(0, len(characters[char][0])):
                canvas.setBlock(dWidth+j, i, *getBlock(characters[char][i][j],
                                                      canvas.direction, texture))
        dWidth += len(characters[char][0]) + 1

def getBlock(chrPartId, direction, texture):

    stairDirectionIds = (
        (1, 0, 4, 5),
        (3, 2, 6, 7),
        (0, 1, 5, 4),
        (2, 3, 7, 6),
        )
    
    blockIds = textureTypes[texture]
    
    if chrPartId == 0:
        return (0, 0) # Air
    elif chrPartId == 1:
        return blockIds[0] # Solid block
    elif chrPartId == 2:
        return blockIds[1] # Bottom-slab
    elif chrPartId == 3:
        return (blockIds[1][0], blockIds[1][1] + 8) # Top-slab
    elif chrPartId == 4: # bottom left - top right normal stair
        return (blockIds[2][0], stairDirectionIds[direction % 4][0])
    elif chrPartId == 5: # bottom right - top left normal stair
        return (blockIds[2][0], stairDirectionIds[direction % 4][1])
    elif chrPartId == 6: # bottom left - top right upside-down stair
        return (blockIds[2][0], stairDirectionIds[direction % 4][2])
    elif chrPartId == 7: # bottom right - top left upside-down stair
        return (blockIds[2][0], stairDirectionIds[direction % 4][3])
    else:
        raise ValueError


def getAlphabet():
    return string.ascii_lowercase

# Matches texture ids/names with a tuple of block ids and data
# for the different blocks with that texture: (block, slab, stair).
# Slab is the block representing the bottom slab of that texture.
# Stair has the data value 0.
# 8 is added to the data for the top slab.
# The ids are mostly in the same order as the block ids are,
# apart from oak planks.
# Id 1 is the "old" wood, used in pi edition as it does not have
# different wood types.
textureTypes = {
    0: ((4, 0), (44, 3), (67, 0)), #cobble
    1: ((5, 0), (44, 2), (53, 0)), #Old wood planks
    2: ((24, 0), (44, 1), (128, 0)), #sandstone
    3: ((45, 0), (44, 4), (108, 0)), #brick
    4: ((98, 0), (44, 5), (109, 0)), #stone brick
    5: ((112, 0), (44, 6), (114, 0)), #nether brick
    6: ((155, 0), (44, 7), (156, 0)), #quartz
    7: ((5, 0), (126, 0), (53, 0)), #oak planks
    8: ((5, 1), (126, 1), (134, 0)), #spruce planks
    9: ((5, 2), (126, 2), (135, 0)), #birch planks
    10: ((5, 3), (126, 3), (136, 0)), #jungle planks
    "COBBLESTONE": ((4, 0), (44, 3), (67, 0)),
    "WOOD_PLANKS": ((5, 0), (44, 2), (53, 0)),
    "SANDSTONE": ((24, 0), (44, 1), (128, 0)),
    "BRICK_BLOCK": ((45, 0), (44, 4), (108, 0)),
    "STONE_BRICK": ((98, 0), (44, 5), (109, 0)),
    "NETHER_BRICK": ((112, 0), (44, 6), (114, 0)),
    "QUARTZ_BLOCK": ((155, 0), (44, 7), (156, 0)),
    "OAK_PLANKS": ((5, 0), (126, 0), (53, 0)),
    "SPRUCE_PLANKS": ((5, 1), (126, 1), (134, 0)),
    "BIRCH_PLANKS": ((5, 2), (126, 2), (135, 0)),
    "JUNBLE_PLANKS": ((5, 3), (126, 3), (136, 0)),
    "Cobblestone": ((4, 0), (44, 3), (67, 0)),
    "Wood Planks": ((5, 0), (44, 2), (53, 0)),
    "Sandstone": ((24, 0), (44, 1), (128, 0)),
    "Brick": ((45, 0), (44, 4), (108, 0)),
    "Stone Brick": ((98, 0), (44, 5), (109, 0)),
    "Nether Brick": ((112, 0), (44, 6), (114, 0)),
    "Quartz": ((155, 0), (44, 7), (156, 0)),
    "Oak Planks": ((5, 0), (126, 0), (53, 0)),
    "Spruce Planks": ((5, 1), (126, 1), (134, 0)),
    "Birch Planks": ((5, 2), (126, 2), (135, 0)),
    "Jungle Planks": ((5, 3), (126, 3), (136, 0)),
    }


##0 = Air
##1 = solid block
##2 = bottom slab
##3 = top slab
##4 = bottom left to top right right-way-up stair
##5 = bottom right to top left right-way-up stair
##6 = bottom left to top right upside-down stair
##7 = bottom right to top left upside-down stair
characters = {
    "a": (
        (4, 3, 5),
        (1, 2, 1),
        (1, 0, 1),
        ),
    "b": (
        (1, 3, 5),
        (1, 3, 5),
        (1, 2, 6),
        ),
    "c": (
        (4, 6, 3),
        (1, 0, 0),
        (7, 5, 2),
        ),
    "d": (
        (1, 3, 5),
        (1, 0, 1),
        (1, 2, 6),
        ),
    "e": (
        (1, 3, 3),
        (1, 2, 0),
        (1, 2, 2),
        ),
    "f": (
        (1, 3, 3),
        (1, 2, 0),
        (1, 0, 0),
        ),
    "g": (
        (4, 3, 5),
        (1, 0, 2),
        (7, 2, 4),
        ),
    "h": (
        (1, 0, 1),
        (1, 2, 1),
        (1, 0, 1),
        ),
    "i": (
        (3, 1, 3),
        (0, 1, 0),
        (2, 1, 2),
        ),
    "j": (
        (0, 3, 1),
        (0, 0, 1),
        (7, 2, 6),
        ),
    "k": (
        (1, 0, 6),
        (1, 1, 0),
        (1, 0, 5),
        ),
    "l": (
        (1, 0, 0),
        (1, 0, 0),
        (1, 2, 2),
        ),
    "m": (
        (1, 5, 4, 1),
        (1, 7, 6, 1),
        (1, 0, 0, 1),
        ),
    "n": (
        (1, 5, 0, 1),
        (1, 7, 5, 1),
        (1, 0, 7, 1),
        ),
    "o": (
        (4, 1, 5),
        (1, 0, 1),
        (7, 1, 6),
        ),
    "p": (
        (1, 3, 5),
        (1, 2, 6),
        (1, 0, 0),
        ),
    "q": (
        (4, 3, 5),
        (1, 0, 1),
        (7, 4, 5),
        ),
    "r": (
        (1, 3, 5),
        (1, 2, 6),
        (1, 0, 5),
        ),
    "s": (
        (4, 3, 3),
        (7, 1, 5),
        (2, 2, 6),
        ),
    "t": (
        (3, 1, 3),
        (0, 1, 0),
        (0, 1, 0),
        ),
    "u": (
        (1, 0, 1),
        (1, 0, 1),
        (7, 2, 6),
        ),
    "v": (
        (5, 0, 4),
        (7, 2, 6),
        (0, 1, 0),
        ),
    "w": (
        (1, 0, 0, 1),
        (1, 4, 5, 1),
        (7, 6, 7, 6),
        ),
    "x": (
        (7, 2, 6),
        (0, 1, 0),
        (4, 3, 5),
        ),
    "y": (
        (5, 0, 4),
        (0, 7, 6),
        (2, 6, 0),
        ),
    "z": (
        (6, 7, 6),
        (0, 1, 0),
        (4, 5, 4),
        ),
    "1": (
        (4, 1, 0),
        (0, 1, 0),
        (2, 1, 2),
        ),
    "2": (
        (4, 7, 5),
        (0, 2, 1),
        (4, 1, 2),
        ),
    "3": (
        (4, 7, 5),
        (0, 4, 6),
        (2, 4, 6),
        ),
    "4": (
        (1, 0, 1),
        (1, 2, 1),
        (0, 0, 1),
        ),
    "5": (
        (1, 3, 3),
        (3, 7, 5),
        (2, 2, 1),
        ),
    "6": (
        (4, 3, 5),
        (1, 2, 2),
        (7, 2, 6),
        ),
    "7": (
        (3, 3, 1),
        (0, 4, 6),
        (4, 6, 0),
        ),
    "8": (
        (4, 3, 5),
        (4, 3, 5),
        (7, 2, 6),
        ),
    "9": (
        (4, 3, 5),
        (3, 3, 1),
        (7, 2, 6),
        ),
    "0": (
        (4, 3, 5),
        (1, 0, 1),
        (7, 2, 6),
        ),
    "1s": ( # Small one, for 10, 11, 12 etc
        (4, 1),
        (0, 1),
        (2, 1),
        ),
    " ": (
        (0,),
        (0,),
        (0,),
        ),
    "!": (
        (1,),
        (1,),
        (2,),
        ),
    ".": (
        (0,),
        (0,),
        (1,),
        ),
    ",": (
        (0,),
        (0,),
        (4,),
        ),
    "?": (
        (4, 3, 5),
        (0, 2, 6),
        (0, 2, 0),
        ),
    "\"": (
        (7, 7),
        (0, 0),
        (0, 0),
        ),
    "'": (
        (4,),
        (0,),
        (0,),
        ),
    "+": (
        (0, 1, 0),
        (1, 1, 1),
        (0, 1, 0),
        ),
    "-": (
        (0, 0),
        (2, 2),
        (0, 0),
        ),
    "/": ( # In place of divide
        (0, 2, 0),
        (2, 2, 2),
        (0, 2, 0),
        ),
    "*": ( # In place of multiply
        (7, 0, 6),
        (0, 1, 0),
        (4, 0, 5),
        ),
    "=": (
        (0, 0),
        (3, 3),
        (3, 3),
        ),
    }
