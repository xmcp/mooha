#coding=utf-8
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox,filedialog,simpledialog,font

import moohalib as mooha
import threading
import os, sys

def exceptor(*args):
    if not __file__:
        import traceback
        tb=traceback.format_exception(*args)
        messagebox.showerror('出现异常','要是看不懂就算了：\n'+'\n'.join(tb))
sys.excepthook=exceptor

tk=Tk()
tk.title('Mooha GUI')
tk.columnconfigure(0,weight=1)
tk.rowconfigure(1,weight=1)

CHUNK=100000
moo=mooha.Mooha()
filedetail={}
inarticle={}
children={}
unvar=StringVar()
pwvar=StringVar()
msg=StringVar(value='您尚未登录')

def procsize(size):
    b=size%1024
    k=int(size/1024)%1024
    m=int(size/1024/1024)
    if m:
        return '%dM %dK %dB'%(m,k,b)
    elif k:
        return '%dK %dB'%(k,b)
    else:
        return '%dB'%b

class ProgressDialog:
    def __init__(self,kind):
        self.tl=Toplevel(tk)
        self.tl.title('%s文件 - Mooha'%kind)
        self.tl.columnconfigure(0,weight=1)
        self.kind=kind

        self.total=0
        self.completed=0
        self.allsize=0
        self.completedbytes=0
        self.size={}
        self.downloaded={}
        self.progress={}
        self.bar=Progressbar(self.tl,orient=HORIZONTAL,length=100,mode='determinate')
        self.current=None
        
        self.bar.grid(row=0,column=0,sticky='we')

    @staticmethod
    def _proc(size):
        if int(size/1024/1024):
            return '%.1f MB'%(size/1024/1024)
        elif int(size/1024):
            return '%.1f KB'%(size/1024)
        else:
            return '%d B'%size

    def additem(self,name,size):
        self.total+=1
        f=Frame(self.tl)
        f.grid(row=self.total,column=0,sticky='we')
        f.columnconfigure(1,weight=1)

        self.size[name]=size
        self.allsize+=size
        self.downloaded[name]=StringVar(value='0 B')
        self.progress[name]=StringVar(value='等待中')

        Label(f,text=os.path.basename(name),font=font.Font(weight=font.BOLD))\
            .grid(row=0,column=0)
        Label(f,text='  ').grid(row=0,column=1)

        Label(f,textvariable=self.downloaded[name]).grid(row=0,column=2)
        Label(f,text=' / %s'%self._proc(size)).grid(row=0,column=3,sticky='we')
        Label(f,textvariable=self.progress[name],foreground='#0000ff',width=7).grid(row=0,column=4,sticky='e')

    def start(self,name):
        self.current=name
        self.progress[self.current].set('0.0%')

    def update(self,downloaded):
        self.downloaded[self.current].set(self._proc(downloaded))
        self.progress[self.current].set('%.1f%%'%(100*downloaded/self.size[self.current]))
        self.bar['value']=100*(self.completedbytes+downloaded)/self.allsize

    def complete(self):
        self.completed+=1
        self.completedbytes+=self.size[self.current]
        
        self.downloaded[self.current].set(self._proc(self.size[self.current]))
        self.progress[self.current].set('完成')
        self.bar['value']=100*self.completedbytes/self.allsize

        if self.completed==self.total:
            self.tl.title('%s完成 - Mooha'%self.kind)
            msg.set('%s完成'%self.kind)
            self.tl.after(500,lambda *_:self.tl.destroy())

    def destroy(self):
        self.tl.destroy()

def auth(*_):
    unentry.state(['disabled'])
    pwentry.state(['disabled'])
    authbtn.state(['disabled'])
    msg.set('正在登录...')
    tk.update_idletasks()
    try:
        moo.login(unvar.get(),pwvar.get())
    except mooha.LoginFailed:
        msg.set('登录失败')
        unentry.state(['!disabled'])
        pwentry.state(['!disabled'])
        authbtn.state(['!disabled'])
    except Exception as e:
        msg.set('[登录失败] %r'%e)
        unentry.state(['!disabled'])
        pwentry.state(['!disabled'])
        authbtn.state(['!disabled'])
        raise
    else:
        pwvar.set('')
        authbtn['text']='注销'
        authbtn['command']=logout
        authbtn.state(['!disabled'])
        for btn in action_btns:
            btn.state(['!disabled'])
        tk.update()
        refresh()

def logout(*_):
    global moo
    moo=mooha.Mooha()
    
    unentry.state(['!disabled'])
    pwentry.state(['!disabled'])
    authbtn['text']='登录'
    authbtn['command']=auth
    tree.delete(*tree.get_children())
    for btn in action_btns:
        btn.state(['disabled'])
    msg.set('注销成功')

def refresh(*_):
    msg.set('正在获取文件列表...')
    tree.delete(*tree.get_children())
    filedetail.clear()
    inarticle.clear()
    tk.update()

    try:
        repos=list(moo.repos())
    except Exception as e:
        msg.set('[仓库列表获取失败] %r'%e)
        raise

    if not repos:
        if messagebox.askyesno(
                'Mooha',
                '您的账户中没有检测到任何可用的仓库。\n\n'
                '第一次使用 Mooha 的新用户请点击右下角的“新仓库”；\n'
                '从旧版 Mooha 升级的老用户需要重建 ArticleID 缓存。\n\n'
                '现在重建缓存吗？'):
            return fixit(sure=True)
    for ind,repo in enumerate(repos):
        try:
            msg.set('正在获取文件列表 (%d/%d)...'%(ind+1,len(repos)))
            tk.update()
            files=moo.files(repo['id'])
        except mooha.NoAttachment:
            pass
        except Exception as e:
            msg.set('[%s 的文件列表获取失败] %r'%(repo['title'],e))
            raise
        else:
            parent=tree.insert('','end',text=repo['title'],values=\
                ('(%d) %s'%(files['filecount'],procsize(files['filesize'])),''))
            tree.item(parent,open=len(files['list'])<=7)
            inarticle[parent]=repo['id']
            children[parent]=files['list']
            for file in files['list']:
                fileid=tree.insert(parent,'end',text=file['filename'],values=\
                    (procsize(file['size']),file['datemodified_f']))
                filedetail[fileid]=file
                inarticle[fileid]=repo['id']
        finally:
            tk.update()
    msg.set('就绪')

def down_callback(*_):
    def download_single(*_):
        def real_download(name,size):
            transed=0
            msg.set('正在下载 %s...'%filedetail[item]['filename'])
            window=ProgressDialog('下载')
            window.additem(name,size)
    
            try:
                with open(fn,'wb') as f:
                    window.start(name)
                    for chunk in moo.download(filedetail[item]['url'],CHUNK):
                        f.write(chunk)
                        transed+=CHUNK
                        window.update(transed)
            except Exception as e:
                msg.set('[下载失败] %r'%e)
                raise
            else:
                window.complete()
    
        item=tree.focus()
        fn=filedialog.asksaveasfilename(
            initialfile=filedetail[item]['filename'],
            confirmoverwrite=True,
            title='下载文件……'
        )
        if fn:
            threading.Thread(
                target=real_download,
                args=[filedetail[item]['filename'],filedetail[item]['size']],
                ).start()
    
    def download_group(items):
        def real_download(dn):
            window=ProgressDialog('下载')
            for item in items:
                window.additem(item['filename'],item['size'])
            for item in items:
                transed=0
                try:
                    with open(os.path.join(dn,item['filename']),'wb') as f:
                        window.start(item['filename'])
                        for chunk in moo.download(item['url'],CHUNK):
                            f.write(chunk)
                            transed+=CHUNK
                            window.update(transed)
                except Exception as e:
                    msg.set('[下载失败] %r'%e)
                    window.destroy()
                    raise
                else:
                    window.complete()
    
        dn=filedialog.askdirectory(title='批量下载：')
        if dn:
            prefered_path=os.path.join(dn,tree.item(item)['text'])
            if os.listdir(dn) and not os.path.isfile(prefered_path):
                if not os.path.exists(prefered_path):
                    os.mkdir(prefered_path)
                dn=prefered_path
            threading.Thread(
                target=real_download,
                args=[dn],
            ).start()    
    
    item=tree.focus()
    if item in filedetail:
        download_single()
    elif item in inarticle:
        if children[item]:
            download_group(children[item])
        else:
            msg.set('仓库为空')
    else:
        msg.set('文件不存在')

def delete():
    def delete_single():
        if messagebox.askokcancel('删除文件','确定删除 %s 吗？'%filedetail[item]['filename']):
            msg.set('正在删除 %s...'%filedetail[item]['filename'])
            tk.update()
            try:
                moo.delete(inarticle[item],filedetail[item]['filename'])
            except Exception as e:
                msg.set('[删除失败] %r'%e)
                raise
            else:
                moo.inject_html(inarticle[item])
                refresh()
                
    def delete_group():
        if messagebox.askokcancel('删除仓库','确定仓库 %s 和其中的所有文件吗？'%(tree.item(item)['text'])):
            msg.set('正在删除 %s...'%(tree.item(item)['text']))
            tk.update()       
            try:
                moo.repo_delete(inarticle[item])
            except Exception as e:
                msg.set('[删除失败] %r'%e)
                raise
            else:
                refresh()
                
    item=tree.focus()
    if item in filedetail:
        delete_single()
    elif item in inarticle:
        delete_group()
    else:
        msg.set('文件不存在')

def rename():
    def rename_single():
        oldfn=filedetail[item]['filename']
        newfn=simpledialog.askstring('新文件名','将 %s 重命名为：'%oldfn)
        if newfn:
            msg.set('正在重命名 %s...'%filedetail[item]['filename'])
            tk.update()            
            try:
                moo.rename(inarticle[item],oldfn,newfn)
            except Exception as e:
                msg.set('[重命名失败] %r'%e)
                raise
            else:
                moo.inject_html(inarticle[item])
                refresh()
    
    def rename_repo():
        name=simpledialog.askstring('新仓库名','将仓库 %s 重命名为：'%(tree.item(item)['text']))
        if name:
            msg.set('正在重命名 %s...'%(tree.item(item)['text']))
            tk.update()            
            try:
                moo.repo_rename(inarticle[item],name)
            except Exception as e:
                msg.set('[重命名失败] %r'%e)
                raise  
            else:
                refresh()
    
    item=tree.focus()
    if item in filedetail:
        rename_single()
    elif item in inarticle:
        rename_repo()
    else:
        msg.set('文件不存在')

def upload():
    def real_upload(fns):
        def callback(encoder):
            window.update(encoder.bytes_read)

        window=ProgressDialog('上传')
        for fn in fns:
            window.additem(fn,os.path.getsize(fn))
        for fn in fns:
            with open(fn,'rb') as f:
                window.start(fn)
                try:
                    moo.upload(inarticle[item],os.path.basename(fn),f,callback)
                except Exception as e:
                    msg.set('[上传失败] %r'%e)
                    window.destroy()
                    raise
                window.complete()

        moo.inject_html(inarticle[item])
        refresh()

    item=tree.focus()
    if item in inarticle:
        fns=filedialog.askopenfilename(title='上传文件...',multiple=True)
        if fns:
            threading.Thread(
                target=real_upload,
                args=[fns],
            ).start()

    else:
        msg.set('没有选择仓库')

def newrepo():
    name=simpledialog.askstring('仓库名','要创建的仓库名称：')
    if name:
        msg.set('正在创建仓库...')
        tk.update()            
        try:
            moo.repo_create(name)
        except Exception as e:
            msg.set('[创建失败] %r'%e)
            raise
        else:
            refresh()

def fixit(*_,sure=False):
    if sure or messagebox.askokcancel('Mooha','重建 ArticleID 缓存？'):
        msg.set('正在重建缓存...')
        tk.update()
        repos=list(moo.repos(cached=False))
        for ind,repo in enumerate(repos):
            msg.set('正在重建缓存 (%d/%d)...'%(ind+1,len(repos)))
            tk.update()
            try:
                moo.files(repo['id'])
            except mooha.NoAttachment:
                pass
            else:
                moo.inject_html(repo['id'])
        refresh()

authf=Frame(tk)
authf.grid(row=0,column=0,sticky='we')
authf.columnconfigure(4,weight=1)

Label(authf,text='用户名：').grid(row=0,column=0)
unentry=Entry(authf,textvariable=unvar)
unentry.grid(row=0,column=1)
unentry.bind('<Return>',lambda *_:authbtn.invoke())
Label(authf,text='密码：').grid(row=0,column=2)
pwentry=Entry(authf,textvariable=pwvar,show='*')
pwentry.grid(row=0,column=3)
pwentry.bind('<Return>',lambda *_:authbtn.invoke())
Label(authf,text=' ').grid(row=0,column=4,sticky='we')
authbtn=Button(authf,text='登录',command=auth)
authbtn.grid(row=0,column=5)

treef=Frame(tk)
treef.grid(row=1,column=0,sticky='nswe')
treef.rowconfigure(0,weight=1)
treef.columnconfigure(0,weight=1)

tree=Treeview(treef,columns=('size','time'),height=12)
tree.grid(row=0,column=0,sticky='nswe')
sbar=Scrollbar(treef,orient=VERTICAL,command=tree.yview)
sbar.grid(row=0,column=1,sticky='ns')
tree.configure(yscrollcommand=sbar.set)

tree.heading('size',text='大小')
tree.heading('time',text='修改时间')
tree.column('#0',width=250,anchor='w')
tree.column('size',width=150,anchor='e')
tree.column('time',width=150,anchor='center')
tree.bind('<Double-Button-1>',down_callback)

actionf=Frame(tk)
actionf.grid(row=2,column=0,sticky='we')
action_btns=[
    Button(actionf,text='刷新',command=refresh,width=5),
    Button(actionf,text='下载',command=down_callback,width=5),
    Button(actionf,text='重命名',command=rename,width=5),
    Button(actionf,text='删除',command=delete,width=5),
    Button(actionf,text='上传',command=upload,width=5),
    Button(actionf,text='新仓库',command=newrepo,width=5),
]
for ind,btn in enumerate(action_btns):
    actionf.columnconfigure(ind,weight=1)
    btn.state(['disabled'])
    btn.grid(row=0,column=ind,sticky='we')

Label(tk,textvariable=msg).grid(row=3,column=0,sticky='we')

tree.bind('<Triple-Button-3>',fixit)
mainloop()
