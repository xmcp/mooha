#coding=utf-8

import requests
import re
from requests_toolbelt.multipart.encoder import MultipartEncoderMonitor

def fuck_urllib3_format_header_param(name, value):
    # the original one is buggy for non-ascii filenames
    # monkey patched
    def trim(x):
        for s in '"\\\r\n':
            x=x.replace(s,'_')
        return x
    
    return '%s="%s"'%(name, trim(value))

requests.packages.urllib3.fields.format_header_param=fuck_urllib3_format_header_param

from bs4 import BeautifulSoup
import ast
import datetime

class NoAttachment(Exception):
    __str__=__repr__=lambda:'该栏目没有附件'
class LoginFailed(Exception):
    def __init__(self,reason='登录失败'):
        self.reason=reason
    def __str__(self):
        return self.reason
    __repr__=__str__


class Mooha:
    base='http://moodle.rdfz.cn'
    parser='html.parser'
    
    def __init__(self):
        self.s=requests.Session()
        self.s.proxies={'http':''}

    def login(self,username,password):
        if username:
            res=self.s.post(
                self.base+'/login/index.php',
                data={'username':username,'password':password},
                allow_redirects=True,
            )
            if 'login' in res.url:
                raise LoginFailed()
        else:
            self.s.cookies.set('MoodleSession',password)
            res=self.s.get(self.base+'/')
            
        soup=BeautifulSoup(res.text,self.parser)
        self.sesskey=soup.find('script',text=re.compile(r'sesskey'))\
            .text.partition('sesskey')[2].partition(',')[0].split('"')[-2]
        self.uid=soup.find('a',attrs={'data-title':'profile,moodle'})\
            .get('href').rpartition('id=')[2]

    def repos(self,cached=True):
        def _all_repos():
            for x in soup.find_all('h3',class_='card-title'):
                if x.attrs['id'].startswith('instance-'):
                    yield {
                        'id': x.attrs['id'].split('-')[1],
                        'title': x.text
                    }
        
        res=self.s.get(self.base+'/my/index.php')
        soup=BeautifulSoup(res.text,self.parser)
        if cached:
            cache=[x['title'] for x in soup.find_all('span','mooha-articleid-cache')]
            yield from filter(lambda x:x['id'] in cache,_all_repos())
        else:
            yield from _all_repos()

    def _unlock(self):
        self.s.post(
            self.base+'/my/index.php',
            data={'edit':'1','sesskey':self.sesskey},
        )

    def _itemid(self,articleid):
        def get():
            res=self.s.get(
                self.base+'/my/index.php',
                params={'sesskey':self.sesskey,'bui_editid':articleid},
            )
            soup=BeautifulSoup(res.text,self.parser)
            if not soup.title or not soup.title.string.startswith('配置'):
                raise RuntimeError('未能打开配置页面: %s'%soup.title)
            try:
                return soup.find('input',attrs={'name':'config_text[itemid]'}).get('value')
            except AttributeError as e:
                raise NoAttachment()
    
        try:
            return get()
        except RuntimeError:
            self._unlock()
            return get()

    def _render_html(self,articleid,filelist):
        def sub():
            yield '<b><span class="mooha-articleid-cache" title="%s">%d 个文件</span></b><br>'\
                  %(articleid,len(filelist))
            for name,size,url in filelist:
                yield '<li><a href=javascript:window.open("%s")><b>%s</b> (%s)</a></li>'\
                    %(url,name,size)
        return ''.join(sub())
    
    def _save(self,articleid,itemid,extra={},text=None):
        default={
            'bui_editid':articleid,
            'bui_editingatfrontpage':'0',
            'bui_contexts':'0',
            'bui_pagetypepattern':'my-index',
            'bui_subpagepattern':'%@NULL@%',
            'sesskey':self.sesskey,
            '_qf__block_html_edit_form':'1',
            'mform_isexpanded_id_configheader':'1',
            'mform_isexpanded_id_whereheader':'0',
            'mform_isexpanded_id_onthispage':'0',
            'config_text[text]':text or self._render_html(articleid,[]),
            'config_text[format]':'1',
            'config_text[itemid]':itemid,
            'bui_visible':'1',
            'bui_region':'content',
        }
        default.update(extra)
        self.s.post(
            self.base+'/my/index.php',
            data=default,
        )

    def files(self,articleid):
        itemid=self._itemid(articleid)

        res=self.s.post(
            self.base+'/repository/draftfiles_ajax.php?action=list',
            data={
                'sesskey':self.sesskey,
                'filepath':'/',
                'itemid':itemid,
            },
        )
        return res.json()

    def upload(self,articleid,filename,content,callback=lambda *_:None):
        if not content:
            raise RuntimeError('不能上传空文件')
        itemid=self._itemid(articleid)
        monitor=MultipartEncoderMonitor.from_fields(
            fields={
                'repo_upload_file':(filename,content),
                'title':(None,''),
                'license':(None,'allrightsreserved'),
                'repo_id':(None,'3'),
                'p':(None,''),
                'page':(None,''),
                'env':(None,'filemanager'),
                'sesskey':(None,self.sesskey),
                'itemid':(None,itemid),
                'savepath':(None,'/'),
            },
            callback=callback,
        )
        res=self.s.post(
            self.base+'/repository/repository_ajax.php?action=upload',
            data=monitor,
            headers={'Content-Type':monitor.content_type},
        )
        assert 'error' not in res.json(), res.json()['error']
        self._save(articleid,itemid)

    def download(self,url,chunk_size=10000):
        return self.s.get(url,stream=True).iter_content(chunk_size)

    def delete(self,articleid,filename):
        itemid=self._itemid(articleid)
        self.s.post(
            self.base+'/repository/draftfiles_ajax.php?action=delete',
            data={
                'sesskey':self.sesskey,
                'filepath':'/',
                'itemid':itemid,
                'filename':filename,
            },
        )
        self._save(articleid,itemid)

    def rename(self,articleid,from_,to):
        itemid=self._itemid(articleid)
        self.s.post(
            self.base+'/repository/draftfiles_ajax.php?action=updatefile',
            data={
                'sesskey':self.sesskey,
                'filepath':'/',
                'newfilepath':'/',
                'itemid':itemid,
                'filename':from_,
                'newfilename':to,
                'newlicense':'allrightsreserved',
            },
        )
        self._save(articleid,itemid)
    
    def repo_rename(self,articleid,name):
        itemid=self._itemid(articleid)
        self._save(articleid,itemid,extra={'config_title':name})
    
    def repo_delete(self,articleid):
        self._unlock()
        res=self.s.post(
            self.base+'/my/index.php',
            data={
                'sesskey':self.sesskey,
                'bui_deleteid':articleid,
                'bui_confirm':1,
            },
            allow_redirects=False,
        )
        assert res.status_code==303, '删除仓库失败'
    
    def repo_create(self,name):
        self._unlock()
        res=self.s.post(
            self.base+'/my/index.php',
            params={'sesskey':self.sesskey,'bui_addblock':'html'},
            allow_redirects=False,
        )
        assert res.status_code==303, '创建仓库失败'
        
        res=self.s.get(self.base+'/my/index.php')
        soup=BeautifulSoup(res.text,self.parser)
        articleid=soup.find('span',text='配置 （新HTML版块） 版块')\
            .parent.attrs['href'].rpartition('=')[2]
        
        self._save(articleid,self._itemid(articleid),{'config_title':name})
    
    def inject_html(self,articleid):
        filelist=[(f['filename'],f['filesize'],f['url']) for f in self.files(articleid)['list']]
        self._save(articleid,self._itemid(articleid),text=self._render_html(articleid,filelist))

if __name__=='__main__':
    a=Mooha()
    print('a=Mooha()')
