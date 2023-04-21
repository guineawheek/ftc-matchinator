"""
first pass video analysis

this module attempts to find approximate timestamps of matches and corresponding match names.

this module also attempts to figure out what event(s) are contained within
"""
import os
import sys
import time
from pathlib import Path
import numpy as np
import cv2
import operator
import dataclasses
import multiprocessing
from . import consts, matchers, util


## CONVENTIONS:
# everything should use xy EXCEPT for numpy shit

# constant tunables



@dataclasses.dataclass
class Pass1EventMatch:
    name: str
    top: bool
    frame_idx: int
    video_sec: float
    is_tele: bool

    match_ts: int
    red_teams: tuple[str]
    blue_teams: tuple[str]
    is_replay: bool
    colors_flipped: bool

@dataclasses.dataclass
class Pass1EventData:
    fps: int
    width: int
    height: int
    matches: list = dataclasses.field(default_factory=list)

## helper functions
def mult_tuple(t, v):
    return tuple(tv * v for tv in t) 

def run_task(rtd):
    #return run(video_path, en_name=en_name, pout=pout, poll=1, debug=False, seek=seek, fcount=seg_len).matches
    return run(*rtd.args, **rtd.kwargs).matches

class RunTaskData:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

def run_parallel(video_path, threads=None, en_name=None, pout=sys.stderr, poll=1):
    """Runs all tasks in parallel.
    *Will not necessarily increase performance lmao 
    """

    threads = threads or os.cpu_count()

    cap = cv2.VideoCapture(video_path)
    cap_len = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    p1ed = Pass1EventData(fps, width, height)
    cap.release()

    seg_len = cap_len // threads
    with multiprocessing.Pool(threads) as p:
        res = p.map(run_task, 
            [RunTaskData(video_path, en_name=en_name, poll=1, debug=False, seek=seek, fcount=seg_len, is_para=True) for seek in range(0, cap_len, seg_len)])
    
    for matches in res:
        p1ed.matches.extend(matches)
    
    return p1ed
    

def run(video_path, en_name=None, pout=sys.stderr, poll=1, debug=False, seek=0, fcount=-1, is_para=False):
    """Runs a fast first pass of the video.
    This will run the pipeline every second in the video, and return a Pass1EventData object
    containing metadata and the timestamps of all frames with a match display on screen. 
    
    """

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened(): 
        raise RuntimeError("could not open video")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    event_data = Pass1EventData(fps, width, height)
    

    #scalex, scaley = np.array([width, height]) / consts.BASE_IMSIZE
    params = consts.ScaledParams(width, height)

    logo_matcher = matchers.EnergizeLogoMatcher(params, en_name)
    cap_matcher = matchers.PPCapMatcher(params)

    # read the FIRST Energize logo that appears on the left of the display
    
    poll_idx = int(fps * poll)
    assert fps > 0, "fps call returned zero ;w;"
    
    idx = seek-1
    fcnt = 0
    #cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    #print("lol")
    prev_time = time.time()
    while cap.isOpened():
        if fcnt >= fcount and fcount > 0:
            break

        if fcnt > (cap.get(cv2.CAP_PROP_FRAME_COUNT) - 3):
            time.sleep(10)
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_FRAMES, fcnt-1)


        succ, frame = cap.read()
        if not succ:
            break
        idx += 1
        fcnt += 1

        if idx % 10 == 0:
            if not is_para:
                print(f"time: " 
                    + util.timef(cap.get(cv2.CAP_PROP_POS_MSEC))
                    + f" fps: {1 / (time.time() - prev_time):.6f}         ", end="\r", file=pout)
            elif idx % 300 != 0:
                print(f"time: " 
                    + util.timef(cap.get(cv2.CAP_PROP_POS_MSEC))
                    + f" fps: {1 / (time.time() - prev_time):.6f}         seek: {seek}", file=pout)
        prev_time = time.time()

        if idx % poll_idx != 0:
            continue
        # more browse logic here

        has_logo, match_tlbr = logo_matcher.match(frame)
        if has_logo:
            # get the topleft and bottomright corners

            # we have a match! (literal)
            # also crop out the match display part of the frame
            match_display, match_is_top = util.get_match_display(frame, match_tlbr, params)
            
            if util.match_is_preview(match_display):
                # welp, this is a match preview. next.
                continue
            
            # we found a match or...something
            match_name, _ = util.extract_match_name(frame, match_tlbr, params)

            if "Example" in match_name:
                # this is the example display. ignore.
                continue

            #  attempt to extract the match timestamp
            timestamp, _ = util.extract_match_time(match_display, match_is_top, params)

            if not util.isint(timestamp):
                # we discard  non-integer timestamps
                if debug:
                    print("reject timestamp", timestamp, file=pout)
                continue
            
            
            # check if this is teleop or auto
            is_tele = cap_matcher.exists(match_display, params)


            # get whether or not the match display is veversed
            display_reversed = util.are_colors_flipped(match_display, params)

            left_teams, right_teams = util.extract_match_teams(match_display, params)

            if display_reversed:
                red_alliance, blue_alliance = tuple(left_teams), tuple(right_teams)
            else:
                red_alliance, blue_alliance = tuple(right_teams), tuple(left_teams)
            

            event_match = Pass1EventMatch(match_name, match_is_top, idx, cap.get(cv2.CAP_PROP_POS_MSEC) / 1000, is_tele, int(timestamp), red_alliance, blue_alliance, None, display_reversed)
            event_data.matches.append(event_match)
    cap.release()

    if debug:
        return util.DictStruct(locals())
    else:
        return event_data



