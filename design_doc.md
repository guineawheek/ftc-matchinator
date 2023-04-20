# Technical design document for Matchinator

-----

# Match clipping
The autoclipper is a centerpiece of the project -- all matches need manual clipping otherwise

## Manual clipper

Use on videos that cannot be autoclipped -- those without match displays
Sound can help, but not reliable.

Robot detector + Tesseract team number detection could help with schedule alignment and match timing
but at best this will suggest layouts for clipping such streams.

Interface will likely be mpv python bindings + dear pygui frontend.

## Autoclipping

Only to be used on match footage with match displays.

## Pass 1
Audio cues, based on the auto-teleop switch sound. 
This part is complicated for relatively marginal gain, but we may be able to adapt DejaVu

## Pass 2
Template match the screen based on static parts of the display (like the corner triangle pictures)
From here, you can solve the rest of the image once you know where the display is, including match timer.

You can read teams in match, qualification number, etc. From these, you can fit them into a known match schedule.
You can score with confidence against a match schedule anyway.

(Current approach: just x-validating the qualification schedule with the FTC-Events data.)

Some events do not chroma key correctly so the match timer will bleed into whatever is going on in the background.

## Side passes

Detecting and reading match results screens to figure out what event(s) are in a stream.
Some events are AM/PM so it'd be nice to be able to tell which is which.

--------

# Video ingest

FTC Discord #media -> discord bot subscribed to channel -> Stream Task Scheduler -> Hetzner machines with tmux prepopulated
Open question: how do we load-balance Hetzner machines properly?
We can leverage sentiment analysis to recommend and prioritize events to record.

I should not have to wake up early to manage stream recorders. The more automated, the better. 

## Corner cases -- effort/coverage tradeoff
Stream wrong? Stream path changed? Stream not mentioned in #media? AAAaaaaaaa lol

We perform a best-faith effort, and if it doesn't pan out, we can make Community tab posts about matches we cannot clip.

Ultimately, time is money. Too much effort to extract your stream because it's an archive-off Twitch stream or the Youtube is private?
Then we're not bothering.




## Autoclipping algo

```
browse:

check every 1 second for a template match.
if there's a giant red blob and a giant blue blob on screen and no event_name_detect flag:
    (R/B detectors should be run using HSV, as the values are laser specific)
    switch to event_name_detect

if a template match 
    switch to display_detect

event_name_detect:
    run the bottom of the screen through tesseract to find the event naem. 
        all event names are latin
    
    set the event_name_detect flag with a last time of 15 minutes (90 frames)

display_detect:
    blob check to make sure this isn't a match preview. otherwise 

    tesseract the match number 
    if the match number already exists, skip

    tesseract the 

    if more in the center? 
```

# Properties of pass1 match data

Matches generally increase linearly, and match names are generally contiguous with each other numerically and spatially
* If they are not, then there are two scenarios:
  * Match is loaded before long break (unlikely as you'd only show the match display after randomization)
  * Match is replayed later

Matches generally have a 30 second auto period, 8 second switchover, and 120 second teleop.

## There is no guarentee...

### ...that your match file will have an entire match
 * Happens when streams get cut mid-match

### ...that your qualification matches are even from the same event division
 * Multi-division state championships sometimes do this (stupid). Fortunately it's becoming more rare
 * It's a bit hard to read the event name from the match display so the likely solution is to read the teams off of the match display

### ...that a match won't get aborted
 * ah shit
 * Likely will affect end-of-match timing detection

### ... that a match won't get replayed
 * need to do some time grouping

### ...that every second in a match will have a frame
  * (NorCal footage is a prime offender. Someone needs to get Mark Edelman a better streaming setup)

### ...that every match second even aligns with real time
* It probably makes the most amount of sense to try and grab the largest auto timing value less than 30 to estimate the start.
 * If there are no auto clips, use the largest teleop timing and do math from that.

### ...that opencv frame indexes are even translatable to video seconds due to variable framerates.
 * Realistically over an 8 hour long stream this may cause up to 2 seconds of drift, but needs more testing.

### ...that you will have auto segments or teleop segments
 * Sometimes the match display does not get brought up immidiately due to operator error

### ...that the event organizers make the overlay span the whole video width
 * 
 * https://www.youtube.com/watch?v=7moi7luslN4

### ...that you have only one match in a video input
 * Minnesota and CenTex like to stream two or more fields on one stream. 

## switching to pyav for video read:
 - can seek file, allows for parallelization (faster)
  - need some algorithm that picks the nearest frame that isn't like, bad
   - aka the middle of a match
 - might be able to do frame.pts * frame.time_base to work with vfr files

# TODO
 - parallelization support (kind of bad at parallelization rn)
 - binthreshing team numbers to hopefully reduce errors
 - live .ts support
 - more pipeline optimizations
 - generalization for future seasons (roinator?)
