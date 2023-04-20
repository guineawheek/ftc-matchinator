import numpy as np

# FIRST Energize Logo match threshold (0.0-1.0)
ENERGIZE_LOGO_MATCH_THR = 0.8

PP_CAP_THR = 0.6

# match preview red/blue threshold
MATCH_PREVIEW_THR = 0.7

# match window threshold
MATCH_TOTAL_SCORE_THR = 0.6

# for match entry grouping in pass2
MATCH_GROUP_MIN_COUNT = 5

# number of seconds to clip a match before auto
MATCH_PRE_AUTO_START = 3

# 
MATCH_POST_TELE_END = 5

class ScaledParams:
    """Returns an object that scales constants appropriately."""
    def __init__(self, in_width, in_height):
        self.in_width = in_width
        self.in_height = in_height

        # base dimensions used
        self.BASE_IMSIZE = np.array([1920, 1080])

        # functions that will scale
        SCALEX = lambda x: int(x * self.in_width / self.BASE_IMSIZE[0])
        SCALEY = lambda y: int(y * self.in_height / self.BASE_IMSIZE[1])

        self.scalex = SCALEX
        self.scaley = SCALEY


        self.NAME_LEFT_OFFSET       = SCALEX(340)  # offset from left side of energize logo
        self.NAME_WIDTH             = SCALEX(460)  # width of match name window
        self.NAME_HEIGHT            = SCALEY(60)   # height of match name window
        self.DISPLAY_HEIGHT         = SCALEY(180)  # height of entire match display

        # match cap window constants -- used to detect if a PP match is in teleop or auto
        self.CAP_WIDTH              = SCALEX(100)  # width of match cap detection windows
        self.CAP_RIGHT_OFFSET       = SCALEX(960 + 470)  # left edge of right offset
        self.CAP_LEFT_OFFSET        = SCALEX(960 - 470 - 100)  # left edge of left offset

        self.TIMER_HEIGHT           = SCALEY(44)
        self.TIMER_WIDTH            = SCALEX(90)
        self.TIMER_LEFT_OFFSET      = SCALEX(915)
        self.TIMER_EDGE_OFFSET      = SCALEY(6)

        # it's not red or blue alliance as colors can be swapped
        self.LEFT_ALLIANCE_OFFSET   = SCALEX(489) 
        self.RIGHT_ALLIANCE_OFFSET  = SCALEX(1275)
        self.ALLIANCE_WIDTH         = SCALEX(154)

        self.LEFT_TOTAL_SCORE_OFFSET = SCALEX(647)
        self.LEFT_TOTAL_SCORE_WIDTH  = SCALEX(212)
        self.LEFT_TOTAL_SCORE_HEIGHT = SCALEY(123)