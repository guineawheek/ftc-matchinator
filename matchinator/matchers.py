import cv2
import numpy as np
from pathlib import Path
from . import consts
import os

class TemplateMatcher:
    """base class for grayscale image template matching
    handles downscaling and matching a single object 
    """ 
    def real_init(self, in_width, in_height, template, scale_size=(1280, 720), threshold=0.5):
        self.width = in_width
        self.height = in_height
        self.threshold = threshold
        self.scale_size = scale_size


        # calculate
        self.compare_size = (min(scale_size[0], self.width), min(scale_size[1], self.height))
        self.compare_ratio = (self.compare_size[0] / self.width, self.compare_size[1] / self.height)

        self.template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        self.scaled_template = cv2.resize(self.template, (int(self.template.shape[1] * self.compare_ratio[0]),
                                                          int(self.template.shape[0] * self.compare_ratio[1])))

    def match(self, frame):
        """
        returns True, ((tl_x, tl_y), (w, h)) if match else False, None
        """
        _, max_val, __, max_loc = cv2.minMaxLoc(self.match_template(frame))
        if max_val >= self.threshold:
            tl = (int(max_loc[0] / self.compare_ratio[0]), int(max_loc[1] / self.compare_ratio[1]))
            wh = (self.template.shape[1], self.template.shape[0])
            return True, (tl, (tl[0] + wh[0], tl[1] + wh[1]))
        else:
            return False, None
    
    def match_template(self, frame):
        """return cv2.matchTemplate results"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        scaled = cv2.resize(gray, (int(gray.shape[1] * self.scale_size[0] / self.width), int(gray.shape[0] * self.scale_size[1] / self.height)))
        return cv2.matchTemplate(scaled, self.scaled_template, cv2.TM_CCOEFF_NORMED)

class ParamMatcher(TemplateMatcher):
    THRESH = 0.8
    IMG_PATH = "templates/en.png"
    def __init__(self, params: consts.ScaledParams, en_name=None):
        en_name = en_name or str(Path(os.path.dirname(__file__))/self.IMG_PATH)
        template = cv2.imread(en_name)
        template = cv2.resize(template, (params.scalex(template.shape[1]), params.scaley(template.shape[0])))

        self.real_init(params.in_width, params.in_height, template, threshold=self.THRESH)


class EnergizeLogoMatcher(ParamMatcher):
    """looks for and matches the FIRST Energize logo in video frames"""
    IMG_PATH = "templates/en.png"
    THRESH = consts.ENERGIZE_LOGO_MATCH_THR

class PPCapMatcher(ParamMatcher):
    """looks for and matches the Power Play unscored cap image in video frames"""
    IMG_PATH = "templates/cap_unscored.png"
    THRESH = consts.PP_CAP_THR
    def exists(self, match_display, params: consts.ScaledParams):
        """
        Checks if the endgame caps exist, as this determines if this is auto/switchover or teleop. 
        Will work on scored caps even though they are colored differently 

        match_display: as returned by get_match_display
        params: ScaledParams 
        """
        left_win = match_display[:, params.CAP_LEFT_OFFSET:params.CAP_LEFT_OFFSET + params.CAP_WIDTH, :]
        right_win = match_display[:, params.CAP_RIGHT_OFFSET:params.CAP_RIGHT_OFFSET + params.CAP_WIDTH, :]

        left_matches = self.match_template(left_win)
        right_matches = self.match_template(right_win)

        return np.any(left_matches > self.THRESH) or np.any(right_matches > self.THRESH) #, np.max(left_matches), np.max(right_matches)
        #return util.DictStruct(locals())


class BlobMatcher:
    """finds lists of blobs based on HSV color values, like those retroreflective tape finders :3"""

    # predefined colors that are commonly used in the match display
    colors = {
        "red": 179,
        "blue": 103, 
        "tan": 21,
    }

    @classmethod
    def threshold(cls, frame, hue, tolerance=5):
        """thresholds an image by hue plus-minus the tolerance. returns same size numpy array."""
        hue = cls.colors.get(hue, hue)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        thr = cv2.inRange(hsv, (max(hue - tolerance, 0), 0, 0), (min(hue + tolerance, 255), 255, 255))

        # handle wraparound
        if (hue - tolerance) < 0:
            thr2 = cv2.inRange(hsv, ((256 + hue - tolerance) % 256, 0, 0), (255, 255, 255))
            thr = cv2.bitwise_or(thr, thr2)

        if (hue + tolerance) > 255:
            thr2 = cv2.inRange(hsv, (0, 0, 0), ((hue + tolerance) % 256, 255, 255))
            thr = cv2.bitwise_or(thr, thr2)
        return thr

    @classmethod
    def find_contours(cls, frame, hue, tolerance=5):
        contours, _ = cv2.findContours(cls.threshold(frame, hue, tolerance=tolerance), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        return contours

