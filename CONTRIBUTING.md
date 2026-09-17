# Contributing a recording

Everything in this corpus is one hand, one Wacom Cintiq 24, one backend. That means nothing
in it can yet tell a fact about **pens** from a fact about **this pen**. A second device, or
a second hand, is worth more here than a hundred more takes from the first.

## What to send

Record with the [Stroke Recorder](https://github.com/TheSevenPens/StrokeRecorder), then open
a pull request adding your `.json` files to `traces/`.

Please **do not edit the file**. The recorder writes what the driver said; a hand-corrected
trace is no longer evidence, and the counters in it stop reconciling.

## What is most wanted

In rough order:

1. **A tablet that is not a Wacom Cintiq 24.** Anything — a Huion, an XP-Pen, an iPad through
   a Windows bridge, a Surface pen, a screenless tablet. Different drivers report different
   things and disagree in ways nobody has written down.
2. **A backend that is not Wintab.** WM_POINTER and the plain framework pointer see the same
   hardware through different stacks and do not agree about the pressure range.
3. **Hover.** Turn on keeping airborne readings. The approach to a landing is the least
   documented part of pen input and the reason this corpus exists.
4. **A left hand, a different grip, a pushed stroke.** Every take here is one person's
   posture, and the lean measurements especially are suspected of being about that.

## The gestures worth drawing

You do not have to do all of these. Any one is useful.

| gesture | why |
|---|---|
| a single tap | press and lift with no movement, which breaks more brush engines than anything else |
| a slow diagonal | about four seconds end to end, for what a pen does when the hand barely moves |
| a fast flick | under half a second, for the widest steps between readings |
| a pressure ramp | one straight line, lightest to heaviest |
| a light line | as light as you can hold and still register, where pens are least well behaved |
| cross-hatching | many short strokes with lifts between them, which is where hover data comes from |
| a loop that crosses itself | for what happens where a stroke overlaps its own ink |
| the same loop at four sizes | fingers to arm, which is how the pen's lean was found to follow the hand |

## Say what you drew

Put it in the pull request: **which tablet, which driver version, which backend, and what you
were doing with your hand.** The file records the device itself, but nothing in it can record
that you were drawing left-handed, or standing, or that the pen has a worn nib.

## What happens to it

Your recording is published under [CC BY 4.0](LICENSE) along with the rest, which means
anyone can use it for anything as long as they say where it came from. By opening the pull
request you are agreeing to that.

**A trace records what a pen did on a tablet.** It carries positions on your desktop, the
tablet and driver names, and the time you recorded it. It carries nothing you typed and
nothing about your machine beyond that. Read one before you send it if you would like to see
for yourself — they are plain JSON.

## If a take is not perfect

Send it anyway and say what went wrong. A recording with a fault in it that is *described* is
worth more than one where the fault is unknown — most of the corpus is tagged as wanting
re-recording, and those tags are the useful part.
