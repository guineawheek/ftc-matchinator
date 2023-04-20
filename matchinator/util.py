import numpy as np
import cv2
import pytesseract
from . import consts
from .matchers import BlobMatcher

class DictStruct:
    """helper class that converts a dict into an object"""
    def __init__(self, fields):
        self.__dict__ = fields
        self._dict = fields

def timef(ms):
    """formats millisecond times nicely"""
    ts = ms // 1000
    hour = int(ts // 3600)
    minute = int((ts // 60) % 60)
    second = int(ts % 60)
    return f"{hour:02}:{minute:02}:{second:02}.{ms % 1000:.6f}"

def isint(v):
    try:
        int(v)
        return True
    except ValueError:
        return False

def tlwh_to_tlbr(tl, wh):
    """convert ((x_left, y_top), (width, height)) to ((x_left, y_top), (x_right, y_bottom))"""
    return (tl, wh), (tl[0] + wh[0], tl[1] + wh[1])

def crop_rect(img, xrange, yrange):
    """img: img
    xrange: (xs, xlen) or None
    yrange: (ys, ylen) or None

    return img[ys:ys + ylen, xs:xs + xlen, :]
    """
    if xrange is None:
        if yrange is None:
            return img
        return img[yrange[0]:yrange[0] + yrange[1], :, :]
    elif yrange is None:
        return img[:, xrange[0]:xrange[0] + xrange[1], :]
    return img[yrange[0]:yrange[0] + yrange[1], xrange[0]:xrange[0] + xrange[1], :]
    
    

def get_match_display(frame, match_tlbr, params: consts.ScaledParams):
    """crops the lower match display from the frame"""
    tl, br = match_tlbr
    height = params.DISPLAY_HEIGHT
    if tl[1] < frame.shape[0] / 2:
        return frame[max(tl[1] - height, 0):tl[1], :, :], True
    else:
        return frame[br[1]:br[1] + height, :, :], False

def match_is_preview(match_display):
    # this looks at the match display and checks if it's currently mostly red and blue
    # if so, then we're looking at a match preview
    blob_size = (np.count_nonzero(BlobMatcher.threshold(match_display, "blue"))
                + np.count_nonzero(BlobMatcher.threshold(match_display, "red")))

    return blob_size / (match_display.shape[0] * match_display.shape[1]) >= consts.MATCH_PREVIEW_THR

def extract_text(img, pyts_config=None):
    """Extracts text from BGR image."""
    if not pyts_config:
        pyts_config = {}
    return pytesseract.image_to_string(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), **pyts_config)

def extract_match_name(frame, match_tlbr, params: consts.ScaledParams):
    """returns (text, image used)"""
    tl, br = match_tlbr

    #name_frame = frame[tl[1]:tl[1] + params.MATCH_NAME_HEIGHT, 
    #            tl[0] + params.MATCH_NAME_LEFT_OFFSET:tl[0] + params.MATCH_NAME_LEFT_OFFSET + params.MATCH_NAME_WIDTH, :]
    name_frame = crop_rect(frame, (tl[0] + params.NAME_LEFT_OFFSET, params.NAME_WIDTH), (tl[1], params.NAME_HEIGHT))
    
    return extract_text(name_frame, {"config": "--psm 6"}).strip(), name_frame

def extract_match_time(match_display, is_top, params: consts.ScaledParams):

    if is_top:
        time_top = params.TIMER_EDGE_OFFSET
        time_bottom = time_top + params.TIMER_HEIGHT
    else:
        time_top = match_display.shape[0] - params.TIMER_EDGE_OFFSET - params.TIMER_HEIGHT
        time_bottom = match_display.shape[0] - params.TIMER_EDGE_OFFSET
    match_time = match_display[time_top:time_bottom, params.TIMER_LEFT_OFFSET:params.TIMER_LEFT_OFFSET + params.TIMER_WIDTH, :]

    # use the traditional matcher, since we only want to allow digits and it may work better 
    return extract_text(match_time, {"config": "--psm 6"}).strip(), match_time

def extract_match_teams(match_display, params: consts.ScaledParams):
    #left_display = match_display[:, params.MATCH_LEFT_ALLIANCE_OFFSET:params.MATCH_LEFT_ALLIANCE_OFFSET+params.MA]
    left_display = crop_rect(match_display, (params.LEFT_ALLIANCE_OFFSET, params.ALLIANCE_WIDTH), None)
    right_display = crop_rect(match_display, (params.RIGHT_ALLIANCE_OFFSET, params.ALLIANCE_WIDTH), None)

    left_teams = extract_text(left_display).strip().split()
    right_teams = extract_text(right_display).strip().split()


    return left_teams, right_teams

def are_colors_flipped(match_display, params: consts.ScaledParams):
    sthresh = BlobMatcher.threshold(crop_rect(match_display, (params.LEFT_TOTAL_SCORE_OFFSET, params.LEFT_TOTAL_SCORE_WIDTH), (0, params.LEFT_TOTAL_SCORE_HEIGHT)), "blue")

    return np.count_nonzero(sthresh) / (sthresh.shape[0] * sthresh.shape[1]) < consts.MATCH_PREVIEW_THR
