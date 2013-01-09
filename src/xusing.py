"""
xusing: records program use from X11 window focus and idle time
"""
import argparse
import ctypes
import datetime
import logging
import logging.handlers as handlers
import os
import time

import Xlib.display


class XScreenSaverInfo(ctypes.Structure):
    """
    A ctypes struct that parallels XScreenSaverInfo from libXss.
    """
    _fields_ = [('window', ctypes.c_ulong),
                ('state', ctypes.c_int),
                ('kind', ctypes.c_int),
                ('since', ctypes.c_ulong),
                ('idle', ctypes.c_ulong),
                ('event_mask', ctypes.c_ulong)]


class XIdle(object):
    """
    Wraps libXss loaded from ctypes to find the idle time of an X session.
    """
    def __init__(self):
        self.xlib = ctypes.cdll.LoadLibrary('libX11.so.6')
        self.xss = ctypes.cdll.LoadLibrary('libXss.so.1')
        xssi_pointer = ctypes.POINTER(XScreenSaverInfo)
        self.xss.XScreenSaverAllocInfo.restype = xssi_pointer

        self.dpy = self.xlib.XOpenDisplay(os.environ.get('DISPLAY'))
        self.root = self.xlib.XDefaultRootWindow(self.dpy)
        self.xss_info = self.xss.XScreenSaverAllocInfo()

    def get_idle_ms(self):
        """
        Returns the number of milliseconds for which there were no key or mouse
        events in an X session, as an integer.
        """
        self.xss.XScreenSaverQueryInfo(self.dpy, self.root, self.xss_info)
        return self.xss_info.contents.idle


class XFocus(object):
    """
    Wraps Xlib to find the focused window of an X session.
    """
    def __init__(self):
        self.display = Xlib.display.Display()

    def get_focused_window(self):
        """
        Returns a tuple of (list of focused window class strings, focused
        window name string), or (None, None), for the window that currently has
        focus in the current X session.
        """
        focus = self.display.get_input_focus()
        if focus.focus.get_wm_class() is None:
            # TODO Climb the tree until find something with a class property
            # (The immediate parent works well enough for now, for the few
            # cases I've encountered.)
            query = focus.focus.query_tree()
            window = query.parent if query else None
        else:
            window = focus.focus
        if not window:
            return (None, None)
        return (window.get_wm_class(), window.get_wm_name())


class Recorder(object):
    """
    Records the idle time and focused window.

    This implementation uses the Python `logging` module.
    """
    def __init__(self, filename=None, stream=False):
        """
        filename: the name of the file to append to
        stream: if True, also write the record to stderr
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if filename:
            full_path = os.path.expanduser(filename)
            rfh = handlers.TimedRotatingFileHandler(full_path, when='midnight')
            self.logger.addHandler(rfh)
        if stream:
            self.logger.addHandler(logging.StreamHandler())

    def write(self, idle_ms, window=None):
        """
        Writes an idle time integer and focused window info (a tuple, from
        `XFocus.get_focused_window`) to the logger.
        """
        now = datetime.datetime.now()
        loadavg = ','.join(str(l) for l in os.getloadavg())
        win_types, win_name = window or (None, None)
        type_str = ','.join(str(win_type) for win_type in (win_types or []))
        self.logger.info('%s %d %s %s %s',
                         now, idle_ms, loadavg, type_str, win_name or '')


def main(args):
    """
    Polls X for idle time and the focused window every `args.interval` seconds,
    writing the results to `args.filename`. If X is idle for more than
    `args.suspend` minutes, no results are written until the session returns
    from idle, at which point the idle duration is flushed to the log.
    """
    idle = XIdle()
    focus = XFocus()
    recorder = Recorder(filename=args.filename, stream=True)

    idle_limit_ms = args.suspend * 60 * 1000
    last_idle_ms = 0

    while True:
        time.sleep(args.interval)
        idle_ms = idle.get_idle_ms()

        # If we are returning from idle, record the total idle time, and if
        # we're not idle, record the focused window.
        if idle_ms < last_idle_ms and last_idle_ms >= idle_limit_ms:
            recorder.write(last_idle_ms)
        elif idle_ms < idle_limit_ms:
            focused_window = focus.get_focused_window()
            recorder.write(idle_ms, focused_window)

        last_idle_ms = idle_ms


if __name__ == '__main__':
    description = 'Record program usage from X11 window focus and idle time.'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-s', '--suspend', dest='suspend',
                        type=int, metavar='SUSPEND', default=15,
                        help='suspend logging when idle for SUSPEND minutes')
    parser.add_argument('-n', '--interval', dest='interval',
                        type=int, metavar='INTERVAL', default=5,
                        help='log an entry every INTERVAL seconds')
    parser.add_argument('-f', '--file', dest='filename',
                        type=str, metavar='FILE', default='~/.logs/xusing.log',
                        help='the file to write to')
    main(parser.parse_args())
