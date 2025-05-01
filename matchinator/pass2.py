import dataclasses
from typing import List
from . import util, matchers, consts, pass1, match_result
import random
import numpy as np
import subprocess

"""

this takes the cv detection data from pass1
and then runs RANSAC on the data to come up with the lowest variance explanation
for the data and where the video probably starts and ends.

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

def combine_matches(edata: pass1.Pass1EventData, seed=0) -> List[Pass2EventMatch]:
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

        p2em.start_ts = float(soln.avg_match_start - consts.MATCH_PRE_AUTO_START)
        p2em.end_ts = float(soln.avg_match_start + 158 + consts.MATCH_POST_TELE_END)
        all_matches.append(p2em)
    return all_matches

def clip_match(p: Pass2EventMatch, src: str, fname_template: str, offset=0, pass1_data: pass1.Pass1EventData=None):
    match_name = p.name
    match_numer = 0
    tiebreaker_num = 1
    spl = match_name.split()
    if match_name.startswith("Qualification"):
        match_name = f"Qualification {spl[1]}"
        match_numer = int(spl[1])
    if match_name.startswith("Playoff"):
        if match_name.endswith("Tiebreaker"):
            tiebreaker_num += 1
            match_name = f"Match {spl[2]} Tiebreaker"
        else:
            match_name = f"Match {spl[2]}"
        match_numer = int(spl[2])
    if "da Vinci" in match_name:
        match_numer = int(spl[-1])
        match_name = f"da Vinci {spl[-1]}"
    
    results_screen: match_result.MatchResultScreen | None = None
    if pass1_data is not None:
        for k, v in pass1_data.match_result_map.items():
            if not k.startswith("https://ftc.events"):
                continue
            if match_name.startswith("da Vinci") and k.endswith(f"FTCCMP1/playoff/{match_numer}/{tiebreaker_num}"):
                results_screen = v
                break
            if match_name.startswith("Qualification") and k.endswith(f"qualifications/{match_numer}"):
                results_screen = v
                break
            if match_name.startswith("Match") and k.endswith(f"playoff/{match_numer}/{tiebreaker_num}"):
                results_screen = v
                break
            
    if results_screen is None:
        print("WARNING: No results screen for", match_name)
        return subprocess.call([
            "ffmpeg",
            "-y",
            "-ss",
            f"{p.start_ts - offset:.03f}",
            "-to",
            f"{p.end_ts - offset:.03f}",
            "-i",
            src,
            "-c:v", "copy",
            "-c:a", "copy",
            fname_template.format(name=match_name)
        ])
    else:
        # cut the video first
        subprocess.check_call([
            "ffmpeg",
            "-y",
            "-ss",
            f"{p.start_ts - offset:.03f}",
            "-to",
            f"{p.end_ts - offset:.03f}",
            "-i",
            src,
            "-c:v", "copy",
            "-c:a", "copy",
            "/tmp/matchinator_match_video.ts"
        ])


        results_start = results_screen.start_ts - consts.PRE_RESULT_FINE - consts.PRE_RESULT_COARSE - offset
        results_end = min(results_screen.start_ts + consts.POST_SCORE_DETECT, results_screen.end_ts - 2) - offset

        # we need to reencode in order for this not to be mega crusty or be weirdly offset due to lack of keyframes
        # this reencode is instantaneous but will vary depending on how a place streams (ugh)
        subprocess.check_call([
            "ffmpeg",
            "-y",
            "-ss", f"{results_start:.03f}",
            "-to", f"{results_end:.03f}",
            "-i", src,
            "-ss", f"{consts.PRE_RESULT_COARSE:.03f}",
            "-c:v", "libx264",
            "-crf", "17",
            "-c:a", "aac", "-b:a", "162k",
            "/tmp/matchinator_results_video.ts"
        ])

        with open("/tmp/matchinator_concat.txt", "w") as f:
            f.write("file '/tmp/matchinator_match_video.ts'\nfile '/tmp/matchinator_results_video.ts'")

        subprocess.check_call([
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            "/tmp/matchinator_concat.txt",
            "-c", "copy",
            fname_template.format(name=match_name)
        ])