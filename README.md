# `xusing`

This project is basically a quick hack using Python and X to figure out what
I'm spending time on when I'm using a computer. The script repeatedly polls the
name and class of the focused window in X and the idle time from the
XScreenSaver extension and writes it to an auto-rotating log file.

Additionally, some configuration of `tmux` and `zsh` gives me some insight into
what I'm running in a terminal, by setting the window name of the terminal
window in X to indicate what I'm doing in that terminal.

I'm basically kicking the tires and seeing how useful it is, and maybe at some
point in the near future I'll add some error handling and something to crunch
on the log files.


## Setup

Clone it, then `pip install -r requirements.txt`, ideally from a virtualenv.
Run `python src/xusing.py --help`. There's no `setup.py` yet.


## Tips for better terminal cooperation

### Vim

If you use terminal Vim, consider adding the following to your `.vimrc` to
allow Vim to set the title of the terminal window in X:

    let &titlestring = expand("%:t")
    if &term == "screen"
        set t_ts=^[]2;
        set t_fs=^[\\
    endif
    set title

(To get the `^[` character, press Ctrl-V then Esc.)

These settings configure Vim to set the Tmux pane title, rather than the window
title. To set the window title instead, use `set t_ts=^[k`.

### Tmux

Tmux can update the terminal window title automatically as panes and windows
change. To do so, add the following to your `.vimrc`:

    set -g set-titles on
    set -g set-titles-string "#h:#S:#W #T"
    set -g automatic-rename on


This sets the window title to include (from left to right) hostname, session
name, window title, and pane title. `man 1 tmux` has more info on the format
characters for `set-titles-string`.

### Zsh

In your `.zshrc`, the `preexec` hook can set the `tmux` pane title to the
command that's about to run, and the `precmd` hook (which runs before the
prompt is displayed, effectively after a command runs) can set the `tmux` pane
title back to a string that indicates that we're back in the shell.

    preexec() {
      if [ "$(id -u)" -ne 0 ]
      then
        printf '\033]2;%s\033\\' "$1"
      fi
    }

    precmd() {
        printf '\033]2;%s\033\\' "zsh $PWD"
    }
