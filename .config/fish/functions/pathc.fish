function pathc
    echo "echo (realpath $argv[1]) | fish_clipboard_copy"
    echo (realpath $argv[1])
    echo (realpath $argv[1]) | fish_clipboard_copy
end
