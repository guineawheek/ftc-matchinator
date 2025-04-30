import dataclasses
import numpy as np
import cv2
from . import consts, util
from pyzbar.pyzbar import decode, Decoded
import matplotlib.pyplot as plt
import typing

@dataclasses.dataclass
class MatchResultScreen:
    # https://ftc.events/FTCCMP1OCHO/qualifications/23
    ftc_events_url: str
    start_ts: float
    end_ts: float

    def fold(self, other: typing.Self):
        if self.ftc_events_url != other.ftc_events_url:
            return
        self.start_ts = min(self.start_ts, other.end_ts)
        self.end_ts = max(self.end_ts, other.end_ts)


def detect_match_result(ts: float, screen: np.ndarray, params: consts.ScaledParams) -> MatchResultScreen | None:
    #roi = util.crop_rect(screen, (params.RESULT_QR_LEFT, params.RESULT_QR_WIDTH), (params.RESULT_QR_TOP, params.RESULT_QR_HEIGHT))
    #plt.imshow(roi)

    #if roi is None:
    #    return None
    entry: Decoded | None = None
    for entry in decode(screen):
        if entry is None:
            continue
        if entry.type != "QRCODE" or entry.data is None:
            break
    if entry is None:
        return None
    return MatchResultScreen(entry.data.decode(), ts, ts + 1)