from msvcrt import getch, kbhit
from moohalib import Mooha
from getpass import getpass
from libconsole import cls, goto, cll

moo=Mooha()
un=None

class ConsoleUI:
    def __init__(self,prompt,title,items):
        items=list(items)
        self._redraw_arg=[prompt,None,None]
        
        self.prompt_loc=len(prompt)+1
        self.update_items(title,items)

    def holder(self,ind):
        return '-' if self.available[ind] else ' '

    def update_items(self,title,items):
        items=list(items)
        self._redraw_arg[1]=title
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
        print(prompt)
        goto(2,0)
        print(title)
        goto(4,0)
        if items:
            for ind,(name,description) in enumerate(items):
                print('%s %s (%s)'%(self.holder(ind),name,description))
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
        print('*')
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
            print(char)
        else:
            self.search_str=self.search_str[:-1]

    def cancel(self):
        cll(0,self.prompt_loc)
        self.search_str=''
        self.update_available({x:True for x in range(len(self.items))})

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

def login():
    moo.login('2011011108','1234567890')
    return True
    #todo: delete these
    global un
    un=input('Username: ')
    pw=getpass('Password: ')
    try:
        moo.login(un,pw)
    except Exception as e:
        print('[Error] %s'%e)
        return False
    else:
        return True

if __name__=='__main__':
    def genitems(repos):
        for x in repos:
            yield (x['title'],x['id'])
    def genfiles(files):
        for x in files:
            yield (x['filename'],x['filesize'])
    
    print('Mooha CLI\n')
    while True:
        if login():
            break
    print('Fetching repos...')
    repos=list(moo.repos())

    ui_repos=ConsoleUI('>','[%s] %d repos (Press Tab to Create)'%(un,len(repos)),genitems(repos))
    while True:
        ui_repos.redraw()
        key,ind=ui_repos.handle([b'\r',b'\t',b'\x1b'])

        if key==b'\x1b': #quit
            break
        
        elif key==b'\r': #go into repo
            cll(2,0)
            goto(2,0)
            print('Fetching files...')
            repo_title,repo_id=repos[ind]['title'],repos[ind]['id']
            files=moo.files(repo_id)['list']
            
            ui_sub=ConsoleUI('<[Esc]','[%s] %d files (Press Tab to Upload)'%(repo_title,len(files)),genfiles(files))
            while True:
                ui_sub.redraw()
                key,ind=ui_sub.handle([b'\x1b',b'\t',b'\r'])
                
                if key==b'\x1b': #quit
                    break
                
                elif key==b'\t': #upload
                    pass
                
                elif key==b'\r': #file info
                    pass

        elif key==b'\t': #create repo
            cll(2,0)
            goto(2,0)
            repo_name=input('Create repository: ')
            if repo_name:
                moo.repo_create(repo_name)
                repos=list(moo.repos())
                ui_repos.update_items('[%s] %d repos (Press Tab to Create)'%(un,len(repos)),genitems(repos))
