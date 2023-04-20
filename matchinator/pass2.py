import dataclasses
from typing import List
from . import util, matchers, consts, pass1


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


def combine_matches(edata: pass1.Pass1EventData):
    groups: List[List[pass1.Pass1EventMatch]] = coalese_groups(filter_groups(coalese_groups(edata.matches)))
    all_matches = []

    for match_group in groups:
        # the easy stuff -- just get the most common occurances
        p2em = Pass2EventMatch(None, None, None, None, None, None, None, None)
        p2em.name = match_group[0].name
        p2em.red_teams = freq_max(match_group, "red_teams")
        p2em.blue_teams = freq_max(match_group, "blue_teams")
        p2em.is_replay = freq_max(match_group, "is_replay")
        p2em.colors_flipped = freq_max(match_group, "colors_flipped")
        p2em.top = freq_max(match_group, "top")

        # now to actually detect where the matches actually are

        auto_max_time, auto_max_ts = None, None
        for auto_match in (c for c in match_group if not c.is_tele):
            # do not match "30", this is prematch
            if auto_match.match_ts >= 30:
                continue
            if auto_max_time is None:
                auto_max_time, auto_max_ts = auto_match.match_ts, auto_match.video_sec
            elif auto_match.match_ts > auto_max_time:
                auto_max_time, auto_max_ts = auto_match.match_ts, auto_match.video_sec

        # we may have only recognized the 8 second switchover
        if auto_max_time <= 8:
            auto_max_time = None
        
        tele_max_time, tele_max_ts = None, None
        tele_min_time, tele_min_ts = None, None

        for tele_match in (c for c in match_group if c.is_tele):
            if tele_match.match_ts == 0:
                continue

            if tele_max_time is None:
                tele_max_time, tele_max_ts = tele_match.match_ts, tele_match.video_sec

            elif tele_match.match_ts > tele_max_time:
                tele_max_time, tele_max_ts = tele_match.match_ts, tele_match.video_sec
            
            if tele_min_time is None:
                tele_min_time, tele_min_ts = tele_match.match_ts, tele_match.video_sec
            elif tele_min_time >= tele_match.match_ts:
                tele_min_time, tele_min_ts = tele_match.match_ts, tele_match.video_sec
            
        # logic out the match start and end times
        if auto_max_time is not None:
            match_start = max(auto_max_ts - (30 - auto_max_time) - consts.MATCH_PRE_AUTO_START, 0)
        elif tele_max_time is None:
            raise RuntimeError("this hsould literally never ahppen bruh")
        else:
            match_start = max(tele_max_ts - (120 - tele_max_time) - (38) - consts.MATCH_PRE_AUTO_START, 0)
        
        if tele_min_time is not None:
            match_end = tele_min_ts + tele_min_time + consts.MATCH_POST_TELE_END
        else:
            match_end = auto_max_ts + auto_max_time + 128 + consts.MATCH_POST_TELE_END

        p2em.start_ts = match_start
        p2em.end_ts = match_end
        all_matches.append(p2em)
    return all_matches