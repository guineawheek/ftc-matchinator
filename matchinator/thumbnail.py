from PIL import ImageFont, ImageDraw, Image
import dataclasses
from . import ftcevents

TEMPLATE = Image.open("matchinator/templates/thumbnail.png")
FONT = "matchinator/templates/LiberationSans-Bold.ttf"

BOX_WIDTH = 550
BOX_HEIGHT = 100

@dataclasses.dataclass
class Schedule:
    teams: dict
    team_map: dict
    matches: dict


def schedule(client: ftcevents.FTCEventsClient, event: str) -> Schedule:
    teams = client.fetch("teams", eventCode=event)['teams']
    team_map = {t['teamNumber']: t['nameShort'] for t in teams}
    matches = client.get_schedule(eventcode=event) or {}

    return Schedule(teams, team_map, matches)

def generate_match_thumb(schedule: Schedule, event_name: str, match_name: str, match_key: str = None) -> Image:
    """client: FTCEvents client.
    event: event code
    event_name: e.g. 2025 Franklin Division
    match_name: the name straight off of the OCR'ed match value"""
    match_ = schedule.matches.get(match_key or match_name) or {
  'scoreRedFinal': 0,
  'scoreBlueFinal': 0,
  'redWins': False,
  'blueWins': False,
  'teams': [
    {'teamNumber': 0, 'teamName': 'FTC-Events', 'station': 'Red1'},
    {'teamNumber': 1, 'teamName': 'Please regenerate', 'station': 'Red2'},
    {'teamNumber': 2, 'teamName': "API call failed!", 'station': 'Blue1'},
    {'teamNumber': 3, 'teamName': 'me later!', 'station': 'Blue2'}
  ]}

    
    #for team in match_['teams']:
    #    if len(team['teamName']) > 27:
    #        # thanks southstem
    #        team['teamName'] = team['teamName'][:24] + "..."
    
      
    blue_teams = [t for t in match_['teams'] if t['station'].startswith('Blue')]
    red_teams = [t for t in match_['teams'] if t['station'].startswith('Red')]
    
    img = TEMPLATE.copy()
    title_fnt = ImageFont.truetype(FONT, 48)
    d = ImageDraw.Draw(img)
    d.multiline_text((40, 22), event_name, font=title_fnt, fill=(0, 0, 0))
    d.multiline_text((1920-40, 22), match_name, anchor="ra", font=title_fnt, fill=(0, 0, 0))
    team_fnt = ImageFont.truetype(FONT, 132)
    d.multiline_text((40, 175), "\n".join(str(t['teamNumber']) for t in blue_teams), font=team_fnt, spacing=20, fill=(255, 255, 255))
    d.multiline_text((1920-40, 175), "\n".join(str(t['teamNumber']) for t in red_teams), 
                     font=team_fnt, spacing=20, anchor="ra", align="right", fill=(255, 255, 255))

    red1 = red_teams[0]['teamName']
    red2 = red_teams[1]['teamName']
    red3 = None
    if len(red_teams) > 2:
        red3 = red_teams[2]['teamName']
    blue1 = blue_teams[0]['teamName']
    blue2 = blue_teams[1]['teamName']
    blue3 = None
    if len(blue_teams) > 2:
        blue3 = blue_teams[2]['teamName']

    d.text((1920/2-35, 305), blue1, align="right", anchor="rb", font=autosize_font(blue1, 450, 50), fill=(255, 255, 255))
    d.text((1920/2-35, 435), blue2, align="right", anchor="rb", font=autosize_font(blue2, 450, 50), fill=(255, 255, 255))
    if blue3 is not None:
        d.text((1920/2-35, 575), blue3, align="right", anchor="rb", font=autosize_font(blue3, 450, 50), fill=(255, 255, 255))

    d.text((1920/2+35, 305), red1, align="left", anchor="lb", font=autosize_font(red1, 450, 50), fill=(255, 255, 255))
    d.text((1920/2+35, 435), red2, align="left", anchor="lb", font=autosize_font(red2, 450, 50), fill=(255, 255, 255))
    if red3 is not None:
        d.text((1920/2+35, 575), red3, align="left", anchor="lb", font=autosize_font(red3, 450, 50), fill=(255, 255, 255))

    score_fnt = ImageFont.truetype(FONT, 192)
    d.multiline_text((1920/4+80, 640), str(match_.get('scoreBlueFinal', "?")), anchor="ma", font=score_fnt, fill=(255, 255, 255))
    d.multiline_text((1920*3/4-80, 640), str(match_.get('scoreRedFinal', "?")), anchor="ma", font=score_fnt, fill=(255, 255, 255))
    
    return img

def autosize_font(text: str, bbox_width: int, bbox_height: int, min_size: float = 10, step: float = 1) -> ImageFont.FreeTypeFont:
    size = min_size
    last_font = ImageFont.truetype(FONT, size)
    font = last_font
    while True:
        (left, top, right, bottom) = font.getbbox(text)
        width = abs(right - left)
        height = abs(bottom - top)
        if width > bbox_width or height > bbox_height:
            break
        last_font = font
        size += step
        font = ImageFont.truetype(FONT, size)
    return last_font