function cd --description "Change directory and list files"
    builtin cd $argv
    and exa -l -g --icons
end
