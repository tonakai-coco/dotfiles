function clip
    echo "echo $argv[1] | fish_clipboard_copy"
    echo $argv[1]
    echo $argv[1] | fish_clipboard_copy
end
