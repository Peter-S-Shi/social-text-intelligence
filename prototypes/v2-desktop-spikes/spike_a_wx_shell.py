"""PROTOTYPE (throwaway) - Spike A-wx: wxPython comparison shell (mock providers).

Same question as spike A, answered for the strongest alternative toolkit: can a
wx frame drive the V1 service in-process, off the UI thread, with accessible names?
"""

from __future__ import annotations

import json
import sys
import threading

import wx

from social_text_intelligence.contracts import NormalizedTextInput
from social_text_intelligence.providers import (
    DeterministicEmotionProvider,
    DeterministicSentimentProvider,
)
from social_text_intelligence.services import AnalysisService


class Frame(wx.Frame):
    def __init__(self) -> None:
        super().__init__(None, title="STI V2 spike A-wx (PROTOTYPE - throwaway)")
        self.service = AnalysisService(
            DeterministicSentimentProvider(), DeterministicEmotionProvider()
        )
        panel = wx.Panel(self)
        self.text = wx.TextCtrl(panel, style=wx.TE_MULTILINE, name="Text to analyze")
        self.button = wx.Button(panel, label="Analyze locally", name="Analyze locally")
        self.result = wx.StaticText(panel, label="No result yet")
        box = wx.BoxSizer(wx.VERTICAL)
        for w in (self.text, self.button, self.result):
            box.Add(w, 1 if w is self.text else 0, wx.EXPAND | wx.ALL, 4)
        panel.SetSizer(box)
        self.button.Bind(wx.EVT_BUTTON, self.on_click)
        self.done = threading.Event()
        self.out: dict[str, object] = {}

    def on_click(self, _event: wx.CommandEvent) -> None:
        text = self.text.GetValue()
        threading.Thread(target=self.work, args=(text,), daemon=True).start()

    def work(self, text: str) -> None:
        report = self.service.analyze(NormalizedTextInput.from_text(text))
        wx.CallAfter(self.show, report)

    def show(self, report: object) -> None:
        s = report.sentiment  # type: ignore[attr-defined]
        self.result.SetLabel(f"Sentiment {s.label.value}")
        self.out = {
            "sentiment": s.label.value,
            "flask_imported": "flask" in sys.modules,
            "accessible_name": self.button.GetName(),
            "wx_version": wx.version(),
        }
        self.done.set()
        wx.CallAfter(self.Close)


def main() -> int:
    app = wx.App(False)
    frame = Frame()
    frame.Show()
    frame.text.SetValue("Thank you so much for the thoughtful help!")
    wx.CallLater(200, lambda: frame.button.Command(wx.CommandEvent(wx.EVT_BUTTON.typeId, frame.button.GetId())))
    wx.CallLater(10_000, frame.Close)
    app.MainLoop()
    print(json.dumps(frame.out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
