"""PROTOTYPE - round 2 shared material: dense synthetic dataset, font helpers,
and painted leaf widgets (strip, field, scale, rose). Each direction passes its
own palette; layouts and navigation stay inside each direction module.
All data is synthetic and generated deterministically.
"""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget

from common import RECORDS  # featured synthetic texts

DISPLAY = "Bahnschrift"
DISPLAY_LIGHT = "Bahnschrift Light"
DISPLAY_COND = "Bahnschrift SemiCondensed"
DISPLAY_COND_LIGHT = "Bahnschrift Light Condensed"
SERIF = "Sitka Display"
SERIF_TEXT = "Sitka Text"
MONO = "Cascadia Mono"
UI = "Segoe UI Variable Text"

EMOTIONS = ["joy", "amusement", "admiration", "gratitude", "anger", "sadness", "fear", "disgust", "neutral"]


# --------------------------------------------------------------------------
# Dense synthetic dataset (600 rows) for strips and fields
# --------------------------------------------------------------------------
def _dataset(n: int = 600, seed: int = 7):
    rnd = random.Random(seed)
    srcs = ["app_store"] * 52 + ["support"] * 33 + ["forum"] * 15
    out = []
    for i in range(n):
        a = [rnd.gammavariate(k, 1) for k in rnd.choice([(4, 1, 0.6), (0.6, 1, 4), (1.2, 2.5, 1.2), (2, 0.8, 2)])]
        s = sum(a)
        neg, neu, pos = (x / s for x in a)
        trip = sorted([neg, neu, pos], reverse=True)
        margin = trip[0] - trip[1]
        sent = ["negative", "neutral", "positive"][[neg, neu, pos].index(trip[0])]
        rec = {"i": i, "id": f"R-{i + 1:04d}", "src": rnd.choice(srcs), "neg": neg, "neu": neu, "pos": pos,
               "pol": pos - neg, "margin": margin, "sent": sent, "status": "unreviewed", "human": None,
               "lang": False, "emo": [rnd.random() ** 3 for _ in EMOTIONS]}
        reviewed = rnd.random() < (0.72 if i < 412 else 0.12)
        if reviewed:
            u = rnd.random()
            if u < 0.035:
                rec["status"] = "uncertain"
            else:
                agree = rnd.random() < (0.55 + 0.45 * margin)
                if agree:
                    rec["status"] = "agree"
                    rec["human"] = sent
                else:
                    rec["status"] = "disagree"
                    rec["human"] = rnd.choice([x for x in ("negative", "neutral", "positive") if x != sent])
        out.append(rec)
    for k in (417, 503):
        out[k]["status"] = "failed"
    for k in (88, 271, 455):
        out[k]["lang"] = True
    return out


DENSE = _dataset()


def counts():
    c = {"unreviewed": 0, "agree": 0, "disagree": 0, "uncertain": 0, "failed": 0}
    for r in DENSE:
        c[r["status"]] += 1
    c["reviewed"] = c["agree"] + c["disagree"] + c["uncertain"]
    c["definitive"] = c["agree"] + c["disagree"]
    c["rate"] = c["agree"] / max(1, c["definitive"])
    c["unsettled"] = sum(1 for r in DENSE if r["margin"] < 0.3 and r["status"] != "failed")
    c["unsettled_open"] = sum(1 for r in DENSE if r["margin"] < 0.3 and r["status"] == "unreviewed")
    return c


C = counts()


def by_source():
    out = []
    for src in ("app_store", "support", "forum"):
        rows = [r for r in DENSE if r["src"] == src and r["status"] in ("agree", "disagree")]
        out.append((src, len(rows), sum(r["status"] == "agree" for r in rows) / max(1, len(rows))))
    return out


def band_agreement(lo: float, hi: float):
    rows = [r for r in DENSE if lo <= r["margin"] < hi and r["status"] in ("agree", "disagree")]
    if not rows:
        return 0.0, 0
    return sum(r["status"] == "agree" for r in rows) / len(rows), len(rows)


# --------------------------------------------------------------------------
# Typography helpers
# --------------------------------------------------------------------------
def font(family: str, px: int, weight: int = 400, spacing: float = 0.0, italic: bool = False) -> QFont:
    f = QFont(family)
    f.setPixelSize(px)
    f.setWeight(QFont.Weight(weight))
    f.setItalic(italic)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


def text(s: str, family: str, px: int, color: str, weight: int = 400, spacing: float = 0.0,
         wrap: bool = False, italic: bool = False, upper: bool = False) -> QLabel:
    w = QLabel(s.upper() if upper else s)
    w.setFont(font(family, px, weight, spacing, italic))
    w.setStyleSheet(f"color:{color}; background:transparent;")
    w.setWordWrap(wrap)
    w.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return w


# --------------------------------------------------------------------------
# Painted leaf widgets
# --------------------------------------------------------------------------
class EvidenceStrip(QWidget):
    """Every record as one vertical tick in import order; optional cursor,
    progress (live analysis) and highlighted range."""

    def __init__(self, colors: dict, height: int = 54, cursor: int | None = None,
                 progress: float | None = None, hollow_unreviewed: bool = True, bg: str | None = None,
                 tall_disagree: bool = True, highlight: tuple[int, int] | None = None, hl_color: str = "#ffffff",
                 rows=None):
        super().__init__()
        self.rows = rows if rows is not None else DENSE
        self.colors = colors
        self.cursor = cursor
        self.progress = progress
        self.bg = bg
        self.tall_disagree = tall_disagree
        self.highlight = highlight
        self.hl_color = hl_color
        self.setFixedHeight(height)
        self.setMinimumWidth(300)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()
        if self.bg:
            p.fillRect(self.rect(), QColor(self.bg))
        n = len(self.rows)
        step = w / n
        done = int(n * self.progress) if self.progress is not None else n
        if self.highlight:
            a, b = self.highlight
            hc = QColor(self.hl_color)
            hc.setAlpha(40)
            p.fillRect(QRectF(a * step, 0, (b - a) * step, h), hc)
        for k, r in enumerate(self.rows):
            x = k * step
            if k >= done:
                c = QColor(self.colors["queued"])
                p.fillRect(QRectF(x, h * 0.62, max(1.0, step * 0.6), h * 0.12), c)
                continue
            st = r["status"]
            c = QColor(self.colors[st])
            if st == "unreviewed":
                hh = h * (0.25 + 0.35 * (1 - r["margin"]))
            elif st == "disagree" and self.tall_disagree:
                hh = h * 0.95
            elif st == "failed":
                hh = h
            else:
                hh = h * 0.55
            p.fillRect(QRectF(x, h - hh, max(1.0, step * 0.62), hh), c)
        if self.progress is not None:
            px = done * step
            p.setPen(QPen(QColor(self.colors.get("head", "#ffffff")), 2))
            p.drawLine(QPointF(px, 0), QPointF(px, h))
        if self.cursor is not None:
            cx = self.cursor * step
            p.setPen(QPen(QColor(self.colors.get("cursor", "#ffffff")), 1.5))
            p.drawLine(QPointF(cx, -2), QPointF(cx, h))
            p.setBrush(QColor(self.colors.get("cursor", "#ffffff")))
            path = QPainterPath()
            path.moveTo(cx - 5, 0)
            path.lineTo(cx + 5, 0)
            path.lineTo(cx, 7)
            path.closeSubpath()
            p.drawPath(path)
        p.end()


class FieldPlot(QWidget):
    """Scatter: x = AI polarity (pos - neg), y = AI certainty margin.
    Reviewed = filled, unreviewed = ring, disagreement = cross."""

    def __init__(self, pal: dict, selection: QRectF | None = None, notes=(), probe=None,
                 subset=None, compact: bool = False, axis_font: str = MONO):
        super().__init__()
        self.pal = pal
        self.selection = selection  # in data coords: x -1..1, y 0..1
        self.notes = notes  # [(x, y, text, dx, dy)]
        self.probe = probe  # (x, y, label)
        self.subset = subset
        self.compact = compact
        self.axis_font = axis_font
        self.setMinimumSize(200, 160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _map(self, x, y, r: QRectF):
        return QPointF(r.left() + (x + 1) / 2 * r.width(), r.bottom() - y * r.height())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.pal
        m = 14 if self.compact else 46
        r = QRectF(m, 12 if self.compact else 26, self.width() - m - (10 if self.compact else 26),
                   self.height() - (26 if self.compact else 64))
        # unsettled band
        band = QRectF(r.left(), self._map(0, 0.3, r).y(), r.width(), r.bottom() - self._map(0, 0.3, r).y())
        bc = QColor(pal["band"])
        p.fillRect(band, bc)
        # grid
        p.setPen(QPen(QColor(pal["grid"]), 1))
        for gx in (-1, -0.5, 0, 0.5, 1):
            a = self._map(gx, 0, r)
            p.drawLine(QPointF(a.x(), r.top()), QPointF(a.x(), r.bottom()))
        for gy in (0, 0.3, 0.6, 1.0):
            a = self._map(-1, gy, r)
            p.drawLine(QPointF(r.left(), a.y()), QPointF(r.right(), a.y()))
        if not self.compact:
            p.setFont(font(self.axis_font, 11))
            p.setPen(QColor(pal["axis"]))
            p.drawText(QRectF(r.left(), r.bottom() + 8, 200, 18), "← AI reads negative")
            p.drawText(QRectF(r.right() - 200, r.bottom() + 8, 200, 18), Qt.AlignmentFlag.AlignRight,
                       "AI reads positive →")
            p.drawText(QRectF(r.center().x() - 60, r.bottom() + 8, 120, 18), Qt.AlignmentFlag.AlignCenter, "neutral")
            p.save()
            p.translate(r.left() - 30, r.center().y())
            p.rotate(-90)
            p.drawText(QRectF(-120, -10, 240, 20), Qt.AlignmentFlag.AlignCenter, "AI certainty (margin) →")
            p.restore()
            p.setPen(QColor(pal["band_text"]))
            p.drawText(QRectF(r.left() + 8, band.top() + 4, 400, 18),
                       "UNSETTLED ZONE · margin < 0.30")
        rows = self.subset if self.subset is not None else DENSE
        rad = 2.2 if self.compact else 3.6
        for d in rows:
            if d["status"] == "failed":
                continue
            jitter = ((d["i"] * 7919) % 100) / 100 * 0.03
            pt = self._map(d["pol"], min(0.99, d["margin"] + jitter), r)
            st = d["status"]
            if st == "unreviewed":
                p.setPen(QPen(QColor(pal["ring"]), 1))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(pt, rad, rad)
            elif st == "disagree":
                p.setPen(QPen(QColor(pal["disagree"]), 1.8 if not self.compact else 1.2))
                k = rad + 0.6
                p.drawLine(QPointF(pt.x() - k, pt.y() - k), QPointF(pt.x() + k, pt.y() + k))
                p.drawLine(QPointF(pt.x() - k, pt.y() + k), QPointF(pt.x() + k, pt.y() - k))
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(pal["agree"] if st == "agree" else pal["uncertain"]))
                p.drawEllipse(pt, rad, rad)
        if self.selection is not None:
            s = self.selection
            a = self._map(s.left(), s.bottom(), r)
            b = self._map(s.right(), s.top(), r)
            sel = QRectF(a, b).normalized()
            c = QColor(pal["select"])
            c.setAlpha(10)
            p.setBrush(c)
            p.setPen(QPen(QColor(pal["select"]), 1.5, Qt.PenStyle.DashLine))
            p.drawRect(sel)
        for (x, y, t, dx, dy) in self.notes:
            a = self._map(x, y, r)
            b = QPointF(a.x() + dx, a.y() + dy)
            p.setPen(QPen(QColor(pal["note"]), 1))
            p.drawLine(a, b)
            p.setBrush(QColor(pal["note"]))
            p.drawEllipse(a, 2.5, 2.5)
            p.setFont(font(DISPLAY_COND, 13, 600))
            lines = t.split("\n")
            for k, ln in enumerate(lines):
                p.drawText(QPointF(b.x() + (4 if dx >= 0 else -4 - p.fontMetrics().horizontalAdvance(ln)),
                                   b.y() + 4 + k * 16), ln)
        if self.probe:
            x, y, t = self.probe
            a = self._map(x, y, r)
            p.setPen(QPen(QColor(pal["probe"]), 2))
            p.setBrush(QColor(pal["probe_fill"]))
            p.drawEllipse(a, 9, 9)
            p.drawLine(QPointF(a.x(), a.y() - 9), QPointF(a.x(), a.y() - 40))
            p.setFont(font(DISPLAY, 13, 600))
            p.drawText(QPointF(a.x() + 6, a.y() - 44), t)
        p.end()


class SentimentScale(QWidget):
    """Calibrated -1..+1 scale with the AI needle, its probability spread,
    and the human marker (if any)."""

    def __init__(self, pal: dict, rec, human: str | None = None, height: int = 74, label_font: str = MONO):
        super().__init__()
        self.pal = pal
        self.rec = rec
        self.human = human
        self.label_font = label_font
        self.setFixedHeight(height)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.pal
        r = QRectF(10, 22, self.width() - 20, self.height() - 44)
        neg, neu, pos = self.rec["scores"]
        # spread bars
        for k, (v, c) in enumerate(((neg, pal["neg"]), (neu, pal["neu"]), (pos, pal["pos"]))):
            cx = r.left() + r.width() * (0.12 + 0.38 * k)
            wbar = r.width() * 0.22
            col = QColor(c)
            col.setAlpha(70)
            p.fillRect(QRectF(cx - wbar / 2, r.bottom() - r.height() * v, wbar, r.height() * v), col)
        p.setPen(QPen(QColor(pal["scale"]), 1))
        p.drawLine(QPointF(r.left(), r.bottom()), QPointF(r.right(), r.bottom()))
        for k in range(21):
            x = r.left() + r.width() * k / 20
            hh = 8 if k % 5 == 0 else 4
            p.drawLine(QPointF(x, r.bottom()), QPointF(x, r.bottom() + hh))
        p.setFont(font(self.label_font, 10))
        for k, t in ((0, "-1 negative"), (10, "0"), (20, "positive +1")):
            x = r.left() + r.width() * k / 20
            al = Qt.AlignmentFlag.AlignLeft if k == 0 else (Qt.AlignmentFlag.AlignRight if k == 20 else Qt.AlignmentFlag.AlignHCenter)
            box = QRectF(x - (0 if k == 0 else (120 if k == 20 else 60)), r.bottom() + 9, 120, 14)
            p.drawText(box, al, t)
        pol = pos - neg
        ax = r.left() + (pol + 1) / 2 * r.width()
        p.setPen(QPen(QColor(pal["ai"]), 2.5))
        p.drawLine(QPointF(ax, r.top() - 14), QPointF(ax, r.bottom()))
        p.setFont(font(self.label_font, 10, 600))
        p.drawText(QPointF(ax + 5, r.top() - 6), f"AI {pol:+.2f}")
        if self.human:
            hx = r.left() + {"negative": 0.12, "neutral": 0.5, "positive": 0.88}[self.human] * r.width()
            p.setPen(QPen(QColor(pal["human"]), 2))
            p.setBrush(QColor(pal["human"]))
            path = QPainterPath()
            path.moveTo(hx, r.bottom() - 2)
            path.lineTo(hx - 7, r.bottom() - 16)
            path.lineTo(hx + 7, r.bottom() - 16)
            path.closeSubpath()
            p.drawPath(path)
            p.drawText(QPointF(hx + 9, r.bottom() - 6), f"you: {self.human}")
        p.end()


class EmotionRose(QWidget):
    """Nine compact emotions as petals; threshold ring at 0.50."""

    def __init__(self, pal: dict, values: dict, human: str | None = None, size: int = 220, label_font: str = MONO):
        super().__init__()
        self.pal = pal
        self.values = values
        self.human = human
        self.label_font = label_font
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.pal
        c = QPointF(self.width() / 2, self.height() / 2)
        R = self.width() / 2 - 46
        p.setPen(QPen(QColor(pal["grid"]), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for k in (0.25, 0.5, 0.75, 1.0):
            pen = QPen(QColor(pal["threshold"] if k == 0.5 else pal["grid"]), 1,
                       Qt.PenStyle.DashLine if k == 0.5 else Qt.PenStyle.SolidLine)
            p.setPen(pen)
            p.drawEllipse(c, R * k, R * k)
        n = len(EMOTIONS)
        p.setFont(font(self.label_font, 10))
        for k, e in enumerate(EMOTIONS):
            a0 = -90 + k * 360 / n
            v = self.values.get(e, 0.0)
            path = QPainterPath(c)
            rr = R * v
            path.arcTo(QRectF(c.x() - rr, c.y() - rr, 2 * rr, 2 * rr), -a0 + 360 / n * 0.42, -360 / n * 0.84)
            path.closeSubpath()
            col = QColor(pal["ai"])
            col.setAlpha(200 if v >= 0.3 else 110)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
            p.drawPath(path)
            ang = math.radians(a0)
            lp = QPointF(c.x() + math.cos(ang) * (R + 24), c.y() + math.sin(ang) * (R + 20))
            is_h = e == self.human
            p.setPen(QColor(pal["human"] if is_h else pal["label"]))
            if is_h:
                p.setFont(font(self.label_font, 10, 700))
            p.drawText(QRectF(lp.x() - 50, lp.y() - 8, 100, 16), Qt.AlignmentFlag.AlignCenter,
                       ("▶ " if is_h else "") + e)
            p.setFont(font(self.label_font, 10))
        p.end()


class Ring(QWidget):
    """Progress ring with centre text."""

    def __init__(self, value: float, fg: str, track: str, size: int = 120, width: int = 8,
                 label: str = "", label_color: str = "#000", family: str = DISPLAY_LIGHT, px: int = 28):
        super().__init__()
        self.v, self.fg, self.track, self.wd = value, fg, track, width
        self.label, self.lc, self.family, self.px = label, label_color, family, px
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.wd, self.wd, self.width() - 2 * self.wd, self.height() - 2 * self.wd)
        p.setPen(QPen(QColor(self.track), self.wd))
        p.drawEllipse(r)
        pen = QPen(QColor(self.fg), self.wd)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        p.drawArc(r, 90 * 16, int(-360 * 16 * self.v))
        p.setFont(font(self.family, self.px))
        p.setPen(QColor(self.lc))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.label)
        p.end()


class Hairline(QWidget):
    def __init__(self, color: str, vertical: bool = False, weight: int = 1):
        super().__init__()
        self.color = color
        if vertical:
            self.setFixedWidth(weight)
        else:
            self.setFixedHeight(weight)
        self.setStyleSheet(f"background:{color};")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


FEATURED = RECORDS
