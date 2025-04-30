import numpy as np

# Sesaon logo match threshold (0.0-1.0)
LOGO_MATCH_THR = 0.7

PP_CAP_THR = 0.6

# match preview red/blue threshold
MATCH_PREVIEW_THR = 0.7

# match window threshold
MATCH_TOTAL_SCORE_THR = 0.6

# for match entry grouping in pass2
MATCH_GROUP_MIN_COUNT = 5

# number of seconds to clip a match before auto
MATCH_PRE_AUTO_START = 4

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

        # Basic dimensions.
        self.WIDTH                  = SCALEX(1920)
        self.HEIGHT                 = SCALEY(1080)

        self.SEASON_LOGO_WIDTH      = SCALEX(170)
        self.NAME_LEFT_OFFSET       = SCALEX(784)  # offset from left side of season logo
        self.NAME_WIDTH             = SCALEX(780)  # width of match name window
        self.NAME_HEIGHT            = SCALEY(60)   # height of match name window
        self.DISPLAY_HEIGHT         = SCALEY(180)  # height of entire match display

        # center timer ROI; used to determine if we're in a match or not, and the time
        self.CENTER_TIMER_LEFT      = SCALEX(860)
        self.CENTER_TIMER_TOP       = SCALEY(0)
        self.CENTER_TIMER_WIDTH     = SCALEX(202)
        self.CENTER_TIMER_HEIGHT    = SCALEY(178)
        self.CENTER_TIMER_VALUE_TOP = SCALEY(75)

        # it's not red or blue alliance as colors can be swapped
        self.LEFT_ALLIANCE_OFFSET   = SCALEX(489) 
        self.RIGHT_ALLIANCE_OFFSET  = SCALEX(1295)
        self.ALLIANCE_WIDTH         = SCALEX(142)

        self.LEFT_TOTAL_SCORE_OFFSET = SCALEX(647)
        self.LEFT_TOTAL_SCORE_WIDTH  = SCALEX(200)
        self.LEFT_TOTAL_SCORE_HEIGHT = SCALEY(158)

        self.RESULT_QR_LEFT          = SCALEX(716)
        self.RESULT_QR_TOP           = SCALEY(780)
        self.RESULT_QR_WIDTH         = SCALEX(168)
        self.RESULT_QR_HEIGHT        = SCALEY(168)