set number
set expandtab
set smartindent
set shiftwidth=4
set softtabstop=4
set autochdir
set encoding=utf-8
set fileencoding=utf-8
set fileencodings=utf-8,cp932
set clipboard+=unnamed,unnamedplus
set ruler
set cursorline
set hlsearch
set laststatus=2
set wildmenu
set encoding=utf8
syntax enable

"LeaderキーをSpaceに設定
let mapleader = "\<Space>"

"カーソル上の単語を置換
nnoremap <expr> S* ':%s/\<' . expand('<cword>') . '\>/'

"下部分にターミナルウィンドウを作る
function! Myterm()
    split
    wincmd j
    resize 5
    terminal
    wincmd k
endfunction
command! Myterm call Myterm()

"起動時にターミナルウィンドウを設置
if has('vim_starting')
    " Myterm
endif

"上のエディタウィンドウと下のターミナルウィンドウ(ターミナル挿入モード)を行き来
tnoremap <C-t> <C-\><C-n><C-w>k
nnoremap <C-t> <C-w>ji
"ターミナル挿入モードからターミナルモードへ以降
tnoremap <Esc> <C-\><C-n>

"ファイルを開き直したときに実行コマンドを再設定
"autocmd BufNewFile,BufRead * Setup

cnoremap init :<C-u>edit $MYVIMRC<CR>  "init.vim呼び出し
noremap <Space>s :source $MYVIMRC<CR>  " init.vim読み込み
noremap <Space>w :<C-u>w<CR>  " ファイル保存
noremap <Space>q :<C-u>q<CR>  " ファイルClose
inoremap <silent> jj <Esc>
inoremap <C-h> <Left>
inoremap <C-l> <Right>
inoremap <C-k> <Up>
inoremap <C-j> <Down>
nmap <C-a> gg<S-v>G
noremap S* :%s/

" New tab
nmap te :tabedit
" Close tab
nmap td :tabclose

" Split window
nmap ss :split<Return><C-w>w
" Move window
map sh <C-w>h
map sk <C-w>k
map sj <C-w>j
map sl <C-w>l

" Resize window
nmap <C-w><left> <C-w><
nmap <C-w><right> <C-w>>
nmap <C-w><up> <C-w>+
nmap <C-w><down> <C-w>-

"// PLUGIN SETTINGS
call plug#begin('~/.config/nvim/plugged')

Plug 'vim-airline/vim-airline'
Plug 'vim-airline/vim-airline-themes'
Plug 'tpope/vim-commentary'
Plug 'neoclide/coc.nvim', {'branch': 'release'}
Plug 'ryanoasis/vim-devicons'
Plug 'preservim/nerdtree'

call plug#end()

" Airline SETTINGS
let g:airline_powerline_fonts = 1
let g:airline#extensions#tabline#enabled = 1
nmap <C-p> <Plug>AirlineSelectPrevTab
nmap <C-n> <Plug>AirlineSelectNextTab

" Coc
highlight CocErrorSign ctermfg=15 ctermbg=196
highlight CocWarningSign ctermfg=0 ctermbg=172

nmap <silent> <space><space> :<C-u>CocList<cr>
nmap <silent> <space>h :<C-u>call CocAction('doHover')<cr>
nmap <silent> <space>df <Plug>(coc-definition)
nmap <silent> <space>rf <Plug>(coc-references)
nmap <silent> <space>rn <Plug>(coc-rename)
nmap <silent> <space>fmt <Plug>(coc-format)

" nerdtree
nmap <space>e :NERDTreeToggle<CR>
