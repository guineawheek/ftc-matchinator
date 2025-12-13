import dataclasses
import numpy as np
import cv2
import pytesseract
from . import consts
from .matchers import BlobMatcher, ITDRedBasketMatcher

@dataclasses.dataclass
class DisplayData:
    display_flipped: bool
    red_teams: tuple[str]
    blue_teams: tuple[str]

class DictStruct:
    """helper class that converts a dict into an object"""
    def __init__(self, fields):
        self.__dict__ = fields
        self._dict = fields

def hms2f(h=0, m=0, s=0, fps=30) -> int:
    return int((h * 60 * 60 + m * 60 + s) * fps)

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

def conv_match_time(v: str) -> int | None:
    parts = v.split(":")
    if len(parts) < 2:
        return None
    (minutes, seconds) = (parts[0].strip("0"), parts[1].lstrip("0"))
    if not isint(minutes) or not isint(seconds):
        return None
    return int(minutes) * 60 + int(seconds)

def tlwh_to_tlbr(tl, wh):
    """convert ((x_left, y_top), (width, height)) to ((x_left, y_top), (x_right, y_bottom))"""
    return (tl, wh), (tl[0] + wh[0], tl[1] + wh[1])

def crop_rect(img, xrange, yrange) -> np.ndarray:
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
    
    

def get_match_display(frame: np.ndarray, logo_tlbr, params: consts.ScaledParams):
    """crops the lower match display from the frame"""
    tl, br = logo_tlbr
    buffer = np.zeros((params.DISPLAY_HEIGHT, params.WIDTH, 3), dtype=np.uint8)

    # The left edge that the copy starts from horizontally
    # default assumes that the display is clipped to the right
    copy_from_left_edge = br[0] + params.SEASON_LOGO_RIGHT_OFFSET - params.WIDTH
    left_edge = 0
    width = params.WIDTH - copy_from_left_edge
    if copy_from_left_edge < 0:
        # display is clipped to the left
        # the copy-into left edge is now to positive, while the start is zero
        left_edge = abs(copy_from_left_edge)
        copy_from_left_edge = 0
        width = params.WIDTH - left_edge

    # same logic except assume panned downwards
    top_edge = 0
    match_is_top = tl[1] < frame.shape[0] / 2
    if match_is_top:
        # display is on top
        copy_from_top_edge = tl[1] - params.DISPLAY_HEIGHT
        height = params.DISPLAY_HEIGHT
        if copy_from_top_edge < 0:
            top_edge = abs(copy_from_top_edge)
            copy_from_top_edge = 0
            height = params.HEIGHT - top_edge
    else:
        # display is on bottom
        copy_from_top_edge = br[1]
        height = min(params.DISPLAY_HEIGHT, (params.HEIGHT - copy_from_top_edge))
        # it's impossible for the top edge to be negative due to detection math 

    buffer[
        top_edge:top_edge + height,
        left_edge:left_edge + width,
        :
    ] = frame[
        copy_from_top_edge:copy_from_top_edge + height,
        copy_from_left_edge:copy_from_left_edge + width,
        :
    ]
    return (buffer, match_is_top)

    #if tl[1] < frame.shape[0] / 2:
    #    return frame[max(tl[1] - height, 0):tl[1], :, :], True
    #else:
    #    return frame[br[1]:br[1] + height, :, :], False

def match_is_preview(match_display: np.ndarray, matcher: ITDRedBasketMatcher, params: consts.ScaledParams):
    # this looks at the match display and checks if parts of the match element displays exist
    # if not, then we're looking at a match preview
    return not matcher.exists(match_display=match_display, params=params)

def extract_text(img, pyts_config=None) -> str:
    """Extracts text from BGR image."""
    if not pyts_config:
        pyts_config = {}
    return pytesseract.image_to_string(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), **pyts_config)

def extract_match_name(frame, match_tlbr, params: consts.ScaledParams):
    """returns (text, image used)"""
    tl, br = match_tlbr

    #name_frame = frame[tl[1]:tl[1] + params.MATCH_NAME_HEIGHT, 
    #            tl[0] + params.MATCH_NAME_LEFT_OFFSET:tl[0] + params.MATCH_NAME_LEFT_OFFSET + params.MATCH_NAME_WIDTH, :]
    name_frame = crop_rect(frame, (tl[0] - params.NAME_LEFT_OFFSET, params.NAME_WIDTH), (tl[1], params.NAME_HEIGHT))
    
    return extract_text(name_frame, {"config": "--psm 6"}).strip(), name_frame

def extract_match_time(match_display: np.ndarray, params: consts.ScaledParams):
    time_top = params.CENTER_TIMER_VALUE_TOP
    time_left = params.CENTER_TIMER_LEFT
    time_right = time_left + params.CENTER_TIMER_WIDTH
    match_time = match_display[time_top:, time_left:time_right, :]

    # use the traditional matcher, since we only want to allow digits and it may work better 
    return extract_text(match_time, {"config": "--psm 6 -c tessedit_char_whitelist=0123456789:"}).strip(), match_time

def extract_display_data(match_display, params: consts.ScaledParams) -> DisplayData:
    #left_display = match_display[:, params.MATCH_LEFT_ALLIANCE_OFFSET:params.MATCH_LEFT_ALLIANCE_OFFSET+params.MA]
    left_display = crop_rect(match_display, (params.LEFT_ALLIANCE_OFFSET, params.ALLIANCE_WIDTH), None)
    right_display = crop_rect(match_display, (params.RIGHT_ALLIANCE_OFFSET, params.ALLIANCE_WIDTH), None)

    left_teams = extract_text(left_display, {"config": "--psm 6 -c tessedit_char_whitelist=0123456789"}).strip().split()
    right_teams = extract_text(right_display, {"config": "--psm 6 -c tessedit_char_whitelist=0123456789"}).strip().split()

    display_reversed = are_colors_flipped(match_display, params)
    if display_reversed:
        red_alliance, blue_alliance = tuple(left_teams), tuple(right_teams)
    else:
        red_alliance, blue_alliance = tuple(right_teams), tuple(left_teams)



    return DisplayData(
        display_flipped=display_reversed,
        red_teams=red_alliance,
        blue_teams=blue_alliance
    )

def are_colors_flipped(match_display, params: consts.ScaledParams):
    sthresh = BlobMatcher.threshold(crop_rect(match_display, (params.LEFT_TOTAL_SCORE_OFFSET, params.LEFT_TOTAL_SCORE_WIDTH), (0, params.LEFT_TOTAL_SCORE_HEIGHT)), "blue")

    return np.count_nonzero(sthresh) / (sthresh.shape[0] * sthresh.shape[1]) < consts.MATCH_PREVIEW_THR
