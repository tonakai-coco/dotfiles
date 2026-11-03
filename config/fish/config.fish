if status is-interactive
    # Commands to run in interactive sessions can go here

    # Disable flow control (XON/XOFF) to allow Ctrl+Q as a keybind in WezTerm
    stty -ixon

    zoxide init fish | source

    if command -q wtn
        wtn init fish | source
    end
end

# abbr.fishを読み込む
source ~/.config/fish/abbr.fish
