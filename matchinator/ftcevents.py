# pylint: disable-all
import requests
import base64
import datetime

BASE_API_URL = "https://ftc-api.firstinspires.org/v2.0"
class FTCEventsClient:
    def __init__(self, username, token, season=None, verbose=False):
        self.verbose = verbose
        self.season = season if season else FTCEventsClient.get_season()
        self.username = username
        self.token = token
        self._b64 = base64.b64encode(f"{self.username}:{self.token}".encode()).decode()
        self.session = requests.Session()

    def fetch(self, path, **params):
        url = f"{BASE_API_URL}/{self.season}/{path}"
        if self.verbose:
            print("fetch", url)
        r = self.session.get(url, headers={"Authorization": "Basic " + self._b64}, params=params)
        r.raise_for_status()
        return r.json()
    
    @staticmethod
    def date_parse(date_str):
        return datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def get_season():
        """Fetches the current season, based on typical kickoff date."""
        today = datetime.datetime.today()
        year = today.year
        # ftc kickoff is always the 2nd saturday of september
        kickoff = [d for d in [datetime.datetime(year=year, month=9, day=i) for i in range(8, 15)] if d.weekday() == 5][0]
        if kickoff > today:
            return today.year - 1
        return today.year

    def get_schedule(self, eventcode):
        match_map = {}
        qual = self.fetch(f"schedule/{eventcode}/qual/hybrid")['schedule']
        totalqual = len(qual)
        for m in qual:
            name = m['description'] + f" of {totalqual}"# --- "
            red = []
            blue = []
            for team in sorted(m['teams'], key=lambda x: x['station']): # blue1 blue2 blue3, red1 red2 red3
                if team['station'].startswith("Blue"):
                    blue.append(str(team['teamNumber']))
                else:
                    red.append(str(team['teamNumber']))
            
            wincode = "R" if m['redWins'] else ("B" if m['blueWins'] else "T")
            m['matchSummary'] = f"{name} --- {', '.join(red)} vs. {', '.join(blue)} -- {m['scoreRedFinal']}-{m['scoreBlueFinal']} {wincode}"
            match_map[name] = m


        play = self.fetch(f"schedule/{eventcode}/playoff/hybrid")['schedule']
        for m in play:
            name = m['description']# + " --- "
            red = []
            blue = []

            for team in sorted(m['teams'], key=lambda x: x['station']): # blue1 blue2 blue3, red1 red2 red3
                if team['station'].startswith("Blue"):
                    blue.append(str(team['teamNumber']))
                else:
                    red.append(str(team['teamNumber']))
            #name = f"{name}{', '.join(red)} vs. {', '.join(blue)}"
            wincode = "R" if m['redWins'] else ("B" if m['blueWins'] else "T")
            m['matchSummary'] = f"{name} --- {', '.join(red)} vs. {', '.join(blue)} -- {m['scoreRedFinal']}-{m['scoreBlueFinal']} {wincode}"
            match_map[name] = m
        
        return match_map