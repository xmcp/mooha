from msvcrt import getch, kbhit
from moohalib import Mooha, NoAttachment
from getpass import getpass
from libconsole import cls, goto, cll
from progressbar import ProgressBar, Percentage, Bar, ETA, FileTransferSpeed
from colorama import *
import sys
import os
import math

init(autoreset=True) #colorama

moo=Mooha()
un=None
CHUNKSIZE=100000

for d in ['~/downloads','~/desktop','~/桌面']:
    if os.path.isdir(os.path.expanduser(d)):
        homedir=os.path.expanduser(d)
        break
else:
    homedir='/'

def friendly_size(b): # copied from progressbar/widgets.py
    FORMAT = '%6.2f%sB'
    PREFIXES = ' kMGTPEZY'
    
    power = int(math.log(b, 1000))
    scaled = b / 1000.**power
    return FORMAT % (scaled, PREFIXES[power])

original_input=input
def input(txt=''):
    deinit()
    init(autoreset=False)
    print(Style.BRIGHT+Fore.CYAN+txt+Fore.RESET,end='')
    res=original_input()
    deinit()
    init(autoreset=True)
    return res

class ConsoleUI:
    def __init__(self,prompt,title,items):
        items=list(items)
        self._redraw_arg=[prompt,title,None]
        
        self.prompt_loc=len(prompt)+1
        self.update_items(items)

    def holder(self,ind):
        return Back.GREEN+'-' if self.available[ind] else ' '

    def update_items(self,items):
        items=list(items)
        self._redraw_arg[2]=items
        self.names=[x[0] for x in items]
        self.selected_loc=0
        self.available={x:True for x in range(len(items))}
        self.search_str=''

    def update_available(self,new):
        old=self.available.copy()
        self.available=new
        for ind in range(len(self.names)):
            if old[ind]!=new[ind]:
                goto(4+ind,0)
                print(self.holder(ind))

    def redraw(self):
        prompt,title,items=self._redraw_arg
        cls()
        goto(0,0)
        print(Fore.CYAN+Style.BRIGHT+'%s %s'%(prompt,Fore.WHITE+self.search_str))
        goto(2,1)
        print(title)
        goto(4,0)
        if items:
            for ind,(name,description) in enumerate(items):
                print(self.holder(ind),end=' ')
                print(Fore.YELLOW+Style.BRIGHT+name,end=' ')
                print(Fore.WHITE+'(%s)'%description)
            self.select(self.selected_loc)
        else:
            print('(Empty)')
        goto(0,self.prompt_loc+len(self.search_str))

    def select(self,ind):
        if not self.names:
            return
        ind=ind%len(self.names)
        goto(4+self.selected_loc,0)
        print(self.holder(self.selected_loc))
        goto(4+ind,0)
        print(Fore.GREEN+Back.GREEN+Style.BRIGHT+'*')
        self.selected_loc=ind

    def _search(self):
        available={
            ind:(self.names[ind].lower().startswith(self.search_str.lower()))
            for ind in range(len(self.names))
        }
        if any(available.values()):
            self.update_available(available)
            for ind,okay in available.items():
                if okay:
                    self.select(ind)
                    break
            return True
        else:
            return False

    def insert(self,char):
        self.search_str+=char
        if self._search():
            goto(0,self.prompt_loc+len(self.search_str)-1)
            print(Style.BRIGHT+char)
        else:
            self.search_str=self.search_str[:-1]

    def cancel(self):
        cll(0,self.prompt_loc)
        self.search_str=''
        self.update_available({x:True for x in range(len(self.names))})

    def backspace(self):
        if self.search_str:
            self.search_str=self.search_str[:-1]
            self._search()
            goto(0,self.prompt_loc+len(self.search_str))
            print(' ')

    def handle(self,hotkeys):
        while True:
            ch=getch()
            if self.search_str and ch==b'\x1b': #esc
                self.cancel()
            elif ch in hotkeys:
                return (ch,self.selected_loc)
            elif ch==b'\xe0' and kbhit(): #cursor
                ch_=getch()
                if ch_==b'H': #up
                    self.select(self.selected_loc-1)
                elif ch_==b'P': #down
                    self.select(self.selected_loc+1)
                elif ch_==b'K': #left
                    self.select(0)
                elif ch_==b'M': #right
                    self.select(-1)
            elif ch==b'\x08': #backspace
                self.backspace()
            else: #search
                self.insert(ch.decode(errors='replace'))
            goto(0,self.prompt_loc+len(self.search_str))

class ProgressUI:
    def __init__(self,kind,items):
        cls()
        goto(0,0)
        print(Fore.CYAN+Style.BRIGHT+' * %s Files...'%kind)
        
        total_size=0
        self.subbar=[]
        self.cur_ind=0
        self.cur_transfered=0
        self.total_transfered=0

        fnlen=max([len(item[0]) for item in items])
        szlen=max([len(item[2]) for item in items])
        for ind,(name,size,dispsize) in enumerate(items):
            goto(4+ind,0)
            total_size+=size
            self.subbar.append(ProgressBar(
                widgets=[Fore.YELLOW+Style.BRIGHT+name.ljust(fnlen+1,' ')+Style.RESET_ALL,' ',Bar(marker='#'),dispsize.rjust(szlen+1)],
                maxval=size,
                fd=sys.stdout,
                delta=14,
            ).start())

        goto(2,0)
        self.mainbar=ProgressBar(
            widgets=[Fore.WHITE+Style.BRIGHT,Percentage(),Style.RESET_ALL,' ',Bar(marker='>'),' ',Style.BRIGHT,ETA(),Style.NORMAL,' ',FileTransferSpeed()],
            maxval=total_size,
            fd=sys.stdout,
            delta=23,
        ).start()

    def update(self,delta):
        self.cur_transfered+=delta
        self.total_transfered+=delta
        self.cur_transfered=min(self.cur_transfered,self.subbar[self.cur_ind].maxval)
        self.total_transfered=min(self.total_transfered,self.mainbar.maxval)
        
        goto(2,0)
        self.mainbar.update(self.total_transfered)
        goto(4+self.cur_ind,0)
        self.subbar[self.cur_ind].update(self.cur_transfered)

    def complete(self):
        self.total_transfered+=self.subbar[self.cur_ind].maxval-self.cur_transfered

        goto(2,0)
        self.mainbar.update(self.total_transfered)
        goto(4+self.cur_ind,0)
        self.subbar[self.cur_ind].finish()

        self.cur_ind+=1
        self.cur_transfered=0
        
def login():
    global un
    un=input('Username: ')
    print(Style.BRIGHT+Fore.CYAN+'Password: '+Fore.RESET,end='')
    pw=getpass('')
    try:
        moo.login(un,pw)
    except Exception as e:
        print('[Error] %s %s'%(type(e),e))
        return False
    else:
        return True

def download(files,destination):
    ui=ProgressUI('Download',[(file['filename'],file['size'],file['filesize']) for file in files])
    for file in files:
        with open(os.path.join(destination,file['filename']),'wb') as f:
            for chunk in moo.download(file['url'],CHUNKSIZE):
                f.write(chunk)
                ui.update(len(chunk))
        ui.complete()

def reuse_download_repo(repo_title,files):
    prefered_path=os.path.join(homedir,repo_title)
    if os.path.isfile(prefered_path):
        prefered_path=homedir
    elif not os.path.exists(prefered_path):
            os.mkdir(prefered_path)
    
    download(files,prefered_path)
    os.startfile(prefered_path)

def upload(fns,destination):
    def getstat():
        for fn in fns:
            _sz=os.path.getsize(fn)
            yield [os.path.basename(fn),_sz,friendly_size(_sz)]

    def callback(encoder):
        nonlocal transfered
        ui.update(encoder.bytes_read-transfered)
        transfered=encoder.bytes_read
    
    ui=ProgressUI('Upload',list(getstat()))
    for fn in fns:
        with open(fn,'rb') as f:
            transfered=0
            moo.upload(destination,os.path.basename(fn),f,callback)
            ui.complete()

def reuse_upload(repo_id):
    cll(2,0)
    goto(2,0)
    fn=input(' Filename or Directory: ')
    if fn:
        if fn[0]=='"' and fn[-1]=='"':
            fn=fn[1:-1]
        if os.path.isfile(fn):
            upload([fn],repo_id)
        elif os.path.isdir(fn):
            upload([os.path.join(fn,f) for f in os.listdir(fn) if os.path.isfile(os.path.join(fn,f))],repo_id)

def genitems(repos):
    for x in repos:
        yield (x['title'],x['id'])
def genfiles(files):
    for x in files:
        yield (x['filename'],x['filesize'])

def refresh_main():
    global repos
    repos=list(moo.repos())
    ui_repos.update_items(genitems(repos))
def refresh_sub():
    global files
    files=moo.files(repo_id)['list']
    ui_sub.update_items(genfiles(files))

def wp(key,txt): #wrap text
    return Back.RED+Style.BRIGHT+'['+key+']'+Style.RESET_ALL+Style.BRIGHT+' '+txt+' '

print('Mooha CLI\n')
while True:
    if login():
        break
print('Fetching repos...')
repos=list(moo.repos())

ui_repos=ConsoleUI('>',
    wp('Enter','List Files')+wp('Space','Upload')+wp('Tab','Options...'),
    genitems(repos)
)
while True:
    ui_repos.redraw()
    key,ind=ui_repos.handle([b'\r',b'\t',b'\x1b',b' '])

    if key==b'\x1b': #quit
        break
    
    elif key==b'\r': #list files
        cll(2,0)
        goto(2,0)
        print('Fetching files...')
        repo_title,repo_id=repos[ind]['title'],repos[ind]['id']
        files=moo.files(repo_id)['list']
        
        ui_sub=ConsoleUI('%s >'%repo_title,
            wp('Enter','Download & Open')+wp('Space','Download')+wp('Tab','Options...'),
            genfiles(files)
        )
        while True:
            ui_sub.redraw()
            key,ind=ui_sub.handle([b'\x1b',b'\t',b'\r',b' '])
            
            if key==b'\x1b': #quit
                break
            
            elif key==b'\t': #file options
                cll(2,0)
                goto(2,0)
                print(' < '+wp('Space','Rename')+wp('X','Delete')+Style.RESET_ALL+'| '+wp('N','Upload')+wp('Enter','Download Repo'))
                key=getch().decode(errors='replace').lower()

                if key==' ': #rename
                    cll(2,0)
                    goto(2,0)
                    new_name=input('Rename file to: ')
                    if new_name:
                        moo.rename(repo_id,files[ind]['filename'],new_name)
                        refresh_sub()

                elif key=='x': #delete
                    cll(2,0)
                    goto(2,0)
                    print(' WARNING: "%s" will be deleted (y/n)'%files[ind]['filename'])
                    if getch() in [b'y',b'Y']:
                        moo.delete(repo_id,files[ind]['filename'])
                        refresh_sub()

                elif key=='n': #upload
                    reuse_upload(repo_id)
                    refresh_sub()

                elif key=='\r': #download repo
                    reuse_download_repo(repo_title,files)
            
            elif key==b' ': #download
                download([files[ind]],homedir)
                os.startfile(homedir)

            elif key==b'\r': #download and open
                download([files[ind]],homedir)
                os.startfile(os.path.join(homedir,files[ind]['filename']))

    elif key==b'\t': #repo options
        cll(2,0)
        goto(2,0)
        print(' < '+wp('Space','Rename')+wp('Enter','Download Repo')+wp('X','Delete')+Style.RESET_ALL+'| '+wp('N','Create Repo'))
        key=getch().decode(errors='replace').lower()

        if key==' ': #rename
            cll(2,0)
            goto(2,0)
            repo_name=input(' Rename repo to: ')
            if repo_name:
                moo.repo_rename(repos[ind]['id'],repo_name)
                refresh_main()

        elif key=='x': #delete
            cll(2,0)
            goto(2,0)
            print(' WARNING: "%s" will be deleted (y/n)'%repos[ind]['title'])
            if getch() in [b'y',b'Y']:
                moo.repo_delete(repos[ind]['id'])
                refresh_main()

        elif key=='\r': #download repo
            cll(2,0)
            goto(2,0)
            print(' Fetching files...')
            reuse_download_repo(repos[ind]['title'],moo.files(repos[ind]['id'])['list'])

        elif key=='n': #create
            cll(2,0)
            goto(2,0)
            repo_name=input(' Create repository: ')
            if repo_name:
                moo.repo_create(repo_name)
                refresh_main()

        elif key=='i': #invalidate cache
            cll(2,0)
            goto(2,0)
            print(' Invalidating cache... Wait a moment.')
            repos=list(moo.repos(cached=False))
            for ind,repo in enumerate(repos):
                try:
                    moo.files(repo['id'])
                except NoAttachment:
                    pass
                else:
                    moo.inject_html(repo['id'])
            refresh_main()

    elif key==b' ': #upload
        reuse_upload(repos[ind]['id'])

#normal quit
cls()
