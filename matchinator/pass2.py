import dataclasses
from typing import List
from . import util, matchers, consts, pass1
import random
import numpy as np

"""
look at match teams, attempt to deduce events from them/group
 - for future release

group match entries by match name/time
discard entries with less than 5 entries, regroup

for each match group:
    find the earliest largest value < 29 for auto

    find the earliest largest value <= 120 for teleop


return all match timestamps and clip videos from source using ffmpreg


TODO:
implement replay suppport
implement multi-event-in-one-stream detection

"""
@dataclasses.dataclass
class Pass2EventMatch:
    name: str
    start_ts: float # in seconds 
    end_ts: float
    red_teams: tuple[int]
    blue_teams: tuple[int]
    is_replay: bool
    top: bool
    colors_flipped: bool

def coalese_groups(matches: List[pass1.Pass1EventMatch]):
    """Coalesces match entries into things
    TODO: add event sorting here 
    """
    all_groups = [[]]
    cur_name = None
    cur_group = all_groups[0]
    for mtch in matches:
        if cur_name is None:
            cur_name = mtch.name
            cur_group.append(mtch)
        else:
            if cur_name == mtch.name:
                cur_group.append(mtch)
            else:
                cur_group = [mtch]
                cur_name = mtch.name
                all_groups.append(cur_group)


    return all_groups

def filter_groups(all_groups: List[list]):
    l = []
    for z in all_groups:
        if len(z) >= consts.MATCH_GROUP_MIN_COUNT:
            l.extend(z)
    return l

def freq_table(lst, attr):
    """Get the frequency table of occurances in a list of object"""
    vals = {}
    for obj in lst:
        val = getattr(obj, attr)
        vals[val] = vals.get(val, 0) + 1
    
    return vals

def freq_max(lst, attr):
    """get the most frequent values for an attribute"""
    tbl = freq_table(lst, attr)
    return sorted(tbl.keys(), key=lambda k: -tbl[k])[0]

@dataclasses.dataclass
class SampleInfo:
    group: List[pass1.Pass1EventMatch]
    avg_match_start: float
    score: float

def create_sample(group: List[pass1.Pass1EventMatch]) -> SampleInfo:
    """
    randomly sample up to 11 points from the group, and then compute the 
    average estimated start time and the variance.
    """
    sample_size = min(len(group), 11)
    sample = random.sample(group, sample_size)
    starts = []
    for entry in sample:
        video_sec = entry.video_sec
        match_ts = entry.match_ts
        # account for the 8 second auto/tele switchover
        if match_ts <= 120:
            match_ts -= 8
            # one second left in auto -> ts of 121 -> 29 seconds ago
            # one second into tele -> ts of 119 -> 31 seconds ago + 8 seconds
        match_start = video_sec - (150 - match_ts)
        starts.append(match_start)

    return SampleInfo(
        group=sample,
        avg_match_start=np.mean(starts),
        score=np.var(starts)
    )

def combine_matches(edata: pass1.Pass1EventData, seed=0):
    random.seed(seed)
    groups: List[List[pass1.Pass1EventMatch]] = coalese_groups(filter_groups(coalese_groups(edata.matches)))
    all_matches = []

    for match_group in groups:
        # the easy stuff -- just get the most common occurances
        p2em = Pass2EventMatch(None, None, None, None, None, None, None, None)
        p2em.name = match_group[0].name
        data_group = [m.display_data for m in match_group]

        p2em.red_teams = freq_max(data_group, "red_teams")
        p2em.blue_teams = freq_max(data_group, "blue_teams")
        p2em.is_replay = freq_max(match_group, "is_replay")
        p2em.colors_flipped = freq_max(data_group, "display_flipped")
        p2em.top = freq_max(match_group, "top")

        # pick 100 random solutions and pick the ones that make the most sense
        soln = min([create_sample(match_group) for i in range(100)], key=lambda x: x.score)

        p2em.start_ts = soln.avg_match_start - consts.MATCH_PRE_AUTO_START
        p2em.end_ts = soln.avg_match_start + 158 + consts.MATCH_POST_TELE_END
        all_matches.append(p2em)
    return all_matches